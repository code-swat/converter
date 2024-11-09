import pymupdf
import tempfile
from typing import Dict

def parse(uploaded_file: bytes) -> Dict:
    """
    Parse tables in a PDF file
    """
    with tempfile.NamedTemporaryFile(delete=True, suffix='.pdf') as temp_file:
        temp_file.write(uploaded_file.read())
        temp_file.flush()
        doc = pymupdf.open(temp_file.name)

    return [page.get_text() for page in doc]
