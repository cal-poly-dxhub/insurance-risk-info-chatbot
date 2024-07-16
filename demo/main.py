import streamlit as st
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
from llm_interface import get_llm_response, classify_response
from utils import print_terminal
from colorama import Fore
from dotenv import load_dotenv
import os
import re
from citation_tools import *

load_dotenv()
DOMAIN = os.getenv("DOMAIN")
def initialize_opensearch():
    region = 'YOUR_AWS_REGION'
    service = 'es'
    domain = DOMAIN

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
    
def get_markdown_urls(hits):
    score = 0
    page_num = 0
    markdown_urls = []

    for hit in hits:
        url = hit['_source']['url']
        password = "YOUR_PASSWORD"
        passage = hit['_source']['passage']

        if "job-safety-analyses" not in url:
            # Download and unlock the PDF
            try:
                pdf_stream = download_pdf(url)
                unlocked_pdf_stream = unlock_pdf(pdf_stream, password)

                # Extract text and find the most similar page
                text_by_page = extract_text_from_pdf(unlocked_pdf_stream)
                page_num, score = find_most_similar_page(passage, text_by_page)

            except Exception as e:
                print(f"Error processing PDF: {e}")

            url = url + f"#page={page_num}"

            doc_title = remove_unlocked_prefix(hit['_source']['doc_id']) + f"-page-{page_num}"
            markdown_urls.append((f"- [{doc_title}]({url})", score))

        else:
            score = 100
            doc_title = remove_unlocked_prefix(hit['_source']['doc_id'])
            markdown_urls.append((f"- [{doc_title}]({url})", score))

    # Remove duplicates based on the first item in the URL tuples
    unique_markdown_urls = {}
    for url, score in markdown_urls:
        if url not in unique_markdown_urls or unique_markdown_urls[url] < score:
            unique_markdown_urls[url] = score

    # Sort the unique URLs by score
    unique_sorted_markdown_urls = sorted(unique_markdown_urls.items(), key=lambda x: x[1], reverse=True)

    # Convert the set to a single string with each URL on a new line
    urls = "\n##### Retrieved Documents\n" + "\n".join(url for url, score in unique_sorted_markdown_urls)
    
    return urls


def setup_streamlit_ui():
    st.title("Prism-bot v0.1")

    suggested_questions = [
        "What should an employer do if a selected employee becomes unavailable for random DOT drug and alcohol testing within the selection period?",
        "What are some important updates that should be made to maintain an accurate random program pool for DOT drug and alcohol testing?",
        "What is the required training for a bus driver?",
        "What PPE should a fire fighter have?",
        "What does an elementary teacher do?",
        "What are the risks of being a carpenter?",
        "How can I ensure the wellness of my employees?",
        "How should I prepare for public power shutoffs?",
        "What are signs of unusual mail handling?",
        "What color is the sky?",
    ]

    with st.sidebar:
        st.markdown("Sample Questions")
        for question in suggested_questions:
            if st.button(question):
                st.session_state['current_question'] = question
                st.session_state['submit'] = True

    if 'messages' not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def remove_unlocked_prefix(doc_id):
    """
    Remove the 'unlocked_' prefix from a document ID.
    """
    return re.sub(r'^unlocked_', '', doc_id)

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

                if response['hits']['total']['value'] > 0:
                    print_terminal(f"Found {response['hits']['total']['value']} relevant documents", Fore.CYAN)
                    hits = response['hits']['hits']
                    

                    # Prepare the context string
                    context = "\n\n".join(hit['_source']['passage'] for hit in hits if 'passage' in hit['_source'])

                    print_terminal("Preparing LLM request", Fore.YELLOW)
                    #model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
                    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
                    temperature = 0.7
                    print_terminal("Sending request to LLM", Fore.YELLOW)
                    llm_response, token_count = get_llm_response(prompt, context, model_id, temperature)
                    print_terminal("Received response from LLM", Fore.GREEN)

                    if classify_response(prompt + llm_response) == "YES":
                        st.markdown(llm_response)
                        st.markdown(f"Token count: <span style='color:blue'>{token_count}</span>", unsafe_allow_html=True)
                        urls = get_markdown_urls(hits)
                        st.markdown(urls)
                        st.session_state.messages.append({"role": "assistant", "content": llm_response + urls})
                    else:
                        st.markdown("Insufficient context.")
                        st.session_state.messages.append({"role": "assistant", "content": "Insufficient context."})

                    print_terminal("Response from LLM: ", Fore.CYAN)
                    print_terminal(llm_response, Fore.CYAN)
                    print(f"Token count: {token_count}", Fore.CYAN)
                    
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
    if 'current_question' not in st.session_state:
        st.session_state['current_question'] = ''


    print_terminal("Starting Prism-bot v0.1", Fore.GREEN)

    client = initialize_opensearch()
    if not client:
        st.error("Failed to connect to OpenSearch. Please check your connection and try again.")
        return

    setup_streamlit_ui()

    prompt = st.chat_input("What is your question?")
    if prompt:
        process_user_input(client, prompt)

    if st.session_state['current_question'] != '':
        process_user_input(client, st.session_state['current_question'])
        st.session_state['current_question'] = ''

    if st.sidebar.button("Clear Chat History"):
        print_terminal("Clearing chat history", Fore.CYAN)
        st.session_state.messages = []
        print_terminal("Chat history cleared", Fore.GREEN)
        st.rerun()

    print_terminal("Prism-bot v0.1 execution completed", Fore.GREEN)

if __name__ == "__main__":
    main()
