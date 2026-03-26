#!/bin/bash
set -e
cd "$(dirname "$0")"

echo "=== Step 1: 解决冲突并提交 ==="
git add .gitignore README.md
git rm -rf models/ 2>/dev/null || true
git commit -m "Merge old mirror-sim history and resolve conflicts"

echo ""
echo "=== Step 2: 检查 SSH 认证 ==="
if ssh -T git@github.com 2>&1 | grep -q "successfully authenticated"; then
    echo "✓ SSH 认证成功，切换为 SSH 推送"
    git remote set-url origin git@github.com:WeixianFu/VMirror-SiM.git
    echo ""
    echo "=== Step 3: 推送到 GitHub ==="
    git push -u origin main
    echo ""
    echo "=== 完成！==="
    echo "GitHub: https://github.com/WeixianFu/VMirror-SiM"
else
    echo "✗ SSH 认证未成功，尝试 HTTPS + credential helper..."
    # 尝试使用 macOS Keychain
    git config --local credential.helper osxkeychain
    echo ""
    echo "=== Step 3: 推送到 GitHub (HTTPS) ==="
    git push -u origin main
    echo ""
    echo "=== 完成！==="
    echo "GitHub: https://github.com/WeixianFu/VMirror-SiM"
fi
