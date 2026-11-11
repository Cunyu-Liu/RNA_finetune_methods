import argparse
import json
import random
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import numpy as np
import torch

from rnafteval import valplateau as vp
from rnafteval.finetune_mrl import batches, encode_seqs
from rnafteval.models import load_model
from rnafteval.splits import prepare_convergence_splits
from rnafteval.strategies import apply_strategy, make_head
from rnafteval.tasks import mrl as mrl_task


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--artifact-dir', type=Path, required=True)
    parser.add_argument('--reference-result', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    parser.add_argument('--device', type=int, default=0)
    args = parser.parse_args()
    assert torch.cuda.is_available(), 'CUDA_UNAVAILABLE_ABORT'
    torch.cuda.set_device(args.device)
    device = f'cuda:{args.device}'
    args.output_dir.mkdir(parents=True, exist_ok=True)
    plateau = json.loads((args.artifact_dir / 'plateau.json').read_text())
    reference = json.loads(args.reference_result.read_text())
    rid = plateau['run_id']
    assert rid.startswith('ft_rinalmo') and rid.endswith('_bestval_v1')
    assert plateau['status'] == 'CONVERGED'
    assert plateau['stop_reason'] == 'validation_no_improvement_patience'
    assert plateau['best_epoch'] == 0
    assert plateau['protocol'] == 'bestval_v1'
    seed = 101
    split_name = reference['split']
    model = reference['model']
    assert reference['n_train'] == 20000
    torch.manual_seed(seed)
    random.seed(seed)
    if split_name == 'family':
        import pyarrow.parquet as pq
        table = pq.read_table('/root/rna-ft-eval/data/family_splits/mrl.parquet').to_pydict()
        records = [{'seq': s, 'label': float(label), 'cluster': cluster}
                   for s, label, cluster in zip(table['seq'], table['label'], table['cluster_id'])]
        train = [row for row, part in zip(records, table['split']) if part == 'train']
        test = [row for row, part in zip(records, table['split']) if part == 'test']
        val = [row for row, part in zip(records, table['split']) if part == 'val'] or None
    else:
        split = mrl_task.load_official_split('/root/rna-ft-eval/data/beacon_raw/mean-ribosome-loading/data')
        train, test = split['train'], split['test']
        val = split.get('validation')
    train, val, test, evidence = prepare_convergence_splits(
        train, val, test, n_train=20000,
        sample_seed=seed, family=split_name == 'family',
        validation_source='family_validation' if split_name == 'family' else 'official_validation',
        evidence_path=str(args.output_dir / f'{rid}_split_evidence.json'),
        protocol='bestval_v1')
    assert evidence == reference['data_evidence'], 'split evidence mismatch'
    assert len(test) == reference['n_test']
    spec, tokenizer, backbone = load_model(model, device)
    with torch.no_grad():
        probe = encode_seqs(tokenizer, [train[0]['seq']], device, 64)
        width = backbone(**probe).last_hidden_state.shape[-1]
    backbone, _ = apply_strategy(backbone, 'full', lora_rank=8)
    head = make_head('per-seq', width, 1).to(device)
    checkpoint = args.artifact_dir / 'best.ckpt'
    state = torch.load(checkpoint, map_location=device, weights_only=True)
    assert state['best_epoch'] == plateau['best_epoch']
    vp.load_backbone_state_dict(backbone, state['backbone'])
    head.load_state_dict(state['head'])
    backbone.eval()
    head.eval()
    ys, ps = [], []
    with torch.no_grad():
        for batch in batches(test, 64):
            encoded = encode_seqs(tokenizer, [row['seq'] for row in batch], device, 64)
            y = torch.tensor([row['label'] for row in batch], dtype=torch.float32, device=device)
            hidden = backbone(**encoded).last_hidden_state
            pad = encoded['attention_mask'] == 0
            pred = head(hidden, pad).squeeze(-1)
            ys.append(y.cpu().numpy())
            ps.append(pred.cpu().numpy())
    y_true = np.concatenate(ys)
    y_pred = np.concatenate(ps)
    assert np.isfinite(y_pred).all()
    mse = float(np.mean((y_true - y_pred) ** 2))
    pred_std = float(y_pred.std())
    summary = {
        'run_id': rid, 'n_test': len(test), 'revalidated_pearson_r': None,
        'nonfinite_reason': 'constant_prediction', 'revalidated_mse': mse,
        'y_true_mean': float(y_true.mean()), 'y_true_std': float(y_true.std()),
        'y_pred_mean': float(y_pred.mean()), 'y_pred_std': pred_std,
        'cuda_available': True, 'cuda_device': device,
        'cuda_device_name': torch.cuda.get_device_name(args.device),
        'cuda_runtime': torch.version.cuda,
        'checkpoint_best_epoch': state['best_epoch'],
        'plateau_status': plateau['status'], 'stop_reason': plateau['stop_reason'],
        'split_evidence_match': True, 'candidate_eligible': False,
        'reference_result': str(args.reference_result),
    }
    assert pred_std < 1e-6, pred_std
    np.savez_compressed(args.output_dir / f'{rid}_predictions.npz', y_true=y_true, y_pred=y_pred)
    (args.output_dir / f'{rid}_revalidation.json').write_text(json.dumps(summary, indent=2) + '\n')
    print(json.dumps(summary, indent=2))


if __name__ == '__main__':
    main()
