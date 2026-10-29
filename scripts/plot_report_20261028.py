from pathlib import Path
import argparse
import math
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from PIL import Image, ImageDraw, ImageFont

WORK = OUT = PPT = HAND = FONT = YAHEI = None


def configure():
    global WORK, OUT, PPT, HAND, FONT, YAHEI
    parser = argparse.ArgumentParser(description='重绘 2026-10-28 导师讨论版图表，所有路径显式传入。')
    parser.add_argument('--work-dir', type=Path, required=True, help='当前结果 CSV 所在目录')
    parser.add_argument('--handoff-dir', type=Path, required=True, help='交接文档根目录')
    parser.add_argument('--ppt-dir', type=Path, required=True, help='历史 PPT 图所在目录')
    parser.add_argument('--output-dir', type=Path, required=True, help='新图与图源数据输出目录')
    parser.add_argument('--font', type=Path, help='可选微软雅黑字体文件')
    args = parser.parse_args()
    WORK = args.work_dir.resolve()
    OUT = args.output_dir.resolve()
    OUT.mkdir(parents=True, exist_ok=True)
    PPT = args.ppt_dir.resolve()
    HAND = args.handoff_dir.resolve()
    FONT = str(args.font) if args.font else None
    if FONT:
        font_manager.fontManager.addfont(FONT)
        YAHEI = font_manager.FontProperties(fname=FONT).get_name()
    else:
        YAHEI = 'Microsoft YaHei'
    plt.rcParams.update({
        'font.family': [YAHEI, 'DejaVu Sans'],
        'axes.unicode_minus': False,
        'axes.spines.top': False,
        'axes.spines.right': False,
        'axes.linewidth': 1.2,
        'legend.frameon': False,
        'pdf.fonttype': 42,
        'svg.fonttype': 'none',
    })
COLORS = {
    'frozen_random': '#6BAED6',
    'frozen_family': '#C6DBEF',
    'finetune_random': '#FD8D3C',
    'finetune_family': '#D94801',
}
LABELS = {
    'frozen_random': 'Frozen (random)',
    'frozen_family': 'Frozen (family)',
    'finetune_random': 'Fine-tuned (random)',
    'finetune_family': 'Fine-tuned (family)',
}
SIX_COLORS = {
    'frozen_random': '#6BAED6',
    'frozen_family': '#C6DBEF',
    'lora_random': '#FD8D3C',
    'lora_family': '#D94801',
    'full_random': '#3B3B3B',
    'full_family': '#A6A6A6',
}
SIX_LABELS = {
    'frozen_random': 'Frozen (R)',
    'frozen_family': 'Frozen (F)',
    'lora_random': 'LoRA (R)',
    'lora_family': 'LoRA (F)',
    'full_random': 'Full-FT (R)',
    'full_family': 'Full-FT (F)',
}
MODELS = ['RiNALMo-micro', 'RiNALMo-mega', 'RiNALMo-650M', 'ERNIE-RNA', 'RNA-FM']
MODEL_SHORT = {
    'RiNALMo-micro': 'RiNALMo\n33M',
    'RiNALMo-mega': 'RiNALMo\n148M',
    'RiNALMo-650M': 'RiNALMo\n650M',
    'ERNIE-RNA': 'ERNIE-RNA\n86M',
    'RNA-FM': 'RNA-FM\n99M',
}


def save_fig(fig, stem):
    fig.savefig(OUT / f'{stem}.png', dpi=300, bbox_inches='tight', facecolor='white')
    fig.savefig(OUT / f'{stem}.pdf', bbox_inches='tight', facecolor='white')
    plt.close(fig)


def grouped_summary(df, task, finetune='lora'):
    rows = []
    for model in MODELS:
        row = {'model': model, 'finetune_arm': finetune}
        for key, strategy, split in [
            ('frozen_random', 'frozen', 'random'),
            ('frozen_family', 'frozen', 'family'),
            ('finetune_random', finetune, 'random'),
            ('finetune_family', finetune, 'family'),
        ]:
            q = df[(df.task == task) & (df.model == model) &
                   (df.strategy == strategy) & (df.split == split) &
                   (df.proof_state == 'complete')]
            vals = pd.to_numeric(q.value, errors='coerce').dropna().to_numpy(float)
            row[f'{key}_n'] = len(vals)
            row[key] = float(vals.mean()) if len(vals) else np.nan
            row[f'{key}_sd'] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            row[f'{key}_rids'] = ';'.join(q.rid.astype(str))
        rows.append(row)
    return pd.DataFrame(rows)


def fourbar(df, task, metric, stem, title, ymax=1.05, chance=None):
    summary = grouped_summary(df, task)
    summary.to_csv(OUT / f'{stem}_data.csv', index=False)
    fig, ax = plt.subplots(figsize=(12.4, 4.6), constrained_layout=True)
    keys = list(COLORS)
    x = np.arange(len(summary))
    width = 0.19
    for j, key in enumerate(keys):
        vals = summary[key].to_numpy(float)
        ns = summary[f'{key}_n'].to_numpy(int)
        sds = summary[f'{key}_sd'].to_numpy(float)
        pos = x + (j - 1.5) * width
        for i, (v, n, sd) in enumerate(zip(vals, ns, sds)):
            if n == 0 or not np.isfinite(v):
                ax.text(pos[i], 0.025, 'NA', ha='center', va='bottom', fontsize=8,
                        color='#8A8A8A', rotation=90)
                continue
            bar = ax.bar(pos[i], v, width=width * 0.94, color=COLORS[key],
                         edgecolor='white', linewidth=0.5,
                         yerr=sd if n > 1 else None, capsize=2,
                         hatch='///' if n < 3 else None,
                         label=LABELS[key] if i == 0 else None)
            ax.text(pos[i], min(v + 0.018, ymax - 0.02), f'{v:.2f}',
                    ha='center', va='bottom', fontsize=8.2, color='#333333')
            if n < 3:
                ax.text(pos[i], max(0.03, v * 0.48), f'n={n}', ha='center', va='center',
                        fontsize=7.2, color='#333333', rotation=90)
    if chance is not None:
        ax.axhline(chance, color='#B03A2E', lw=0.9, ls='--', alpha=0.65)
        ax.text(len(summary) - 0.45, chance + 0.012, 'chance', color='#B03A2E',
                fontsize=8, ha='right')
    ax.set_title(title + '\nFine-tuned = LoRA; bars = mean ± SD; hatched = n<3; NA = not complete',
                 fontsize=13, fontweight='bold', color='#1F3A5F', pad=12)
    ax.set_ylabel(metric, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in summary.model], fontsize=9.5)
    ax.set_ylim(0, ymax)
    ax.grid(axis='y', color='#E8E8E8', lw=0.7)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in keys]
    ax.legend(handles, [LABELS[k] for k in keys], ncol=4,
              loc='upper center', bbox_to_anchor=(0.5, 1.02), fontsize=9)
    ax.text(0.995, -0.19, 'bestval_v1 | official models | formal seeds 17/29/43 | complete proof only',
            transform=ax.transAxes, ha='right', va='top', fontsize=8.5, color='#777777')
    save_fig(fig, stem)


