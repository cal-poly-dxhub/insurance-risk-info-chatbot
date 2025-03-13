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

BUCKET_NAME = "BUCKETNAME"
UNLOCKED_PDFS_FOLDER = "unlocked_pdfs"

s3_client = boto3.client('s3')

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
        match = re.search(r'Job: ---(.*?)---', text)
        if match:
            job_title = match.group(1).strip()
            return job_title
        else:
            return None
    except Exception as e:
        print(f"An error occurred while extracting the job title: {e}")
        return None

def unlock_and_get_excel_as_csv_string(file_path, password):
    try:
        with open(file_path, 'rb') as file:
            office_file = msoffcrypto.OfficeFile(file)
            office_file.load_key(password=password)
            decrypted_file = io.BytesIO()
            office_file.decrypt(decrypted_file)

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
    try:
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        bedrock_runtime = boto3.client(service_name='bedrock-runtime')

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": "Format this data into a  human readable format. Make sure all data is included.",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1,
            "top_p": 0.999,
            "top_k": 250,
        })

        response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        
        return response_body["content"][0]["text"]
    except Exception as e:
        print(f"Claude Error: {e}")
        return None

def unlock_and_save_pdf(file_path, password):
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                raise Exception("Failed to authenticate the document with the provided password.")

        unlocked_file_path = f"data/unlocked_{os.path.basename(file_path)}"
        doc.save(unlocked_file_path)
        doc.close()
        
        return unlocked_file_path
    except Exception as e:
        print(f"An error occurred while processing PDF: {e}")
        return None

def upload_to_s3(file_path, bucket_name, object_name=None):
    try:
        if object_name is None:
            object_name = os.path.basename(file_path)
        s3_key = os.path.join(UNLOCKED_PDFS_FOLDER, object_name)
        s3_client.upload_file(file_path, bucket_name, s3_key)
        print(f"File uploaded to S3: {s3_key}")
    except Exception as e:
        print(f"An error occurred while uploading to S3: {e}")

# Main executionimport requests
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

s3_client = boto3.client('s3')

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
        match = re.search(r'Job: ---(.*?)---', text)
        if match:
            job_title = match.group(1).strip()
            return job_title
        else:
            return None
    except Exception as e:
        print(f"An error occurred while extracting the job title: {e}")
        return None

def unlock_and_get_excel_as_csv_string(file_path, password):
    try:
        with open(file_path, 'rb') as file:
            office_file = msoffcrypto.OfficeFile(file)
            office_file.load_key(password=password)
            decrypted_file = io.BytesIO()
            office_file.decrypt(decrypted_file)

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
    try:
        model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        bedrock_runtime = boto3.client(service_name='bedrock-runtime')

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": "Format this data into a  human readable format. Make sure all data is included.",
            "max_tokens": 2000,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 1,
            "top_p": 0.999,
            "top_k": 250,
        })

        response = bedrock_runtime.invoke_model(body=body, modelId=model_id)
        response_body = json.loads(response.get('body').read())
        
        return response_body["content"][0]["text"]
    except Exception as e:
        print(f"Claude Error: {e}")
        return None

def unlock_and_save_pdf(file_path, password):
    try:
        doc = fitz.open(file_path)
        if doc.is_encrypted:
            if not doc.authenticate(password):
                raise Exception("Failed to authenticate the document with the provided password.")

        unlocked_file_path = f"unlocked_{os.path.basename(file_path)}"
        doc.save(unlocked_file_path)
        doc.close()
        
        return unlocked_file_path
    except Exception as e:
        print(f"An error occurred while processing PDF: {e}")
        return None

def upload_to_s3(file_path, bucket_name, object_name=None):
    try:
        if object_name is None:
            object_name = os.path.basename(file_path)
        s3_key = os.path.join(UNLOCKED_PDFS_FOLDER, object_name)
        s3_client.upload_file(file_path, bucket_name, s3_key)
        print(f"File uploaded to S3: {s3_key}")
    except Exception as e:
        print(f"An error occurred while uploading to S3: {e}")

def delete_temp_file(file_path):
    try:
        os.remove(file_path)
        print(f"Deleted temporary file: {file_path}")
    except Exception as e:
        print(f"Error deleting file {file_path}: {e}")

def rename_to_pdf(file_path):
    """
    Renames the given file by appending '.pdf' to the filename and returns the new file path.
    """
    # Extract the directory and file name from the original file path
    directory, original_file_name = os.path.split(file_path)
    
    # Create the new file name with '.pppdf' appended
    new_file_name = original_file_name + ".pdf"
    
    # Create the new file path
    new_file_path = os.path.join(directory, new_file_name)
    
    # Rename the original file to the new file name
    os.rename(file_path, new_file_path)
    
    return new_file_path

PASSWORD = "PASSWORD""

with open("urls.txt", "r") as file:
    urls = file.readlines()

for url in urls:
    url = url.strip()
    file_name = get_last_part_of_url(url)
    file_path = f"{file_name}"
    password = 'PRISMresource'

    # Download the file
    file_type = download_file(url, file_path)

    if 'pdf' in file_type.lower():
        pdf_path = file_path + ".pdf"

        pdf_path = rename_to_pdf(unlock_and_save_pdf(file_path, password))



        upload_to_s3(pdf_path, BUCKET_NAME)

        # Delete the temporary file
        delete_temp_file(pdf_path)

        print(f"Successfully processed PDF {file_name}")

    elif 'xlsx' in file_type.lower() or 'spreadsheet' in file_type.lower():
        xlsx_path = file_path + ".xlsx"

        csv_text = unlock_and_get_excel_as_csv_string(file_path, PASSWORD)
        
        if csv_text:
            # Convert the CSV text to a DataFrame
            df = pd.read_csv(io.StringIO(csv_text), sep='-')
            
            # Save the DataFrame as an Excel file
            df.to_excel(xlsx_path, index=False)
            
            # Upload the file to S3
            upload_to_s3(xlsx_path, BUCKET_NAME)
            
            # Delete the temporary file
            delete_temp_file(xlsx_path)
            
            print(f"Excel file processed and uploaded successfully: {file_name}")

    else:
        print(f"Unsupported file type: {file_type}")
