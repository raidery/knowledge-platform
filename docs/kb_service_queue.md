# KB Service Redis Queue 使用指南

本文档介绍了如何在 KB Service 中使用 Redis Queue (RQ) 来异步处理任务。

## 目录结构

```
apps/kb_service/
├── core/
│   └── queue.py          # 队列管理器
├── workers/
│   ├── tasks.py          # 任务处理器
│   └── start_worker.py   # Worker 启动脚本
└── api/
    └── monitor.py        # 队列监控 API

scripts/
├── start_rq_dashboard.sh # 启动 RQ Dashboard 脚本
└── start_all.sh          # 启动所有服务脚本
```

## 功能特性

1. **智能队列处理**：根据文件大小自动决定是否使用队列异步处理（默认阈值1MB）
2. **多种队列**：支持 default、ingest、batch 等不同类型的任务队列
3. **队列监控**：提供 API 接口和 Web UI 监控队列状态和任务执行情况
4. **Worker 管理**：可启动多个 Worker 进程处理队列任务
5. **环境变量配置**：通过 `.env` 文件配置 Redis 连接和队列阈值

## 使用方法

### 1. 配置环境变量

复制 `.env.example` 文件并根据需要修改配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```bash
# 文件大小阈值，超过此大小的文件将使用队列异步处理
# 支持多种格式: 字节数(1048576) 或 带单位(1M, 1MB, 1m, 1mb)
QUEUE_SIZE_THRESHOLD=1M

# Redis Connection
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
REDIS_PASSWORD=Pass@1234
```

### 2. 启动 Redis 服务器

确保 Redis 服务器正在运行：
```bash
redis-server
```

### 3. 启动 Worker 进程

在项目根目录下启动 Worker：
```bash
# 启动默认队列的 Worker
python apps/kb_service/workers/start_worker.py

# 启动指定队列的 Worker
python apps/kb_service/workers/start_worker.py --queues ingest batch
```

### 4. 启动服务

有两种方式启动服务：

#### 方式一：分别启动各服务
```bash
# 启动主应用
python run.py

# 启动 RQ Dashboard (在另一个终端)
./scripts/start_rq_dashboard.sh
```

#### 方式二：一键启动所有服务
```bash
./scripts/start_all.sh
```

### 5. 使用队列 API

API 会根据文件大小自动决定是否使用队列处理，无需手动指定参数：

#### 文档摄入接口
```bash
# 小文件（<=1MB）同步处理
curl -X POST "http://localhost:9999/api/v1/kb/ingest" \
  -F "file=@small_document.txt" \
  -F "business_id=test_business"

# 大文件（>1MB）自动使用队列异步处理
curl -X POST "http://localhost:9999/api/v1/kb/ingest" \
  -F "file=@large_document.pdf" \
  -F "business_id=test_business"
```

#### 批量摄入接口
```bash
curl -X POST "http://localhost:9999/api/v1/kb/batch/ingest" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "test_business",
    "directory_path": "/path/to/documents",
    "file_patterns": ["*.pdf", "*.docx"]
  }'
```

### 6. 监控队列状态

#### 通过 API 监控

提供了一系列监控 API 来查看队列状态：

##### 查看所有队列信息
```bash
curl "http://localhost:9999/api/v1/kb/monitor/queues"
```

##### 查看特定队列信息
```bash
curl "http://localhost:9999/api/v1/kb/monitor/queues/ingest"
```

##### 清空队列
```bash
curl -X DELETE "http://localhost:9999/api/v1/kb/monitor/queues/ingest"
```

#### 通过 Web UI 监控

访问 RQ Dashboard Web 界面：
```
http://localhost:9099
```

## 配置

### 环境变量配置

所有配置都通过环境变量进行管理，在 `.env` 文件中设置：

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| QUEUE_SIZE_THRESHOLD | 1M (1048576 bytes) | 文件大小阈值，支持多种格式 |
| REDIS_HOST | localhost | Redis 主机地址 |
| REDIS_PORT | 6379 | Redis 端口 |
| REDIS_DB | 0 | Redis 数据库编号 |
| REDIS_PASSWORD | None | Redis 密码 |
| RQ_DASHBOARD_PORT | 9099 | RQ Dashboard 端口 |

## 最佳实践

1. **生产环境部署**：建议使用进程管理工具（如 systemd、supervisor）来管理 Worker 进程
2. **错误处理**：Worker 会自动重试失败的任务，但需要注意日志监控
3. **性能优化**：可以根据任务类型启动不同数量的 Worker 进程
4. **监控告警**：定期检查队列长度，避免任务积压
5. **合理设置阈值**：根据实际业务场景调整 `QUEUE_SIZE_THRESHOLD` 值，支持多种格式如 `1M`、`1MB`、`1048576` 等

## 故障排除

1. **Worker 无法启动**：检查 Redis 服务器是否正常运行
2. **任务执行失败**：查看 Worker 日志获取详细错误信息
3. **队列积压**：增加 Worker 数量或优化任务处理逻辑
4. **Dashboard 无法访问**：检查端口是否被占用，防火墙设置等