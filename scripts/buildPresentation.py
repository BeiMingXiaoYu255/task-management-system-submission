"""Build the English project presentation (17-18 slides) for the Task Management System v1.2.2."""

from __future__ import annotations

import os
from pathlib import Path

from PIL import Image
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu, Inches, Pt

PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSETS = PROJECT_ROOT / "deliverables" / "assets"
OUTPUT_DIRECTORY = PROJECT_ROOT / "deliverables" / "01_Presentation"
OUTPUT_FILE = OUTPUT_DIRECTORY / "TaskManagementSystem_Project_Presentation.pptx"

BLACK = RGBColor(0x11, 0x11, 0x11)
DARK_BACKGROUND = RGBColor(0x14, 0x14, 0x14)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LIGHT_BACKGROUND = RGBColor(0xF7, 0xF7, 0xF7)
PANEL_BACKGROUND = RGBColor(0xF1, 0xF1, 0xF1)
MID_GRAY = RGBColor(0x6B, 0x6B, 0x6B)
LIGHT_GRAY = RGBColor(0xD9, 0xD9, 0xD9)
FONT = "Segoe UI"
MONO = "Consolas"
SLIDE_WIDTH = Inches(13.333)
SLIDE_HEIGHT = Inches(7.5)


def set_text(run, text, size=16, bold=False, color=BLACK, font=FONT, italic=False):
    """Apply typography to one text run."""
    run.text = text
    run.font.name = font
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.italic = italic
    run.font.color.rgb = color


def add_textbox(slide, left, top, width, height, text, size=16, bold=False, color=BLACK,
                align=PP_ALIGN.LEFT, font=FONT, anchor=MSO_ANCHOR.TOP, line_spacing=1.1):
    textbox = slide.shapes.add_textbox(left, top, width, height)
    frame = textbox.text_frame
    frame.word_wrap = True
    frame.vertical_anchor = anchor
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    paragraph = frame.paragraphs[0]
    paragraph.alignment = align
    paragraph.line_spacing = line_spacing
    set_text(paragraph.add_run(), text, size=size, bold=bold, color=color, font=font)
    return textbox


def add_paragraphs(slide, left, top, width, height, items, base_size=17, color=BLACK,
                   bullet_color=MID_GRAY, line_spacing=1.18, space_after=8):
    """Add a list of (text, size, bold, level) items as paragraphs."""
    textbox = slide.shapes.add_textbox(left, top, width, height)
    frame = textbox.text_frame
    frame.word_wrap = True
    frame.margin_left = 0
    frame.margin_right = 0
    frame.margin_top = 0
    frame.margin_bottom = 0
    first = True
    for item in items:
        text = item[0]
        size = item[1] if len(item) > 1 and item[1] else base_size
        bold = item[2] if len(item) > 2 else False
        level = item[3] if len(item) > 3 else 0
        paragraph = frame.paragraphs[0] if first else frame.add_paragraph()
        first = False
        paragraph.level = level
        paragraph.line_spacing = line_spacing
        paragraph.space_after = Pt(space_after)
        if level == 0:
            run = paragraph.add_run()
            set_text(run, ("—  " if text.startswith("•") is False and len(items) > 1 else "") + text.lstrip("• "), size=size, bold=bold, color=color)
            paragraph.alignment = PP_ALIGN.LEFT
        else:
            run = paragraph.add_run()
            set_text(run, "· " + text, size=size, bold=bold, color=color)
            paragraph.alignment = PP_ALIGN.LEFT
    return textbox


def add_rect(slide, left, top, width, height, fill, line=None, line_width=1.0, radius=False):
    shape_type = MSO_SHAPE.ROUNDED_RECTANGLE if radius else MSO_SHAPE.RECTANGLE
    shape = slide.shapes.add_shape(shape_type, left, top, width, height)
    shape.fill.solid()
    shape.fill.fore_color.rgb = fill
    if line is None:
        shape.line.fill.background()
    else:
        shape.line.color.rgb = line
        shape.line.width = Pt(line_width)
    if radius:
        shape.adjustments[0] = 0.04
    shape.shadow.inherit = False
    return shape


def add_line(slide, x1, y1, x2, y2, color=LIGHT_GRAY, width=1.0):
    connector = slide.shapes.add_connector(1, x1, y1, x2, y2)
    connector.line.color.rgb = color
    connector.line.width = Pt(width)
    return connector


