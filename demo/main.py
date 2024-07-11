import streamlit as st
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth
import boto3
from llm_interface import get_llm_response

region = 'YOUR_AWS_REGION'
service = 'es'
domain = 'search-prism2-6tfd5m2fn72rpegmkn2xmlaqa4.YOUR_AWS_REGION.es.amazonaws.com'

credentials = boto3.Session().get_credentials()
awsauth = AWS4Auth(credentials.access_key, credentials.secret_key, 
                   region, service, session_token=credentials.token)

client = OpenSearch(
    hosts = [{'host': domain, 'port': 443}],
    http_auth = awsauth,
    use_ssl = True,
    verify_certs = True,
    connection_class = RequestsHttpConnection
)

st.title("Prism-bot v0.1")

# Sidebar
st.sidebar.title("Sample questions")
st.sidebar.code("Should I require wet signatures on endorsements to policies? ", language="plaintext")
st.sidebar.code("The contractor states that they are a sole proprietor and does not carry workers' compensation insurance as they have no employees, is this acceptable? ", language="plaintext")
st.sidebar.code("The ISO released an update to the CGL form in April of 2013, CG 00 01 and a number of Additional Insured endorsements. What are the important changes and what impact do they have? ", language="plaintext")

if 'messages' not in st.session_state:
    st.session_state.messages = []

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

if prompt := st.chat_input("What is your question?"):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # OpenSearch query
    query = {
        "query": {
            "match": {
                "passage": prompt
            }
        },
        "size": 3 
    }
    
    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                response = client.search(index="test2-titanv2-new", body=query)
                
                if response['hits']['total']['value'] > 0:
                    context = ""
                    for hit in response['hits']['hits']:
                        if 'passage' in hit['_source']:
                            context += hit['_source']['passage'] + "\n\n"
                    
                    model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
                    temperature = 0.7
                    llm_response, _ = get_llm_response(prompt, context, model_id, temperature)
                    
                    st.markdown(llm_response)
                    st.session_state.messages.append({"role": "assistant", "content": llm_response})
                else:
                    st.markdown("No relevant documents found.")
                    st.session_state.messages.append({"role": "assistant", "content": "No relevant documents found."})
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
                st.markdown(error_message)
                st.session_state.messages.append({"role": "assistant", "content": error_message})

if st.sidebar.button("Clear Chat History"):
    st.session_state.messages = []
    st.rerun()