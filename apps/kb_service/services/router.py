from dataclasses import dataclass

from apps.kb_service.models.ingest_job import Backend, DocumentType


@dataclass
class RouteResult:
    backend: Backend
    dataset_id: str | None = None


class RouterService:
    def route(self, doc_type: DocumentType, dataset_id: str | None = None) -> RouteResult:
        if doc_type == DocumentType.PLAIN_TEXT:
            return RouteResult(backend=Backend.RAGFLOW)
        # complex_layout / scanned_pdf / table_heavy / image_rich → Dify
        return RouteResult(backend=Backend.DIFY, dataset_id=dataset_id)
