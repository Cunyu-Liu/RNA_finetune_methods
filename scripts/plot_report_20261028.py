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
    df = pd.read_csv(HAND / 'archive_20261028/绘图数据/figures_v2_20261025/status/status_tables_figs/c4_table.csv')
    models = ['RiNALMo-micro', 'RiNALMo-mega', 'RiNALMo-650M', 'ERNIE-RNA', 'RNA-FM',
              'RNA-Sc-10M', 'RNA-Sc-30M', 'RNA-Sc-100M', 'NucleicBERT', 'AIDO.RNA-1.6B']
    short = ['RiNALMo\n33M', 'RiNALMo\n148M', 'RiNALMo\n650M', 'ERNIE\n86M', 'RNA-FM\n99M',
             'RNA-Sc\n10M', 'RNA-Sc\n30M', 'RNA-Sc\n100M', 'NucleicBERT\n404M', 'AIDO\n1.6B']
    tasks = [('noncoding-rna-family', 'ncRNA ACC'), ('mrl', 'MRL Pearson r')]
    fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.1), constrained_layout=True)
    out_rows = []
    for ax, (task, label) in zip(axes, tasks):
        x = np.arange(len(models))
        width = 0.25
        for j, strategy in enumerate(['frozen', 'lora', 'full']):
            vals = []
            for model in models:
                q = df[(df.model == model) & (df.task == task) & (df.strategy == strategy)]
                v = float(q.iloc[0].delta) if len(q) else np.nan
                vals.append(v)
                out_rows.append({'task': task, 'model': model, 'strategy': strategy, 'delta_random_minus_family': v})
            ax.bar(x + (j - 1) * width, vals, width=width * 0.92,
                   color=['#6BAED6', '#FD8D3C', '#D94801'][j], label=strategy)
        ax.axhline(0, color='#555555', lw=0.8)
        ax.set_title(label, fontsize=12, fontweight='bold', color='#1F3A5F')
        ax.set_xticks(x)
        ax.set_xticklabels(short, fontsize=8, rotation=35, ha='right', rotation_mode='anchor')
        ax.set_ylabel('Δ = random − family')
        ax.grid(axis='y', color='#ECECEC', lw=0.6)
        ax.set_axisbelow(True)
    axes[0].legend(ncol=3, loc='upper left', fontsize=9)
    fig.suptitle('Random−family difference | valid ncRNA and MRL legacy panels only',
                 fontsize=13.5, fontweight='bold', color='#1F3A5F')
    pd.DataFrame(out_rows).to_csv(OUT / 'e4_delta_two_tasks_data.csv', index=False)
    save_fig(fig, 'e4_delta_two_tasks')


def equiv_high_ncrna_mrl():
    pairs = pd.read_csv(WORK / 'equiv_high_pairs_legacy_20261028.csv')
    curves = pd.read_csv(WORK / 'equiv_high_curves_legacy_20261028.csv')
    tasks = [('noncoding-rna-family', 'ncRNA ACC'), ('mrl', 'MRL Pearson r')]
    fig, axes = plt.subplots(2, 2, figsize=(11.8, 6.2), constrained_layout=True)
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
        ax.set_title(f'{metric}: full@{int(pair.full_n_train)} vs LoRA@{int(pair.lora_n_train)}',
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
    fig.suptitle('Local data-budget equivalence | RiNALMo-micro | family split | legacy exploration',
                 fontsize=14, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.025, 'Valid ncRNA and MRL panels only; full = grid-best, LoRA = 3e-4; MRL is not a 3n rule; 8-task controlled equivalence remains pending',
             ha='center', va='top', fontsize=9, color='#666666')
    save_fig(fig, 'e3_equiv_high_ncrna_mrl_only')


def equiv_low_two_cases():
    pairs = pd.read_csv(WORK / 'equiv_low_pairs_legacy_20261028.csv')
    curves = pd.read_csv(WORK / 'equiv_low_curves_legacy_20261028.csv')
    fig, axes = plt.subplots(2, 2, figsize=(11.8, 6.2), constrained_layout=True)
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
    fig.suptitle('Low-budget local comparisons | family split | legacy exploration',
                 fontsize=14, fontweight='bold', color='#1F3A5F')
    fig.text(0.5, -0.025, 'Two valid historical cases only; full = grid-best, LoRA = 3e-4; no universal 3n or threshold rule; 8-task controlled equivalence remains pending',
             ha='center', va='top', fontsize=9, color='#666666')
    save_fig(fig, 'e3_equiv_low_two_cases')


def memory_ncrna():
    df = pd.read_csv(HAND / 'archive_20261028/绘图数据/figures_v2_20261025/status/status_tables_figs/resources_costbenefit.csv')
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
    # Only crop and re-layout previously validated panels. No values are read from pixels.
    navy = '#1F3A5F'
    gray = '#666666'

    def scaler(src, base):
        sx, sy = src.width / base[0], src.height / base[1]
        def box(values):
            return tuple(round(v * (sx if i % 2 == 0 else sy)) for i, v in enumerate(values))
        def pt(x, y):
            return round(x * sx), round(y * sy)
        return box, pt, lambda size: font(max(8, round(size * sx)))

    # E3: retain ncRNA, MRL and 100M re-test, remove invalid modification and its summary.
    src = Image.open(PPT / 'fig_ppt_e3_3tasks.png').convert('RGB')
    box, pt, fs = scaler(src, (1022, 518))
    out = Image.new('RGB', src.size, 'white')
    d = ImageDraw.Draw(out)
    center(d, pt(511, 17), 'E3 data-size effect | ncRNA and MRL valid legacy panels; no universal immunity claim', fs(16), navy)
    out.paste(src.crop(box((0, 35, 1022, 250))), pt(0, 35))
    out.paste(src.crop(box((0, 250, 256, 492))), pt(220, 252))
    out.paste(src.crop(box((766, 250, 1022, 492))), pt(548, 252))
    center(d, pt(511, 507), '旧 per-base m6A 面板与相关总结已移除；其余 8 任务数据量曲线按 best-val 补测', fs(10), gray)
    out.save(OUT / 'e3_ncrna_mrl_only.png')




def main():
    configure()
    df = pd.read_csv(WORK / 'mrl_mod_bestval_results_20261028.csv')
    assert len(df) == 180
    assert df.rid.nunique() == 180
    fourbar(df, 'mrl', 'MRL Pearson r (3-seed mean)', 'mrl_bestval_official_fourbar',
            'MRL | official-model best-val comparison', ymax=0.92)
    fourbar(df, 'modification', 'm6A AUC (sequence-level multi-label)', 'modification_bestval_official_fourbar',
            'Modification | corrected sequence-level 12-label task; m6A index 7', ymax=1.08, chance=0.5)
    resource_mrl(df)
    lr_ncrna_mrl()
    extension_fourbar()
    e4_delta_two_tasks()
    crop_valid_panels()
    equiv_high_ncrna_mrl()
    equiv_low_two_cases()
    memory_ncrna()
    print('Generated figures in', OUT)


if __name__ == '__main__':
    main()
