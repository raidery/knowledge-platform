# KB Service 文档上传页面实现计划

**Spec**: `docs/superpowers/specs/2026-04-30-kb-ingest-design.md`

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 为 KB Service `/ingest` API 创建前端上传页面和工作台嵌入组件

**Architecture:**
- 新建 `web/src/api/kb_service.js` 封装 ingest API
- 新建 `web/src/components/kb/ingest_uploader.vue` 可复用上传组件
- 新建 `web/src/views/kb_service/ingest.vue` 独立上传页面
- 修改 `web/src/views/workbench/index.vue` 嵌入上传卡片

**Tech Stack:** Vue 3 + Naive UI + Axios + Scoped CSS

---

## 文件结构

```
web/src/
├── api/
│   └── kb_service.js              # 新增
├── components/
│   └── kb/
│       └── ingest_uploader.vue    # 新增
├── views/
│   ├── kb_service/
│   │   └── ingest.vue             # 新增
│   └── workbench/
│       └── index.vue              # 修改：嵌入 IngestUploader
```

---

## Task 1: 创建 API 模块

**Files:**
- Create: `web/src/api/kb_service.js`

**Steps:**

- [ ] **Step 1: 创建 kb_service.js**

```js
import { request } from '@/utils'

/**
 * 上传文档到知识库
 * @param {FormData} formData
 * @returns {Promise}
 */
export function ingestDocument(formData) {
  return request.post('/kb_service/ingest', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
  })
}
```

- [ ] **Step 2: 在 api/index.js 中引入**

```js
// 在 api/index.js 顶部添加
import { ingestDocument } from './kb_service'

// 在 export default 对象中添加 (使用命名引入，不要改动现有结构)
export default {
  // ... 现有代码保留不动 ...

  // 新增：kb_service API
  ingestDocument,
}
```

---

## Task 2: 创建可复用上传组件

**Files:**
- Create: `web/src/components/kb/ingest_uploader.vue`

**Steps:**

- [ ] **Step 1: 创建组件模板**

```vue
<template>
  <n-card :title="title" rounded-10>
    <n-form ref="formRef" :model="form" label-placement="top">
      <!-- business_id 输入 -->
      <n-form-item label="Business ID" path="business_id" required>
        <n-input v-model:value="form.business_id" placeholder="请输入业务 ID" />
      </n-form-item>

      <!-- 文件上传 -->
      <n-form-item label="文档文件" path="file" required>
        <n-upload
          v-model:file-list="fileList"
          :max="1"
          accept=".docx,.pdf,.txt,.doc"
          @change="handleFileChange"
        >
          <n-button>选择文件</n-button>
        </n-upload>
      </n-form-item>

      <!-- 上传按钮 -->
      <n-form-item>
        <n-button
          type="primary"
          :loading="uploading"
          :disabled="!canUpload"
          @click="handleUpload"
        >
          {{ uploading ? '上传中...' : '上传' }}
        </n-button>
      </n-form-item>
    </n-form>

    <!-- 结果展示 -->
    <n-card v-if="result" title="上传结果" mt-15 size="small">
      <n-descriptions :column="1" label-placement="left">
        <n-descriptions-item label="Job ID">{{ result.job_id }}</n-descriptions-item>
        <n-descriptions-item label="Doc ID">{{ result.doc_id || '-' }}</n-descriptions-item>
        <n-descriptions-item label="状态">
          <n-tag :type="result.status === 'completed' ? 'success' : 'info'">
            {{ result.status }}
          </n-tag>
        </n-descriptions-item>
        <n-descriptions-item label="创建时间">{{ result.created_at }}</n-descriptions-item>
        <n-descriptions-item v-if="result.sections_count" label="切分段数">
          {{ result.sections_count }}
        </n-descriptions-item>
      </n-descriptions>
    </n-card>
  </n-card>
</template>
```

- [ ] **Step 2: 添加 script setup**