def new_slide(prs, background=LIGHT_BACKGROUND):
    slide = prs.slides.add_slide(prs.slide_layouts[6])
    fill = slide.background.fill
    fill.solid()
    fill.fore_color.rgb = background
    return slide


def add_chrome(slide, page_number, section, title, dark=False):
    """Add kicker, title, top rule and footer to a content slide."""
    text_color = WHITE if dark else BLACK
    muted_color = RGBColor(0x9A, 0x9A, 0x9A) if dark else MID_GRAY
    line_color = RGBColor(0x3A, 0x3A, 0x3A) if dark else LIGHT_GRAY
    add_textbox(slide, Inches(0.55), Inches(0.32), Inches(9.0), Inches(0.28),
                (section or "").upper(), size=10, bold=True, color=muted_color)
    add_textbox(slide, Inches(0.55), Inches(0.62), Inches(12.2), Inches(0.85),
                title, size=28, bold=True, color=text_color)
    add_line(slide, Inches(0.55), Inches(1.55), Inches(12.78), Inches(1.55), color=line_color, width=1.0)
    add_textbox(slide, Inches(0.55), Inches(7.12), Inches(7.0), Inches(0.25),
                "Task Management System · v1.2.2", size=9, color=muted_color)
    add_textbox(slide, Inches(11.85), Inches(7.12), Inches(0.9), Inches(0.25),
                f"{page_number + 1:02d}", size=9, color=muted_color, align=PP_ALIGN.RIGHT)


def add_picture(slide, image_path, left, top, width, height, border=True, fill=PANEL_BACKGROUND):
    """Add an image scaled to fit inside a frame, centered, with optional border."""
    image_path = Path(image_path)
    with Image.open(image_path) as image:
        image_width, image_height = image.size
    frame_ratio = width / height
    image_ratio = image_width / image_height
    if image_ratio > frame_ratio:
        render_width = width
        render_height = Emu(int(width / image_ratio))
    else:
        render_height = height
        render_width = Emu(int(height * image_ratio))
    render_left = Emu(int(left + (width - render_width) / 2))
    render_top = Emu(int(top + (height - render_height) / 2))
    if border:
        add_rect(slide, left, top, width, height, fill, line=LIGHT_GRAY, line_width=0.75)
    slide.shapes.add_picture(str(image_path), render_left, render_top, render_width, render_height)


def add_picture_cover(slide, image_path, left, top, width, height, border=True, fill=PANEL_BACKGROUND):
    """Add an image that fills the frame by cropping instead of letterboxing."""
    image_path = Path(image_path)
    with Image.open(image_path) as image:
        image_width, image_height = image.size
    frame_ratio = width / height
    image_ratio = image_width / image_height
    if border:
        add_rect(slide, left, top, width, height, fill, line=LIGHT_GRAY, line_width=0.75)
    picture = slide.shapes.add_picture(str(image_path), left, top, width, height)
    if image_ratio > frame_ratio:
        visible = frame_ratio / image_ratio
        crop = (1 - visible) / 2
        picture.crop_left = crop
        picture.crop_right = crop
    else:
        visible = image_ratio / frame_ratio
        crop = (1 - visible) / 2
        picture.crop_top = crop
        picture.crop_bottom = crop
    return picture


def add_notes(slide, text):
    slide.notes_slide.notes_text_frame.text = text


def add_kpi(slide, left, top, width, height, value, label, dark=False):
    fill = RGBColor(0x1E, 0x1E, 0x1E) if dark else WHITE
    line = RGBColor(0x3A, 0x3A, 0x3A) if dark else LIGHT_GRAY
    add_rect(slide, left, top, width, height, fill, line=line, line_width=0.75)
    value_color = WHITE if dark else BLACK
    label_color = RGBColor(0xA8, 0xA8, 0xA8) if dark else MID_GRAY
    add_textbox(slide, left + Inches(0.22), top + Inches(0.18), width - Inches(0.4), Inches(0.55),
                value, size=26, bold=True, color=value_color)
    add_textbox(slide, left + Inches(0.22), top + Inches(0.72), width - Inches(0.4), Inches(0.5),
                label, size=11, color=label_color)


