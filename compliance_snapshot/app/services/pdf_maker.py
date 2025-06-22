from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from pathlib import Path


def build_placeholder_pdf(output: Path):
    styles = getSampleStyleSheet()
    doc = SimpleDocTemplate(str(output))
    story = [Paragraph("Compliance Snapshot – processing placeholder", styles["Title"])]
    doc.build(story)

