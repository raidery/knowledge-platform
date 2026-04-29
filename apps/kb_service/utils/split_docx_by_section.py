#!/usr/bin/env python3
r"""
================================================================================
模块概要
================================================================================
文件: split_docx_by_section.py  v2.0
功能: 按节切分 Word 文档（DOCX），完整保留图片/表格，体积严格控制。

本模块将一个 DOCX 文档按"节标题"拆分为多个独立的子 DOCX 文件。
每个子文档保留原文档中该节用到的所有资源（图片、表格、图表等），
同时剔除未使用的部分（其他节的媒体、嵌入字体等），从而严格控制体积。

================================================================================
核心能力
================================================================================
1. 智能节检测
   - 支持正则匹配节标题（默认匹配"第X节" / "Section N"）
   - 支持指定 heading 级别（--level，默认3，即"标题3"样式）
   - 前言部分（_intro）默认保留，可用 --no-intro 排除

2. 依赖图解析（核心算法）
   - 从 document.xml.rels 出发，递归解析所有 .rels 文件
   - 构建"本节实际用到的文件集合"，包括：
     * 图片（word/media/）
     * 图表（word/charts/ 及其 .rels、xlsx 缓存）
     * 图表关系（word/charts/_rels/*.rels.rels）
     * 嵌入对象（oleObject）
     * 图形（diagram、diagramLayout、diagramQuickStyle、diagramColors）
     * 嵌入字体（默认剔除，--keep-fonts 保留）
   - External 关系（外链）不占 ZIP 空间，只跟踪 Internal

3. 体积控制（4个 Bug 修复）
   - Bug1: 修复只过滤 word/media/，漏掉 charts/embeddings/diagrams/ 的问题
   - Bug2: 修复 chart 的 .rels.rels 及 xlsx 缓存未过滤的问题
   - Bug3: 默认关闭嵌入字体（word/fonts/），单文件 10MB+ → 显著瘦身
   - Bug4: [Content_Types].xml 精简，只保留实际存在文件的 Override/Default

4. 输出
   - 文件名格式：{原文件名}_intro.docx / {原文件名}_01_{第一节标题}.docx
   - 每个子文档为独立 ZIP，可直接用 Word 打开
   - 输出统计：原始大小、子文档大小、占比

================================================================================
与 ingest 服务的集成点
================================================================================
ingest API (apps/kb_service/api/ingest.py) 在文档切分后，需要：
  1. 调用 split_docx() 替代原来的"整文档上传"逻辑
  2. 遍历切出的每个子文档，逐个调用"文档解析 → 向量化 → 存入知识库"的流程
  3. 关联元数据：parent_doc_id、section_title、section_index

集成方式见下方"集成分析"注释块（ brainstorming 结果）。

================================================================================
外部依赖
================================================================================
- lxml: XML 解析（pip install lxml）
- Python 3.11+: 标准库：argparse, pathlib, zipfile, re, io, copy

================================================================================
使用方式（CLI）
================================================================================
  python split_docx_by_section.py input.docx
  python split_docx_by_section.py input.docx --out-dir ./out/ --level 2
  python split_docx_by_section.py input.docx --pattern "Part\s+\d+" --no-intro
  python split_docx_by_section.py input.docx --keep-fonts  # 保留字体，体积较大

================================================================================
内部数据结构
================================================================================
入口函数 split_docx() 返回 None，结果直接写入磁盘。
如需在内存中处理（集成到 ingest），关注 build_section_zip() → 返回 bytes，
可直接推送至下一步处理，无需落盘。

关键数据结构：
  sections: list[tuple[title: str, elements: list]]  # 节标题与该节所有块元素
  dep_files: set[str]                                  # 本节依赖的 ZIP 内文件路径集合
  kept_doc_rels: dict[str, (rtype, target, mode)]     # 过滤后的 document.xml.rels

================================================================================

修复的4处漏洞：
  Bug1: 只过滤 word/media/，word/charts/ word/embeddings/ word/diagrams/ 全漏掉
  Bug2: chart 的子 .rels 文件及关联 xlsx 缓存数据未过滤
  Bug3: 嵌入字体（word/fonts/）每个子文档都复制，CJK字体单个10MB+
  Bug4: [Content_Types].xml 原样复制，声明不存在的类型

修复策略：
  - 构建"本节实际用到的文件集合"，只打包集合内文件
  - 递归解析所有子目录的 .rels 文件，跟踪完整依赖图
  - 字体：默认关闭嵌入字体开关（settings.xml），避免体积膨胀；
    用 --keep-fonts 可保留（渲染与原文完全一致但体积大）
  - [Content_Types].xml 精简：只保留实际存在文件的 Override/Default

用法：
  python split_docx_by_section.py input.docx
  python split_docx_by_section.py input.docx --out-dir ./out/ --level 2
  python split_docx_by_section.py input.docx --pattern "Part\s+\d+" --no-intro
  python split_docx_by_section.py input.docx --keep-fonts  # 保留字体，体积较大

依赖：pip install lxml
"""

