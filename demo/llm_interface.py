import json
import os
import time

import boto3
from botocore.exceptions import ClientError
from langchain_aws import ChatBedrockConverse
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

from utils import print_terminal, count_tokens
from colorama import Fore

# Initialize the Bedrock client
bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="YOUR_AWS_REGION",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def create_langchain_messages(messages):
    """Convert the message format to LangChain message objects."""
    langchain_messages = []
    for msg in messages:
        if msg[0] == "system":
            langchain_messages.append(SystemMessage(content=msg[1]))
        elif msg[0] == "user":
            langchain_messages.append(HumanMessage(content=msg[1]))
        elif msg[0] == "assistant":
            langchain_messages.append(AIMessage(content=msg[1]))
    return langchain_messages

def generate_response(messages, model_id, temperature):
    """Generate a response using the Bedrock Converse API via LangChain."""
    try:
        llm = ChatBedrockConverse(
            model=model_id,
            temperature=temperature,
            max_tokens=1000,
            client=bedrock_runtime,
        )

        langchain_messages = create_langchain_messages(messages)
        
        response = llm.invoke(langchain_messages)
        
        token_count = count_tokens(str(langchain_messages) + response.content)
        
        return response.content, token_count
    
    except ClientError as e:
        print_terminal(f"An error occurred: {e}", Fore.RED)
        if "ThrottlingException" in str(e):
            print_terminal("Rate limit exceeded. Retrying in 60 seconds...", Fore.YELLOW)
            time.sleep(60)
            return generate_response(messages, model_id, temperature)
        return "I'm sorry, but I encountered an error while processing your request. Please try again.", 0

def classify_query(query):
    with open("classification_prompt.txt", "r") as file:
        classification_prompt = file.read()

    messages = [("user", classification_prompt.format(query=query))]
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    temperature = 0

    response, _ = generate_response(messages, model_id, temperature)

    classifications = re.findall(r'\b([A-Z]{2})\b', response)

    if len(classifications) == 1:
        return classifications[0]
    else:
        print_terminal("Error: Invalid classification response", Fore.RED)
        return None

def get_llm_response(user_query, context, model_id, temperature):
    with open("response_prompt.txt", "r") as file:
        response_prompt = file.read()

    llm_prompt = response_prompt.format(user_query=user_query, context=context)
    print_terminal("LLM prompt:", Fore.MAGENTA)
    print_terminal(llm_prompt, Fore.WHITE)

    messages = [("user", llm_prompt)]
    response, token_count = generate_response(messages, model_id, temperature)

    return response, token_count


def classify_response(prompt):
    """Invoke Claude 3 LLM and return the response."""
    try:
        bedrock_runtime = boto3.client(service_name='bedrock-runtime')

        model_id = "anthropic.claude-3-haiku-20240307-v1:0"

        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "system": "Determine if the provided answer properly answers the question. Respond only with YES or NO.",
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