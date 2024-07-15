import json
import re
import boto3
import os
from botocore.exceptions import ClientError
from utils import print_terminal, count_tokens
from colorama import Fore
import streamlit as st
import time

bedrock_runtime = boto3.client(
    service_name="bedrock-runtime",
    region_name="YOUR_AWS_REGION",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
)

def generate_response(messages, model_id, temperature):
    model_kwargs = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "temperature": temperature,
        "top_k": 100,
        "top_p": 0.999,
    }

    formatted_messages = []
    for msg in messages:
        role = "user" if msg[0] == "user" else "assistant"
        formatted_messages.append({"role": role, "content": msg[1]})

    body = json.dumps({
        "messages": formatted_messages,
        **model_kwargs
    })

    try:
        response = bedrock_runtime.invoke_model(
            modelId=model_id,
            body=body
        )
        response_body = json.loads(response.get('body').read())
        return response_body['content'][0]['text']
    except bedrock_runtime.exceptions.ThrottlingException as e:
        print_terminal(f"An error occurred: {e}", Fore.RED)
        time.sleep(60)
        return generate_response(messages, model_id, temperature)
    except ClientError as e:
        print_terminal(f"An error occurred: {e}", Fore.RED)
        return "I'm sorry, but I encountered an error while processing your request. Please try again."

def classify_query(query):
    with open("classification_prompt.txt", "r") as file:
        classification_prompt = file.read()

    messages = [("user", classification_prompt.format(query=query))]
    # model_id = "anthropic.claude-3-5-sonnet-20240620-v1:0"
    model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
    temperature = 0

    response = generate_response(messages, model_id, temperature)

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
    response = generate_response(messages, model_id, temperature)

    return response, count_tokens(llm_prompt)

def get_llm_context_check(user_query, context, model_id, temperature=1):
    # Define the prompt to instruct the LLM to determine if there is enough context
    context_check_prompt = """
    Your task is to determine if a returned answer sufficiently answers for a question
    """

    # Format the prompt with the user query and context
    llm_prompt = context_check_prompt.format(user_query=user_query, context=context)
    print_terminal("LLM context check prompt:", Fore.MAGENTA)
    print_terminal(llm_prompt, Fore.WHITE)

    # Prepare the messages for the LLM
    messages = [("user", llm_prompt)]
    # Generate the response using the LLM
    response = generate_response(messages, model_id, temperature)

    return response, count_tokens(llm_prompt)

# def summarize(input_text):
#     with open("summarize_prompt.txt", "r") as file:
#         response_prompt = file.read()

#     llm_prompt = response_prompt.format(input_text=input_text)
#     print_terminal("Summarizing prompt:", Fore.MAGENTA)
#     print_terminal(llm_prompt, Fore.WHITE)

#     messages = [("user", llm_prompt)]
#     model_id = "anthropic.claude-3-haiku-20240307-v1:0"
#     temperature = 0
#     response = generate_response(messages, model_id, temperature)

#     print_terminal("Summarized response:", Fore.MAGENTA)
#     print_terminal(response, Fore.WHITE)

#     return response
