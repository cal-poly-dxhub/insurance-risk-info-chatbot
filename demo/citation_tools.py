import fitz  # PyMuPDF
import requests
from io import BytesIO
from pypdf import PdfReader, PdfWriter
from fuzzywuzzy import fuzz

def download_pdf(url):
    response = requests.get(url)
    if response.status_code == 200:
        return BytesIO(response.content)
    else:
        raise Exception(f"Failed to download PDF, status code: {response.status_code}")

def unlock_pdf(file_stream, password):
    reader = PdfReader(file_stream)
    if reader.is_encrypted:
        reader.decrypt(password)
        writer = PdfWriter()
        for page_num in range(reader.get_num_pages()):
            writer.add_page(reader.get_page(page_num))
        output_stream = BytesIO()
        writer.write(output_stream)
        output_stream.seek(0)
        return output_stream
    else:
        file_stream.seek(0)
        return file_stream

def extract_text_from_pdf(pdf_stream):
    doc = fitz.open(stream=pdf_stream, filetype="pdf")
    text_by_page = []
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text()
        text_by_page.append(text)
    return text_by_page

def find_most_similar_page(passage, text_by_page, threshold=70):
    best_match = 0
    highest_score = 0

    for page_num, text in enumerate(text_by_page):
        score = fuzz.partial_ratio(passage, text)
        if score > highest_score and score >= threshold:
            highest_score = score
            best_match = page_num + 1  # Adjust index to start from 1

    return best_match, score