```vue
<script setup>
import { ref, computed } from 'vue'
import { ingestDocument } from '@/api/kb_service'
import { useMessage } from 'naive-ui'

const props = defineProps({
  title: {
    type: String,
    default: '文档上传',
  },
})

const message = useMessage()
const formRef = ref(null)
const form = ref({
  business_id: '',
})
const fileList = ref([])
const selectedFile = ref(null)
const uploading = ref(false)
const result = ref(null)

const canUpload = computed(() => {
  return form.value.business_id && selectedFile.value
})

function handleFileChange(options) {
  const file = options.file
  if (file) {
    selectedFile.value = file.file
  }
}

async function handleUpload() {
  if (!canUpload.value) {
    message.warning('请填写 business_id 并选择文件')
    return
  }

  uploading.value = true
  result.value = null

  try {
    const formData = new FormData()
    formData.append('file', selectedFile.value)
    formData.append('business_id', form.value.business_id)

    const res = await ingestDocument(formData)
    result.value = res.data
    message.success('上传成功')
  } catch (error) {
    message.error('上传失败: ' + (error.message || '未知错误'))
  } finally {
    uploading.value = false
  }
}
</script>
```

- [ ] **Step 3: 添加 scoped 样式**

```vue
<style scoped>
/* 组件样式 */
</style>
```

---

## Task 3: 创建独立上传页面

**Files:**
- Create: `web/src/views/kb_service/ingest.vue`

**Steps:**

- [ ] **Step 1: 创建页面**

```vue
<template>
  <AppPage :show-footer="false">
    <n-card title="文档上传" rounded-10>
      <kb-ingest-uploader />
    </n-card>
  </AppPage>
</template>

<script setup>
import KbIngestUploader from '@/components/kb/ingest_uploader.vue'
</script>
```

- [ ] **Step 2: 创建该模块的 route.js（用于动态路由注册）**

```js
export default {
  path: '/kb_service',
  name: 'KbService',
  children: [
    {
      path: 'ingest',
      name: 'KbIngest',
      component: () => import('@/views/kb_service/ingest.vue'),
    },
  ],
}
```

---

## Task 4: 嵌入工作台

**Files:**
- Modify: `web/src/views/workbench/index.vue` (在 `<n-card>` 列表后添加上传卡片)

**Steps:**

- [ ] **Step 1: 引入组件**

```vue
<script setup>
import { useUserStore } from '@/store'
import { useI18n } from 'vue-i18n'
import KbIngestUploader from '@/components/kb/ingest_uploader.vue'

// ... 现有代码
</script>
```

- [ ] **Step 2: 在模板中添加上传卡片**

在现有的 `n-card` (label_project) 后添加:

```vue
<n-card
  :title="$t('views.workbench.label_ingest')"
  size="small"
  :segmented="true"
  mt-15
  rounded-10
>
  <kb-ingest-uploader title="文档上传" />
</n-card>
```

- [ ] **Step 3: 添加国际化 key**

在 `web/i18n/messages/cn.json` 中添加:
```json
{
  "views": {
    "workbench": {
      "label_ingest": "文档上传"
    }
  }
}
```

在 `web/i18n/messages/en.json` 中添加:
```json
{
  "views": {
    "workbench": {
      "label_ingest": "Document Upload"
    }
  }
}
```

---

## Task 5: 验证

**Steps:**

- [ ] **Step 1: 启动前端 dev server**

```bash
cd web && pnpm dev
```

- [ ] **Step 2: 检查工作台页面**

访问 `/workbench`，确认上传卡片显示正常

- [ ] **Step 3: 检查独立页面**

访问 `/kb_service/ingest`，确认页面正常显示

- [ ] **Step 4: 测试上传流程**

1. 填写 business_id
2. 选择一个 .docx 文件
3. 点击上传
4. 确认结果卡片正确显示返回数据

---

## 后端 API 注意事项

确保后端 `POST /api/v1/kb_service/ingest` 路由已正确注册，且：
- 支持 `multipart/form-data` 上传
- `business_id` 为必填字段
- 返回 `IngestResponse` 结构

---

## 提交

完成所有步骤后，提交代码:

```bash
git add web/src/api/kb_service.js web/src/components/kb/ingest_uploader.vue web/src/views/kb_service/ web/src/views/workbench/index.vue web/src/locales/
git commit -m "feat(web): add KB service ingest upload page and workbench card"
```