def sixbar_summary(df, task):
    rows = []
    for model in MODELS:
        row = {'model': model}
        for key in SIX_COLORS:
            strategy, split = key.split('_', 1)
            q = df[(df.task == task) & (df.model == model) &
                   (df.strategy == strategy) & (df.split == split) &
                   (df.proof_state == 'complete')]
            assert q.seed.nunique() == len(q), (task, model, key, 'duplicate seed')
            vals = pd.to_numeric(q.value, errors='coerce').dropna().to_numpy(float)
            row[f'{key}_n'] = len(vals)
            row[key] = float(vals.mean()) if len(vals) else np.nan
            row[f'{key}_sd'] = float(vals.std(ddof=1)) if len(vals) > 1 else 0.0
            row[f'{key}_rids'] = ';'.join(q.rid.astype(str))
        rows.append(row)
    return pd.DataFrame(rows)


def sixbar(df, task, metric, stem, title, ymax=1.05, chance=None):
    summary = sixbar_summary(df, task)
    summary.to_csv(OUT / f'{stem}_data.csv', index=False)
    fig, ax = plt.subplots(figsize=(12.4, 4.6), constrained_layout=True)
    keys = list(SIX_COLORS)
    x = np.arange(len(summary))
    width = 0.135
    for j, key in enumerate(keys):
        vals = summary[key].to_numpy(float)
        ns = summary[f'{key}_n'].to_numpy(int)
        sds = summary[f'{key}_sd'].to_numpy(float)
        pos = x + (j - 2.5) * width
        for i, (v, n, sd) in enumerate(zip(vals, ns, sds)):
            if n == 0 or not np.isfinite(v):
                ax.text(pos[i], 0.025, 'NA', ha='center', va='bottom', fontsize=7.5,
                        color='#8A8A8A', rotation=90)
                continue
            ax.bar(pos[i], v, width=width * 0.94, color=SIX_COLORS[key],
                   edgecolor='white', linewidth=0.5,
                   yerr=sd if n > 1 else None, capsize=2,
                   hatch='///' if n < 3 else None)
            ax.text(pos[i], min(v + 0.018, ymax - 0.02), f'{v:.2f}',
                    ha='center', va='bottom', fontsize=7.2, color='#333333')
            if n < 3:
                ax.text(pos[i], max(0.03, v * 0.48), f'n={n}', ha='center', va='center',
                        fontsize=6.8, color='#333333', rotation=90)
    if chance is not None:
        ax.axhline(chance, color='#B03A2E', lw=0.9, ls='--', alpha=0.65)
        ax.text(len(summary) - 0.45, chance + 0.012, 'chance', color='#B03A2E',
                fontsize=8, ha='right')
    ax.set_title(title + '\nbars = mean ± SD; hatched = n<3; NA = not complete',
                 fontsize=13, fontweight='bold', color='#1F3A5F', pad=12)
    ax.set_ylabel(metric, fontsize=11)
    ax.set_xticks(x)
    ax.set_xticklabels([MODEL_SHORT[m] for m in summary.model], fontsize=9.5)
    ax.set_ylim(0, ymax)
    ax.grid(axis='y', color='#E8E8E8', lw=0.7)
    ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=SIX_COLORS[k]) for k in keys]
    ax.legend(handles, [SIX_LABELS[k] for k in keys], ncol=6,
              loc='upper center', bbox_to_anchor=(0.5, 1.02), fontsize=8.2)
    ax.text(0.995, -0.19, 'bestval_v1 | official models | formal seeds 17/29/43 | complete proof only',
            transform=ax.transAxes, ha='right', va='top', fontsize=8.5, color='#777777')
    save_fig(fig, stem)


def lr_ncrna_mrl():
    df = pd.read_csv(WORK / 'lr_ncrna_mrl_legacy_20261028.csv')
    models = ['RNA-Sc-10M', 'RiNALMo-micro', 'SpliceBERT', 'ERNIE-RNA', 'RNA-FM', 'NucleicBERT', 'AIDO.RNA-1.6B']
    short = ['RNA-Sc\n10M', 'RiNALMo\n33M', 'SpliceBERT\n19M', 'ERNIE\n86M', 'RNA-FM\n99M', 'NucleicBERT\n404M', 'AIDO\n1.6B']
    tasks = [('noncoding-rna-family', 'ncRNA ACC'), ('mrl', 'MRL Pearson r')]
    fig, axes = plt.subplots(1, 2, figsize=(15.2, 4.5), constrained_layout=True)
    for ax, (task, metric) in zip(axes, tasks):
        x = np.arange(len(models))
        for j, arm in enumerate(['default', 'tuned']):
            for i, model in enumerate(models):
                q = df[(df.task == task) & (df.model == model) & (df.arm == arm)]
                assert len(q) == 1
                r = q.iloc[0]
                pos = x[i] + (-0.17 if j == 0 else 0.17)
                if r.n == 0 or pd.isna(r['mean']):
                    ax.text(pos, 0.025, 'NA', ha='center', va='bottom', fontsize=7.5,
                            color='#8A8A8A', rotation=90)
                    continue
                v = float(r['mean'])
                color = '#C94C4C' if arm == 'default' else '#27AE60'
                ax.bar(pos, v, width=0.30, color=color, yerr=float(r.sd), capsize=2,
                       hatch='///' if r.n < 3 else None, edgecolor='white', linewidth=0.5,
                       label=('Default 3e-4' if arm == 'default' else 'Validation-tuned LR') if i == 0 else None)
                value_text = f'{v:.3f}' if abs(v) < 0.005 else f'{v:.2f}'
                if arm == 'tuned':
                    value_text += '\n' + str(r.lr)
                ax.text(pos, v + 0.025, value_text, ha='center', va='bottom', fontsize=7.2,
                        color='#333333')
                if r.n < 3:
                    ax.text(pos, max(0.035, v * 0.45), f'n={r.n}', ha='center', va='center',
                            fontsize=7, rotation=90, color='#333333')
        ax.axhline(0, color='#777777', lw=0.7)
        ax.set_title(metric, fontsize=12, fontweight='bold', color='#1F3A5F')
        ax.set_xticks(x)
        ax.set_xticklabels(short, fontsize=8, rotation=25, ha='right', rotation_mode='anchor')
        ax.set_ylim(-0.12, 1.12)
        ax.grid(axis='y', color='#E8E8E8', lw=0.7)
        ax.set_axisbelow(True)
    axes[0].legend(ncol=2, loc='upper left', fontsize=9)
    fig.suptitle('Default 3e-4 vs validation-tuned LR | full-FT | valid legacy ncRNA and MRL panels',
                 fontsize=13, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.03, 'seed101 selects LR; formal seeds 17/29/43; hatched = n<3; NA = no complete formal run; random-init/e3/best-val excluded',
             ha='center', va='top', fontsize=8.5, color='#666666')
    save_fig(fig, 'a8_ncrna_mrl_only')


