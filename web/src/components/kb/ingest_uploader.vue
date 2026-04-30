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

<style scoped>
/* scoped styles if needed */
</style>
