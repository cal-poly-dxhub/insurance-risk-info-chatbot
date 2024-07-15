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

    # Test OpenSearch connection
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

def process_user_input(client, prompt):
    print_terminal(f"Received user prompt: {prompt}", Fore.CYAN)
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    print_terminal("Preparing OpenSearch query", Fore.YELLOW)
    query = {
        "query": {
            "match": {
                "passage": prompt
            }
        },
        "size": 3
    }
    print_terminal("OpenSearch query prepared", Fore.GREEN)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                print_terminal("Executing OpenSearch query", Fore.YELLOW)
                response = client.search(index="test2-titanv2-new", body=query)
                print_terminal("OpenSearch query executed successfully", Fore.GREEN)
                print_terminal("Response from OpenSearch: ", Fore.CYAN)
                print_terminal(str(response), Fore.CYAN)

                if response['hits']['total']['value'] > 0:
                    print_terminal(f"Found {response['hits']['total']['value']} relevant documents", Fore.CYAN)
                    
                    id_url_doc_map = {}
                    context_chunks = []

                    for hit in response['hits']['hits']:
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
                        data['url'] = get_url_with_page(data['url'], data['passage'])
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
        process_user_input(client, prompt)

    if st.sidebar.button("Clear Chat History"):
        print_terminal("Clearing chat history", Fore.CYAN)
        st.session_state.messages = []
        print_terminal("Chat history cleared", Fore.GREEN)
        st.rerun()

    print_terminal("Prism-bot v0.1 execution completed", Fore.GREEN)

if __name__ == "__main__":
    main()