def resource_mrl(df):
    rows = []
    for model in MODELS:
        for strategy in ['frozen', 'lora', 'full']:
            q = df[(df.task == 'mrl') & (df.model == model) &
                   (df.strategy == strategy) & (df.split == 'random') &
                   (df.proof_state == 'complete')]
            vals = pd.to_numeric(q.value, errors='coerce').dropna().to_numpy(float)
            walls = pd.to_numeric(q.wall_sec, errors='coerce').dropna().to_numpy(float)
            rows.append({
                'model': model, 'strategy': strategy, 'n': len(vals),
                'pearson_r': vals.mean() if len(vals) else np.nan,
                'sd': vals.std(ddof=1) if len(vals) > 1 else 0.0,
                'wall_median_min': np.median(walls) / 60 if len(walls) else np.nan,
                'rids': ';'.join(q.rid.astype(str)),
            })
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / 'mrl_resource_time_performance_data.csv', index=False)
    strategy_style = {
        'frozen': ('#9EACB0', 'Frozen'),
        'lora': ('#E87E2B', 'LoRA'),
        'full': ('#3B3B3B', 'Full FT'),
    }
    fig, ax = plt.subplots(figsize=(11.4, 5.4), constrained_layout=True)
    ybase = np.arange(len(MODELS)) * 1.25
    for j, strategy in enumerate(['frozen', 'lora', 'full']):
        color, label = strategy_style[strategy]
        for i, model in enumerate(MODELS):
            r = summary[(summary.model == model) & (summary.strategy == strategy)].iloc[0]
            y = ybase[i] + (1 - j) * 0.25
            if r.n == 0 or not np.isfinite(r.pearson_r):
                ax.text(0.03, y, 'NA', va='center', fontsize=8, color='#999999')
                continue
            wall = f'{r.wall_median_min:.0f} min' if np.isfinite(r.wall_median_min) else 'wall NA'
            ax.barh(y, r.pearson_r, height=0.21, color=color,
                    hatch='///' if r.n < 3 else None, edgecolor='white', linewidth=0.5,
                    label=label if i == 0 else None)
            ax.text(r.pearson_r + 0.012, y, f'{r.pearson_r:.2f} · {wall}',
                    va='center', fontsize=8.3, color='#333333')
    ax.set_yticks(ybase)
    ax.set_yticklabels([MODEL_SHORT[m].replace('\n', ' ') for m in MODELS], fontsize=9.5)
    ax.invert_yaxis()
    ax.set_xlim(0, 1.05)
    ax.set_xlabel('MRL Pearson r (random split)', fontsize=10.5)
    ax.set_title('Time × performance | best-val official models\nBars = 3-seed mean; labels = median wall time; NA = not complete',
                 fontsize=12.5, fontweight='bold', color='#1F3A5F')
    ax.grid(axis='x', color='#E8E8E8', lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc='upper center', bbox_to_anchor=(0.5, -0.12), fontsize=9)
    save_fig(fig, 'mrl_resource_time_performance')