import argparse
import copy
import io
import re
import zipfile
from pathlib import Path
from lxml import etree

# ─── 命名空间 ──────────────────────────────────────────────────────────────────
W   = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
R   = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG = "http://schemas.openxmlformats.org/package/2006/relationships"
CT  = "http://schemas.openxmlformats.org/package/2006/content-types"

def tag(ns, local):
    return f"{{{ns}}}{local}"


# ─── XML 工具 ─────────────────────────────────────────────────────────────────

def parse_xml(data: bytes) -> etree._Element:
    return etree.parse(io.BytesIO(data)).getroot()

def parse_rels_data(data: bytes) -> dict:
    """解析 .rels 字节 → {rId: (Type, Target, TargetMode)}"""
    rels = {}
    try:
        root = parse_xml(data)
    except Exception:
        return rels
    for rel in root:
        rid  = rel.get("Id", "")
        if rid:
            rels[rid] = (
                rel.get("Type", ""),
                rel.get("Target", ""),
                rel.get("TargetMode", "Internal"),
            )
    return rels

def build_rels_xml(rels: dict) -> bytes:
    root = etree.Element(f"{{{PKG}}}Relationships")
    for rid, (rtype, target, mode) in rels.items():
        el = etree.SubElement(root, f"{{{PKG}}}Relationship")
        el.set("Id", rid)
        el.set("Type", rtype)
        el.set("Target", target)
        if mode and mode != "Internal":
            el.set("TargetMode", mode)
    return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)


# ─── 路径工具 ─────────────────────────────────────────────────────────────────

def resolve_target(base_dir: str, target: str) -> str:
    """将 .rels 中相对 Target 解析为 ZIP 内绝对路径（无前导 /）"""
    if target.startswith("/"):
        return target.lstrip("/")
    joined = base_dir.rstrip("/") + "/" + target
    parts = []
    for p in joined.split("/"):
        if p == "..":
            if parts:
                parts.pop()
        elif p and p != ".":
            parts.append(p)
    return "/".join(parts)

def rels_path_for(content_path: str) -> str:
    """content_path → 对应的 .rels 路径"""
    parts = content_path.split("/")
    return "/".join(parts[:-1]) + "/_rels/" + parts[-1] + ".rels"

def base_dir_of(path: str) -> str:
    parts = path.split("/")
    return "/".join(parts[:-1])


# ─── 段落工具 ─────────────────────────────────────────────────────────────────

def get_para_text(p: etree._Element) -> str:
    return "".join(t.text or "" for t in p.iter(tag(W, "t")))

# def get_para_style(p: etree._Element) -> str:
#     ppr = p.find(tag(W, "pPr"))
#     if ppr is None:
#         return ""
#     ps = ppr.find(tag(W, "pStyle"))
#     return ps.get(tag(W, "val"), "") if ps is not None else ""

# def is_section_heading(p: etree._Element, heading_level: int, pattern: re.Pattern) -> bool:
#     style = get_para_style(p).lower().replace(" ", "")
#     style_match = (style == f"heading{heading_level}")
#     if not style_match:
#         ppr = p.find(tag(W, "pPr"))
#         if ppr is not None:
#             ol = ppr.find(tag(W, "outlineLvl"))
#             if ol is not None:
#                 style_match = (int(ol.get(tag(W, "val"), "99")) == heading_level - 1)
#     if not style_match:
#         return False
#     text = get_para_text(p).strip()
#     return bool(pattern.search(text)) if text else False
def get_para_style(p: etree._Element) -> str:
    ppr = p.find(tag(W, "pPr"))
    if ppr is None:
        return ""
    ps = ppr.find(tag(W, "pStyle"))
    if ps is None:
        return ""
    return (ps.get(tag(W, "val"), "") or ps.get("val", "") or "").strip()


