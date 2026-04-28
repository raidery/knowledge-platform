# Test for kb_service models
from apps.kb_service.models import (
    BaseModel,
    TimestampMixin,
    IngestJob,
    AuditLog,
    DocumentChunk,
    DocumentType,
    Backend,
    JobStatus,
)


def test_models_import():
    """Verify all models and enums can be imported."""
    assert BaseModel is not None
    assert TimestampMixin is not None
    assert IngestJob is not None
    assert AuditLog is not None
    assert DocumentChunk is not None
    assert DocumentType is not None
    assert Backend is not None
    assert JobStatus is not None


def test_document_type_enum():
    """Verify DocumentType enum values."""
    assert DocumentType.PLAIN_TEXT == "plain_text"
    assert DocumentType.COMPLEX_LAYOUT == "complex_layout"
    assert DocumentType.SCANNED_PDF == "scanned_pdf"
    assert DocumentType.TABLE_HEAVY == "table_heavy"
    assert DocumentType.IMAGE_RICH == "image_rich"


def test_backend_enum():
    """Verify Backend enum values."""
    assert Backend.RAGFLOW == "ragflow"
    assert Backend.DIFY == "dify"


def test_job_status_enum():
    """Verify JobStatus enum values."""
    assert JobStatus.PROCESSING == "processing"
    assert JobStatus.PENDING_REVIEW == "pending_review"
    assert JobStatus.PUBLISHED == "published"
    assert JobStatus.REJECTED == "rejected"
    assert JobStatus.FAILED == "failed"


def test_ingest_job_table_name():
    """Verify IngestJob table name."""
    assert IngestJob._meta.db_table == "kb_ingest_job"


def test_audit_log_table_name():
    """Verify AuditLog table name."""
    assert AuditLog._meta.db_table == "kb_audit_log"


def test_document_chunk_table_name():
    """Verify DocumentChunk table name."""
    assert DocumentChunk._meta.db_table == "kb_document_chunk"