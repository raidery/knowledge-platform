import os
from dataclasses import dataclass
from enum import Enum


class DocumentType(str, Enum):
    PLAIN_TEXT = "plain_text"
    COMPLEX_LAYOUT = "complex_layout"
    SCANNED_PDF = "scanned_pdf"
    TABLE_HEAVY = "table_heavy"
    IMAGE_RICH = "image_rich"


@dataclass
class DocumentChunk:
    chunk_index: int
    file_path: str
    page_start: int
    page_end: int
    title: str | None = None
    word_count: int = 0


class DocumentPreprocessor:
    MIME_TYPE_MAP = {
        ".pdf": "application/pdf",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".md": "text/markdown",
    }

    def detect_document_type(self, file_path: str) -> DocumentType:
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".txt" or ext == ".md":
            return DocumentType.PLAIN_TEXT
        elif ext == ".pdf":
            return DocumentType.COMPLEX_LAYOUT
        elif ext == ".docx":
            return DocumentType.COMPLEX_LAYOUT
        return DocumentType.COMPLEX_LAYOUT

    def clean_document(self, file_path: str) -> str:
        # 去噪音：保留原格式，只做必要清洗
        # Phase 1: 轻量实现，直接返回原路径
        return file_path

    def split_document(
        self, file_path: str, pages_per_chunk: int = 50, max_chunks: int = 100
    ) -> list[DocumentChunk]:
        # 按页拆分（物理拆分，不是语义chunking）
        # Phase 1: 简单实现，返回单个完整文件
        return [
            DocumentChunk(
                chunk_index=0,
                file_path=file_path,
                page_start=1,
                page_end=9999,
            )
        ]
