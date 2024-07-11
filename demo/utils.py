from colorama import init, Fore
import tiktoken
import json
import logging
init(autoreset=True)

# logging.basicConfig(filename='/home/ec2-user/streamlit_app.log', level=logging.INFO, format='%(asctime)s - %(message)s')

def print_terminal(message, color=Fore.WHITE, APP_ENV="prod"):
    print(color + message)
    # colored_message = f"{color}{message}{Fore.RESET}"
    # print(colored_message)  # This will print to the console
    # logging.info(message)   # This will log to the file without color codes

def is_context_sufficient(llm_response):
    return "INSUFFICIENT CONTEXT" not in llm_response

def fill_query_parameters(query, parameters):
    filled_query = query
    for key, value in parameters.items():
        if isinstance(value, list):
            value_str = '[' + ', '.join(map(str, value[:5])) + f', ... {len(value)} more elements]'
        else:
            value_str = json.dumps(value)
        filled_query = filled_query.replace(f'${key}', value_str)
    return filled_query

def count_tokens(text):
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))
