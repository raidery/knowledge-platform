import os
import re
from pathlib import Path


def ensure_dir(path: str) -> str:
    os.makedirs(path, exist_ok=True)
    return path


def save_upload_file(file_content: bytes, filename: str, upload_dir: str) -> str:
    ensure_dir(upload_dir)
    safe_name = re.sub(r'[\\/:*?"<>|]', "_", filename)
    file_path = os.path.join(upload_dir, safe_name)
    with open(file_path, "wb") as f:
        f.write(file_content)
    return file_path


def get_file_size(file_path: str) -> int:
    return os.path.getsize(file_path)


def get_file_extension(filename: str) -> str:
    return os.path.splitext(filename)[1].lower()