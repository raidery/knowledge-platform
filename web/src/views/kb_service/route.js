export default [
  {
    path: '/kb_service',
    name: 'KbService',
    redirect: '/kb_service/ingest',
    meta: {
      title: '知识库服务',
      icon: 'carbon:document',
      order: 2,
    },
    children: [
      {
        path: 'ingest',
        name: 'KbIngest',
        component: () => import('@/views/kb_service/ingest.vue'),
        meta: {
          title: '文档上传',
        },
      },
    ],
  },
]
