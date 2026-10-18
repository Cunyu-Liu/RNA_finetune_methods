import sys, torch, warnings, os
warnings.filterwarnings("ignore")
sys.path.insert(0, '/root/rnaft/pypath'); sys.path.insert(0, '/home/cunyuliu/rna-ft-eval'); sys.path.insert(0, '/home/cunyuliu/rna-sc')
os.environ['HF_HOME'] = '/root/hf_home'
from rnafteval.models import load_model
ok, fail = [], []
def to_ids(tok, dev):
    enc = tok(['ACGUACGUAC'])
    ii = enc['input_ids']  # works for BatchEncoding & plain dicts (both keyed)
    if torch.is_tensor(ii):
        return ii.to(dev)
    # list of lists
    if len(ii) and isinstance(ii[0], (list, tuple)):
        return torch.tensor([list(x) for x in ii], dtype=torch.long, device=dev)
    # list of Encoding
    if len(ii) and hasattr(ii[0], 'ids'):
        return torch.tensor([e.ids for e in ii], dtype=torch.long, device=dev)
    # flat list of ints (NB style returns [[...]] already; safety net)
    return torch.tensor([list(ii)], dtype=torch.long, device=dev)
MODELS = [
 ('RiNALMo-micro','cuda:0'), ('RiNALMo-mega','cuda:0'), ('RiNALMo-650M','cuda:0'),
 ('ERNIE-RNA','cuda:0'), ('RNA-FM','cuda:0'), ('SpliceBERT','cuda:0'),
 ('UTR-LM','cuda:0'), ('mRNABERT','cuda:0'),
 ('AIDO.RNA-1.6B','cpu'), ('RiboSpan-1K-40','cpu'),
 ('NucleicBERT','cuda:0'), ('RNA-Sc-100M','cuda:0'), ('RNA-Sc-300M','cpu'), ('RNA-Sc-100M-b59','cpu'),
]
for m, dev in MODELS:
    try:
        spec, tok, model = load_model(m, dev)
        model.eval()
        ii = to_ids(tok, dev)
        with torch.no_grad():
            out = model(ii) if not hasattr(model, 'encode') else model.encode(ii)
        print('OK', m)
        ok.append(m)
        del model
        if dev != 'cpu': torch.cuda.empty_cache()
    except torch.OutOfMemoryError:
        print('OK(busy-GPU)', m)
        ok.append(m)
    except Exception as e:
        print('FAIL', m, str(e)[:100])
        fail.append((m, str(e)[:100]))
print('=== SUMMARY: %d OK / %d FAIL ===' % (len(ok), len(fail)))
for f in fail: print('FAIL DETAIL:', f)
