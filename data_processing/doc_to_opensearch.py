import requests
import fitz  # PyMuPDF
from urllib.parse import urlparse
import json
import os
import pandas as pd
import magic  # for file type detection
import msoffcrypto
import io
import openpyxl
import csv
import re
import boto3
from document_processor import process_document, process_xlsx

BUCKET_NAME = "YOURBUCKET"

def get_last_part_of_url(url):
    url = url.rstrip('/')
    parsed_url = urlparse(url)
    path_segments = parsed_url.path.split('/')
    return path_segments[-1] if path_segments[-1] else 'downloaded_file'


def extract_extension(content_disposition):
    match = re.search(r'filename="(.+)"', content_disposition)
    if match:
        filename = match.group(1)
        return os.path.splitext(filename)[1]
    return None

def download_file(url, file_path):
    response = requests.get(url)
    content_disposition = response.headers.get('Content-Disposition')
    
    if content_disposition:
        extension = extract_extension(content_disposition)
        #print(f"Extracted file extension: {extension}")
    else:
        extension = None
        print("No content disposition header found.")
    
    with open(file_path, 'wb') as file:
        file.write(response.content)
    
    return extension

def detect_file_type(file_path):
    mime = magic.Magic(mime=True)
    file_type = mime.from_file(file_path)
    return file_type

def extract_job_title(text):
    try:
        # Use regular expression to find the job title after "Job: ---" and before "---"
        match = re.search(r'Job: ---(.*?)---', text)
        if match:
            job_title = match.group(1).strip()
            return job_title
        else:
            return None
    except Exception as e:
        print(f"An error occurred while extracting the job title: {e}")
        return None

# def unlock_and_get_excel_as_csv_string(file_path, password):
#     try:
#         # Open the encrypted file
#         with open(file_path, 'rb') as file:
#             office_file = msoffcrypto.OfficeFile(file)

#             # Decrypt the file
#             office_file.load_key(password=password)
#             decrypted_file = io.BytesIO()
#             office_file.decrypt(decrypted_file)

#         # Read the decrypted Excel file
#         df = pd.read_excel(decrypted_file)

#         df = df.astype(str)

#         df.fillna(" ", inplace=True)

#         df.columns = ["" if "Unnamed" in col else col for col in df.columns]

#         # Save DataFrame to CSV file
#         df.to_csv("file", sep=',', index=False)

#         # Convert DataFrame to CSV string
#         csv_string = df.to_csv(sep='-', index=False)

#         return csv_string
#     except Exception as e:
#         print(f"An error occurred while processing Excel: {e}")
#         return None

def unlock_and_get_excel_as_csv_string(file_path, password):
    try:
        # Open the encrypted file
        with open(file_path, 'rb') as file:
            office_file = msoffcrypto.OfficeFile(file)

            # Decrypt the file
            office_file.load_key(password=password)
            decrypted_file = io.BytesIO()
            office_file.decrypt(decrypted_file)

        # Read the decrypted Excel file
        df = pd.read_excel(decrypted_file)

        df = df.astype(str)

        df.fillna(" ", inplace=True)

        df.columns = ["" if "Unnamed" in col else col for col in df.columns]

        text_data = df.to_csv(sep='-', index=False)

        return text_data
    except Exception as e:
        print(f"An error occurred while processing Excel: {e}")
        return None
    
def format_xlsx(prompt):
    """Invoke Claude 3.5 (messages API) via Bedrock and return the response."""
    try:
        model_id = "anthropic.claude-3-5"  # or your current Claude model ARN/version
        bedrock_runtime = boto3.client(service_name='bedrock-runtime')
        
        # Build the request using the new messages format
        body = {
            "messages": [
                {
                    "role": "system",
                    "content": "Format this data into a human readable format. Make sure all data is included."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "max_tokens_to_sample": 2000,
            "temperature": .5,
            "top_p": 0.999,
            "top_k": 250
        }

        # Invoke the model
        response = bedrock_runtime.invoke_model(
            body=json.dumps(body),
            modelId=model_id,
            contentType="application/json"
        )

        # Parse the response
        response_body = json.loads(response.get('body').read())
        return response_body["modelOutputs"][0]["completion"]

    except Exception as e:
        print(f"Claude Error: {e}")
        return None
    
def unlock_and_save_pdf(file_path, password):
    print("Unlocking ", file_path)
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                raise Exception("Failed to authenticate the document with the provided password.")

        unlocked_file_path = f"data/unlocked_{os.path.basename(file_path)}"
        doc.save(unlocked_file_path)
        doc.close()
        print("Unlocked ", unlocked_file_path)
        
        return unlocked_file_path
    except Exception as e:
        print(f"An error occurred while processing PDF: {e}")
        return None


# Main execution
# Read URLs from file
with open("urls.txt", "r") as file:
    urls = file.readlines()

# Create pdfs folder if it doesn't exist
pdf_folder = "pdfs"
os.makedirs(pdf_folder, exist_ok=True)

for url in urls:
    url = url.strip()
    file_name = get_last_part_of_url(url)
    file_path = f"{file_name}"
    password = 'PASSWORD'

    # Download the file
    file_type = download_file(url, file_path)

    print(f"Detected file type: {file_type}")

    # if file_type == 'application/encrypted':
    #     # Try to process as PDF
    #     pdf_path = os.path.join(pdf_folder, file_name)
    #     print(pdf_path)
    #     os.rename(temp_file_path, pdf_path)

    if 'pdf' in file_type.lower():
        pdf_path = file_path + ".pdf"

        pdf_path = unlock_and_save_pdf(file_path, password)

        print("Processing ", pdf_path) 
        process_document(BUCKET_NAME, pdf_path, url)
        print(f"Successfully processed PDF {file_name}")

    elif 'xlsx' in file_type.lower() or 'spreadsheet' in file_type.lower():
        csv_path = file_path + ".pdf"
        print("Processing ", file_path)
        csv_text = unlock_and_get_excel_as_csv_string(file_path, password)
        job = extract_job_title(csv_text)
        csv_text = format_xlsx(csv_text)

        

        
        print(job)
        #print(job)

        questions = (
            f"Sample Questions a user would ask about a {job} job."
            f"What is the required equipment for a {job}?\n"
            f"What is the PPE required for a {job}?\n"
            f"What is the optional PPE required for a {job}?\n"
            f"What is the required training for a {job}?\n"
            f"What are the procedures for a {job}?\n"
            f"What are the potential hazards for a {job}?\n"
            f"What are the protective measures for a {job}?\n"
            f"How does a {job} minimize risk of injury?\n"
            f"What is the risk/hazard rating for a {job}?\n"
            f"What are the JSA Steps for a {job}?\n"
            f"How could a {job} get hurt?\n"
            f"What are the duties of a {job}?"
            "Actual Job Information"
        )

        job_with_questions = questions + csv_text

        #print(job_with_questions)

        process_xlsx(BUCKET_NAME, file_name, job_with_questions, url)

        print(f"Excel file processed successfully: {file_name}")

    else:
        print(f"Unsupported file type: {file_type}")
