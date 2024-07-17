import streamlit as st
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
from llm_interface import get_llm_response
from utils import print_terminal
from colorama import Fore
import random
import string
from pdf_utils import get_url_with_page
# from search_utils import _get_emb_, hybrid_search, normalize_scores_0
from search_utils import _get_emb_, hybrid_search
import time

def get_parameter(param_name):
    ssm = boto3.client('ssm', region_name='YOUR_AWS_REGION')
    response = ssm.get_parameter(Name=param_name, WithDecryption=True)
    return response['Parameter']['Value']

def initialize_opensearch():
    region = 'YOUR_AWS_REGION'
    service = 'es'
    domain = get_parameter('/prism/opensearch/domain')

    print_terminal("Initializing AWS credentials", Fore.YELLOW)
    credentials = boto3.Session().get_credentials()
    awsauth = AWS4Auth(credentials.access_key, credentials.secret_key,
                       region, service, session_token=credentials.token)
    print_terminal("AWS credentials initialized successfully", Fore.GREEN)

    print_terminal("Establishing connection to OpenSearch", Fore.YELLOW)
    client = OpenSearch(
        hosts = [{'host': domain, 'port': 443}],
        http_auth = awsauth,
        use_ssl = True,
        verify_certs = True,
        connection_class = RequestsHttpConnection
    )

    try:
        info = client.info()
        print_terminal(f"Successfully connected to OpenSearch. Cluster name: {info['cluster_name']}", Fore.GREEN)
        return client
    except Exception as e:
        print_terminal(f"Failed to connect to OpenSearch: {str(e)}", Fore.RED)
        return None

def setup_streamlit_ui():
    st.set_page_config(page_title="Prism-bot v0.1")
    st.title("Prism-bot v0.1")

    # Sidebar
    st.sidebar.title("Sample questions")
    st.sidebar.code("What should an employer do if a selected employee becomes unavailable for random DOT drug and alcohol testing within the selection period?", language="plaintext")
    st.sidebar.code("What are some important updates that should be made to maintain an accurate random program pool for DOT drug and alcohol testing?", language="plaintext")
    st.sidebar.code("What steps should an agency take if they participate in a Consortium or use a Third Party Administrator (TPA) for their DOT drug and alcohol testing program?", language="plaintext")

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def generate_unique_id(existing_ids):
    while True:
        new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        if new_id not in existing_ids:
            return new_id

def check_irrelevant_question(llm_response):
    if 'IQ' in llm_response:
        return True
    return False

def select_top_documents(hybrid_results, max_docs=10):
    documents = hybrid_results['hits']['hits']
    sorted_docs = sorted(documents, key=lambda x: x['_score'], reverse=True)
    
    if len(sorted_docs) <= max_docs:
        return sorted_docs
    
    selected_docs = sorted_docs[:max_docs]
    scores = [doc['_score'] for doc in selected_docs]
    
    # Find the largest score drop-off
    score_diffs = [scores[i] - scores[i+1] for i in range(len(scores)-1)]
    if score_diffs:
        max_drop_index = score_diffs.index(max(score_diffs))
        print_terminal(f"Dropping documents from index {max_drop_index+1}", Fore.CYAN)
        print_terminal(f"Picked docs and scores: {[(doc['_id'], doc['_score']) for doc in selected_docs]}", Fore.CYAN)
        print_terminal(f"Top 10 dropped docs and scores: {[(doc['_id'], doc['_score']) for doc in sorted_docs[max_drop_index+1:max_drop_index+11]]}", Fore.CYAN)
        return sorted_docs[:max_drop_index+1]
    else:
        return selected_docs

