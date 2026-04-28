"""
SplitDocxService — 封装 split_docx_by_section.py 的核心逻辑
"""
import os
import uuid
import re
import io
import shutil
import zipfile
from pathlib import Path
from dataclasses import dataclass

from apps.kb_service.utils.split_docx_by_section import split_docx


# 5MB / 20MB 阈值（bytes）
SIZE_SMALL = 5 * 1024 * 1024
SIZE_LARGE = 20 * 1024 * 1024

# 默认节标题正则
DEFAULT_PATTERN = r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"


@dataclass
class SectionMeta:
    """切分出的单个 section 的元数据"""
    title: str           # 节标题，"_intro" 表示前言
    index: int           # 节序号（0=intro, 1+=正文节）
    file_path: str       # 临时文件路径（调用方清理）
    file_size: int       # bytes


class SplitError(Exception):
    """切分失败异常"""
    pass


class SplitDocxService:
    """DOCX 节切分服务"""

    def __init__(self):
        self._temp_dirs: list[str] = []

    def _get_split_level(self, file_size: int, split_level: int | None) -> int | None:
        """
        根据文件大小返回 split_level。
        - split_level 显式传入 → 直接使用
        - split_level=None → 自适应
        - 返回 None 表示不切分
        """
        if split_level is not None:
            return split_level
        if file_size < SIZE_SMALL:
            return None  # 不切分
        if file_size < SIZE_LARGE:
            return 3
        return 2

    def _get_pattern(self, split_pattern: str | None) -> str | None:
        return split_pattern if split_pattern else DEFAULT_PATTERN

    def _ensure_temp_dir(self) -> str:
        """创建隔离的临时目录"""
        temp_dir = f"/tmp/docx_split_{uuid.uuid4().hex[:8]}"
        os.makedirs(temp_dir, exist_ok=True)
        self._temp_dirs.append(temp_dir)
        return temp_dir

    def _write_section_bytes(self, data: bytes, temp_dir: str, index: int, title: str) -> str:
        """将 section bytes 写入临时文件，返回文件路径"""
        safe = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
        filename = f"section_{index:02d}_{safe}.docx"
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, "wb") as f:
            f.write(data)
        return file_path

    def split(
        self,
        file_path: str,
        split_level: int | None = None,
        split_pattern: str | None = None,
        force_split: bool = False,
    ) -> list[SectionMeta]:
        """
        切分 DOCX，返回 section 元数据列表。

        Args:
            file_path: 原始 DOCX 文件路径
            split_level: 手动指定切分级别（None=自适应）
            split_pattern: 正则模式覆盖默认匹配
            force_split: True 则忽略大小阈值强制切分

        Returns:
            list[SectionMeta]: 各 section 的元数据列表

        Raises:
            SplitError: 切分失败
        """
        file_size = os.path.getsize(file_path)
        level = self._get_split_level(file_size, split_level)
        pattern = self._get_pattern(split_pattern)

        # 不切分的场景
        if level is None and not force_split:
            return []

        # 实际执行切分
        try:
            # 调用原 split_docx，将结果写入临时目录
            out_dir = self._ensure_temp_dir()
            split_docx(
                input_path=file_path,
                out_dir=out_dir,
                heading_level=level or 3,
                pattern_str=pattern,
                keep_intro=True,
                disable_fonts=True,
            )
        except Exception as e:
            self.cleanup()
            raise SplitError(f"切分失败: {e}") from e

        # 解析临时目录中的输出文件，构建 SectionMeta 列表
        sections: list[SectionMeta] = []
        temp_dir_path = Path(out_dir)
        for f in sorted(temp_dir_path.glob("*.docx")):
            name = f.stem  # e.g. "原文件_intro" / "原文件_01_第1节"
            data = f.read_bytes()

            # 解析 index 和 title
            # 格式: {stem}_intro.docx 或 {stem}_{index:02d}_{title}.docx
            if "_intro" in name:
                title = "_intro"
                index = 0
            else:
                # 找到最后一个 _ 分隔的位置，提取 index 和 title
                # 但 title 本身可能含有下划线，所以用 rsplit 取最后两部分
                parts = name.split("_")
                # 最后一段是 index（两位数字），倒数第二段是 title
                index_part = parts[-1]
                title_part = "_".join(parts[2:])  # 跳过 原文件名(index)
                try:
                    index = int(index_part)
                except ValueError:
                    index = 0
                title = title_part

            sections.append(SectionMeta(
                title=title,
                index=index,
                file_path=str(f),
                file_size=len(data),
            ))

        return sections

    def cleanup(self):
        """清理所有临时目录"""
        for temp_dir in self._temp_dirs:
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)
        self._temp_dirs.clear()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
        return False
