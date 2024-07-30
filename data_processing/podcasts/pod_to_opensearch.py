import json
import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth


def insert_into_opensearch():

    # OpenSearch connection details
    YOUR_OPENSEARCH_ENDPOINT = True
    service = 'es'
    region = 'YOUR_AWS_REGION'
    domain_endpoint = "YOUR_OPENSEARCH_ENDPOINT"

    # Get AWS credentials
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, region, service, session_token=credentials.token)

    # Initialize OpenSearch client
    client = OpenSearch(
        hosts=[{'host': domain_endpoint, 'port': 443}],
        http_auth=awsauth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection
    )

    # Index name
    index_name = 'test-index'  # Replace with your existing index name

    # Load JSON data
    with open('output.json', 'r') as file:
        data = json.load(file)

    # Prepare documents for bulk indexing
    bulk_data = []
    for item in data:
        doc = {
            "doc_id": f"transcript_{item.get('speaker', 'unknown')}_{item.get('start_time', '0')}",
            "passage": item['content'],
            "page": None,
            "embedding": None,  # You'll need to implement _get_emb_ function if you want to include embeddings
            "table": None,
            "list": None,
            "section_header_ids": None,
            "section_title_ids": None,
            "url": None,  # Add URL if available
            "start_time": item.get('start_time'),
            "end_time": item.get('end_time'),
            "speaker": item.get('speaker')
        }
        bulk_data.append({"index": {"_index": index_name}})
        bulk_data.append(doc)

    # Perform bulk insert
    response = client.bulk(body=bulk_data)

    # Check for errors
    if response['errors']:
        print("Some errors occurred during bulk insert:")
        for item in response['items']:
            if 'error' in item['index']:
                print(f"Error: {item['index']['error']}")
    else:
        print(f"Successfully inserted {len(data)} documents.")

    # Print some stats
    print(f"Took: {response['took']} ms")
    print(f"Items: {len(response['items'])}")


url = "https://inx-pro12-studio-s3-client-files-16a7cbab1103b783.s3.us-east-2.amazonaws.com/Attachment/84A28157-6FCD-4277-A2C2-9EF1B95C64DD.mp3?X-Amz-Algorithm=AWS4-HMAC-SHA256&X-Amz-Credential=AKIASWH7V5VPPET3UCFO%2F20240726%2Fus-east-2%2Fs3%2Faws4_request&X-Amz-Date=20240726T203438Z&X-Amz-Expires=604800&X-Amz-SignedHeaders=host&X-Amz-Signature=2c3d9aa9397e2abd53d0041ecd310e617224a4cb517c8267d9755cbdca588571"