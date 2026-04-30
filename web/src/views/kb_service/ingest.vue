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
