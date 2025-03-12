from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from requests_aws4auth import AWS4Auth
import boto3

"""
This script demonstrates indexing documents into an Amazon OpenSearch Service domain using AWS Identity and Access Management (IAM) for authentication.
"""
# Embedding Model
model = "titanv2"
# Use OpenSearch Servelss or Not
openserach_serverless = True
service = 'es'
# replace wit your OpenSearch Service domain/Serverless endpoint
domain_endpoint = "YOUR-DOMAIN-HERE"

credentials = boto3.Session().get_credentials()
awsauth = AWSV4SignerAuth(credentials, "us-west-2", service)
os_ = OpenSearch(
    hosts=[{'host': domain_endpoint, 'port': 443}],
    http_auth=awsauth,
    use_ssl=True,
    verify_certs=True,
    timeout=300,
    # http_compress = True, # enables gzip compression for request bodies
    connection_class=RequestsHttpConnection
)

# Sample Opensearch domain index mapping
mapping = {
    'settings': {
        'index': {
            'knn': True,
            "knn.algo_param.ef_search": 100,
        }
    },

    'mappings': {
        'properties': {
            'embedding': {
                'type': 'knn_vector',
                'dimension': 1024,  # change as per sequence length of Embedding Model
                "method": {
                    "name": "hnsw",
                    "space_type": "cosinesimil",
                    "engine": "nmslib",
                    "parameters": {
                        "ef_construction": 256,
                        "m": 48
                    }
                }
            },

            'passage': {
                'type': 'text'
            },

            'doc_id': {
                'type': 'keyword'
            },
            'page': {
                'type': 'long'
            },

            'table': {
                'type': 'text'
            },

            'list': {
                'type': 'text'
            },

            'title_headers': {
                'type': 'text'
            },
            'section_header_ids': {
                'type': 'text'
            },
            'section_title_ids': {
                'type': 'text'
            },

        }
    }
}

domain_index = f"prism-index"  # domain index name

if not os_.indices.exists(index=domain_index):
    print("Index not exists")
    os_.indices.create(index=domain_index, body=mapping)
    # Verify that the index has been created
    if os_.indices.exists(index=domain_index):
        print(f"Index {domain_index} created successfully.")
    else:
        print(f"Failed to create index '{domain_index}'.")
else:
    print(f'{domain_index} Index already exists!')
