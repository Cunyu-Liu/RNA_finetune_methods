"""Clean stale pending E6 rows (e6_v2 OOM batch) + kill old racing daemons."""
import json
import subprocess

# 1. ledger clean
p = '/root/rnaft/ledger.jsonl'
lines = open(p).read().strip().split('\n')
out = []
for l in lines:
    try:
        d = json.loads(l)
    except Exception:
        out.append(l)
        continue
    if d.get('task') == 'e6-forgetting' and d.get('status') == 'pending':
        continue
    # AIDO mrl v3/v4 failed attempts also pending
    if d.get('run_id', '').startswith('ft_aidorna16b_mrl_full_s43') and d.get('status') == 'pending':
        continue
    out.append(l)
open(p, 'w').write('\n'.join(out) + '\n')
print('ledger kept', len(out))

# 2. kill old racing daemons (e6_v2/aido_retry4/q_diag already done or superseded by master)
for pat in ('e6_v2.sh', 'aido_retry4.sh', 'q_diag.sh'):
    subprocess.run(['pkill', '-f', pat], capture_output=True)
    print('killed', pat)
print('done')
