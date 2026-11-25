"""Map document headings to rendered PDF page numbers for the TOC."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
PDFTOTEXT = r"C:\texlive\2026\bin\windows\pdftotext.exe"
DRAFTS = PROJECT_ROOT / "deliverables" / "drafts"

DESIGN_HEADINGS = [
    "摘要", "1 项目背景与目的", "2 技术栈", "3 模块设计与系统架构", "4 技术实现",
    "5 测试结果", "6 开发过程", "7 结论与展望", "8 参考文献",
]
MANUAL_HEADINGS = [
    "1 软件简介与运行环境", "2 安装、首次启动与卸载", "3 登录、注册、退出与修改密码",
    "4 界面总览", "5 团队管理", "6 任务管理", "7 待办清单与便签小窗",
    "8 团队协作", "9 AI 功能", "10 通知中心", "11 个人资料与系统设置",
    "12 管理后台", "13 局域网多设备使用", "14 数据备份、版本升级与卸载",
    "15 常见问题与故障排查",
]


def page_text(pdf_path, page_number):
    result = subprocess.run(
        [PDFTOTEXT, "-f", str(page_number), "-l", str(page_number), str(pdf_path), "-"],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    return re.sub(r"\s+", "", result.stdout)


def map_heading(pdf_path, heading, total_pages):
    target = re.sub(r"\s+", "", heading)
    # TOC 页面本身也会出现标题文本，正文从第 3 页开始
    for page_number in range(3, total_pages + 1):
        text = page_text(pdf_path, page_number)
        if target and target in text:
            return page_number
    # 退化匹配：去掉编号和标点后的核心标题
    core = re.sub(r"^[0-9]+", "", target)
    core = re.sub(r"[，,。.、：:（）()]", "", core)
    for page_number in range(3, total_pages + 1):
        text = page_text(pdf_path, page_number)
        if len(core) >= 4 and core in text:
            return page_number
    return None


def page_count(pdf_path):
    result = subprocess.run(
        [r"C:\texlive\2026\bin\windows\pdfinfo.exe", str(pdf_path)],
        capture_output=True, text=True, encoding="utf-8", errors="ignore",
    )
    match = re.search(r"Pages:\s+(\d+)", result.stdout)
    return int(match.group(1)) if match else 0


def build_mapping(pdf_path, headings):
    total = page_count(pdf_path)
    mapping = {}
    for heading in headings:
        mapping[heading] = map_heading(pdf_path, heading, total)
    return mapping


if __name__ == "__main__":
    design_pdf = PROJECT_ROOT / "deliverables" / "02_DesignDocument" / "项目设计文档.pdf"
    manual_pdf = PROJECT_ROOT / "deliverables" / "03_UserManual" / "任务管理系统_项目说明书.pdf"
    mapping = {
        "design": build_mapping(design_pdf, DESIGN_HEADINGS),
        "manual": build_mapping(manual_pdf, MANUAL_HEADINGS),
    }
    target = DRAFTS / "toc_pages.json"
    target.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(mapping, ensure_ascii=False, indent=2))
