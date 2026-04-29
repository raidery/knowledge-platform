import os
import pytest
from apps.kb_service.services.split_docx import SplitDocxService, SectionMeta

class TestSplitDocxService:
    """SplitDocxService 单元测试"""

    def test_split_rag1_docx_file(self):
        """测试大文件 tests/rag-1.docx 的分割"""
        import sys
        from pathlib import Path
        sys.path.insert(0, str(Path(__file__).parent.parent))

        from apps.kb_service.services.split_docx import SplitDocxService

        file_path = "tests/rag-1.docx"
        if not Path(file_path).exists():
            import pytest
            pytest.skip(f"文件不存在: {file_path}")

        svc = SplitDocxService()
        try:
            result = svc.split(file_path)
            print(f"✓ 文件分割成功")
            print(f"  原始文件: {file_path}")
            print(f"  分割段落数: {len(result)}")
            for i, section in enumerate(result[:5]):
                print(f"    [{i+1}] {section.content[:50]}...")
        finally:
            svc.cleanup()

    def test_get_split_level_small_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(1 * 1024 * 1024, None) is None  # <5MB 不切
        assert svc._get_split_level(1 * 1024 * 1024, 2) == 2        # 强制指定

    def test_get_split_level_medium_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(10 * 1024 * 1024, None) == 3    # 5-20MB

    def test_get_split_level_large_file(self):
        svc = SplitDocxService()
        assert svc._get_split_level(30 * 1024 * 1024, None) == 2    # >20MB

    def test_get_pattern_default(self):
        svc = SplitDocxService()
        assert svc._get_pattern(None) == r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"

    def test_get_pattern_custom(self):
        svc = SplitDocxService()
        assert svc._get_pattern(r"Part\s+\d+") == r"Part\s+\d+"

    def test_cleanup(self):
        svc = SplitDocxService()
        temp_dir = svc._ensure_temp_dir()
        assert os.path.exists(temp_dir)
        svc.cleanup()
        assert not os.path.exists(temp_dir)

    def test_context_manager(self):
        with SplitDocxService() as svc:
            temp_dir = svc._ensure_temp_dir()
        # exit 自动 cleanup
        assert not os.path.exists(temp_dir)