def is_section_heading(p: etree._Element, heading_level: int, pattern: re.Pattern) -> bool:
    text = get_para_text(p).strip()
    if not text:
        return False

    # 只要文本匹配“第几节/Section N”之类，就直接认为是节标题
    if pattern.search(text):
        return True

    # 下面保留样式判断，作为兜底
    style = get_para_style(p).lower().replace(" ", "")
    style_match = style in {
        f"heading{heading_level}",
        str(heading_level),
    }

    if not style_match:
        ppr = p.find(tag(W, "pPr"))
        if ppr is not None:
            ol = ppr.find(tag(W, "outlineLvl"))
            if ol is not None:
                try:
                    style_match = (int(ol.get(tag(W, "val"), "99")) == heading_level - 1)
                except ValueError:
                    style_match = False

    return style_match
# ─── 依赖图解析 ───────────────────────────────────────────────────────────────

# 需要"按本节过滤"的关系类型关键字
MEDIA_REL_KEYWORDS = [
    "/image", "/video", "/audio",
    "/oleObject",
    "/chart",
    "/diagram", "/diagramLayout", "/diagramQuickStyle", "/diagramColors",
]

def is_media_rel(rtype: str) -> bool:
    return any(kw in rtype for kw in MEDIA_REL_KEYWORDS)

def collect_element_rids(elements) -> set:
    """从段落/块元素列表收集所有 r:id / r:embed / r:href 值"""
    rids = set()
    probe = [tag(R, "id"), tag(R, "embed"), tag(R, "href"),
             tag(R, "link"), tag(R, "pict")]
    for elem in elements:
        for el in elem.iter():
            for attr in probe:
                v = el.get(attr)
                if v:
                    rids.add(v)
    return rids

def resolve_dependencies(seed_files: set, zf: zipfile.ZipFile, zip_set: set) -> set:
    """
    从 seed_files 出发递归解析 .rels，返回全部依赖文件集合。
    只跟踪 Internal 关系（External 超链接不占 ZIP 空间）。
    """
    visited = set()
    queue   = [f for f in seed_files if f in zip_set]

    while queue:
        path = queue.pop()
        if path in visited:
            continue
        if path not in zip_set:
            continue
        visited.add(path)

        rpath = rels_path_for(path)
        if rpath in zip_set and rpath not in visited:
            visited.add(rpath)
            try:
                rels = parse_rels_data(zf.read(rpath))
            except Exception:
                rels = {}
            base = base_dir_of(path)
            for rid, (rtype, target, mode) in rels.items():
                if mode == "External":
                    continue
                resolved = resolve_target(base, target)
                if resolved and resolved not in visited:
                    queue.append(resolved)

    return visited


# ─── settings.xml 字体处理 ───────────────────────────────────────────────────

FONT_EMBED_TAGS = [
    tag(W, "embedTrueTypeFonts"),
    tag(W, "embedSystemFonts"),
    tag(W, "saveSubsetFonts"),
]

def disable_font_embedding(settings_bytes: bytes) -> bytes:
    """关闭 settings.xml 中的字体嵌入开关"""
    try:
        root = parse_xml(settings_bytes)
        for ftag in FONT_EMBED_TAGS:
            for el in list(root.iter(ftag)):
                parent = el.getparent()
                if parent is not None:
                    parent.remove(el)
        return etree.tostring(root, xml_declaration=True, encoding="UTF-8", standalone=True)
    except Exception:
        return settings_bytes


# ─── [Content_Types].xml 精简 ────────────────────────────────────────────────

