#!/usr/bin/env bash
# 为完整 6-max 创建虚拟环境（需 Python 3.11+，以安装 pokerkit）。
# 用法: ./scripts/setup_venv_6max.sh  或  bash scripts/setup_venv_6max.sh
set -e
cd "$(dirname "$0")/.."
PY311=""
for p in python3.11 python3.12 python3.13; do
  if command -v "$p" &>/dev/null; then
    PY311="$p"
    break
  fi
done
if [[ -z "$PY311" ]]; then
  echo "未找到 Python 3.11+。请先安装，例如："
  echo "  Ubuntu: sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update && sudo apt-get install -y python3.11 python3.11-venv"
  echo "  然后重新运行: $0"
  exit 1
fi
echo "使用: $PY311 ($($PY311 --version))"
rm -rf .venv
"$PY311" -m venv .venv
.venv/bin/pip install -U pip
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install 'pokerkit>=0.4.0'
echo "已创建 .venv 并安装依赖（含 pokerkit）。激活: source .venv/bin/activate"
