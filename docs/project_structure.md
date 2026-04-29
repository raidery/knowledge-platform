# RAG 知识平台项目结构

## 目录结构

```
knowledge-platform/
├── apps/
│   ├── rbac/                      # 🔴 独立抽出的 RBAC 管理模块
│   │   ├── main.py
│   │   ├── api/                   # 用户/角色/菜单/API 管理
│   │   ├── services/              # 权限校验逻辑
│   │   ├── models/                # User, Role, Menu, Api, Dept, AuditLog
│   │   └── schemas/               # Pydantic models
│   │
│   ├── kb_service/                # 🟣 核心知识库编排服务
│   │   ├── main.py
│   │   ├── api/
│   │   │   ├── ingest.py           # 新建知识库/文档入库 API
│   │   │   ├── update.py          # 文档更新 API
│   │   │   ├── publish.py         # 发布 API
│   │   │   ├── rollback.py         # 回滚 API
│   │   │   ├── query.py           # 查询业务知识库状态
│   │   │   └── feedback.py        # 业务反馈 API（点赞/点踩）
│   │   ├── services/
│   │   │   ├── business_registry.py # 业务注册与知识库映射
│   │   │   ├── parser_service.py   # docx/pdf/ocr 解析
│   │   │   ├── chunk_service.py    # 分块策略
│   │   │   ├── metadata_service.py # 元数据标准化
│   │   │   ├── diff_service.py     # 版本差异比对
│   │   │   ├── release_service.py  # 发布/灰度/生效
│   │   │   ├── audit_service.py    # 审计日志
│   │   │   ├── eval_service.py      # 离线评估服务（RAGAS/TruLens）
│   │   │   └── context_service.py  # 上下文增强（给前端展示历史记录）
│   │   ├── utils/
│   │   │   └── redis_cache.py      # 语义缓存（Semantic Cache）
│   │   ├── clients/
│   │   │   └── dify_client.py      # Dify API 封装
│   │   └── schemas/
│   │       └── chat_schema.py      # 定义输入输出格式
│   │
│   ├── future_business/           # 🟢 未来新增业务预留
│   │
│   ├── chunk_policy.yaml          # 分块策略
│   ├── dify_datasets.yaml         # Dify 数据集映射
│   ├── ragflow_collections.yaml   # RAGFlow collection 映射
│   └── workflow_rules.yaml         # 发布/更新规则
│
├── storage/
│   ├── postgres/                   # 元数据、版本、审计
│   └── object_storage/           # 原始文档、解析中间件
│
├── pipelines/
│   ├── ingest_pipeline.py         # 新建业务/首次入库流程
│   ├── update_pipeline.py         # 文档更新流程
│   ├── publish_pipeline.py        # 发布流程
│   └── rollback_pipeline.py       # 回滚流程
│
├── workflows/
│   ├── dify/
│   │   ├── loan_chatflow.yaml     # 贷款业务 Chatflow
│   │   ├── risk_chatflow.yaml     # 风控业务 Chatflow
│   │   └── ...
│   └── templates/
│       └── ...
│
└── docs/
    ├── project_structure.md       # 项目结构文档
    └── standards/
        ├── metadata_spec.md       # 元数据规范
        ├── versioning_spec.md     # 版本管理规范
        └── chunking_spec.md       # 分块策略规范
```

## 核心模块说明

### apps/rbac

独立抽出的 RBAC 管理模块，提供平台级基础设施。

**职责**
- 用户管理（User）
- 角色与权限管理（Role、Menu、Api）
- 部门管理（Dept）
- 审计日志（AuditLog）

**内部结构**
| 层级 | 说明 |
|------|------|
| api/ | 用户/角色/菜单/API 管理接口 |
| services/ | 权限校验逻辑 |
| models/ | User, Role, Menu, Api, Dept, AuditLog |
| schemas/ | Pydantic 请求/响应模型 |

### apps/kb_service

核心知识库编排服务，负责文档从入库到发布的全生命周期管理。

**API 层 (api/)**
- `ingest.py` - 新建知识库/文档首次入库
- `update.py` - 文档增量更新
- `publish.py` - 正式发布与灰度发布
- `rollback.py` - 版本回滚
- `query.py` - 查询业务知识库状态
- `feedback.py` - 业务反馈接口（点赞/点踩）

**Service 层 (services/)**
| 服务 | 职责 |
|------|------|
| business_registry | 业务注册与知识库映射 |
| parser_service | docx/pdf/ocr 文档解析 |
| chunk_service | 文档分块策略执行 |
| metadata_service | 元数据标准化 |
| diff_service | 版本间差异比对 |
| release_service | 发布/灰度/生效控制 |
| audit_service | 操作审计日志 |
| eval_service | 离线评估服务（检索召回率、幻觉率） |
| context_service | 上下文增强（发送给 Dify 前捞取最近 3 轮记录） |

**Utils 层 (utils/)**
| 工具 | 职责 |
|------|------|
| redis_cache | 语义缓存（Semantic Cache），高频问题直接返回 |

**Client 层 (clients/)**
- `dify_client.py` - Dify API 封装

### apps/future_business

预留的未来业务扩展目录。

### storage

- `postgres/` - PostgreSQL 存储：元数据、版本记录、审计日志
- `object_storage/` - 对象存储：原始文档、解析中间产物

### pipelines

批处理流水线，封装完整业务流程：

- `ingest_pipeline.py` - 新建业务或首次入库
- `update_pipeline.py` - 文档更新流程
- `publish_pipeline.py` - 发布流程
- `rollback_pipeline.py` - 回滚流程

