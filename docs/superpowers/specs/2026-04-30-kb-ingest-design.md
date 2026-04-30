# KB Service 文档上传页面设计

**日期**: 2026-04-30
**状态**: Approved
**范围**: KB Service `/ingest` API 的前端调用页面

---

## 1. 背景

后端已实现 `POST /api/v1/kb_service/ingest` 端点，支持文档上传、队列异步处理和切分。本设计为该 API 搭建前端页面，Phase 1 仅实现一次性上传 + 结果展示。

---

## 2. 页面功能（Phase 1）

### 2.1 独立上传页面 (`/kb_service/ingest`)

- 文件选择（支持拖拽）
- business_id 输入框（必填）
- 上传按钮
- 上传成功后展示结果卡片（job_id、doc_id、status、sections_count）

### 2.2 工作台嵌入

- 在 `views/workbench/index.vue` 嵌入 IngestUploader 卡片

---

## 3. 组件结构

```
web/src/
├── api/
│   └── kb_service.js          # 新增：KB Service API（ingest）
├── components/
│   └── kb/
│       └── ingest_uploader.vue  # 新增：可复用上传组件
├── views/
│   ├── kb_service/
│   │   └── ingest.vue          # 新增：独立上传页面
│   └── workbench/
│       └── index.vue           # 修改：嵌入 IngestUploader
```

---

## 4. API 设计

**端点**: `POST /api/v1/kb_service/ingest`

**请求体** (multipart/form-data):
- `file`: File
- `business_id`: string (必填)
- `dataset_id`: string (可选)
- `callback_url`: string (可选)
- `enable_split`: boolean (默认 false)
- `pages_per_chunk`: number (默认 50)
- `max_chunks`: number (默认 100)
- `split_level`: number (可选)
- `split_pattern`: string (可选)
- `force_split`: boolean (默认 false)

**响应** (IngestResponse):
- `job_id`: string
- `doc_id`: string
- `status`: string ("queued" | "completed")
- `created_at`: string
- `sections_count`: number | null
- `sections`: SectionMeta[] | null

---

## 5. 结果卡片展示字段

| 字段 | 说明 |
|------|------|
| job_id | 任务 ID |
| doc_id | 文档 ID（同步时返回） |
| status | queued / completed |
| created_at | 创建时间 |
| sections_count | 切分段数量（若有） |

---

## 6. 路由

```js
{
  path: '/kb_service/ingest',
  name: 'KbIngest',
  component: () => import('@/views/kb_service/ingest.vue'),
  meta: { title: '文档上传' }
}
```

---

## 7. 后续扩展（Phase 2-4）

- Phase 2: 历史任务列表管理
- Phase 3: 高级切分配置面板
- Phase 4: 实时进度追踪

---

## 8. 技术选型

- **UI 框架**: Naive UI (`n-upload`, `n-card`, `n-form`, `n-input`)
- **HTTP**: 复用现有 `@/utils/request` Axios 封装
- **样式**: Scoped CSS，遵循项目现有风格