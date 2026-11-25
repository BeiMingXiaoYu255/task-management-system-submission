"""Build the Chinese design document, Chinese user manual and bilingual evaluation reports (DOCX)."""

from __future__ import annotations

import re
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK, WD_LINE_SPACING, WD_TAB_ALIGNMENT, WD_TAB_LEADER
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DRAFTS = PROJECT_ROOT / "deliverables" / "drafts"
ASSETS = PROJECT_ROOT / "deliverables" / "assets"
OUTPUT = PROJECT_ROOT / "deliverables"

BLACK = RGBColor(0, 0, 0)
SONG = "宋体"
HEI = "黑体"
TIMES = "Times New Roman"
CONSOLAS = "Consolas"


# ---------- low-level formatting helpers ----------

def set_run_font(run, east_asia=SONG, latin=TIMES, size=12, bold=False, italic=False):
    run.font.name = latin
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = BLACK
    rpr = run._element.get_or_add_rPr()
    fonts = rpr.find(qn("w:rFonts"))
    if fonts is None:
        fonts = OxmlElement("w:rFonts")
        rpr.append(fonts)
    fonts.set(qn("w:ascii"), latin)
    fonts.set(qn("w:hAnsi"), latin)
    fonts.set(qn("w:eastAsia"), east_asia)


def set_paragraph_format(paragraph, first_line_indent=True, before=0, after=0, line_spacing=1.5,
                         align=WD_ALIGN_PARAGRAPH.JUSTIFY, keep_with_next=False):
    fmt = paragraph.paragraph_format
    fmt.alignment = align
    fmt.space_before = Pt(before)
    fmt.space_after = Pt(after)
    fmt.line_spacing = line_spacing
    fmt.keep_with_next = keep_with_next
    if first_line_indent:
        fmt.first_line_indent = Pt(24)
    else:
        fmt.first_line_indent = Pt(0)


def add_inline_runs(paragraph, text, east_asia=SONG, latin=TIMES, size=12, base_bold=False):
    """Parse **bold**, *italic* and backticks into runs."""
    pattern = re.compile(r"(\*\*.+?\*\*|\*[^*]+?\*|`[^`]+`)")
    position = 0
    for match in pattern.finditer(text):
        if match.start() > position:
            run = paragraph.add_run(text[position:match.start()])
            set_run_font(run, east_asia=east_asia, latin=latin, size=size, bold=base_bold)
        token = match.group(0)
        if token.startswith("**") and token.endswith("**"):
            run = paragraph.add_run(token[2:-2])
            set_run_font(run, east_asia=east_asia, latin=latin, size=size, bold=True)
        elif token.startswith("*") and token.endswith("*"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, east_asia=east_asia, latin=latin, size=size, italic=True, bold=base_bold)
        elif token.startswith("`") and token.endswith("`"):
            run = paragraph.add_run(token[1:-1])
            set_run_font(run, east_asia=CONSOLAS, latin=CONSOLAS, size=size - 1, bold=base_bold)
        position = match.end()
    if position < len(text):
        run = paragraph.add_run(text[position:])
        set_run_font(run, east_asia=east_asia, latin=latin, size=size, bold=base_bold)


def add_paragraph(document, text, first_line_indent=True, size=12, align=WD_ALIGN_PARAGRAPH.JUSTIFY,
                  before=0, after=0, east_asia=SONG, latin=TIMES, bold=False):
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, first_line_indent=first_line_indent, before=before, after=after, align=align)
    add_inline_runs(paragraph, text, east_asia=east_asia, latin=latin, size=size, base_bold=bold)
    return paragraph


def add_heading(document, text, level, english=False):
    sizes = {1: 16, 2: 14, 3: 12}
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, first_line_indent=False, before=(18 if level == 1 else 12), after=(10 if level == 1 else 6),
                         line_spacing=1.3, align=WD_ALIGN_PARAGRAPH.LEFT, keep_with_next=True)
    run = paragraph.add_run(text)
    set_run_font(run, east_asia=HEI, latin=TIMES if english else HEI, size=sizes.get(level, 12), bold=True)
    return paragraph