def build_content_types(original_bytes: bytes, kept_files: set) -> bytes:
    """只保留 kept_files 中实际存在文件的 Override/Default 条目"""
    try:
        root = parse_xml(original_bytes)
    except Exception:
        return original_bytes

    kept_exts = {p.rsplit(".", 1)[-1].lower() for p in kept_files if "." in p}
    kept_exts.update(["rels", "xml"])  # 始终保留这两种

    new_root = etree.Element(f"{{{CT}}}Types")
    for child in root:
        local = child.tag.split("}")[-1] if "}" in child.tag else child.tag
        if local == "Default":
            if child.get("Extension", "").lower() in kept_exts:
                new_root.append(copy.deepcopy(child))
        elif local == "Override":
            part = child.get("PartName", "").lstrip("/")
            if part in kept_files:
                new_root.append(copy.deepcopy(child))
        else:
            new_root.append(copy.deepcopy(child))

    return etree.tostring(new_root, xml_declaration=True, encoding="UTF-8", standalone=True)


# ─── 构建子文档 ZIP ───────────────────────────────────────────────────────────

def build_section_zip(
    src_zf: zipfile.ZipFile,
    doc_root: etree._Element,
    paragraphs: list,
    doc_rels: dict,
    global_sectpr,
    zip_set: set,
    disable_fonts: bool,
) -> bytes:

    # 1. 本节直接引用的 rId
    used_rids = collect_element_rids(paragraphs)

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

    # 3. 种子文件：document.xml + 直接关系指向的文件
    seeds = {"word/document.xml"}
    for rid, (rtype, target, mode) in kept_doc_rels.items():
        if mode != "External":
            seeds.add(resolve_target("word", target))

    # 4. 递归解析整棵依赖树
    dep_files = resolve_dependencies(seeds, src_zf, zip_set)

    # 5. 加入包级固定文件和 word 必要文件
    for f in ["[Content_Types].xml", "_rels/.rels",
               "docProps/core.xml", "docProps/app.xml", "docProps/custom.xml",
               "word/settings.xml", "word/styles.xml", "word/fontTable.xml",
               "word/numbering.xml", "word/theme/theme1.xml"]:
        if f in zip_set:
            dep_files.add(f)

    # 6. 排除嵌入字体目录
    if disable_fonts:
        dep_files = {f for f in dep_files if not f.startswith("word/fonts/")}

    # 7. 构建新 document.xml
    new_root = copy.deepcopy(doc_root)
    new_body = new_root.find(tag(W, "body"))
    for child in list(new_body):
        new_body.remove(child)
    for p in paragraphs:
        new_body.append(copy.deepcopy(p))
    if global_sectpr is not None:
        new_body.append(copy.deepcopy(global_sectpr))

    new_doc_bytes  = etree.tostring(new_root, xml_declaration=True,
                                    encoding="UTF-8", standalone=True)
    new_rels_bytes = build_rels_xml(kept_doc_rels)
    new_ct_bytes   = build_content_types(src_zf.read("[Content_Types].xml"), dep_files)

    # 8. 写 ZIP（只写 dep_files 中的文件）
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as zout:
        for name in dep_files:
            if name == "word/document.xml":
                zout.writestr(name, new_doc_bytes)
            elif name == "word/_rels/document.xml.rels":
                zout.writestr(name, new_rels_bytes)
            elif name == "[Content_Types].xml":
                zout.writestr(name, new_ct_bytes)
            elif name == "word/settings.xml" and disable_fonts:
                zout.writestr(name, disable_font_embedding(src_zf.read(name)))
            else:
                zout.writestr(name, src_zf.read(name))

    return buf.getvalue()


# ─── 主流程 ──────────────────────────────────────────────────────────────────

