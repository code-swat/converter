import pymupdf
import tempfile

from typing import Dict

def parse(data: bytes) -> Dict:
    """
    Parse tables in a PDF file
    """
    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as temp_file:
        temp_file.write(data)
        temp_file.flush()
        doc = pymupdf.open(temp_file.name)

    return [page.get_text() for page in doc]

def stats(data: bytes) -> Dict:
    """
    Get stats from a PDF file
    """
    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as temp_file:
        temp_file.write(data)
        temp_file.flush()
        doc = pymupdf.open(temp_file.name)
        stats = { "pages": len(doc) }

    return stats