def extension_fourbar():
    df = pd.read_csv(WORK / 'b20fix_8task_table.csv')
    models = ['rinalmomicro', 'rinalmomega', 'rinalmo650m', 'ernierna', 'rnafm', 'nucleicbert']
    short = {
        'rinalmomicro': 'RiNALMo\n33M', 'rinalmomega': 'RiNALMo\n148M',
        'rinalmo650m': 'RiNALMo\n650M', 'ernierna': 'ERNIE\n86M',
        'rnafm': 'RNA-FM\n99M', 'nucleicbert': 'NucleicBERT\n404M',
    }
    tasks = [('spliceai', 'SpliceAI macro-F1'), ('degradation', 'mRNA degradation PCC'), ('ssi', 'SSI PCC')]
    all_rows = []
    fig, axes = plt.subplots(1, 3, figsize=(14.2, 4.8))
    for ax, (task, metric) in zip(axes, tasks):
        rows = []
        for model in models:
            q = df[(df.task == task) & (df.model == model)]
            arms = []
            for arm in ['lora', 'full']:
                n = int(q[q.strategy == arm].n_seeds.sum())
                if n:
                    arms.append((arm, n))
            arm = 'lora' if any(a == 'lora' for a, _ in arms) else (arms[0][0] if arms else 'lora')
            row = {'task': task, 'model': model, 'finetune_arm': arm}
            for key, strategy, split in [
                ('frozen_random', 'frozen', 'random'), ('frozen_family', 'frozen', 'family'),
                ('finetune_random', arm, 'random'), ('finetune_family', arm, 'family')]:
                z = q[(q.strategy == strategy) & (q.split == split)]
                if len(z):
                    row[key] = float(z.iloc[0]['mean'])
                    row[f'{key}_n'] = int(z.iloc[0].n_seeds)
                else:
                    row[key] = np.nan
                    row[f'{key}_n'] = 0
            rows.append(row)
            all_rows.append(row)
        x = np.arange(len(models))
        width = 0.19
        for j, key in enumerate(COLORS):
            for i, row in enumerate(rows):
                v, n = row[key], row[f'{key}_n']
                pos = x[i] + (j - 1.5) * width
                if not n or not np.isfinite(v):
                    ax.text(pos, 0.025, 'NA', ha='center', va='bottom', fontsize=7,
                            color='#8A8A8A', rotation=90)
                    continue
                ax.bar(pos, v, width=width * 0.94, color=COLORS[key],
                       hatch='///' if n < 3 else None, edgecolor='white', linewidth=0.4)
                ax.text(pos, v + 0.015, f'{v:.2f}', ha='center', va='bottom', fontsize=6.8)
                if n < 3:
                    ax.text(pos, max(0.035, v * 0.45), f'n{n}', ha='center', va='center',
                            fontsize=6.5, rotation=90, color='#333333')
        ax.set_title(metric, fontsize=11.5, fontweight='bold', color='#1F3A5F')
        ax.set_xticks(x)
        ax.set_xticklabels([short[m] for m in models], fontsize=7.4, rotation=25,
                           ha='right', rotation_mode='anchor')
        ax.set_ylim(0, 0.82)
        ax.grid(axis='y', color='#E8E8E8', lw=0.7)
        ax.set_axisbelow(True)
    handles = [plt.Rectangle((0, 0), 1, 1, color=COLORS[k]) for k in COLORS]
    fig.subplots_adjust(left=0.05, right=0.995, top=0.76, bottom=0.17, wspace=0.14)
    fig.suptitle('Three-task extension | B20-corrected stage results',
                 fontsize=13, fontweight='bold', color='#1F3A5F', y=0.98)
    fig.text(0.5, 0.915, 'Fine-tuned = LoRA when available, otherwise full FT; hatched = n<3; NA = not complete',
             ha='center', va='center', fontsize=10, color='#1F3A5F')
    fig.legend(handles, [LABELS[k] for k in COLORS], ncol=4, loc='upper center',
               bbox_to_anchor=(0.5, 0.875), fontsize=9)
    pd.DataFrame(all_rows).to_csv(OUT / 'extension_three_task_fourbar_data.csv', index=False)
    save_fig(fig, 'extension_three_task_fourbar')


