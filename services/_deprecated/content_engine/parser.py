"""
文档解析器
═════════
支持 PDF（PyMuPDF）和 DOCX（python-docx）。
解析结果：章节列表 + 全文文本。

MVP 策略：
- PDF：按页提取文本，尝试从 TOC 中获取章节结构
- DOCX：按 Heading 段落提取章节结构
- 解析失败不崩溃，返回单章节兜底
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

import structlog

logger = structlog.get_logger()


@dataclass
class ParsedChapter:
    """解析出的章节"""
    title: str
    depth: int  # 1-based
    content: str
    sort_order: int
    children: list[ParsedChapter] = field(default_factory=list)


@dataclass
class ParseResult:
    """解析结果"""
    full_text: str
    chapters: list[ParsedChapter]
    page_count: int = 0
    error: Optional[str] = None


# ── PDF 解析 ──────────────────────────────────────────


def parse_pdf(data: bytes) -> ParseResult:
    """使用 PyMuPDF (fitz) 解析 PDF。"""
    try:
        import fitz  # PyMuPDF
    except ImportError:
        logger.error("pymupdf_not_installed")
        return ParseResult(
            full_text="",
            chapters=[],
            error="PyMuPDF (fitz) 未安装",
        )

    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        logger.error("pdf_open_failed", error=str(e), exc_info=True)
        return ParseResult(full_text="", chapters=[], error=f"PDF 打开失败: {e}")

    page_count = len(doc)
    pages_text: list[str] = []

    for page in doc:
        text = page.get_text("text")
        if text.strip():
            pages_text.append(text)

    full_text = "\n\n".join(pages_text)

    # 尝试从 TOC 获取章节
    toc = doc.get_toc()  # [[level, title, page], ...]
    chapters: list[ParsedChapter] = []

    if toc:
        logger.info("pdf_toc_found", entries=len(toc))
        for idx, (level, title, page_num) in enumerate(toc):
            depth = min(level, 4)  # 限制深度 ≤ 4
            # 提取该章节对应页的文本（简化：取 TOC entry 对应的那一页）
            page_text = ""
            if 1 <= page_num <= page_count:
                try:
                    page_text = doc[page_num - 1].get_text("text")
                except Exception:
                    pass

            chapters.append(ParsedChapter(
                title=title.strip(),
                depth=depth,
                content=page_text,
                sort_order=idx,
            ))
    else:
        logger.info("pdf_no_toc, using_single_chapter", pages=page_count)
        # 无 TOC：整个文档作为单章节
        chapters.append(ParsedChapter(
            title="全文",
            depth=1,
            content=full_text,
            sort_order=0,
        ))

    doc.close()

    return ParseResult(
        full_text=full_text,
        chapters=chapters,
        page_count=page_count,
    )


# ── DOCX 解析 ─────────────────────────────────────────


_HEADING_RE = re.compile(r"^Heading\s*(\d+)$", re.IGNORECASE)


def parse_docx(data: bytes) -> ParseResult:
    """使用 python-docx 解析 DOCX，按 Heading 切分章节。"""
    try:
        from docx import Document
        from io import BytesIO
    except ImportError:
        logger.error("python_docx_not_installed")
        return ParseResult(
            full_text="",
            chapters=[],
            error="python-docx 未安装",
        )

    try:
        doc = Document(BytesIO(data))
    except Exception as e:
        logger.error("docx_open_failed", error=str(e), exc_info=True)
        return ParseResult(full_text="", chapters=[], error=f"DOCX 打开失败: {e}")

    all_text_parts: list[str] = []
    chapters: list[ParsedChapter] = []
    current_title = ""
    current_depth = 1
    current_content: list[str] = []
    sort_idx = 0

    def _flush():
        nonlocal sort_idx
        if current_title or current_content:
            chapters.append(ParsedChapter(
                title=current_title or f"段落 {sort_idx + 1}",
                depth=current_depth,
                content="\n".join(current_content),
                sort_order=sort_idx,
            ))
            sort_idx += 1

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        all_text_parts.append(text)
        style_name = para.style.name if para.style else ""

        # 检测是否 Heading
        m = _HEADING_RE.match(style_name)
        if m:
            # 保存之前的章节
            _flush()
            heading_level = int(m.group(1))
            current_title = text
            current_depth = min(heading_level, 4)
            current_content = []
        else:
            current_content.append(text)

    # 最后一个章节
    _flush()

    full_text = "\n".join(all_text_parts)

    # 如果没解析出任何章节，兜底
    if not chapters:
        chapters.append(ParsedChapter(
            title="全文",
            depth=1,
            content=full_text,
            sort_order=0,
        ))

    return ParseResult(
        full_text=full_text,
        chapters=chapters,
        page_count=0,
    )


# ── 统一入口 ──────────────────────────────────────────


def parse_document(data: bytes, filename: str) -> ParseResult:
    """根据文件名后缀选择解析器。"""
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext == "pdf":
        return parse_pdf(data)
    elif ext in ("docx",):
        return parse_docx(data)
    else:
        return ParseResult(
            full_text="",
            chapters=[],
            error=f"不支持的文件类型: .{ext}（仅支持 PDF/DOCX）",
        )
