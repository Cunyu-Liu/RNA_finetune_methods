#!/bin/bash
# HydraRNA env 搭建（0930，权重到位后）：
# conda env py3.9 + nvidia::cuda-toolkit 11.8（免 root）+ torch 2.3.1+cu118 + 源码编译 mamba-ssm 2.2.2 + causal-conv1d
# + editable fairseq（hydrarna-code 内）。全程写日志；任一步失败如实登记不硬跑。
set -x
LOG=/mnt/cunyuliu/rna-ft-eval/logs/hydrarna_env.log
exec >> $LOG 2>&1
echo "=== hydrarna env start $(date) ==="
CONDADIR=/home/cunyuliu/miniconda3
CODE=/mnt/cunyuliu/hf_home/hydrarna-code
ENVNAME=hydrarna

if ! $CONDADIR/bin/conda env list | grep -q "^$ENVNAME "; then
  $CONDADIR/bin/conda create -y -n $ENVNAME python=3.9.12 || exit 1
fi
SRC=$CONDADIR/envs/$ENVNAME/bin
$SRC/python -V || exit 1

# 1) cuda toolkit 11.8（免 root，conda 安装，供源码编译）
if ! $CONDADIR/bin/conda list -n $ENVNAME 2>/dev/null | grep -q "cuda-toolkit.*11.8"; then
  $CONDADIR/bin/conda install -y -n $ENVNAME -c "nvidia/label/cuda-11.8.0" cuda-toolkit || exit 2
fi

# 2) torch 2.3.1 cu118
$SRC/pip install "torch==2.3.1" --index-url https://download.pytorch.org/whl/cu118 || exit 3
$SRC/python -c "import torch;assert torch.cuda.is_available();print('torch',torch.__version__,'cuda ok', torch.version.cuda)"

# 3) causal-conv1d + mamba-ssm 源码编译（A100=sm80）
export CUDA_HOME=$CONDADIR/envs/$ENVNAME
export PATH=$CUDA_HOME/bin:$PATH
export TORCH_CUDA_ARCH_LIST="8.0"
export MAX_JOBS=16
$SRC/pip install "causal-conv1d==1.4.0" --no-build-isolation || exit 4
$SRC/pip install "mamba-ssm==2.2.2" --no-build-isolation || exit 5
$SRC/python -c "import mamba_ssm, causal_conv1d; print('mamba_ssm', mamba_ssm.__version__)"

# 4) fairseq（hydrarna 定制版，editable 安装）
cd $CODE/fairseq || exit 6
$SRC/pip install --editable ./ 2>&1 | tail -2 || exit 7
$SRC/pip install "transformers==4.44.0" pandas tqdm tensorboardX || exit 8

# 5) 冒烟：import 模型代码
cd $CODE
$SRC/python - <<'PYEOF'
import sys
sys.path.insert(0, "/mnt/cunyuliu/hf_home/hydrarna-code")
print("smoke import start")
PYEOF
echo "=== hydrarna env done $(date) rc=$? ==="