def e4_delta_two_tasks():
    df = pd.read_csv(WORK.parent / 'legacy_inputs/c4_table.csv')
    df = df[df.task == 'mrl'].copy()
    models = ['RiNALMo-micro', 'RiNALMo-mega', 'RiNALMo-650M', 'ERNIE-RNA', 'RNA-FM',
              'RNA-Sc-10M', 'RNA-Sc-30M', 'RNA-Sc-100M', 'NucleicBERT', 'AIDO.RNA-1.6B']
    short = ['RiNALMo\n33M', 'RiNALMo\n148M', 'RiNALMo\n650M', 'ERNIE\n86M', 'RNA-FM\n99M',
             'RNA-Sc\n10M', 'RNA-Sc\n30M', 'RNA-Sc\n100M', 'NucleicBERT\n404M', 'AIDO\n1.6B']
    fig, ax = plt.subplots(figsize=(12.4, 4.3), constrained_layout=True)
    out_rows = []
    x = np.arange(len(models))
    width = 0.25
    for j, strategy in enumerate(['frozen', 'lora', 'full']):
        vals = []
        for model in models:
            q = df[(df.model == model) & (df.strategy == strategy)]
            v = float(q.iloc[0].delta) if len(q) else np.nan
            vals.append(v)
            out_rows.append({'task': 'mrl', 'model': model, 'strategy': strategy,
                             'delta_random_minus_family': v})
        ax.bar(x + (j - 1) * width, vals, width=width * 0.92,
               color=['#6BAED6', '#FD8D3C', '#D94801'][j], label=strategy)
    ax.axhline(0, color='#555555', lw=0.8)
    ax.set_title('MRL Pearson r | random − family | legacy descriptive comparison',
                 fontsize=13.5, fontweight='bold', color='#1F3A5F')
    ax.set_xticks(x)
    ax.set_xticklabels(short, fontsize=8, rotation=35, ha='right', rotation_mode='anchor')
    ax.set_ylabel('Δ = random − family')
    ax.grid(axis='y', color='#ECECEC', lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(ncol=3, loc='upper left', fontsize=9)
    fig.text(0.5, -0.03, 'ncRNA legacy panels are quarantined; eight-task corrected Δ matrix remains pending',
             ha='center', fontsize=9, color='#B64342')
    pd.DataFrame(out_rows).to_csv(OUT / 'e4_delta_mrl_only_data.csv', index=False)
    save_fig(fig, 'e4_delta_mrl_only')


def equiv_high_ncrna_mrl():
    pairs = pd.read_csv(WORK.parent / 'legacy_inputs/equiv_high_pairs_legacy_20261028.csv')
    curves = pd.read_csv(WORK.parent / 'legacy_inputs/equiv_high_curves_legacy_20261028.csv')
    tasks = [('mrl', 'MRL Pearson r')]
    fig, axes = plt.subplots(2, 1, figsize=(12.4, 6.2), constrained_layout=True)
    axes = axes.reshape(2, 1)
    for col, (task, metric) in enumerate(tasks):
        pair = pairs[pairs.task == task].iloc[0]
        ax = axes[0, col]
        xs = [0, 1]
        ys = [pair.full_mean, pair.lora_mean]
        ax.plot(xs, ys, color='#555555', lw=2, ls='--', marker='o', markersize=8,
                markerfacecolor='white', markeredgewidth=2)
        ax.scatter([0], [pair.full_mean], s=90, color='#1F3A5F', zorder=3, label='full-FT')
        ax.scatter([1], [pair.lora_mean], s=90, color='#D94801', zorder=3, label='LoRA')
        for x, y in zip(xs, ys):
            ax.text(x, y + 0.018, f'{y:.3f}', ha='center', va='bottom', fontsize=11,
                    fontweight='bold', color='#1F3A5F')
        ax.set_xlim(-0.45, 1.45)
        ax.set_ylim(min(ys) - 0.09, max(ys) + 0.07)
        ax.set_xticks(xs)
        ax.set_xticklabels([f'full-FT\nn={int(pair.full_n_train)}', f'LoRA\nn={int(pair.lora_n_train)}'], fontsize=10)
        ax.set_ylabel(metric)
        ax.set_title(f'{metric}: full@{int(pair.full_n_train)} vs LoRA@{int(pair.lora_n_train)} | Δ={abs(pair.full_mean-pair.lora_mean):.3f}',
                     fontsize=12, fontweight='bold', color='#1F3A5F')
        ax.grid(axis='y', color='#E8E8E8', lw=0.7)
        ax.set_axisbelow(True)
        ax.legend(loc='best', fontsize=9)

        ax = axes[1, col]
        q = curves[curves.task == task].copy()
        q['n_plot'] = range(len(q))
        for strategy, color, label in [('full', '#1F3A5F', 'full-FT'), ('lora', '#D94801', 'LoRA')]:
            vals = pd.to_numeric(q[f'{strategy}_mean'], errors='coerce')
            ax.plot(q.n_plot, vals, marker='o', ms=4, lw=1.8, color=color, label=label)
        pair_n = {int(pair.full_n_train), int(pair.lora_n_train)}
        highlight = q[q.n.isin(pair_n)]
        for _, r in highlight.iterrows():
            for strategy, color in [('full', '#1F3A5F'), ('lora', '#D94801')]:
                v = pd.to_numeric(pd.Series([r[f'{strategy}_mean']]), errors='coerce').iloc[0]
                if pd.notna(v):
                    ax.scatter(r.n_plot, v, s=85, facecolor='none', edgecolor='#C0392B', linewidth=2)
        ax.set_xticks(q.n_plot)
        ax.set_xticklabels([str(int(n)) for n in q.n], fontsize=8, rotation=35, ha='right')
        ax.set_xlabel('Labeled sequences (equal-spaced)')
        ax.set_ylabel(metric)
        ax.set_title('Learning curves; red circles = paired budgets', fontsize=10.5, color='#1F3A5F')
        ax.grid(color='#ECECEC', lw=0.6)
        ax.set_axisbelow(True)
        ax.legend(loc='best', fontsize=8.5)
    fig.suptitle('MRL local data-budget comparison | RiNALMo-micro | family split | legacy exploration',
                 fontsize=14, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.025, 'ncRNA legacy inputs are quarantined; this MRL case is not a universal 3n rule; eight-task corrected equivalence remains pending',
             ha='center', va='top', fontsize=9, color='#B64342')
    save_fig(fig, 'e3_equiv_high_mrl_only')


def equiv_low_two_cases():
    pairs = pd.read_csv(WORK.parent / 'legacy_inputs/equiv_low_pairs_legacy_20261028.csv')
    curves = pd.read_csv(WORK.parent / 'legacy_inputs/equiv_low_curves_legacy_20261028.csv')
    pairs = pairs[pairs.task == 'mrl'].copy()
    assert len(pairs) == 1
    fig, axes = plt.subplots(2, 1, figsize=(12.4, 6.2), constrained_layout=True)
    axes = axes.reshape(2, 1)
    for col, (_, pair) in enumerate(pairs.iterrows()):
        task_label = 'MRL Pearson r' if pair.task == 'mrl' else 'ncRNA ACC'
        model_label = 'RiNALMo-micro' if pair.model == 'RiNALMo-micro' else 'RNA-Sc-10M'
        ax = axes[0, col]
        xs, ys = [0, 1], [pair.full_mean, pair.lora_mean]
        ax.plot(xs, ys, color='#555555', lw=2, ls='--', marker='o', markersize=8,
                markerfacecolor='white', markeredgewidth=2)
        ax.scatter([0], [pair.full_mean], s=90, color='#1F3A5F', zorder=3, label='full-FT')
        ax.scatter([1], [pair.lora_mean], s=90, color='#D94801', zorder=3, label='LoRA')
        for x, y in zip(xs, ys):
            ax.text(x, y + max(ys) * 0.04, f'{y:.3f}', ha='center', va='bottom', fontsize=11,
                    fontweight='bold', color='#1F3A5F')
        ax.set_xlim(-0.45, 1.45)
        ax.set_ylim(min(0, min(ys) - 0.06), max(ys) + 0.12)
        ax.set_xticks(xs)
        ax.set_xticklabels([f'full-FT\nn={int(pair.full_n_train)}', f'LoRA\nn={int(pair.lora_n_train)}'], fontsize=10)
        ax.set_ylabel(task_label)
        ax.set_title(f'{model_label} | {task_label}', fontsize=12, fontweight='bold', color='#1F3A5F')
        ax.grid(axis='y', color='#E8E8E8', lw=0.7)
        ax.set_axisbelow(True)
        ax.legend(loc='best', fontsize=9)

        ax = axes[1, col]
        q = curves[(curves.task == pair.task) & (curves.model == pair.model)].copy()
        q['n_plot'] = range(len(q))
        for strategy, color, label in [('frozen', '#6BAED6', 'frozen'), ('full', '#1F3A5F', 'full-FT'), ('lora', '#D94801', 'LoRA')]:
            vals = pd.to_numeric(q[f'{strategy}_mean'], errors='coerce')
            ax.plot(q.n_plot, vals, marker='o', ms=4, lw=1.7, color=color, label=label)
        for _, r in q[q.n.isin({1000, 3000})].iterrows():
            for strategy in ['full', 'lora']:
                v = pd.to_numeric(pd.Series([r[f'{strategy}_mean']]), errors='coerce').iloc[0]
                if pd.notna(v):
                    ax.scatter(r.n_plot, v, s=85, facecolor='none', edgecolor='#C0392B', linewidth=2)
        ax.set_xticks(q.n_plot)
        ax.set_xticklabels([str(int(n)) for n in q.n], fontsize=8, rotation=35, ha='right')
        ax.set_xlabel('Labeled sequences (equal-spaced)')
        ax.set_ylabel(task_label)
        ax.set_title('Learning curves; red circles = paired budgets', fontsize=10.5, color='#1F3A5F')
        ax.grid(color='#ECECEC', lw=0.6)
        ax.set_axisbelow(True)
        ax.legend(loc='best', fontsize=8.5)
    fig.suptitle('MRL low-budget local comparison | family split | legacy exploration',
                 fontsize=14, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.025, 'ncRNA legacy inputs are quarantined; no universal 3n or threshold rule; eight-task corrected equivalence remains pending',
             ha='center', va='top', fontsize=9, color='#B64342')
    save_fig(fig, 'e3_equiv_low_mrl_only')


def ncrna_shuffle_audit():
    import json

    src = WORK / 'ncrna_shuffle_audit'
    shuffled = json.loads((src / 'shuffled_one_result.json').read_text())
    no_shuffle = json.loads((src / 'noshuffle_one_result.json').read_text())
    assert no_shuffle['run_id'].endswith('noshuffle_one_diag')
    assert no_shuffle['epoch_shuffle'] is False
    assert shuffled['run_id'].endswith('bestval_v1_fixedsplit')
    for key in ('model', 'task', 'strategy', 'seed', 'split', 'n_train', 'n_test', 'lr'):
        assert shuffled[key] == no_shuffle[key], key
    order = pd.read_csv(src / 'label_order_first512.csv')
    summary = json.loads((src / 'label_order_summary.json').read_text())
    rows = []
    curves = []
    for arm, result, runner, max_len in [
            ('shuffled', shuffled, 'finetune_one', 512),
            ('no_shuffle', no_shuffle, 'finetune_one', 512)]:
        rows.append({'arm': arm, 'run_id': result['run_id'], 'runner': runner,
                     'max_len': max_len, 'batch_size': 32, 'rank': 8,
                     'test_acc': result['value'], 'best_epoch': result['best_epoch'],
                     'epochs_trained': result['epochs_trained'],
                     'best_val_loss': result['best_val'],
                     'wall_sec': result['wall_sec'],
                     'peak_mem_mb': result['peak_mem_mb'],
                     'protocol': result['protocol']})
        for epoch, (train_loss, val_loss) in enumerate(zip(
                result['epoch_train_losses'], result['epoch_val_losses'])):
            curves.append({'arm': arm, 'epoch': epoch, 'train_loss': train_loss,
                           'val_loss': val_loss, 'run_id': result['run_id']})
    pd.DataFrame(rows).to_csv(OUT / 'ncrna_shuffle_audit_summary.csv', index=False)
    pd.DataFrame(curves).to_csv(OUT / 'ncrna_shuffle_audit_curves.csv', index=False)

    navy, blue, red, gray = '#1F3A5F', '#3775BA', '#B64342', '#666666'
    fig = plt.figure(figsize=(13.2, 4.5), constrained_layout=True)
    grid = fig.add_gridspec(1, 3, width_ratios=[1.15, 1.25, 0.8])
    ax = fig.add_subplot(grid[0, 0])
    image = np.vstack([order.original_label.to_numpy()[:320],
                       order.shuffled_label_epoch0.to_numpy()[:320]])
    ax.imshow(image, aspect='auto', cmap='tab20', vmin=0, vmax=12,
              interpolation='nearest')
    ax.set_yticks([0, 1], ['Original', 'Shuffled'])
    ax.set_xticks([])
    ax.set_title(f"A | Training order\n{summary['label_runs']} label runs; longest = {summary['longest_label_run']}",
                 fontsize=11.5, fontweight='bold', color=navy)
    for spine in ax.spines.values():
        spine.set_visible(True)

    ax = fig.add_subplot(grid[0, 1])
    for arm, color, label in [('shuffled', blue, 'Per-epoch shuffle'),
                              ('no_shuffle', red, 'No shuffle')]:
        result = shuffled if arm == 'shuffled' else no_shuffle
        vals = result['epoch_val_losses']
        ax.plot(range(len(vals)), vals, marker='o', ms=4.5, lw=2.2,
                color=color, label=label)
        best = result['best_epoch']
        ax.scatter(best, vals[best], s=110, facecolor='white', edgecolor=color,
                   linewidth=2.2, zorder=4)
    ax.set_xlabel('Epoch')
    ax.set_ylabel('Validation loss')
    ax.set_title('B | Best checkpoint selection\n circles = restored best epoch',
                 fontsize=11.5, fontweight='bold', color=navy)
    ax.grid(color='#E9E9E9', lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(loc='upper right', fontsize=9)

    ax = fig.add_subplot(grid[0, 2])
    vals = [shuffled['value'], no_shuffle['value']]
    bars = ax.bar([0, 1], vals, width=0.62, color=[blue, red], edgecolor='white')
    for bar, val in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, val + 0.025, f'{val:.3f}',
                ha='center', va='bottom', fontsize=11, fontweight='bold', color=navy)
    ax.axhline(1 / 13, color=gray, lw=1, ls='--')
    ax.text(1.42, 1 / 13 + 0.018, '1/13', ha='right', fontsize=8.5, color=gray)
    ax.set_xticks([0, 1], ['Shuffled', 'No shuffle'])
    ax.set_ylim(0, 1.04)
    ax.set_ylabel('Family-test ACC')
    ax.set_title('C | Strict A/B\nonly shuffle differs', fontsize=11.5,
                 fontweight='bold', color=navy)
    ax.grid(axis='y', color='#E9E9E9', lw=0.7)
    ax.set_axisbelow(True)
    fig.suptitle('ncRNA family near-random performance is reproduced by disabling shuffle',
                 fontsize=14, fontweight='bold', color=navy)
    fig.text(0.5, -0.035,
             'RiNALMo-micro | LoRA rank8 | seed17 | family split | max_len=512 | batch=32 | best-val; diagnostic seed not included in formal means',
             ha='center', va='top', fontsize=8.8, color=gray)
    save_fig(fig, 'ncrna_shuffle_audit')


def equivalence_protocol_status():
    from matplotlib import patches
    fig, ax = plt.subplots(figsize=(12.4, 4.5), constrained_layout=True)
    ax.set_xlim(0, 12.4)
    ax.set_ylim(0, 4.5)
    ax.axis('off')
    navy, blue, orange, gray = '#1F3A5F', '#DCEAF7', '#FDE3CF', '#666666'
    boxes = [
        (0.35, 1.25, 2.5, 1.55, blue, 'Controlled inputs', 'same task + split + protocol'),
        (3.45, 2.35, 2.65, 1.25, blue, 'Small model', 'full-FT at labels n'),
        (3.45, 0.55, 2.65, 1.25, orange, 'Large model', 'LoRA at labels m'),
        (7.0, 1.25, 2.35, 1.55, '#E7F3E8', 'Closest match', 'per seed + 95% CI'),
        (10.0, 1.25, 2.05, 1.55, '#F2F2F2', 'Report', 'full@n ≈ LoRA@m\nor not observed'),
    ]
    for x, y, w, h, color, title, subtitle in boxes:
        ax.add_patch(patches.FancyBboxPatch((x, y), w, h,
                     boxstyle='round,pad=0.03,rounding_size=0.08',
                     facecolor=color, edgecolor='#B7C4D2', linewidth=1.1))
        ax.text(x + w / 2, y + h * 0.64, title, ha='center', va='center',
                fontsize=12, fontweight='bold', color=navy)
        ax.text(x + w / 2, y + h * 0.31, subtitle, ha='center', va='center',
                fontsize=9.5, color=gray)
    for x1, y1, x2, y2 in [(2.85, 2.02, 3.45, 2.95), (2.85, 2.02, 3.45, 1.18),
                           (6.1, 2.95, 7.0, 2.25), (6.1, 1.18, 7.0, 1.8),
                           (9.35, 2.02, 10.0, 2.02)]:
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle='->', lw=1.5, color=navy))
    ax.set_title('Data-budget equivalence | required comparison design',
                 fontsize=14, fontweight='bold', color=navy, pad=10)
    ax.text(6.2, 0.12,
            'Legacy ncRNA curves are quarantined. Corrected eight-task curves must be completed before reporting numerical equivalence.',
            ha='center', va='bottom', fontsize=9.5, color='#B64342')
    save_fig(fig, 'equivalence_protocol_status')