def add_caption(document, text, above=False):
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, first_line_indent=False, before=(6 if above else 4), after=(4 if above else 8),
                         line_spacing=1.0, align=WD_ALIGN_PARAGRAPH.CENTER)
    run = paragraph.add_run(text)
    set_run_font(run, east_asia=SONG, latin=TIMES, size=10.5, bold=above)
    return paragraph


def add_picture(document, image_path, caption, width_cm=14.6):
    if not Path(image_path).exists():
        add_paragraph(document, "（缺少图片：" + str(image_path) + "）", align=WD_ALIGN_PARAGRAPH.CENTER)
        return
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, first_line_indent=False, before=6, after=2, align=WD_ALIGN_PARAGRAPH.CENTER)
    paragraph.paragraph_format.keep_with_next = True
    run = paragraph.add_run()
    run.add_picture(str(image_path), width=Cm(width_cm))
    add_caption(document, caption, above=False)


def set_cell_border(cell, **kwargs):
    tc = cell._tc
    tc_pr = tc.get_or_add_tcPr()
    borders = tc_pr.first_child_found_in("w:tcBorders")
    if borders is None:
        borders = OxmlElement("w:tcBorders")
        tc_pr.append(borders)
    for edge in ("top", "left", "bottom", "right"):
        if edge in kwargs:
            tag = "w:" + edge
            element = borders.find(qn(tag))
            if element is None:
                element = OxmlElement(tag)
                borders.append(element)
            for key in kwargs[edge]:
                element.set(qn("w:" + key), str(kwargs[edge][key]))


def set_three_line_table(table, header_rows=1):
    """Apply a Chinese three-line table style: top/bottom rules and a header rule only."""
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = True
    for row_index, row in enumerate(table.rows):
        # 行内容不跨页
        tr_pr = row._tr.get_or_add_trPr()
        cant_split = OxmlElement("w:cantSplit")
        tr_pr.append(cant_split)
        if row_index < header_rows:
            # 表头跨页重复
            header = OxmlElement("w:tblHeader")
            tr_pr.append(header)
        for cell in row.cells:
            cell.vertical_alignment = 1
            set_cell_border(
                cell,
                top={"sz": 16, "val": "single", "color": "000000"} if row_index == 0 else {"sz": 0, "val": "nil"},
                bottom={"sz": 16, "val": "single", "color": "000000"} if row_index == header_rows - 1 else (
                    {"sz": 8, "val": "single", "color": "000000"} if row_index == len(table.rows) - 1 else {"sz": 0, "val": "nil"}
                ),
                left={"sz": 0, "val": "nil"},
                right={"sz": 0, "val": "nil"},
            )
            for paragraph in cell.paragraphs:
                set_paragraph_format(paragraph, first_line_indent=False, before=1, after=1, line_spacing=1.0,
                                     align=WD_ALIGN_PARAGRAPH.CENTER)
                for run in paragraph.runs:
                    set_run_font(run, east_asia=SONG, latin=TIMES, size=10.5, bold=(row_index < header_rows))


def add_table(document, rows, caption=None):
    if not rows:
        return
    column_count = max(len(row) for row in rows)
    table = document.add_table(rows=len(rows), cols=column_count)
    table.style = "Table Grid"
    for row_index, row in enumerate(rows):
        for column_index in range(column_count):
            value = row[column_index] if column_index < len(row) else ""
            cell = table.cell(row_index, column_index)
            cell.text = ""
            paragraph = cell.paragraphs[0]
            add_inline_runs(paragraph, value.strip(), east_asia=SONG, latin=TIMES, size=10.5, base_bold=(row_index == 0))
    if caption:
        caption_paragraph = add_caption(document, caption, above=True)
        caption_paragraph.paragraph_format.keep_with_next = True
    set_three_line_table(table)
    add_paragraph(document, "", first_line_indent=False, size=6, after=2)


def add_page_number_footer(section, prefix=""):
    footer = section.footer
    paragraph = footer.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(prefix)
    set_run_font(run, east_asia=SONG, latin=TIMES, size=9)
    fld_char_1 = OxmlElement("w:fldChar")
    fld_char_1.set(qn("w:fldCharType"), "begin")
    instr_text = OxmlElement("w:instrText")
    instr_text.set(qn("xml:space"), "preserve")
    instr_text.text = " PAGE "
    fld_char_2 = OxmlElement("w:fldChar")
    fld_char_2.set(qn("w:fldCharType"), "end")
    run_element = paragraph.add_run()._r
    run_element.append(fld_char_1)
    run_element.append(instr_text)
    run_element.append(fld_char_2)
    for footer_run in paragraph.runs:
        set_run_font(footer_run, east_asia=SONG, latin=TIMES, size=9)


