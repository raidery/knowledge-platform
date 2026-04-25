# Git 操作指南

本文档记录本项目常用的 Git 操作命令。

## 基本操作

### 查看状态
```bash
git status
```

### 查看差异
```bash
# 查看工作区与暂存区的差异
git diff

# 查看已暂存的变更
git diff --staged

# 查看某个文件的具体变更
git diff <file_path>
```

### 暂存文件
```bash
# 暂存单个文件
git add <file_path>

# 暂存所有变更（包括新增、修改、删除）
git add -A

# 暂存所有已跟踪文件的变更（不包括新文件）
git add -u

# 暂存所有变更（包含新文件、修改、删除）
git add .
```

### 提交变更
```bash
# 提交已暂存的文件
git commit -m "commit message"

# 提交时显示详细的变更统计
git commit --stat

# 修改最后一次提交（追加文件或修改提交信息）
git commit --amend
```

## 分支操作

### 查看分支
```bash
# 查看本地分支
git branch

# 查看所有分支（包括远程）
git branch -a

# 查看分支并显示最后一次提交
git branch -v
```

### 创建与切换分支
```bash
# 创建新分支
git branch <branch_name>

# 切换分支
git checkout <branch_name>

# 创建并切换到新分支
git checkout -b <branch_name>
```

### 合并与删除分支
```bash
# 合并分支到当前分支
git merge <branch_name>

# 删除已合并的分支
git branch -d <branch_name>

# 强制删除分支
git branch -D <branch_name>
```

## 远程操作

### 远程仓库
```bash
# 查看远程仓库
git remote -v

# 添加远程仓库
git remote add <name> <url>

# 拉取远程变更
git pull origin <branch_name>

# 推送变更到远程
git push origin <branch_name>

# 推送所有分支
git push --all origin
```

### 推送当前分支到远程
```bash
git push -u origin <branch_name>
```

## 查看历史

### 提交历史
```bash
# 查看提交历史
git log

# 查看简化的提交历史
git log --oneline

# 查看最近 N 次提交
git log -n <number>

# 查看某个文件的提交历史
git log <file_path>
```

### 查看谁修改了某行代码
```bash
git blame <file_path>
```

## 撤销操作

### 撤销工作区修改
```bash
# 撤销单个文件的修改
git checkout -- <file_path>

# 丢弃所有未暂存的修改
git checkout -- .
```

### 取消暂存
```bash
# 取消暂存单个文件
git reset HEAD <file_path>

# 取消暂存所有文件
git reset HEAD
```

### 回退版本
```bash
# 回退到上一个版本
git reset --hard HEAD^

# 回退到指定版本
git reset --hard <commit_sha>

# 回退前保持修改（软回退）
git reset --soft HEAD^
```

## 标签操作

### 创建标签
```bash
# 创建轻量标签
git tag <tag_name>

# 创建附注标签
git tag -a <tag_name> -m "tag message"
```

### 查看与推送标签
```bash
# 查看所有标签
git tag

# 推送标签到远程
git push origin <tag_name>

# 推送所有标签
git push --tags
```

## 子模块操作

```bash
# 添加子模块
git submodule add <url> <path>

# 初始化子模块
git submodule init

# 更新子模块
git submodule update
```

## 常用工作流

### 提交代码到 GitHub
```bash
# 1. 查看状态
git status

# 2. 暂存变更
git add .

# 3. 提交变更
git commit -m "your commit message"

# 4. 推送到远程
git push origin <branch_name>
```

### 同步远程变更
```bash
# 1. 切换到 main 分支
git checkout main

# 2. 拉取远程变更
git pull origin main

# 3. 创建新分支进行开发
git checkout -b <feature_branch>

# 4. 开发完成后，切换到 main
git checkout main

# 5. 合并新分支
git merge <feature_branch>

# 6. 推送更新
git push origin main
```

## 注意事项

- 提交前务必确认 `git status`，避免提交不必要的文件
- 敏感信息（如 `.env`、密钥等）不要提交到仓库
- 使用有意义的提交信息，便于追溯历史
- 多人协作时，推送前先 `git pull` 拉取最新代码