def process_user_input(client, prompt):
    print_terminal(f"Received user prompt: {prompt}", Fore.CYAN)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    print_terminal("Preparing OpenSearch query", Fore.YELLOW)
    
    embedding = _get_emb_(prompt)
    
    lexical_query = {
        "query": {
            "match": {
                "passage": prompt
            }
        },
        "size": 20,
        "_source": {"exclude": ["embedding"]}
    }
    
    semantic_query = {
        "query": {
            "knn": {
                "embedding": {
                    "vector": embedding,
                    "k": 20
                }
            }
        },
        "size": 20,
        "_source": {"exclude": ["embedding"]}
    }

    print_terminal("OpenSearch query prepared", Fore.GREEN)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                print_terminal("Executing OpenSearch queries", Fore.YELLOW)
                lexical_results = client.search(index="test2-titanv2-new", body=lexical_query)
                semantic_results = client.search(index="test2-titanv2-new", body=semantic_query)
                print_terminal("OpenSearch queries executed successfully", Fore.GREEN)

                hybrid_results = hybrid_search(20, lexical_results, semantic_results, interpolation_weight=0.5, normalizer="minmax", use_rrf=False)
                
                selected_docs = select_top_documents(hybrid_results)
                
                if selected_docs:
                    print_terminal(f"Found {len(selected_docs)} relevant documents", Fore.CYAN)
                    
                    id_url_doc_map = {}
                    context_chunks = []

                    for hit in selected_docs:
                        if 'passage' in hit['_source'] and 'url' in hit['_source'] and 'doc_id' in hit['_source']:
                            unique_id = generate_unique_id(id_url_doc_map.keys())
                            id_url_doc_map[unique_id] = {
                                'url': hit['_source']['url'],
                                'passage': hit['_source']['passage'],
                                'doc_id': hit['_source']['doc_id'],
                                'locked': False
                            }
                            context_chunks.append(f"uuid: {unique_id}, passage: {hit['_source']['passage']}")

                    context = "\n\n".join(context_chunks)

                    print_terminal("Preparing LLM request", Fore.YELLOW)
                    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
                    temperature = 0.7
                    
                    print_terminal("Sending request to LLM", Fore.YELLOW)
                    llm_response, token_count = get_llm_response(prompt, context, model_id, temperature)
                    print_terminal("Received response from LLM", Fore.GREEN)

                    # Replace UUIDs with URLs in the LLM response
                    for uuid, data in id_url_doc_map.items():
                        if 'unlocked_' in data['doc_id']:
                            data['locked'] = False 
                            data['doc_id'] = data['doc_id'].replace("unlocked_", "")
                        elif 'locked_' in data['doc_id']:
                            data['locked'] = True
                            data['doc_id'] = data['doc_id'].replace("locked_", "")
                        print_terminal("Old url: ", Fore.CYAN)
                        print_terminal(data['url'], Fore.CYAN)
                        # data['url'] = get_url_with_page(data['url'], data['passage'])
                        modified_url =  get_url_with_page(data['url'], data['passage'], timeout=2)
                        if modified_url is not None:
                            data['url'] = modified_url
                        print_terminal("New url: ", Fore.CYAN)
                        print_terminal(data['url'], Fore.CYAN)
                        llm_response = llm_response.replace(uuid, f"[{data['doc_id']}]({data['url']})")

                    if check_irrelevant_question(llm_response):
                        st.markdown("Sorry I can't answer that question. Please ask another question.")
                        print_terminal("Irrelevant question detected", Fore.YELLOW)
                    else:
                        st.markdown(llm_response)
                    st.markdown(f"Token count: <span style='color:blue'>{token_count}</span>", unsafe_allow_html=True)
                    print_terminal("Response from LLM: ", Fore.CYAN)
                    print_terminal(llm_response, Fore.CYAN)
                    print(f"Token count: {token_count}", Fore.CYAN)
                    st.session_state.messages.append({"role": "assistant", "content": llm_response})
                    print_terminal("Response displayed to user", Fore.GREEN)
                else:
                    print_terminal("No relevant documents found", Fore.YELLOW)
                    st.markdown("No relevant documents found.")
                    st.session_state.messages.append({"role": "assistant", "content": "No relevant documents found."})
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                print_terminal(f"Error: {error_message}", Fore.RED)
                st.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

def main():
    print_terminal("Starting Prism-bot v0.1", Fore.GREEN)

    client = initialize_opensearch()
    if not client:
        st.error("Failed to connect to OpenSearch. Please check your connection and try again.")
        return

    setup_streamlit_ui()

    prompt = st.chat_input("What is your question?")
    if prompt:
        query_start_time = time.time()
        process_user_input(client, prompt)
        query_end_time = time.time()
        print_terminal(f"Query processing time: {query_end_time - query_start_time:.2f} seconds", Fore.YELLOW)
    if st.sidebar.button("Clear Chat History"):
        print_terminal("Clearing chat history", Fore.CYAN)
        st.session_state.messages = []
        print_terminal("Chat history cleared", Fore.GREEN)
        st.rerun()

    print_terminal("Prism-bot v0.1 execution completed", Fore.GREEN)

if __name__ == "__main__":
    main()
