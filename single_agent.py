import os
import json
from typing import Optional, List, Dict
from openai import OpenAI

# Initialize OpenAI client with an API key
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])


def get_chat_completion(messages: List[Dict[str, str]], model: str = 'gpt-4-turbo') -> str:
    """
    Generate a completion response from OpenAI's GPT-4-turbo model.

    Args:
        messages (List[Dict[str, str]]): List of message dictionaries with role and content.
        model (str): The name of the model to use. Defaults to 'gpt-4-turbo'.

    Returns:
        str: The content of the first choice's response.
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=0,
    )
    return response.choices[0].message.content


def load_json_file(file_path: str) -> Dict:
    """
    Load JSON data from a file.

    Args:
        file_path (str): Path to the JSON file.

    Returns:
        Dict: The data parsed from the JSON file.
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    return data


def summarize_article(text: str,
                      model: str = 'gpt-4-turbo',
                      additional_instructions: Optional[str] = None) -> str:
    """
    Summarize a financial article using GPT-4-turbo.

    Args:
        text (str): The content of the article to summarize.
        model (str): The model to use for summarization. Defaults to 'gpt-4-turbo'.
        additional_instructions (Optional[str]): Additional instructions for the summarization task.

    Returns:
        str: The generated summary of the article.
    """
    # Set the system message to instruct the model
    system_message_content = "Jesteś ekspertem finansowym. Podsumuj załączony dokument finansowy w zwięzłych punktach."
    if additional_instructions is not None:
        system_message_content += f"\n\n{additional_instructions}"

    messages = [
        {"role": "system", "content": system_message_content},
        {"role": "user", "content": text}
    ]

    # Fetch the summary from the OpenAI chat completion function
    response = get_chat_completion(messages, model=model)
    return response


def summarize_articles_from_file(input_file_path: str, output_file_path: str) -> None:
    """
    Summarize financial articles from a JSON file and save results.

    Args:
        input_file_path (str): Path to the input JSON file containing article(s).
        output_file_path (str): Path to the output JSON file where summaries will be saved.

    Returns:
        None
    """
    # Load the JSON data from the file
    data = load_json_file(input_file_path)

    # Initialize results list for storing summaries
    results = []

    # Determine the structure of data (dict or list) and summarize accordingly
    if isinstance(data, dict):
        # Single article
        url = data['url']
        content = data['content']
        summary = summarize_article(content)
        results.append({"url": url, "summary": summary})
    elif isinstance(data, list):
        # Multiple articles
        for article in data:
            url = article['url']
            content = article['content']
            summary = summarize_article(content)
            results.append({"url": url, "summary": summary})
    else:
        raise ValueError("Unsupported JSON format. Expected list or dict.")

    # Write the summaries to the output file
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        json.dump(results, outfile, indent=4)

# Example usage
summarize_articles_from_file("scraped_article_single.json", "summary.json")
