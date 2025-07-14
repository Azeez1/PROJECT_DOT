from pathlib import Path
from pdf2docx import Converter


def pdf_to_docx(pdf_path: Path) -> Path:
    """Convert a generated PDF to DOCX and return the DOCX path."""
    docx_path = pdf_path.with_suffix('.docx')
    cv = Converter(str(pdf_path))
    try:
        cv.convert(str(docx_path))
    finally:
        cv.close()
    return docx_path

