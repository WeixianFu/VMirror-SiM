#!/bin/bash
# ============================================================
# VMirror-SiM Git 融合脚本
# 在你的 Mac 终端中运行此脚本
# ============================================================

set -e

# --- 配置 ---
GITHUB_REPO="https://github.com/WeixianFu/mirror-sim.git"
VMIRROR_DIR="$(cd "$(dirname "$0")" && pwd)"  # 当前 VMirror-SiM 目录
TEMP_CLONE="/tmp/mirror-sim-clone"

echo "=== Step 1: 克隆 GitHub 远端仓库 ==="
rm -rf "$TEMP_CLONE"
git clone "$GITHUB_REPO" "$TEMP_CLONE"

echo ""
echo "=== Step 2: 从远端复制有价值的代码文件 ==="
# 复制 src/ 目录（核心代码 + notebooks）
cp -r "$TEMP_CLONE/src/"* "$VMIRROR_DIR/src/"
echo "  ✓ src/ 已复制（含 sim_1.ipynb, sim_raysect.ipynb 等）"

# 复制 LICENSE
cp "$TEMP_CLONE/LICENSE" "$VMIRROR_DIR/"
echo "  ✓ LICENSE 已复制"

# 复制 pyproject.toml
cp "$TEMP_CLONE/pyproject.toml" "$VMIRROR_DIR/"
echo "  ✓ pyproject.toml 已复制"

echo ""
echo "=== Step 3: 初始化 Git 仓库 ==="
cd "$VMIRROR_DIR"
git init
git add .
git commit -m "Initial commit: restructure project as VMirror-SiM

Merged local assets and GitHub mirror-sim codebase:
- docs/: project documentation and AI generation prompts
- src/: Python scripts and simulation notebooks (from GitHub)
- assets/reference-images/: AI model generation reference images
- assets/models/: 3D models (.gitignored, local only)
- config/, renders/, results/: placeholder directories"

echo ""
echo "=== Step 4: 设置 GitHub 远端 ==="
echo ""
echo "⚠️  请先在 GitHub 上进行以下操作："
echo "   1. 打开 https://github.com/WeixianFu/mirror-sim/settings"
echo "   2. 在 'Repository name' 中改为 'VMirror-SiM'"
echo "   3. 点击 'Rename'"
echo ""
echo "完成后，运行以下命令推送："
echo ""
echo "  cd $VMIRROR_DIR"
echo "  git remote add origin https://github.com/WeixianFu/VMirror-SiM.git"
echo "  git branch -M main"
echo "  git push -u origin main --force"
echo ""
echo "或者如果你不想覆盖远端历史，可以用合并方式："
echo ""
echo "  git remote add origin https://github.com/WeixianFu/VMirror-SiM.git"
echo "  git fetch origin"
echo "  git merge origin/main --allow-unrelated-histories -m 'Merge old mirror-sim history'"
echo "  git push -u origin main"
echo ""

# 清理临时目录
rm -rf "$TEMP_CLONE"

echo "=== 完成！==="
echo "VMirror-SiM 目录: $VMIRROR_DIR"
