# DOCX 切分后上传 Dify 失败的修复记录

## 问题描述

使用 `test_queue_functionality.py` 测试大文件 `rag-1.docx` 上传到 Dify 后，文档显示 **0 字节**，但 `word_count > 0`，状态为 `error`。

## 排查过程

### 1. 确认问题可复现

执行 `python tests/test_queue_functionality.py` 后，观察 Dify 文档列表：

```bash
curl -s "http://localhost:8000/v1/datasets/{dataset_id}/documents" \
  -H "Authorization: Bearer {api_key}" | python3 -c ...
```

结果：切分后的 12 个子文档全部显示 `size=0`，状态 `error`。

### 2. 检查 Worker 日志

```bash
docker logs docker-worker-1 --since "2026-04-29T22:20:00" 2>&1 | grep -i -E "(error|exception|failed)"
```

发现错误：

```
KeyError: "There is no item named 'word/fonts/font3.odttf' in the archive"
```

### 3. 定位根因

DOCX 切分时使用了 `disable_fonts=True`，移除了 `word/fonts/` 目录下的文件，但 `document.xml.rels` 中仍然保留了对这些字体的引用。Dify 的 python-docx 库在解析时会尝试读取这些引用，导致 `KeyError`。

### 4. 第一次修复尝试

修改 `apps/kb_service/utils/split_docx_by_section.py` 中的 `build_section_zip` 函数，在 `disable_fonts=True` 时过滤字体引用：

```python
# 2. 过滤 document.xml.rels
kept_doc_rels = {}
for rid, (rtype, target, mode) in doc_rels.items():
    if is_media_rel(rtype) and mode != "External":
        if rid in used_rids:
            kept_doc_rels[rid] = (rtype, target, mode)
    elif disable_fonts and "/font" in rtype.lower():
        # 禁用字体时，移除字体引用避免 KeyError
        pass
    else:
        kept_doc_rels[rid] = (rtype, target, mode)
```

### 5. 验证修复（失败）

重新测试后，错误变化：

```
KeyError: "There is no item named 'docProps/core.xml' in the archive"
```

说明之前移除了字体文件后，还缺少其他必需文件。

### 6. 检查原 DOCX 文件结构

```bash
python3 -c "
import zipfile
zf = zipfile.ZipFile('tests/rag-1.docx', 'r')
for name in sorted(zf.namelist()):
    print(name)
"
```

输出：

```
[Content_Types].xml
_rels/.rels
docProps/app.xml
docProps/core.xml
docProps/custom.xml
word/_rels/document.xml.rels
word/_rels/fontTable.xml.rels
word/document.xml
word/fontTable.xml
word/fonts/
word/fonts/font1.odttf
word/fonts/font2.odttf
word/fonts/font3.odttf
word/numbering.xml
word/settings.xml
word/styles.xml
word/theme/theme1.xml
```

### 7. 完整修复

修改 `build_section_zip` 函数，添加更多必需文件：

```python
# 5. 加入包级固定文件和 word 必要文件
for f in ["[Content_Types].xml", "_rels/.rels",
           "docProps/core.xml", "docProps/app.xml", "docProps/custom.xml",
           "word/settings.xml", "word/styles.xml", "word/fontTable.xml",
           "word/numbering.xml", "word/theme/theme1.xml"]:
    if f in zip_set:
        dep_files.add(f)
```

## 修复涉及的文件

| 文件 | 修改内容 |
|------|----------|
| `apps/kb_service/utils/split_docx_by_section.py` | 1. 过滤字体引用<br>2. 添加必需文件到打包列表 |
| `apps/kb_service/services/split_docx.py` | 将 `SPLIT_OUTPUT_ROOT` 从 `./datasets` 改为 `/tmp/kb_datasets`（绝对路径） |
| `apps/kb_service/clients/dify/dataset.py` | DEBUG 日志不再打印文件内容，只打印文件名和大小 |

## 修复验证

1. 清理旧数据：
   ```bash
   rm -rf /tmp/kb_datasets/*
   # 删除 Dify 中的失败文档
   ```

2. 重新运行测试：
   ```bash
   python tests/test_queue_functionality.py
   ```

3. 检查结果：
   ```bash
   curl -s "http://localhost:8000/v1/datasets/{dataset_id}/documents" \
     -H "Authorization: Bearer {api_key}" | python3 -c ...
   ```

   所有切分文档应显示正常的 `size` 和 `word_count`，状态为 `completed`。

## 根本原因总结

1. **字体引用未清理**：`disable_fonts=True` 时只移除了字体文件，但没有移除 `document.xml.rels` 中对字体的引用
2. **必需文件遗漏**：DOCX 打包时遗漏了 `docProps/core.xml` 等必需文件

## 预防措施

后续修改 `split_docx_by_section.py` 时，应确保：
1. 任何文件的移除操作都要同步清理引用
2. 打包文件列表应包含 DOCX 规范要求的所有必需文件
