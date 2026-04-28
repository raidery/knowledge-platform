import os
import uuid
from pathlib import Path


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def save_upload_file(file_content: bytes, filename: str, upload_dir: str) -> str:
    ensure_dir(upload_dir)
    ext = Path(filename).suffix
    unique_name = f"{uuid.uuid4().hex}{ext}"
    file_path = os.path.join(upload_dir, unique_name)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()