def ncrna_legacy_quarantine():
    fig, ax = plt.subplots(figsize=(12.4, 4.6), constrained_layout=True)
    ax.axis('off')
    navy, gray = '#1F3A5F', '#666666'
    columns = ['Evidence stream', 'Current status', 'Required action']
    rows = [
        ['micro strict shuffle A/B', 'COMPLETE', 'Use diagnostic only; keep out of formal means'],
        ['legacy mega / 650M E3 points', 'QUARANTINED', 'Re-test with corrected protocol'],
        ['1500 / 2000 / 2500 dense budgets', 'REGISTERED', 'Run after main-matrix acceptance'],
        ['eight-task large-model lanes', 'INCOMPLETE', 'Show NA; never fill from legacy'],
    ]
    table = ax.table(cellText=rows, colLabels=columns, cellLoc='left', loc='center',
                     colWidths=[0.31, 0.18, 0.51])
    table.auto_set_font_size(False)
    table.set_fontsize(10)
    table.scale(1, 1.75)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#D8DEE6')
        if r == 0:
            cell.set_facecolor(navy)
            cell.get_text().set_color('white')
            cell.get_text().set_fontweight('bold')
        else:
            cell.set_facecolor('#F7F9FC' if r % 2 else 'white')
            if c == 1:
                status = cell.get_text().get_text()
                cell.get_text().set_color('#3775BA' if status == 'COMPLETE' else '#B64342' if status == 'QUARANTINED' else gray)
                cell.get_text().set_fontweight('bold')
    ax.set_title('⑤d evidence audit | old points are not interchangeable with missing points',
                 fontsize=14, fontweight='bold', color=navy, pad=14)
    ax.text(0.5, 0.04,
            'No interpolation, zero filling, or legacy substitution. Every future point must map to a corrected RID and complete proof.',
            transform=ax.transAxes, ha='center', fontsize=9.5, color=gray)
    save_fig(fig, 'ncrna_legacy_quarantine')