def add_header(section, text):
    header = section.header
    paragraph = header.paragraphs[0]
    paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    run = paragraph.add_run(text)
    set_run_font(run, east_asia=SONG, latin=TIMES, size=9)
    # bottom rule for the header
    p_pr = paragraph._p.get_or_add_pPr()
    p_bdr = OxmlElement("w:pBdr")
    bottom = OxmlElement("w:bottom")
    bottom.set(qn("w:val"), "single")
    bottom.set(qn("w:sz"), "4")
    bottom.set(qn("w:space"), "1")
    bottom.set(qn("w:color"), "000000")
    p_bdr.append(bottom)
    p_pr.append(p_bdr)


def configure_document(document, header_text):
    section = document.sections[0]
    section.page_width = Cm(21.0)
    section.page_height = Cm(29.7)
    section.top_margin = Cm(2.54)
    section.bottom_margin = Cm(2.54)
    section.left_margin = Cm(3.0)
    section.right_margin = Cm(2.6)
    section.different_first_page_header_footer = True
    normal_style = document.styles["Normal"]
    normal_style.font.name = TIMES
    normal_style.font.size = Pt(12)
    normal_style.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)
    add_header(section, header_text)
    add_page_number_footer(section)


def add_cover(document, title, subtitle, meta_lines):
    for _ in range(3):
        add_paragraph(document, "", first_line_indent=False, size=12)
    paragraph = document.add_paragraph()
    set_paragraph_format(paragraph, first_line_indent=False, align=WD_ALIGN_PARAGRAPH.CENTER)
    run = paragraph.add_run(title)
    set_run_font(run, east_asia=HEI, latin=TIMES, size=26, bold=True)
    if subtitle:
        paragraph = document.add_paragraph()
        set_paragraph_format(paragraph, first_line_indent=False, before=8, after=8, align=WD_ALIGN_PARAGRAPH.CENTER)
        run = paragraph.add_run(subtitle)
        set_run_font(run, east_asia=HEI, latin=TIMES, size=18, bold=True)
    for _ in range(4):
        add_paragraph(document, "", first_line_indent=False, size=12)
    for line in meta_lines:
        paragraph = document.add_paragraph()
        set_paragraph_format(paragraph, first_line_indent=False, after=4, align=WD_ALIGN_PARAGRAPH.CENTER)
        run = paragraph.add_run(line)
        set_run_font(run, east_asia=SONG, latin=TIMES, size=13)
    add_page_break(document)


def add_toc_entries(document, entries, key):
    """Add TOC lines with dot leaders and page numbers when a mapping exists."""
    import json
    mapping_path = DRAFTS / "toc_pages.json"
    mapping = {}
    if mapping_path.exists():
        try:
            mapping = json.loads(mapping_path.read_text(encoding="utf-8")).get(key, {})
        except Exception:
            mapping = {}
    for entry in entries:
        paragraph = document.add_paragraph()
        set_paragraph_format(paragraph, first_line_indent=False, after=2, line_spacing=1.2,
                             align=WD_ALIGN_PARAGRAPH.LEFT)
        paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(15.4), WD_TAB_ALIGNMENT.RIGHT, WD_TAB_LEADER.DOTS)
        run = paragraph.add_run(entry)
        set_run_font(run, east_asia=SONG, latin=TIMES, size=11)
        page = mapping.get(entry)
        if page:
            paragraph.add_run("\t")
            run = paragraph.add_run(str(page))
            set_run_font(run, east_asia=SONG, latin=TIMES, size=11)


def add_page_break(document):
    paragraph = document.add_paragraph()
    paragraph.add_run().add_break(WD_BREAK.PAGE)


