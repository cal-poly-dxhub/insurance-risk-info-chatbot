import requests
import io
from pypdf import PdfReader
from difflib import SequenceMatcher
import re
import boto3
import time
from utils import print_terminal
from colorama import Fore
import threading
from stopit import threading_timeoutable as timeoutable

def get_parameter(param_name):
    ssm = boto3.client('ssm', region_name='YOUR_AWS_REGION')
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response['Parameter']['Value']

def preprocess_text(text):
    return re.sub(r'\s+', ' ', text).lower().strip()

def fast_find_text_in_pdf(url, search_text, threshold=0.5):
    response = requests.get(url)
    pdf_file = io.BytesIO(response.content)

    try:
        pdf_reader = PdfReader(pdf_file)
        if pdf_reader.is_encrypted:
            pdf_reader.decrypt(get_parameter('/prism/pdf/password'))
    except:
        print(f"Error: Unable to read PDF or incorrect password for {url}")
        return None

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

@timeoutable()
def get_url_with_page(url, chunk):
    start_time = time.time()
    
    page_number = fast_find_text_in_pdf(url, chunk)
    
    time_elapsed = time.time() - start_time
    print_terminal(f"Time elapsed: {time_elapsed:.2f} seconds", Fore.YELLOW)
    
    if page_number is not None:
        return f"{url}#page={page_number}"
    else:
        return url