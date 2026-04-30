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