# ---------- markdown parsing ----------

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.+?)\s*$")
IMAGE_PATTERN = re.compile(r"^!\[(.+?)\]\((.+?)\)\s*$")
TABLE_SEPARATOR = re.compile(r"^\|?\s*:?-{2,}")


def parse_markdown(markdown_path):
    lines = Path(markdown_path).read_text(encoding="utf-8").replace("\ufeff", "").splitlines()
    blocks = []
    index = 0
    while index < len(lines):
        line = lines[index]
        stripped = line.strip()
        if not stripped:
            index += 1
            continue
        heading = HEADING_PATTERN.match(stripped)
        if heading:
            blocks.append(("heading", len(heading.group(1)), heading.group(2).strip()))
            index += 1
            continue
        image = IMAGE_PATTERN.match(stripped)
        if image:
            blocks.append(("image", image.group(1).strip(), image.group(2).strip()))
            index += 1
            continue
        if stripped.startswith("```"):
            language = stripped[3:].strip()
            index += 1
            code_lines = []
            while index < len(lines) and not lines[index].strip().startswith("```"):
                code_lines.append(lines[index])
                index += 1
            index += 1
            blocks.append(("code", "\n".join(code_lines)))
            continue
        if stripped.startswith("|") and "|" in stripped:
            table_lines = []
            while index < len(lines) and lines[index].strip().startswith("|"):
                table_lines.append(lines[index].strip())
                index += 1
            if len(table_lines) >= 2 and TABLE_SEPARATOR.match(table_lines[1]):
                table_lines = [table_lines[0]] + table_lines[2:]
            rows = []
            for table_line in table_lines:
                cells = [cell.strip() for cell in table_line.strip("|").split("|")]
                rows.append(cells)
            blocks.append(("table", rows))
            continue
        if stripped.startswith(">"):
            quote_lines = []
            while index < len(lines) and lines[index].strip().startswith(">"):
                quote_lines.append(lines[index].strip().lstrip(">").strip())
                index += 1
            blocks.append(("quote", " ".join(quote_lines)))
            continue
        if stripped.startswith("- ") or stripped.startswith("* "):
            items = []
            while index < len(lines) and (lines[index].strip().startswith("- ") or lines[index].strip().startswith("* ")):
                items.append(lines[index].strip()[2:].strip())
                index += 1
            blocks.append(("list", items, "bullet"))
            continue
        numbered = re.match(r"^(\d+)\.\s+(.*)$", stripped)
        if numbered:
            items = []
            while index < len(lines):
                item_match = re.match(r"^(\d+)\.\s+(.*)$", lines[index].strip())
                if not item_match:
                    break
                items.append(item_match.group(2).strip())
                index += 1
            blocks.append(("list", items, "number"))
            continue
        # paragraph: gather until blank / block start
        paragraph_lines = [stripped]
        index += 1
        while index < len(lines):
            candidate = lines[index].strip()
            if (not candidate or HEADING_PATTERN.match(candidate) or IMAGE_PATTERN.match(candidate)
                    or candidate.startswith("|") or candidate.startswith(">") or candidate.startswith("```")
                    or candidate.startswith("- ") or candidate.startswith("* ") or re.match(r"^\d+\.\s+", candidate)):
                break
            paragraph_lines.append(candidate)
            index += 1
        blocks.append(("paragraph", " ".join(paragraph_lines)))
    return blocks


def resolve_image_path(relative_path):
    path = Path(relative_path)
    if path.is_absolute():
        return path
    # markers are ../assets/... relative to drafts directory
    candidate = (DRAFTS / path).resolve()
    if candidate.exists():
        return candidate
    candidate = (ASSETS / path.name).resolve()
    return candidate


def add_figure(document, caption, image_path, width_cm=14.6):
    add_picture(document, resolve_image_path(image_path), caption, width_cm=width_cm)


# ---------- document assembly ----------

