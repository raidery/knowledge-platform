# Git 常用命令

## 提交代码

```bash
# 1. 查看状态
git status

# 2. 暂存所有变更
git add -A

# 3. 提交
git commit -m "提交信息"

# 4. 推送到远程
git push origin main
```

## 拉取代码

```bash
# 拉取远程最新代码
git pull origin main
```

## 工作流（推荐）

```bash
# 使用 worktree 创建独立工作区
git worktree add .claude/worktrees/<分支名> -b <分支名>

# 在 worktree 中开发...
git add -A && git commit -m "xxx" && git push origin <分支名>

# 开发完成后移除 worktree
git worktree remove .claude/worktrees/<分支名>
```
