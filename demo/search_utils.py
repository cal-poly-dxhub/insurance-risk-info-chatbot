import boto3
from requests_aws4auth import AWS4Auth
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
import json
from langchain_community.embeddings import BedrockEmbeddings
import requests

def _get_emb_(passage):
    """
    This function takes a passage of text and a model name as input, and returns the corresponding text embedding.
    The function first checks the provided model name and then invokes the appropriate model or API to generate the text embedding.
    After invoking the appropriate model or API, the function extracts the text embedding from the response and returns it.
    """

    # create an Amazon Titan Text Embeddings client
    embeddings_client = BedrockEmbeddings(model_id="amazon.titan-embed-text-v2:0", region_name="YOUR_AWS_REGION")

    # Invoke the model
    embedding = embeddings_client.embed_query(passage)
    return (embedding)

import numpy as np

def query_opensearch(index, query, opensearch_url):
    """
    Query an OpenSearch index.
    :param index: The name of the index.
    :param query: The query to search.
    :param opensearch_url: The OpenSearch endpoint URL.
    :return: The search results.
    """
    url = f"{opensearch_url}/{index}/_search"
    headers = {'Content-Type': 'application/json'}
    response = requests.get(url, headers=headers, json=query)
    return response.json()

def normalize_scores_(scores,normalizer):
    """
    Normalize scores using L2/min-max normalization.
    :param scores: The list of scores to normalize.
    :param mormalizer: normalizing tekniq
    :return: The normalized scores.
    """
    if "minmax" in normalizer:
        scores = np.array(scores)
        return (scores - np.min(scores)) / (np.max(scores) - np.min(scores))
    elif "l2" in normalizer:
        scores = np.array(scores)
        return scores / np.linalg.norm(scores)
    else:
        raise "enter either minmax or l2 as normalizer"

def interpolate_scores(lexical_score, semantic_score, alpha=0.5):
    """
    Interpolate lexical and semantic scores using a weighted sum.
    :param lexical_score: The normalized score from the lexical search.
    :param semantic_score: The normalized score from the semantic search.
    :param alpha: The interpolation weight (default: 0.5).
    :return: The interpolated score.
    """
    return alpha * lexical_score + (1 - alpha) * semantic_score

def reciprocal_rank_fusion(lexical_results, semantic_results, k=60):
    """
    Combine lexical and semantic search results using Reciprocal Rank Fusion (RRF).
    :param lexical_results: The results from the lexical search.
    :param semantic_results: The results from the semantic search.
    :param k: The parameter for RRF (default: 60).
    :return: The combined search results.
    """
    combined_results = {}

    for hit in lexical_results['hits']['hits']:
        doc_id = hit['_id']
        if doc_id not in combined_results:
            combined_results[doc_id] = {'_id': doc_id, '_source': hit['_source'], '_score': 0}
        combined_results[doc_id]['_score'] += 1 / (k + hit['_score'])

    for hit in semantic_results['hits']['hits']:
        doc_id = hit['_id']
        if doc_id not in combined_results:
            combined_results[doc_id] = {'_id': doc_id, '_source': hit['_source'], '_score': 0}
        combined_results[doc_id]['_score'] += 1 / (k + hit['_score'])

    combined_results = list(combined_results.values())
    combined_results = sorted(combined_results, key=lambda x: x['_score'], reverse=True)

    return {'hits': {'hits': combined_results}}

def hybrid_search(top_K_results,lexical_results, semantic_results, interpolation_weight=0.5, normalizer="minmax",use_rrf=False, rrf_k=60):
    """
    Perform hybrid search by combining lexical and semantic search results.
    :param lexical_results: The results from the lexical search.
    :param semantic_results: The results from the semantic search.
    :param interpolation_weight: The interpolation weight for score interpolation.
    :param normalizer: The normalization function (default: minmax normalization).
    :return: The combined search results.
    """

    if use_rrf:
        return reciprocal_rank_fusion(lexical_results, semantic_results, k=rrf_k)

    combined_results = []

    # Normalize the scores from lexical and semantic searches
    lexical_scores = [hit['_score'] for hit in lexical_results['hits']['hits']]
    semantic_scores = [hit['_score'] for hit in semantic_results['hits']['hits']]
    normalized_lexical_scores = normalize_scores_(lexical_scores,normalizer)
    normalized_semantic_scores = normalize_scores_(semantic_scores,normalizer)

    # Combine the results based on document IDs
    lexical_docs = {hit['_id']: (hit, score) for hit, score in zip(lexical_results['hits']['hits'], normalized_lexical_scores)}
    semantic_docs = {hit['_id']: (hit, score) for hit, score in zip(semantic_results['hits']['hits'], normalized_semantic_scores)}

    for doc_id in set(lexical_docs.keys()) | set(semantic_docs.keys()):
        lexical_hit, lexical_score = lexical_docs.get(doc_id, (None, 0))
        semantic_hit, semantic_score = semantic_docs.get(doc_id, (None, 0))

        if lexical_hit and semantic_hit:
            # Interpolate scores if both lexical and semantic results are available
            interpolated_score = interpolate_scores(lexical_score, semantic_score, interpolation_weight)
            combined_hit = {
                '_id': doc_id,
                '_source': {**lexical_hit['_source']},
                '_score': interpolated_score,
            }
        elif lexical_hit:
            # Use lexical hit if only lexical result is available
            combined_hit = {
                '_id': doc_id,
                '_source': lexical_hit['_source'],
                '_score': lexical_score
            }
        else:
            # Use semantic hit if only semantic result is available
            combined_hit = {
                '_id': doc_id,
                '_source': semantic_hit['_source'],
                '_score': semantic_score
            }
        combined_results.append(combined_hit)
    # Sort the combined results by the blended score
    combined_results = sorted(combined_results, key=lambda hit: hit['_score'], reverse=True)
    return {'hits': {'hits': combined_results[:top_K_results]}}