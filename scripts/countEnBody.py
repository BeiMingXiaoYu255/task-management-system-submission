from pathlib import Path
import re
from docx import Document
from docx.table import Table
from docx.text.paragraph import Paragraph
from docx.oxml.ns import qn

path = Path(r"C:\\Users\\q1506\\Desktop\\SoftwareDevelopment\\task-management-system") / "deliverables/04_EvaluationReport/ProjectEvaluationReport_EN.docx"
document = Document(path)
body = document.element.body
words = 0
in_refs = False
counted = 0
for child in body.iterchildren():
    if child.tag == qn('w:p'):
        paragraph = Paragraph(child, document)
        text = paragraph.text.strip()
        if text == '9. References':
            in_refs = True
            break
        words += len(re.findall(r"\b\w+\b", text))
        counted += 1
    elif child.tag == qn('w:tbl'):
        table = Table(child, document)
        for row in table.rows:
            for cell in row.cells:
                words += len(re.findall(r"\b\w+\b", cell.text))
        counted += 1
print("EN body words incl. tables before references:", words)