def memory_ncrna():
    df = pd.read_csv(WORK.parent / 'legacy_inputs/resources_costbenefit.csv')
    models = ['SpliceBERT', 'RiNALMo-micro', 'ERNIE-RNA', 'RNA-FM', 'RiNALMo-mega', 'NucleicBERT', 'RiNALMo-650M']
    labels = ['SpliceBERT 19M', 'RiNALMo 33M', 'ERNIE 86M', 'RNA-FM 99M', 'RiNALMo 148M', 'NucleicBERT 404M', 'RiNALMo 650M']
    strategies = [('frozen', '#6BAED6'), ('lora', '#FD8D3C'), ('full', '#B64342')]
    rows = []
    for model in models:
        for strategy, _ in strategies:
            q = df[(df.task == 'noncoding-rna-family') & (df.model == model) & (df.strategy == strategy)]
            assert len(q) == 1, (model, strategy, len(q))
            rows.append({'model': model, 'strategy': strategy, 'n': int(q.iloc[0].n),
                         'peak_med_GB': float(q.iloc[0].peak_med_MB) / 1000.0})
    summary = pd.DataFrame(rows)
    summary.to_csv(OUT / 'ncrna_memory_legacy_data.csv', index=False)
    fig, axes = plt.subplots(1, 3, figsize=(12.6, 4.2), constrained_layout=True)
    y = np.arange(len(models))
    for ax, (strategy, color) in zip(axes, strategies):
        vals = [summary[(summary.model == m) & (summary.strategy == strategy)].iloc[0].peak_med_GB for m in models]
        ax.barh(y, vals, color=color, height=0.62)
        for yi, v in zip(y, vals):
            ax.text(v + 0.35, yi, f'{v:.1f}', va='center', fontsize=8.5, color='#333333')
        ax.axvline(24, color='#1F3A5F', ls='--', lw=1)
        ax.set_title({'frozen': 'Frozen', 'lora': 'LoRA', 'full': 'Full FT'}[strategy],
                     fontsize=12, fontweight='bold', color='#1F3A5F')
        ax.set_yticks(y)
        ax.set_yticklabels(labels if strategy == 'frozen' else [], fontsize=9)
        ax.invert_yaxis()
        ax.set_xlim(0, 30)
        ax.set_xlabel('Peak GPU memory (GB)')
        ax.grid(axis='x', color='#E8E8E8', lw=0.7)
        ax.set_axisbelow(True)
    fig.suptitle('ncRNA memory cost | legacy ledger median peak | dashed line = 24GB',
                 fontsize=13.5, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.035, 'Same task and legacy protocol; NucleicBERT LoRA and RiNALMo-650M full exceed 24GB; no cross-task max or extrapolation',
             ha='center', va='top', fontsize=8.8, color='#666666')
    save_fig(fig, 'ncrna_memory_legacy')


def font(size, bold=False):
    if FONT:
        return ImageFont.truetype(FONT, size=size, index=0)
    return ImageFont.load_default(size=size)


def center(draw, xy, text, fnt, fill):
    draw.text(xy, text, font=fnt, fill=fill, anchor='mm')