def build_deck():
    prs = Presentation()
    prs.slide_width = SLIDE_WIDTH
    prs.slide_height = SLIDE_HEIGHT
    slide_number = 0

    # ---------- Slide 1: title ----------
    slide = new_slide(prs, DARK_BACKGROUND)
    add_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.08), WHITE)
    add_textbox(slide, Inches(0.8), Inches(1.15), Inches(11.6), Inches(0.35),
                "FINAL PROJECT PRESENTATION · 25 NOVEMBER 2026", size=11, color=RGBColor(0xA8, 0xA8, 0xA8))
    add_textbox(slide, Inches(0.8), Inches(1.65), Inches(11.8), Inches(1.0),
                "Task Management System", size=54, bold=True, color=WHITE)
    add_textbox(slide, Inches(0.8), Inches(2.85), Inches(11.4), Inches(1.4),
                "Lightweight desktop task management with cross-team collaboration, dual review and AI-assisted assignment · v1.2.2",
                size=22, color=RGBColor(0xD8, 0xD8, 0xD8), line_spacing=1.2)
    add_line(slide, Inches(0.8), Inches(4.55), Inches(12.5), Inches(4.55), color=RGBColor(0x44, 0x44, 0x44))
    contributions = [
        ("A", "Frontend foundation & core task domain"),
        ("B", "Collaboration & experience domain"),
        ("C", "Backend architecture & database"),
        ("D", "AI auto-assignment module"),
    ]
    for index, (label, description) in enumerate(contributions):
        left = Inches(0.8 + index * 3.05)
        add_textbox(slide, left, Inches(4.95), Inches(0.5), Inches(0.4), label, size=20, bold=True, color=WHITE)
        add_textbox(slide, left + Inches(0.42), Inches(4.98), Inches(2.45), Inches(0.9),
                    description, size=11, color=RGBColor(0xB8, 0xB8, 0xB8), line_spacing=1.15)
    add_textbox(slide, Inches(0.8), Inches(6.85), Inches(11.6), Inches(0.3),
                "Sources: project development documentation · test documentation · QA acceptance report · release checksums",
                size=9, color=RGBColor(0x7A, 0x7A, 0x7A))
    slide_number += 1
    add_notes(slide, "This deck presents the delivered v1.2.2 desktop product, the engineering evidence behind it, and the three time-boxed iterations completed between 15 and 25 November 2026.")

    # ---------- Slide 2: agenda ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "Overview", "Agenda")
    agenda_items = [
        ("01", "Design background and scope", "Problem, target users, fixed scope"),
        ("02", "Technology stack and architecture", "Tauri, React, FastAPI, MariaDB, packaging"),
        ("03", "Product walkthrough", "Task loop, collaboration, AI, interface"),
        ("04", "Process, quality and evidence", "Time boxing, test results, improvements"),
        ("05", "Team and reflection", "Contributions A–D, limitations, questions"),
    ]
    top = Inches(1.95)
    for index, (number, title, subtitle) in enumerate(agenda_items):
        row_top = top + Inches(index * 0.92)
        add_textbox(slide, Inches(0.7), row_top + Inches(0.02), Inches(0.75), Inches(0.5),
                    number, size=22, bold=True, color=BLACK)
        add_textbox(slide, Inches(1.55), row_top, Inches(5.0), Inches(0.42),
                    title, size=19, bold=True, color=BLACK)
        add_textbox(slide, Inches(1.55), row_top + Inches(0.42), Inches(5.8), Inches(0.32),
                    subtitle, size=12, color=MID_GRAY)
        add_line(slide, Inches(0.7), row_top + Inches(0.78), Inches(7.4), row_top + Inches(0.78), color=LIGHT_GRAY, width=0.75)
    add_picture(slide, ASSETS / "ui-dashboard.png", Inches(8.1), Inches(1.9), Inches(4.65), Inches(4.6))
    add_notes(slide, "The first half explains what was built and how it works. The second half focuses on the development process and the measured evidence behind the final release.")
    slide_number += 1

    # ---------- Slide 3: background ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "01 · Design background", "Small teams, disconnected tools")
    pains = [
        ("Fragmented ownership", "Tasks, deadlines and review comments live in chat threads and spreadsheets."),
        ("No cross-team handshake", "Email threads do not preserve who received, executed or signed off."),
        ("Cloud is not always available", "Small teams work on isolated LANs or networks where SaaS is blocked."),
        ("Heavyweight tools", "Jira-class tools bring accounts, configuration and Electron-sized clients."),
    ]
    goals = [
        ("One installer, zero setup", "Bundled MariaDB, Redis, backend and frontend; no server required."),
        ("Desktop plus LAN", "The same application is usable locally and from a browser on the local network."),
        ("Explicit collaboration", "Named liaisons and dual review make cross-team work auditable."),
        ("Quiet interface", "A deliberately monochrome, low-cognitive-load visual system."),
    ]
    add_textbox(slide, Inches(0.7), Inches(1.85), Inches(5.7), Inches(0.3), "TODAY", size=11, bold=True, color=MID_GRAY)
    add_textbox(slide, Inches(6.7), Inches(1.85), Inches(5.9), Inches(0.3), "TARGET", size=11, bold=True, color=MID_GRAY)
    for index, (title, description) in enumerate(pains):
        top = Inches(2.3 + index * 1.12)
        add_rect(slide, Inches(0.7), top, Inches(5.55), Inches(0.96), PANEL_BACKGROUND)
        add_textbox(slide, Inches(0.92), top + Inches(0.13), Inches(5.1), Inches(0.3), title, size=15, bold=True)
        add_textbox(slide, Inches(0.92), top + Inches(0.44), Inches(5.1), Inches(0.42), description, size=11, color=MID_GRAY)
    for index, (title, description) in enumerate(goals):
        top = Inches(2.3 + index * 1.12)
        add_rect(slide, Inches(6.7), top, Inches(5.9), Inches(0.96), WHITE, line=LIGHT_GRAY, line_width=0.75)
        add_textbox(slide, Inches(6.92), top + Inches(0.13), Inches(5.4), Inches(0.3), title, size=15, bold=True)
        add_textbox(slide, Inches(6.92), top + Inches(0.44), Inches(5.4), Inches(0.42), description, size=11, color=MID_GRAY)
    add_notes(slide, "The brief was not to build another enterprise task suite. It was to make a small team's task loop legible without a server room or a subscription, which is why offline and LAN deployment shaped the architecture.")
    slide_number += 1

    # ---------- Slide 4: scope ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "01 · Scope", "Scope and key features")
    features = [
        ("Identity & permissions", "Registration and login, three global roles, team roles, custom member levels, team certification."),
        ("Teams & collaboration", "One-level sub-teams, collaboration units, named liaisons, cross-team tasks with dual review."),
        ("Tasks & to-dos", "Member or level-range assignment, mandatory/optional acceptance, per-assignee progress, review and rejection."),
        ("AI assistance", "Local rule-based ranking, optional OpenAI-compatible LLM, four dispatch modes, auto-assignment on publish."),
        ("Supporting surface", "Dashboard, notification centre, sticky to-do window, admin console, English-only UI, LAN access."),
    ]
    for index, (title, description) in enumerate(features):
        top = Inches(1.9 + index * 0.96)
        add_textbox(slide, Inches(0.7), top, Inches(0.35), Inches(0.3), f"0{index + 1}", size=12, bold=True, color=MID_GRAY)
        add_textbox(slide, Inches(1.25), top, Inches(3.6), Inches(0.35), title, size=16, bold=True)
        add_textbox(slide, Inches(4.95), top - Inches(0.02), Inches(7.7), Inches(0.7), description, size=12, color=MID_GRAY, line_spacing=1.2)
        add_line(slide, Inches(0.7), top + Inches(0.72), Inches(12.6), top + Inches(0.72), color=LIGHT_GRAY, width=0.75)
    add_notes(slide, "Scope was fixed early and defended at every review. Anything that did not strengthen the publish–accept–submit–review loop was cut or deferred; the deferred list appears in the limitations slide.")
    slide_number += 1

    # ---------- Slide 5: stack ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "02 · Technology stack", "A deliberately small stack")
    stack_rows = [
        ("Desktop shell", "Tauri 2 (Rust + system WebView)", "8.90 MB main executable; no bundled Chromium"),
        ("Frontend", "React 18 · TypeScript · Vite 5 · CSS Modules", "Hand-written SVG charts; no UI or chart library"),
        ("Backend", "FastAPI · Python 3.11 · SQLAlchemy 2 · Pydantic 2", "Layered controllers → services → repositories → models"),
        ("Data & cache", "Portable MariaDB 11.4 · Redis 5.0", "Bundled; auto start/stop; idempotent schema migration"),
        ("Packaging", "PyInstaller · Tauri Bundler · NSIS · CI matrix", "Installer 31.13 MB · portable ZIP 40.57 MB"),
    ]
    row_top = Inches(1.9)
    for index, (layer, technology, rationale) in enumerate(stack_rows):
        top = row_top + Inches(index * 0.92)
        add_textbox(slide, Inches(0.7), top, Inches(1.7), Inches(0.3), layer.upper(), size=10, bold=True, color=MID_GRAY)
        add_textbox(slide, Inches(0.7), top + Inches(0.24), Inches(5.6), Inches(0.42), technology, size=13, bold=True)
        add_textbox(slide, Inches(6.55), top + Inches(0.22), Inches(6.0), Inches(0.5), rationale, size=11, color=MID_GRAY)
        add_line(slide, Inches(0.7), top + Inches(0.72), Inches(12.5), top + Inches(0.72), color=LIGHT_GRAY, width=0.75)
    add_notes(slide, "Each choice reduced either footprint or moving parts. Tauri removes a bundled browser; FastAPI and Pydantic keep the API contract explicit; the portable database and cache remove installation preconditions.")
    slide_number += 1

    # ---------- Slide 6: architecture ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "02 · Architecture", "System architecture: one installer, four runtime pieces")
    add_picture(slide, ASSETS / "architecture.png", Inches(0.55), Inches(1.78), Inches(8.6), Inches(4.75))
    callouts = [
        ("Tauri shell", "Starts the backend, bundled MariaDB and Redis, and closes them on exit."),
        ("Single origin", "React build at / and REST API at /api/v1; LAN clients need no additional web server."),
        ("Optional LLM", "A dashed external dependency: the product remains fully usable without it."),
    ]
    for index, (title, description) in enumerate(callouts):
        top = Inches(1.85 + index * 1.52)
        add_textbox(slide, Inches(9.45), top, Inches(3.2), Inches(0.35), title, size=13, bold=True)
        add_textbox(slide, Inches(9.45), top + Inches(0.34), Inches(3.25), Inches(0.9), description, size=10.5, color=MID_GRAY, line_spacing=1.2)
    add_notes(slide, "There is no separate web server and no external database service: the installer contains all four runtime pieces and supervises their lifecycle.")
    slide_number += 1

    # ---------- Slide 7: module map ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "02 · Architecture", "System module map")
    add_picture(slide, ASSETS / "module-map.png", Inches(0.55), Inches(1.8), Inches(12.2), Inches(4.9))
    add_notes(slide, "The module map shows the four stable boundaries used for parallel work: frontend, backend, data/contracts, and runtime/delivery.")
    slide_number += 1

    # ---------- Slide 8: task lifecycle ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "03 · Product walkthrough", "Core workflow — task lifecycle")
    add_picture(slide, ASSETS / "task-lifecycle.png", Inches(0.55), Inches(1.78), Inches(12.25), Inches(4.55))
    add_textbox(slide, Inches(0.55), Inches(6.5), Inches(12.2), Inches(0.45),
                "Per-assignee state is tracked separately from aggregate task status; only the publisher can review, and every transition is audited.",
                size=11.5, color=MID_GRAY)
    add_notes(slide, "Progress is per assignee, not per task. One person can be archived while another is still working, which is why every assignment carries its own state.")
    slide_number += 1

    # ---------- Slide 9: collaboration ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "03 · Product walkthrough", "Core workflow — collaboration and dual review")
    add_picture(slide, ASSETS / "collaboration-workflow.png", Inches(0.55), Inches(1.78), Inches(12.25), Inches(4.65))
    add_textbox(slide, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.4),
                "The receiving side must confirm and assign executors before work starts; both sides must sign off before the task closes.",
                size=11.5, color=MID_GRAY)
    add_notes(slide, "Cross-team work gets an explicit handshake: named liaisons on both sides, receiver confirmation, and two review stages before archiving.")
    slide_number += 1

    # ---------- Slide 10: AI ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "03 · Product walkthrough", "AI auto-assignment: local first, LLM optional")
    add_picture(slide, ASSETS / "ai-assignment.png", Inches(0.55), Inches(1.78), Inches(12.25), Inches(4.6))
    add_textbox(slide, Inches(0.55), Inches(6.5), Inches(12.2), Inches(0.45),
                "Formula: round(skill match ratio × 100) − active to-dos × workload penalty. Zero-overlap candidates and scores below threshold are excluded.",
                size=11, font=MONO, color=MID_GRAY)
    add_notes(slide, "The local engine is deterministic, free and testable; the LLM is an optional re-ranker. Four dispatch modes and automatic fallback keep the feature usable without an API key.")
    slide_number += 1

    # ---------- Slide 11: UI ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "03 · Product walkthrough", "UI showcase: monochrome by construction")
    add_picture(slide, ASSETS / "ui-collage.png", Inches(0.55), Inches(1.8), Inches(12.2), Inches(4.9))
    add_notes(slide, "All screenshots are from the human-style QA acceptance runs on the installed v1.2.2 build. Grayscale hierarchy comes from weight, border and spacing rather than colour.")
    slide_number += 1

    # ---------- Slide 12: time boxing ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "04 · Process", "Development process with time boxing")
    add_picture(slide, ASSETS / "timeboxing.png", Inches(0.55), Inches(1.8), Inches(12.2), Inches(4.65))
    add_textbox(slide, Inches(0.55), Inches(6.55), Inches(12.2), Inches(0.4),
                "Three increments of four, three and four days; every box closed with an installed build, a test gate and a written contract update.",
                size=11.5, color=MID_GRAY)
    add_notes(slide, "The dates are not decorative: the first build existed on 18 November, collaboration landed on 21 November, and the final installer was accepted on 25 November.")
    slide_number += 1

    # ---------- Slide 13: improvement ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "04 · Process evidence", "Process improvement evidence")
    add_picture(slide, ASSETS / "process-improvement.png", Inches(0.55), Inches(1.78), Inches(12.25), Inches(5.0))
    add_notes(slide, "The slide answers whether the process actually improved: test depth tripled because each increment added regression coverage, and acceptance moved from source-level tests to installed-artifact checks.")
    slide_number += 1

    # ---------- Slide 14: test results ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "04 · Quality", "Quality assurance and test results")
    rows = [
        ("Backend pytest", "136 / 136", "Services, repositories, API contracts, migrations"),
        ("Playwright E2E", "21 / 21", "Multi-role browser acceptance"),
        ("Human-style QA", "33 + 29", "Web walkthrough + desktop UI Automation"),
        ("Installer acceptance", "76 / 76", "Fresh 16, sticky 15, upgrade 24, styles 21"),
        ("Language gate", "0 findings", "181 frontend files and whole backend scanned"),
        ("Type check and build", "clean", "TypeScript, Vite production build, Vitest 14/14"),
    ]
    header_top = Inches(1.9)
    add_textbox(slide, Inches(0.7), header_top, Inches(3.4), Inches(0.3), "SUITE", size=9.5, bold=True, color=MID_GRAY)
    add_textbox(slide, Inches(4.2), header_top, Inches(1.7), Inches(0.3), "RESULT", size=9.5, bold=True, color=MID_GRAY)
    add_textbox(slide, Inches(6.0), header_top, Inches(4.5), Inches(0.3), "SCOPE", size=9.5, bold=True, color=MID_GRAY)
    add_line(slide, Inches(0.7), header_top + Inches(0.35), Inches(10.6), header_top + Inches(0.35), color=BLACK, width=1.2)
    for index, (suite, result, scope) in enumerate(rows):
        top = header_top + Inches(0.48 + index * 0.72)
        add_textbox(slide, Inches(0.7), top, Inches(3.3), Inches(0.3), suite, size=12, bold=True)
        add_textbox(slide, Inches(4.2), top, Inches(1.7), Inches(0.3), result, size=12, bold=True)
        add_textbox(slide, Inches(6.0), top, Inches(5.0), Inches(0.5), scope, size=10.5, color=MID_GRAY)
        add_line(slide, Inches(0.7), top + Inches(0.52), Inches(10.6), top + Inches(0.52), color=LIGHT_GRAY, width=0.6)
    add_picture(slide, ASSETS / "ui-sticky-window.png", Inches(10.75), Inches(1.9), Inches(2.05), Inches(3.4))
    add_textbox(slide, Inches(10.75), Inches(5.4), Inches(2.05), Inches(0.7), "Desktop sticky window,\nverified by UIA", size=9.5, color=MID_GRAY, line_spacing=1.15)
    add_notes(slide, "The distinction that matters is source-level tests versus artifact-level acceptance. The upgrade row proves a v1.0 database migrates in place and remains idempotent on the second start.")
    slide_number += 1

    # ---------- Slide 15: contributions A & B ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "05 · Team", "Team contributions — A and B")
    columns = [
        ("A", "Frontend foundation and core task domain", [
            "Tauri shell, routing, design system, themes and shared components",
            "Authentication, dashboard, team pages and member management UI",
            "Task form, assignment, review UI and the first 12 E2E cases",
        ]),
        ("B", "Collaboration and experience domain", [
            "Collaboration centre, sub-team management, notification centre and AI configuration UI",
            "Settings, profile and admin console surfaces; full English UI migration and AST language gates",
            "Visual QA fixes: toast overlap and sticky-window header crowding",
        ]),
    ]
    for index, (letter, title, bullets) in enumerate(columns):
        left = Inches(0.7 + index * 6.3)
        add_textbox(slide, left, Inches(1.9), Inches(0.6), Inches(0.6), letter, size=30, bold=True)
        add_textbox(slide, left + Inches(0.65), Inches(1.95), Inches(5.0), Inches(0.5), title, size=15, bold=True)
        add_paragraphs(slide, left, Inches(2.65), Inches(5.5), Inches(2.2),
                       [(f"• {bullet}", 11.5, False, 0) for bullet in bullets], base_size=11.5, space_after=9)
    add_picture_cover(slide, ASSETS / "thumb-dashboard.png", Inches(0.7), Inches(4.85), Inches(5.6), Inches(2.0))
    add_picture_cover(slide, ASSETS / "thumb-collaboration.png", Inches(7.0), Inches(4.85), Inches(5.6), Inches(2.0))
    add_notes(slide, "A owned the frame and core task loop; B owned collaboration and settings surfaces and drove the English migration. The split follows domain boundaries rather than file counts.")
    slide_number += 1

    # ---------- Slide 16: contributions C & D ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "05 · Team", "Team contributions — C and D")
    columns = [
        ("C", "Backend architecture and database", [
            "FastAPI layered design, camelCase Pydantic contracts and permission model",
            "17-table MariaDB model, idempotent migrations, notifications, audit and admin APIs",
            "Desktop runtime orchestration, packaging and the 136-test backend suite",
        ]),
        ("D", "AI auto-assignment module", [
            "Local recommendation engine, OpenAI-compatible LLM client and four dispatch modes",
            "Auto-assignment on publish, manual fallback and persisted AI configuration with connectivity test",
            "46 AI-related tests across assignment, LLM, notification and configuration suites",
        ]),
    ]
    for index, (letter, title, bullets) in enumerate(columns):
        left = Inches(0.7 + index * 6.3)
        add_textbox(slide, left, Inches(1.9), Inches(0.6), Inches(0.6), letter, size=30, bold=True)
        add_textbox(slide, left + Inches(0.65), Inches(1.95), Inches(5.0), Inches(0.5), title, size=15, bold=True)
        add_paragraphs(slide, left, Inches(2.65), Inches(5.5), Inches(2.2),
                       [(f"• {bullet}", 11.5, False, 0) for bullet in bullets], base_size=11.5, space_after=9)
    add_picture_cover(slide, ASSETS / "thumb-runtime.png", Inches(0.7), Inches(4.85), Inches(5.6), Inches(2.0))
    add_picture_cover(slide, ASSETS / "thumb-ai.png", Inches(7.0), Inches(4.85), Inches(5.6), Inches(2.0))
    add_notes(slide, "C's contribution is the part users never see: layering, permissions and migrations that let v1.0 data survive two feature releases. D's contribution is the assignment intelligence and its fallback behaviour.")
    slide_number += 1

    # ---------- Slide 17: lessons ----------
    slide = new_slide(prs, WHITE)
    add_chrome(slide, slide_number, "05 · Reflection", "Lessons learned and limitations")
    add_textbox(slide, Inches(0.7), Inches(1.9), Inches(5.9), Inches(0.3), "PROVEN", size=10, bold=True, color=MID_GRAY)
    add_textbox(slide, Inches(6.8), Inches(1.9), Inches(5.9), Inches(0.3), "NOT YET PROVEN / LIMITS", size=10, bold=True, color=MID_GRAY)
    proven = [
        "Contract-first design prevented most integration rework.",
        "Time boxing kept three demoable increments inside eleven days.",
        "Installed-artifact acceptance exposed defects that source tests missed.",
        "136 backend, 21 E2E and 62 human-style UI checks pass on v1.2.2.",
        "v1.0 → v1.2.2 migration preserves existing users and teams.",
    ]
    limits = [
        "Real LLM API behaviour unverified — no production key; local engine and mocks only.",
        "Windows installer unsigned; SmartScreen warnings expected.",
        "Windows-first packaging; Linux/macOS scripts and CI not executed on hardware.",
        "Single-machine deployment and polling notifications; no horizontal scaling.",
        "No attachments or real-time push; UI is English-only.",
    ]
    add_paragraphs(slide, Inches(0.7), Inches(2.35), Inches(5.6), Inches(3.8), [(f"• {item}", 12, False, 0) for item in proven], base_size=12, space_after=10)
    add_paragraphs(slide, Inches(6.8), Inches(2.35), Inches(5.8), Inches(3.8), [(f"• {item}", 12, False, 0) for item in limits], base_size=12, space_after=10)
    add_rect(slide, Inches(0.7), Inches(6.15), Inches(11.9), Inches(0.55), PANEL_BACKGROUND)
    add_textbox(slide, Inches(0.9), Inches(6.27), Inches(11.5), Inches(0.35),
                "Next iteration: real LLM validation, signed builds, Linux/macOS hardware verification and notification push.",
                size=11, color=MID_GRAY)
    add_notes(slide, "We separate what is proven from what is not. The installed Windows build, migration path and local AI engine are proven by repeated acceptance runs; paid LLM behaviour is not, because no key was available.")
    slide_number += 1

    # ---------- Slide 18: thank you ----------
    slide = new_slide(prs, DARK_BACKGROUND)
    add_rect(slide, Inches(0), Inches(0), Inches(13.333), Inches(0.08), WHITE)
    add_textbox(slide, Inches(0.85), Inches(1.7), Inches(11.6), Inches(0.4),
                "THANK YOU", size=12, bold=True, color=RGBColor(0xA8, 0xA8, 0xA8))
    add_textbox(slide, Inches(0.85), Inches(2.15), Inches(11.6), Inches(1.1),
                "Questions and discussion", size=44, bold=True, color=WHITE)
    add_textbox(slide, Inches(0.85), Inches(3.6), Inches(11.5), Inches(0.8),
                "v1.2.2 · 25 November 2026 · Team A / B / C / D", size=18, color=RGBColor(0xC8, 0xC8, 0xC8))
    add_line(slide, Inches(0.85), Inches(4.65), Inches(12.4), Inches(4.65), color=RGBColor(0x44, 0x44, 0x44))
    add_textbox(slide, Inches(0.85), Inches(4.95), Inches(5.4), Inches(1.2),
                "Demo available\nv1.2.2 installed with the QA dataset\nTask lifecycle · collaboration · AI assignment",
                size=12, color=RGBColor(0xB8, 0xB8, 0xB8), line_spacing=1.5)
    add_textbox(slide, Inches(6.9), Inches(4.95), Inches(5.5), Inches(1.2),
                "Artefacts\nsource in Backend/ and Frontend/\ndocs/, release/ and SHA-256 manifest",
                size=12, color=RGBColor(0xB8, 0xB8, 0xB8), line_spacing=1.5)
    add_notes(slide, "Thank you. We welcome questions on the data model, AI scoring, or the acceptance evidence; if there is one question, ask what we would fix first — real LLM validation and signed builds.")
    slide_number += 1

    OUTPUT_DIRECTORY.mkdir(parents=True, exist_ok=True)
    prs.save(str(OUTPUT_FILE))
    print(f"Saved presentation with {slide_number} slides: {OUTPUT_FILE}")


if __name__ == "__main__":
    build_deck()
