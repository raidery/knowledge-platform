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