def crop_valid_panels():
    curves = pd.read_csv(WORK.parent / 'legacy_inputs/equiv_low_curves_legacy_20261028.csv')
    q = curves[(curves.task == 'mrl') & (curves.model == 'RiNALMo-micro')].copy()
    assert len(q) >= 4
    q.to_csv(OUT / 'e3_mrl_legacy_data.csv', index=False)
    fig, ax = plt.subplots(figsize=(12.4, 4.5), constrained_layout=True)
    x = np.arange(len(q))
    for strategy, color, label in [('frozen', '#6BAED6', 'frozen'),
                                   ('full', '#1F3A5F', 'full-FT'),
                                   ('lora', '#D94801', 'LoRA')]:
        vals = pd.to_numeric(q[f'{strategy}_mean'], errors='coerce')
        ax.plot(x, vals, marker='o', ms=5, lw=2, color=color, label=label)
    ax.set_xticks(x)
    ax.set_xticklabels([str(int(n)) for n in q.n])
    ax.set_xlabel('Labeled sequences (equal-spaced)')
    ax.set_ylabel('MRL Pearson r')
    ax.set_title('E3 data-size effect | MRL | RiNALMo-micro | family split | legacy',
                 fontsize=14, fontweight='bold', color='#1F3A5F')
    ax.grid(color='#ECECEC', lw=0.6)
    ax.set_axisbelow(True)
    ax.legend(loc='best', fontsize=9)
    fig.text(0.5, -0.035,
             'ncRNA and old per-base modification panels are quarantined; eight-task corrected learning curves remain pending',
             ha='center', va='top', fontsize=9.2, color='#B64342')
    save_fig(fig, 'e3_mrl_legacy')


def c5c_ncrna_lora_scale():
    budgets = [1000, 1500, 2000, 2500, 3000]
    specs = [
        ('RiNALMo-micro', 'RiNALMo 33M', '#3775BA',
         'c5c_ncrna_micro_lora_random_1000_3000_summary_20261029.csv'),
        ('RiNALMo-mega', 'RiNALMo 148M', '#D94801',
         'c5c_ncrna_mega_lora_random_summary_20261029.csv'),
    ]
    x = np.arange(len(budgets))
    fig, ax = plt.subplots(figsize=(12.4, 4.6), constrained_layout=True)
    exported = []
    for model, label, color, filename in specs:
        df = pd.read_csv(WORK / filename)
        q = df[(df.model == model) & (df.task == 'noncoding-rna-family') &
               (df.strategy == 'lora') & (df.split == 'random') &
               (df.metric == 'ACC')].copy()
        q['n_train'] = pd.to_numeric(q.n_train, errors='raise').astype(int)
        q = q.set_index('n_train').loc[budgets].reset_index()
        assert len(q) == len(budgets) and q.n_seeds.eq(3).all()
        assert q[['mean', 'sd', 'ci95_halfwidth']].notna().all().all()
        rids = [rid for cell in q.rids for rid in cell.split(';')]
        assert len(rids) == len(set(rids)) == 15
        for row in q.itertuples():
            assert len(row.rids.split(';')) == 3
            assert len(row.best_epochs.split(';')) == 3
        exported.append(q)
        mean = q['mean'].to_numpy(float)
        ci = q.ci95_halfwidth.to_numpy(float)
        ax.errorbar(x, mean, yerr=ci, color=color, marker='o', ms=5.5,
                    lw=2.2, capsize=3, elinewidth=1.1, label=label)
        for xi, yi in zip(x, mean):
            ax.text(xi, yi + 0.009, f'{yi:.3f}', ha='center', va='bottom',
                    fontsize=8.3, color=color)
    all_rids = [rid for q in exported for cell in q.rids for rid in cell.split(';')]
    assert len(all_rids) == len(set(all_rids)) == 30
    output_columns = ['model', 'task', 'strategy', 'split', 'n_train', 'metric',
                      'n_seeds', 'mean', 'sd', 'ci95_halfwidth', 'best_epochs', 'rids']
    pd.concat(exported, ignore_index=True)[output_columns].to_csv(
        OUT / 'c5c_ncrna_lora_micro_mega_data.csv', index=False)
    ax.set_xticks(x)
    ax.set_xticklabels([str(n) for n in budgets], fontsize=10)
    ax.set_xlabel('Labeled sequences (equal-spaced measured budgets)', fontsize=11)
    ax.set_ylabel('ncRNA ACC', fontsize=11)
    all_means = pd.concat(exported)['mean'].to_numpy(float)
    all_ci = pd.concat(exported).ci95_halfwidth.to_numpy(float)
    ax.set_ylim(max(0.0, float((all_means - all_ci).min()) - 0.025),
                min(1.0, float((all_means + all_ci).max()) + 0.025))
    ax.grid(axis='y', color='#E8E8E8', lw=0.7)
    ax.set_axisbelow(True)
    ax.legend(loc='lower right', ncol=2, fontsize=10)
    ax.set_title('⑤c data-size effect | ncRNA | random split | LoRA rank8\n'
                 'corrected best-val | 3-seed mean ± 95% CI',
                 fontsize=13.5, fontweight='bold', color='#1F3A5F', pad=11)
    fig.text(0.5, -0.035,
             'Complete proof only; lines connect measured budgets. 650M and all other C5c arms remain pending; no legacy or imputed points.',
             ha='center', va='top', fontsize=9, color='#666666')
    save_fig(fig, 'c5c_ncrna_lora_micro_mega')


def main():
    configure()
    df = pd.read_csv(WORK / 'mrl_mod_bestval_results_20261028.csv')
    assert len(df) == 180
    assert df.rid.nunique() == 180
    sixbar(df, 'mrl', 'MRL Pearson r (3-seed mean)', 'mrl_bestval_official_sixbar',
           'MRL | official-model best-val comparison', ymax=0.92)
    sixbar(df, 'modification', 'm6A AUC (sequence-level multi-label)', 'modification_bestval_official_sixbar',
           'Modification | corrected sequence-level 12-label task; m6A index 7', ymax=1.08, chance=0.5)
    resource_mrl(df)
    lr_ncrna_mrl()
    extension_fourbar()
    e4_delta_two_tasks()
    crop_valid_panels()
    ncrna_shuffle_audit()
    equivalence_protocol_status()
    ncrna_legacy_quarantine()
    c5c_ncrna_lora_scale()
    equiv_high_ncrna_mrl()
    equiv_low_two_cases()
    memory_ncrna()
    print('Generated figures in', OUT)


if __name__ == '__main__':
    main()