def split_docx(
    input_path: str,
    out_dir: str = None,
    heading_level: int = 1,
    pattern_str: str = None,
    keep_intro: bool = True,
    disable_fonts: bool = True,
):
    input_path = Path(input_path).resolve()
    if not input_path.exists():
        raise FileNotFoundError(f"文件不存在: {input_path}")

    if out_dir is None:
        out_dir = input_path.parent
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    if pattern_str is None:
        # pattern_str = r"(第\s*\d+\s*[节章]|Section\s+\d+|Chapter\s+\d+|SECTION\s+\d+)"
        # pattern_str = r"(第\s*[一二三四五六七八九十百千万0-9]+\s*[节章]|Section\s+\d+|Chapter\s+\d+|SECTION\s+\d+)"
        pattern_str = r"(第\s*[一二三四五六七八九十百千万0-9]+\s*节|Section\s+\d+)"
    pattern = re.compile(pattern_str, re.IGNORECASE)

    with zipfile.ZipFile(input_path, "r") as zf:
        zip_names = zf.namelist()
        zip_set   = set(zip_names)

        doc_bytes = zf.read("word/document.xml")
        doc_root  = etree.parse(io.BytesIO(doc_bytes)).getroot()
        body      = doc_root.find(tag(W, "body"))
        if body is None:
            raise ValueError("找不到 <w:body>")

        doc_rels_bytes = zf.read("word/_rels/document.xml.rels") \
                         if "word/_rels/document.xml.rels" in zip_set else b""
        doc_rels = parse_rels_data(doc_rels_bytes)

        global_sectpr = body.find(tag(W, "sectPr"))

        has_fonts = any(n.startswith("word/fonts/") for n in zip_names)
        if not has_fonts:
            disable_fonts = False

        # ── 切分 ──────────────────────────────────────────────────────────
        body_children = [c for c in body if c.tag != tag(W, "sectPr")]

        sections: list[tuple[str, list]] = []
        current_title = "_intro"
        current_elems: list = []

        for elem in body_children:
            if elem.tag == tag(W, "p") and is_section_heading(elem, heading_level, pattern):
                sections.append((current_title, current_elems))
                current_title = get_para_text(elem).strip() or f"section_{len(sections)+1}"
                current_elems = [elem]
            else:
                current_elems.append(elem)
        sections.append((current_title, current_elems))

        # 去掉空前言
        if sections and sections[0][0] == "_intro" and not sections[0][1]:
            sections = sections[1:]

        if len(sections) <= 1:
            print("⚠️  未检测到多个节。已识别的段落样式：")
            for child in body_children[:30]:
                if child.tag == tag(W, "p"):
                    st = get_para_style(child)
                    tx = get_para_text(child).strip()
                    if st and tx:
                        print(f"     [{st}] {tx[:80]}")
            return

        # ── 写文件 ────────────────────────────────────────────────────────
        stem = input_path.stem
        src_kb = input_path.stat().st_size // 1024
        total_kb = 0

        print(f"源文件 {src_kb:,} KB  →  {len(sections)} 节")
        if disable_fonts:
            print("  (已关闭字体嵌入以控制体积；如需完整字体渲染请加 --keep-fonts)")
        print()

        for i, (title, elems) in enumerate(sections):
            if title == "_intro" and not keep_intro:
                continue
            if not elems:
                continue

            safe = re.sub(r'[\\/:*?"<>|]', "_", title)[:60]
            name = f"{stem}_{safe}.docx" if title != "_intro" \
                   else f"{stem}_intro.docx"
            out_path = out_dir / name

            data = build_section_zip(
                src_zf       = zf,
                doc_root     = doc_root,
                paragraphs   = elems,
                doc_rels     = doc_rels,
                global_sectpr= global_sectpr,
                zip_set      = zip_set,
                disable_fonts= disable_fonts,
            )

            out_path.write_bytes(data)
            kb  = len(data) // 1024
            pct = kb * 100 // src_kb if src_kb else 0
            total_kb += kb
            print(f"  ✔ {name}  {len(elems)} 块 | {kb:,} KB ({pct}% 原文件)")

        print(f"\n完成。输出总计 {total_kb:,} KB → {out_dir}")


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    p = argparse.ArgumentParser(description="按节切分 Word 文档（体积严格控制）")
    p.add_argument("input")
    p.add_argument("--out-dir", default=None)
    p.add_argument("--level", type=int, default=3)
    p.add_argument("--pattern", default=None)
    p.add_argument("--no-intro", action="store_true")
    p.add_argument("--keep-fonts", action="store_true",
                   help="保留嵌入字体（渲染完全一致，但体积较大）")
    args = p.parse_args()

    split_docx(
        input_path   = args.input,
        out_dir      = args.out_dir,
        heading_level= args.level,
        pattern_str  = args.pattern,
        keep_intro   = not args.no_intro,
        disable_fonts= not args.keep_fonts)

if __name__ == "__main__":
    main()
