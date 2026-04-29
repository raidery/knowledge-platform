# Claude Code 配置：OpenSpec + Superpowers + Gstack

## 概述

三个插件组成主干：

| 插件 | 职责 | 类比 |
|------|------|------|
| **OpenSpec** | 规范与需求层（proposal / design / tasks） | 蓝图 |
| **Superpowers** | 思考与流程层（plan / brainstorm / debug / TDD / review / verify） | 大脑 |
| **Gstack** | 执行与外部世界层（browser / QA / ship / deploy / canary / 护栏） | 手脚 |

---

## 核心原则

1. **规范先行**：任何需求变更必须先过 OpenSpec，调用 `/opsx:propose`，产出 `proposal.md` + `design.md` + `tasks.md`，再动手写代码。
2. **流程归 Superpowers**：brainstorm、plan、debug、TDD、verify、code review 默认走 Superpowers，不走 OMC / feature-dev 等同名第三方 skill。
3. **执行归 Gstack**：浏览器、QA、ship、deploy、canary、retro 走 Gstack。
4. **独立 Reviewer 通道**：verification 和 code-review 分两个 pass，不能在同一上下文里合并。
5. **证据优先**：没有测试/截图/QA 报告不算完成。
6. **歧义先 Brainstorm**：任何创造性工作前先调用 brainstorming。
7. **最短路径优先**：能用一个 skill 解决的，不升级为完整闭环。

---

## OpenSpec 规范工作流

### 双文件夹模型

```
openspec/
  specs/      # 当前系统的事实来源（规范文件）
  changes/    # 每次变更的完整提案
```

### 每份变更必须包含三个文件

| 文件 | 用途 |
|------|------|
| `proposal.md` | 为什么要做（背景、目标、成功标准、不做会怎样） |
| `design.md` | 技术方案（架构决策、接口设计、数据流、依赖关系） |
| `tasks.md` | 实施清单（可执行的具体任务，作为 Superpowers 的输入） |

### 职责边界

- **OpenSpec** 只产出规范文档，不写代码。
- **Superpowers** 只按 `tasks.md` 执行编码流程，不修改 OpenSpec 规范。
- **Gstack** 只做验证和交付动作，不参与需求分析或架构决策。
- 三者之间通过**文件和命令**传递信息，不通过共享内存或隐式状态。

### 规范与执行的衔接

```
需求输入
    ↓
OpenSpec 输出 tasks.md
    ↓
tasks.md 作为 Superpowers 的输入启动 brainstorming
    ↓
编码执行过程中如发现规范遗漏或错误
    ↓
回退到 OpenSpec 更新 design.md / tasks.md，再继续执行
```

---

## 任务分流

### 只读任务

分析、解释、架构说明、代码阅读 —— 直接处理。
真实 bug 排查但尚未修改 —— 用 `systematic-debugging`。

### 轻量任务

单文件或小范围修改、明确 bug 修复、配置/文案调整、小测试补充。

跳过完整 brainstorming / writing-plans / worktrees / 重 review 链。直接实现 + 定向验证 + 必要时 `/browse` 看效果。

### 中任务

多文件但边界清晰，新功能或明确的重构。

```
OpenSpec /opsx:propose（必须首先调用）
    ↓
简短 brainstorming + 短 writing-plans
    ↓
实现
    ↓
/browse 或 /qa + verification
```

### 大任务

跨模块、共享逻辑、新架构、公共 API 变更。完整闭环：

```
OpenSpec /opsx:propose（必须首先调用）
    ↓
brainstorming → writing-plans → /plan-*-review
    ↓
executing-plans + worktrees + TDD
    ↓
/qa → verification → code-review
    ↓
finishing-branch → /ship → /land-and-deploy → /canary
```

---

## 浏览器规则

`/browse` 是唯一的浏览器入口。**禁止**使用 `mcp__claude-in-chrome__*` 和 `mcp__computer-use__*` 来操作浏览器。

---

## Subagent 策略

**一定派子代理**：
- 用户明说 "并行 / parallel / dispatch"
- 2-4 个边界清晰、独立验证、无共享状态的子任务
- 纯只读的多目标研究

**一定不派**：
- 任务有顺序依赖
- 多个子任务改同一文件 / contract / shared types
- `package.json` / lockfile / 根配置 / CI / schema / 总入口 默认串行
- 单一目标的 bug 修复
- 根因未明的调试

---

## 安全护栏

- `rm -rf` / `DROP TABLE` / `force-push` / `git reset --hard` / `kubectl delete` 必须先过 `/careful` 或 `/guard`
- 调试敏感模块时用 `/freeze` 限定可改范围
- `/ship` 和 `/land-and-deploy` 必须用户明确确认
- 密钥/凭证/API Key 不得硬编码
- 数据库访问用参数化查询
- 不用不可信输入拼接 shell 命令或 SQL

---

## Change Delivery Gate

声明完成、准备 commit / push / PR 之前必须满足：

1. 已完成相关验证，并如实报告结果
2. 已过对应质量门禁（review / verification）
3. 关键验证无法执行时必须明确说明原因
4. 禁止虚构命令输出
5. 没有验证证据，不得声称"通过" / "完成"

---

## 不要重复造轮子

### 需求分析
- 先用 `/opsx:propose`
- proposal / design / tasks 文档编写
- 规范评审、技术方案确认
- `tasks.md` 作为 Superpowers 的唯一输入

### 只走 Superpowers
- plan / brainstorming / writing-plans / executing-plans
- TDD / debugging / verification
- code review / subagent / worktrees / 分支收尾

### 只走 Gstack
- 浏览器、QA、ship、deploy、canary、retro、document-release
- 多视角 plan review (CEO / Eng / Design)
- 危险命令护栏 / freeze 沙箱
- 安全审计 / design-consultation / investigate
