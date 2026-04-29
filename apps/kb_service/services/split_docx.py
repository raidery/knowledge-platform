"""
SplitDocxService — 封装 split_docx_by_section.py 的核心逻辑
"""
import os
import uuid
import re
import shutil
from pathlib import Path
from dataclasses import dataclass

from apps.kb_service.utils.split_docx_by_section import split_docx


# 5MB / 20MB 阈值（bytes）
SIZE_SMALL = 5 * 1024 * 1024
SIZE_LARGE = 20 * 1024 * 1024

# 默认节标题正则
DEFAULT_PATTERN = r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"

# 切分输出根目录
SPLIT_OUTPUT_ROOT = Path("/tmp/kb_datasets")


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
            raise SplitError(f"切分失败: {e}") from e

        # 解析临时目录中的输出文件，构建 SectionMeta 列表
        sections: list[SectionMeta] = []
        temp_dir_path = Path(out_dir)
        input_stem = Path(file_path).stem
        final_dir = SPLIT_OUTPUT_ROOT / input_stem
        final_dir.mkdir(parents=True, exist_ok=True)

        print(f"[SPLIT DEBUG] temp_dir={out_dir}, stem={input_stem}, final_dir={final_dir}")
        print(f"[SPLIT DEBUG] temp files: {list(temp_dir_path.glob('*.docx'))}")

        for f in sorted(temp_dir_path.glob("*.docx")):
            print(f"[SPLIT DEBUG] moving {f} -> {final_dir / f.name}, exists={f.exists()}, size={f.stat().st_size}")
            name = f.stem  # e.g. "原文件_intro" / "原文件_01_第1节"
            data = f.read_bytes()

            # 解析 index 和 title
            # 格式: {stem}_intro.docx 或 {stem}_{index:02d}_{title}.docx
            if "_intro" in name:
                title = "_intro"
                index = 0
            else:
                # 使用 rsplit 从右边分割，最多分成3部分: [stem, index_part, title]
                parts = name.rsplit("_", 2)
                if len(parts) >= 2 and parts[-1].isdigit():
                    index_part = parts[-1]
                    title = parts[2] if len(parts) >= 3 else ""
                    try:
                        index = int(index_part)
                    except ValueError:
                        index = 0
                else:
                    index = 0
                    title = ""

            # 移动到最终目录 ./datasets/{stem}/
            final_path = final_dir / f.name
            shutil.move(str(f), str(final_path))

            sections.append(SectionMeta(
                title=title,
                index=index,
                file_path=str(final_path),
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
        #self.cleanup()
        return False
