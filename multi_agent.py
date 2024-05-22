import os
import json
from typing import List, Dict
from openai import OpenAI

# Initialize OpenAI client with an API key
client = OpenAI(api_key="API_KEY")


def get_chat_completion(messages: List[Dict[str, str]], model: str = 'gpt-4o') -> str:
    """
    Generate a completion response from OpenAI's model.

    Args:
        messages (List[Dict[str, str]]): List of message dictionaries with role and content.
        model (str): The name of the model to use.

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


def refine_summary_with_feedback(text: str, model: str = 'gpt-4o') -> str:
    """
    Generate and refine a summary based on feedback from a secondary agent.

    Args:
        text (str): The content of the financial document.
        model (str): The model to use. Defaults to 'gpt-4o'.

    Returns:
        str: The refined summary of the document.
    """
    # Initial summarization by the financial expert
    first_agent_prompt = "Jesteś ekspertem finansowym. Podsumuj załączony dokument finansowy w zwięzłych punktach."
    messages = [{"role": "system", "content": first_agent_prompt}, {"role": "user", "content": text}]
    summary = get_chat_completion(messages, model=model)

    # Auditing and feedback by the meticulous auditor
    second_agent_prompt = "Jesteś skrupulatnym audytorem. Porównaj poniższy dokument finansowy z jego podsumowaniem. " \
                          "Zidentyfikuj wszelkie ważne brakujące informacje i zasugeruj ulepszenia."
    messages = [{"role": "system", "content": second_agent_prompt},
                {"role": "user", "content": f"Document:\n{text}\n\nSummary:\n{summary}"}]
    feedback = get_chat_completion(messages, model=model)

    # Refinement of the summary by the financial expert based on auditor feedback
    final_agent_prompt = "Jesteś ekspertem finansowym. Podsumuj poniższy dokument finansowy w zwięzłych punktach. Pamiętaj, aby uwzględnić wszelkie informacje zwrotne przekazane przez drugiego agenta i poprawić poprzednie podsumowanie."
    messages = [{"role": "system", "content": final_agent_prompt},
                {"role": "user", "content": f"Document:\n{text}\n\nFeedback:\n{feedback}\n\nSummary:\n{summary}"}]
    refined_summary = get_chat_completion(messages, model=model)

    return refined_summary


def summarize_and_refine_article(file_path: str, output_file_path: str, model: str = 'gpt-4-turbo') -> None:
    """
    Load an article from a file, summarize it, and refine it based on feedback.

    Args:
        file_path (str): Path to the input JSON file containing the article.
        output_file_path (str): Path to the output JSON file where the final summary will be saved.
        model (str): The model to use for the operations.

    Returns:
        None
    """
    data = load_json_file(file_path)
    content = data['content']
    final_summary = refine_summary_with_feedback(content, model=model)

    # Save the final summary to a JSON file
    with open(output_file_path, 'w', encoding='utf-8') as outfile:
        json.dump({"summary": final_summary}, outfile, indent=4)


# Example usage
summarize_and_refine_article("scraped_article_single.json", "multi_agent_summary.json")
