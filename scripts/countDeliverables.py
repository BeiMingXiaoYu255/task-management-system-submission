from pathlib import Path
import re
from docx import Document

base = Path(r"C:\\Users\\q1506\\Desktop\\SoftwareDevelopment\\task-management-system")

def count_docx_words(path, stop_heading=None):
    document = Document(path)
    words = 0
    chars = 0
    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if stop_heading and text == stop_heading:
            break
        words += len(re.findall(r"\b\w+\b", text))
        chars += len(re.findall(r"[\u4e00-\u9fff]", text))
    return words, chars

en = base / "deliverables/04_EvaluationReport/ProjectEvaluationReport_EN.docx"
cn = base / "deliverables/04_EvaluationReport/项目评估报告_中文版.docx"
print("EN body words before references:", count_docx_words(en, "9. References"))
print("CN body chars:", count_docx_words(cn, "9. 参考文献"))
design = base / "deliverables/02_DesignDocument/项目设计文档.docx"
manual = base / "deliverables/03_UserManual/任务管理系统_项目说明书.docx"
print("Design chars:", count_docx_words(design)[1])
print("Manual chars:", count_docx_words(manual)[1])

from pptx import Presentation
prs = Presentation(str(base / "deliverables/01_Presentation/TaskManagementSystem_Project_Presentation.pptx"))
print("PPT slides:", len(prs.slides))
