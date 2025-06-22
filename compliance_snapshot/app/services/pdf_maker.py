 codex/create-upload-form-and-routes
from pathlib import Path
from reportlab.pdfgen import canvas


def build_placeholder_pdf(output: Path):
    """Create a simple placeholder PDF file."""
    c = canvas.Canvas(str(output))
    c.drawString(100, 750, "Compliance Snapshot Placeholder")
    c.save()
=======
# PDF generation utilities
>>>>> main
