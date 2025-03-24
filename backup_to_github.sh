#!/bin/bash

# 定义你的 Git 仓库目录
REPO_DIR="/home/ubuntu/web"
cd $REPO_DIR || { echo "目录 $REPO_DIR 不存在"; exit 1; }

# 获取当前时间作为 commit 信息
TIMESTAMP=$(date "+%Y-%m-%d %H:%M:%S")

# 添加所有更改
git add .

# 提交更改
git commit -m "Auto backup: $TIMESTAMP"

# 推送到 GitHub
git push origin main

echo "备份完成！"