def build_design_document():
    document = Document()
    configure_document(document, "任务管理系统项目设计文档")
    add_cover(
        document,
        "任务管理系统项目设计文档",
        "Task Management System · v1.2.2",
        ["项目开发团队（成员 A、B、C、D）", "版本：1.2.2", "日期：2026 年 11 月 25 日"],
    )
    add_heading(document, "目录", 1)
    toc_entries = [
        "摘要",
        "1 项目背景与目的",
        "2 技术栈",
        "3 模块设计与系统架构",
        "4 技术实现",
        "5 测试结果",
        "6 开发过程",
        "7 结论与展望",
        "8 参考文献",
    ]
    add_toc_entries(document, toc_entries, "design")
    add_page_break(document)

    blocks = parse_markdown(DRAFTS / "designDocument.md")
    table_counter = 0
    chapter = "0"
    skip_title = True
    last_image_caption = ""
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            level = block[1]
            text = block[2]
            if level == 1 and skip_title:
                skip_title = False
                continue
            if level == 1:
                continue
            chapter_match = re.match(r"^(\d+)", text)
            if chapter_match and level == 2:
                chapter = chapter_match.group(1)
                table_counter = 0
            if text.startswith("摘要"):
                add_heading(document, "摘要", 1)
                continue
            add_heading(document, text, 1 if level == 2 else 2 if level == 3 else 3)
        elif kind == "paragraph":
            text = block[1]
            if text.startswith("**表") and text.endswith("**"):
                # table caption captured by the following table block
                add_caption(document, text.strip("*").strip(), above=True)
                continue
            if (last_image_caption and re.match(r"^图\s*\d+[-–—]\d+", text)
                    and text[:12] == last_image_caption[:12]):
                last_image_caption = ""
                continue
            last_image_caption = ""
            add_paragraph(document, text)
        elif kind == "list":
            items = block[1]
            style = block[2]
            for item_index, item in enumerate(items, start=1):
                prefix = f"{item_index}. " if style == "number" else "• "
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=2, line_spacing=1.5,
                                     align=WD_ALIGN_PARAGRAPH.JUSTIFY)
                paragraph.paragraph_format.left_indent = Pt(24)
                run = paragraph.add_run(prefix)
                set_run_font(run, east_asia=SONG, latin=TIMES, size=12)
                add_inline_runs(paragraph, item, east_asia=SONG, latin=TIMES, size=12)
        elif kind == "quote":
            paragraph = document.add_paragraph()
            set_paragraph_format(paragraph, first_line_indent=True, after=2, line_spacing=1.5)
            paragraph.paragraph_format.left_indent = Pt(24)
            add_inline_runs(paragraph, block[1], east_asia=SONG, latin=TIMES, size=11)
        elif kind == "code":
            for code_line in block[1].splitlines():
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=0, line_spacing=1.0)
                run = paragraph.add_run(code_line)
                set_run_font(run, east_asia=CONSOLAS, latin=CONSOLAS, size=9)
        elif kind == "table":
            add_table(document, block[1])
        elif kind == "image":
            caption, image_path = block[1], block[2]
            add_figure(document, caption, image_path, width_cm=14.4)
            last_image_caption = caption
    document.save(OUTPUT / "02_DesignDocument" / "项目设计文档.docx")
    print("design document saved")


def build_user_manual():
    document = Document()
    configure_document(document, "任务管理系统 · 项目说明书")
    add_cover(
        document,
        "任务管理系统 · 项目说明书",
        "用户手册 · v1.2.2",
        ["项目开发团队（成员 A、B、C、D）", "版本：1.2.2", "日期：2026 年 11 月 25 日"],
    )
    add_heading(document, "目录", 1)
    toc_entries = [
        "1 软件简介与运行环境", "2 安装、首次启动与卸载", "3 登录、注册、退出与修改密码",
        "4 界面总览", "5 团队管理", "6 任务管理", "7 待办清单与便签小窗",
        "8 团队协作", "9 AI 功能", "10 通知中心", "11 个人资料与系统设置",
        "12 管理后台", "13 局域网多设备使用", "14 数据备份、版本升级与卸载",
        "15 常见问题与故障排查",
    ]
    add_toc_entries(document, toc_entries, "manual")
    add_page_break(document)

    blocks = parse_markdown(DRAFTS / "userManual.md")
    skip_title = True
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            level = block[1]
            text = block[2]
            if level == 1 and skip_title:
                skip_title = False
                continue
            if level == 1:
                continue
            add_heading(document, text, 1 if level == 2 else 2 if level == 3 else 3)
        elif kind == "paragraph":
            add_paragraph(document, block[1])
        elif kind == "list":
            items = block[1]
            style = block[2]
            for item_index, item in enumerate(items, start=1):
                prefix = f"{item_index}. " if style == "number" else "• "
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=2, line_spacing=1.5)
                paragraph.paragraph_format.left_indent = Pt(24)
                run = paragraph.add_run(prefix)
                set_run_font(run, east_asia=SONG, latin=TIMES, size=12)
                add_inline_runs(paragraph, item, east_asia=SONG, latin=TIMES, size=12)
        elif kind == "quote":
            add_paragraph(document, block[1], size=11)
        elif kind == "code":
            for code_line in block[1].splitlines():
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=0, line_spacing=1.0)
                run = paragraph.add_run(code_line)
                set_run_font(run, east_asia=CONSOLAS, latin=CONSOLAS, size=9)
        elif kind == "table":
            add_table(document, block[1])
        elif kind == "image":
            caption, image_path = block[1], block[2]
            add_figure(document, caption, image_path, width_cm=14.2)
    document.save(OUTPUT / "03_UserManual" / "任务管理系统_项目说明书.docx")
    print("user manual saved")


