# import requests
# import io
# from pypdf import PdfReader
# from difflib import SequenceMatcher
# import re
# import boto3
# import time
# from utils import print_terminal
# from colorama import Fore
# def get_parameter(param_name):
#     ssm = boto3.client('ssm', region_name='YOUR_AWS_REGION')
#     response = ssm.get_parameter(Name=param_name, WithDecryption=True)
#     return response['Parameter']['Value']

# def preprocess_text(text):
#     return re.sub(r'\s+', ' ', text).lower().strip()

# def fast_find_text_in_pdf(url, search_text, threshold=0.5):
#     response = requests.get(url)
#     pdf_file = io.BytesIO(response.content)

#     try:
#         pdf_reader = PdfReader(pdf_file)
#         if pdf_reader.is_encrypted:
#             pdf_reader.decrypt(get_parameter('/prism/pdf/password'))
#     except:
#         print(f"Error: Unable to read PDF or incorrect password for {url}")
#         return None

#     search_text = preprocess_text(search_text)
#     best_match = (0, None)  # (similarity, page_number)

#     # Extract all page texts at once
#     page_texts = [preprocess_text(page.extract_text()) for page in pdf_reader.pages]

#     # First, find the most similar page
#     for page_num, page_text in enumerate(page_texts, 1):
#         similarity = SequenceMatcher(None, search_text, page_text).ratio()
#         if similarity > best_match[0]:
#             best_match = (similarity, page_num)

#     if best_match[0] >= threshold:
#         return best_match[1]
#     return None

# def get_url_with_page(url, chunk):
#     start_time = time.time()
#     page_number = fast_find_text_in_pdf(url, chunk)
#     time_elapsed = time.time() - start_time
#     print_terminal(f"Time elapsed: {time_elapsed:.2f} seconds", Fore.YELLOW)
#     if page_number is not None:
#         return f"{url}#page={page_number}"
#     else:
#         return url  # Return the original URL if text is not found
import requests
import io
from pypdf import PdfReader
import re
import boto3
from multiprocessing import Pool
import mmap
import time
from utils import print_terminal
from colorama import Fore

def get_parameter(param_name):
    ssm = boto3.client('ssm', region_name='YOUR_AWS_REGION')
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response['Parameter']['Value']

def preprocess_text(text):
    return re.sub(r'\s+', ' ', text).lower().strip()

def rabin_karp_search(text, pattern):
    if len(pattern) > len(text):
        return -1
    
    base = 256
    prime = 101
    
    def hash_func(s):
        return sum(ord(s[i]) * (base ** (len(s)-i-1)) for i in range(len(s))) % prime
    
    pattern_hash = hash_func(pattern)
    text_hash = hash_func(text[:len(pattern)])
    
    for i in range(len(text) - len(pattern) + 1):
        if text_hash == pattern_hash and text[i:i+len(pattern)] == pattern:
            return i
        if i < len(text) - len(pattern):
            text_hash = ((text_hash - ord(text[i]) * (base ** (len(pattern)-1))) * base + ord(text[i+len(pattern)])) % prime
    
    return -1

def process_page(args):
    page_num, page_text, search_text = args
    if rabin_karp_search(page_text, search_text) != -1:
        return (1, page_num)  # Found an exact match
    return (0, page_num)

def fast_find_text_in_pdf(url, search_text, threshold=0.5):
    response = requests.get(url)
    with open('temp.pdf', 'wb') as f:
        f.write(response.content)
    
    with open('temp.pdf', 'rb') as file:
        pdf_file = mmap.mmap(file.fileno(), 0, access=mmap.ACCESS_READ)
        
        try:
            pdf_reader = PdfReader(pdf_file)
            if pdf_reader.is_encrypted:
                pdf_reader.decrypt(get_parameter('/prism/pdf/password'))
        except:
            print(f"Error: Unable to read PDF or incorrect password for {url}")
            return None

        search_text = preprocess_text(search_text)
        
        with Pool() as pool:
            results = pool.map(process_page, [(i+1, preprocess_text(page.extract_text()), search_text) for i, page in enumerate(pdf_reader.pages)])
        
        best_match = max(results, key=lambda x: x[0])
        
        if best_match[0] >= threshold:
            return best_match[1]
        return None

def get_url_with_page(url, chunk):
    start_time = time.time()
    page_number = fast_find_text_in_pdf(url, chunk)
    time_elapsed = time.time() - start_time
    print_terminal(f"Time elapsed: {time_elapsed:.2f} seconds, Page: {page_number}", Fore.YELLOW)
    if page_number is not None:
        return f"{url}#page={page_number}"
    else:
        return url  # Return the original URL if text is not found