from apps.kb_service.models.ingest_job import Backend, DocumentType


class RouterService:
    def route(self, doc_type: DocumentType) -> Backend:
        if doc_type == DocumentType.PLAIN_TEXT:
            return Backend.RAGFLOW
        # complex_layout / scanned_pdf / table_heavy / image_rich → Dify
        return Backend.DIFY
