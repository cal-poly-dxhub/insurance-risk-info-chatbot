import requests
import io
from pypdf import PdfReader
from difflib import SequenceMatcher
import re

def preprocess_text(text):
    return re.sub(r'\s+', ' ', text).lower().strip()

def fast_find_text_in_pdf(url, search_text, threshold=0.5):
    response = requests.get(url)
    pdf_file = io.BytesIO(response.content)
    pdf_reader = PdfReader(pdf_file)

    search_text = preprocess_text(search_text)
    best_match = (0, None)  # (similarity, page_number)

    # Extract all page texts at once
    page_texts = [preprocess_text(page.extract_text()) for page in pdf_reader.pages]

    # First, find the most similar page
    for page_num, page_text in enumerate(page_texts, 1):
        similarity = SequenceMatcher(None, search_text, page_text).ratio()
        if similarity > best_match[0]:
            best_match = (similarity, page_num)

    if best_match[0] >= threshold:
        return best_match[1]
    return None

def get_url_with_page(url, chunk):
    page_number = fast_find_text_in_pdf(url, chunk)

    if page_number is not None:
        return f"{url}#page={page_number}"
    else:
        return url  # Return the original URL if text is not found