### workflows

业务对话流配置：

- `dify/` - 各业务的 Chatflow YAML（如贷款、风控等）
- `templates/` - 通用对话流模板

### docs/standards

技术规范文档：

- `metadata_spec.md` - 元数据规范
- `versioning_spec.md` - 版本管理规范
- `chunking_spec.md` - 分块策略规范

## 评价与反馈体系

### 离线评估 (eval_service)

接入 RAGAS 或 TruLens 等工具，对 RAG 系统进行离线评估：

- **检索召回率** - 评估向量检索是否命中正确答案
- **幻觉率检测** - 评估生成回答的准确率
- **答案相关性** - 评估回答与问题的匹配程度

### 业务反馈 (feedback.py)

记录业务人员的实时反馈，用于后期调优：

- 点赞/点踩操作持久化到数据库
- 与 eval_service 形成闭环，持续优化知识库质量

## 缓存层 (Semantic Cache)

高频重复性问题（如"如何开户"、"理财产品利率"）直接返回缓存答案，无需打到 Dify：

- **原理**：请求到达 Dify 前，先在向量数据库搜索高度匹配的既往问题
- **收益**：节省 Token 消耗、降低响应延迟
- **实现**：`apps/kb_service/utils/redis_cache.py`

## 配置说明

| 配置文件 | 用途 |
|----------|------|
| `chunk_policy.yaml` | 定义文档分块策略 |
| `dify_datasets.yaml` | Dify 数据集与业务的映射关系 |
| `ragflow_collections.yaml` | RAGFlow collection 映射 |
| `workflow_rules.yaml` | 发布与更新的业务规则 |


```
flowchart TD
    %% ========== 样式定义 配色分区 ==========
    classDef userLayer fill:#e6f7ff,stroke:#1890ff,stroke-width:1px
    classDef gatewayLayer fill:#f0f8fb,stroke:#00b96b,stroke-width:1px
    classDef coreLayer fill:#fff7e6,stroke:#faad14,stroke-width:1px
    classDef rbacLayer fill:#fef0f0,stroke:#f5222d,stroke-width:1px
    classDef extendLayer fill:#f6ffed,stroke:#52c41a,stroke-width:1px
    classDef pipelineLayer fill:#f9f0ff,stroke:#722ed1,stroke-width:1px
    classDef configLayer fill:#fff2e8,stroke:#ff7a45,stroke-width:1px
    classDef storageLayer fill:#f1f3f5,stroke:#4e5969,stroke-width:1px
    classDef externalLayer fill:#e8f4f8,stroke:#036672,stroke-width:1px

    %% ========== 接入层 ==========
    U1["业务终端用户"]:::userLayer
    U2["平台管理员/运维"]:::userLayer

    %% ========== 网关会话层 ==========
    subgraph Gateway ["🍃 问答网关层"]
        CG["chat_gateway<br/>统一会话管理 / 上下文串联 / 流式应答"]
    end
    class Gateway,CG gatewayLayer

    %% ========== 核心业务服务层 ==========
    subgraph RBAC ["🔐 权限管控模块"]
        RB["rbac 服务<br/>用户/角色/部门/菜单/接口鉴权/操作审计"]
    end
    class RBAC,RB rbacLayer

    subgraph KBCore ["📚 知识库核心服务 kb_service"]
        KB_API["API层<br/>文档入库/更新/发布/回滚/用户反馈"]
        KB_SVC["业务服务层<br/>文档解析·分块·版本比对·发布灰度·RAG评估Eval"]
        KB_UTIL["工具能力<br/>Redis语义缓存 / 文本处理 / 文件转换"]
        KB_CLI["外部客户端<br/>Dify API 统一封装"]
    end
    class KBCore,KB_API,KB_SVC,KB_UTIL,KB_CLI coreLayer

    %% ========== 扩展预留层 ==========
    subgraph Extend ["🚀 业务扩展层"]
        FB["future_business<br/>新业务模块预留隔离目录"]
    end
    class Extend,FB extendLayer

    %% ========== 流程编排层 ==========
    subgraph Pipeline ["⚙️ 流程编排层"]
        PIPE["pipelines<br/>标准化流水线<br/>入库/更新/发布/回滚全流程"]
    end
    class Pipeline,PIPE pipelineLayer

    %% ========== 配置&工作流层 ==========
    subgraph Config ["📋 配置&工作流管理层"]
        CFG["configs 全局配置<br/>分块策略/Dify映射/发布规则"]
        DIFY_WF["workflows/dify<br/>各业务独立Chatflow编排"]
    end
    class Config,CFG,DIFY_WF configLayer

    %% ========== 存储层 ==========
    subgraph Storage ["💾 持久化存储层"]
        PG["PostgreSQL<br/>元数据/版本/会话/审计/评价反馈数据"]
        OSS["对象存储<br/>原始文档/解析中间文件/附件资源"]
    end
    class Storage,PG,OSS storageLayer

    %% ========== 外部依赖层 ==========
    subgraph External ["🌐 外部依赖服务"]
        DIFY["Dify 平台<br/>大模型调用/检索编排/知识库问答工作流"]
    end
    class External,DIFY externalLayer

    %% ========== 业务流向连线 ==========
    U1 --> Gateway
    U2 --> RBAC

    Gateway --> KBCore
    Gateway --> RBAC

    KBCore --> Pipeline
    KBCore --> External
    KBCore --> Storage

    Pipeline --> Config
    DIFY_WF --> CFG

    RBAC --> Storage
    Extend -.-> KBCore

```