def build_evaluation_document(markdown_name, output_name, english=True):
    document = Document()
    configure_document(document, "Project Evaluation Report" if english else "项目评估报告")
    if english:
        add_cover(
            document,
            "Project Evaluation Report",
            "Task Management System · v1.2.2",
            ["Team A / B / C / D", "English version", "25 November 2026", "Body length: under 2,500 words (references excluded)"],
        )
    else:
        add_cover(
            document,
            "项目评估报告",
            "任务管理系统 · v1.2.2",
            ["项目团队：成员 A、B、C、D", "中文版", "2026 年 11 月 25 日", "正文篇幅参考英文版（不含参考文献）"],
        )
    blocks = parse_markdown(DRAFTS / markdown_name)
    skip_title = True
    in_references = False
    for block in blocks:
        kind = block[0]
        if kind == "heading":
            level = block[1]
            text = block[2]
            if level == 1 and skip_title:
                skip_title = False
                continue
            if level == 1:
                continue
            if re.match(r"^(9\.?\s*)?References|^参考文献", text):
                in_references = True
            heading_level = 1 if level == 2 else 2 if level == 3 else 3
            add_heading(document, text, heading_level, english=english)
        elif kind == "paragraph":
            if in_references:
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=3, line_spacing=1.15,
                                     align=WD_ALIGN_PARAGRAPH.LEFT)
                paragraph.paragraph_format.left_indent = Pt(24)
                paragraph.paragraph_format.first_line_indent = Pt(-24)
                add_inline_runs(paragraph, block[1], east_asia=SONG if not english else TIMES,
                                latin=TIMES, size=10.5)
            else:
                add_paragraph(document, block[1], size=11 if english else 11,
                              east_asia=TIMES if english else SONG)
        elif kind == "list":
            items, style = block[1], block[2]
            for item_index, item in enumerate(items, start=1):
                prefix = f"{item_index}. " if style == "number" else "• "
                paragraph = document.add_paragraph()
                set_paragraph_format(paragraph, first_line_indent=False, after=2, line_spacing=1.5)
                paragraph.paragraph_format.left_indent = Pt(24)
                run = paragraph.add_run(prefix)
                set_run_font(run, east_asia=SONG if not english else TIMES, latin=TIMES, size=11)
                add_inline_runs(paragraph, item, east_asia=SONG if not english else TIMES, latin=TIMES, size=11)
        elif kind == "table":
            add_table(document, block[1])
        elif kind == "image":
            add_figure(document, block[1], block[2], width_cm=14.0)
    target = OUTPUT / "04_EvaluationReport" / output_name
    document.save(target)
    print("evaluation saved:", target)


if __name__ == "__main__":
    build_design_document()
    build_user_manual()
    build_evaluation_document("evaluationReport_EN.md", "ProjectEvaluationReport_EN.docx", english=True)
    chinese_path = DRAFTS / "evaluationReport_CN.md"
    if chinese_path.exists():
        build_evaluation_document("evaluationReport_CN.md", "项目评估报告_中文版.docx", english=False)
    else:
        print("Chinese evaluation draft not found; skipped.")
