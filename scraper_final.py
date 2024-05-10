import requests
from bs4 import BeautifulSoup
import pandas as pd
from urllib.parse import urljoin
import zipfile
from io import BytesIO
import pdfplumber
from lxml import etree
import json


def scrape_articles(date):
    """
    Scrape article titles and URLs from the main page for a specific date.

    Args:
        date (str): Date to filter articles by (formatted as DD-MM-YYYY).

    Returns:
        pd.DataFrame: A DataFrame containing titles and URLs for each article.
    """
    # Base URL with a dynamic date parameter
    base_url = f"https://www.gpw.pl/komunikaty?categoryRaports=EBI,ESPI&typeRaports=RB,P,Q,O,R&searchText=&date={date}"

    # Fetch the webpage content
    response = requests.get(base_url)
    response.raise_for_status()  # Ensure the request is successful

    # Parse the webpage content with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Find article links using a CSS selector
    articles = soup.select("#search-result > li > strong > a")

    # Compile a list of titles and their corresponding URLs
    results = [{'Title': article.text.strip(), 'URL': urljoin(base_url, article.get('href'))} for article in articles]

    # Return the data as a DataFrame
    return pd.DataFrame(results)


def get_text_from_pdf(buffer):
    """
    Extract text from a PDF file provided as an in-memory buffer using `pdfplumber`.

    Args:
        buffer (BytesIO): An in-memory binary buffer containing the PDF content.

    Returns:
        str: Extracted text from the PDF.
    """
    pdf_text = ""
    with pdfplumber.open(buffer) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                pdf_text += page_text
    return pdf_text

def get_text_from_xhtml(content):
    """
    Extract text from an XHTML content string.

    Args:
        content (bytes): The raw HTML content of the XHTML file.

    Returns:
        str: Extracted text from the XHTML.
    """
    tree = etree.HTML(content)
    return ''.join(tree.xpath("//text()"))


def get_text_from_zip(content):
    """
    Extract text from a ZIP file containing different file types.

    Args:
        content (bytes): Binary content of the ZIP file.

    Returns:
        str: Concatenated text extracted from all valid files inside the ZIP.
    """
    text = ''
    # Open the ZIP file from binary content
    with zipfile.ZipFile(BytesIO(content)) as zfile:
        # Loop through each file in the ZIP archive
        for file_name in zfile.namelist():
            with zfile.open(file_name) as file:
                if file_name.endswith('.txt'):
                    # Extract text from plain text files
                    text += file.read().decode('utf-8')
                elif file_name.endswith('.pdf'):
                    # Extract text from PDF files
                    text += get_text_from_pdf(file)
                elif file_name.endswith('.xhtml'):
                    # Extract text from XHTML files
                    text += get_text_from_xhtml(file.read())
    return text


def get_text_from_attachment(url):
    """
    Fetch and extract text from a given attachment URL, handling different file types.

    Args:
        url (str): The URL of the attachment to download and extract.

    Returns:
        str: Extracted text content from the attachment.
    """
    # Download the attachment content
    response = requests.get(url)
    response.raise_for_status()

    # Extract the file extension before the comma
    filename = url.split('/')[-1]  # Get the last part of the URL
    attachment_type = filename.split(',')[0].split('.')[-1]

    # Process the file content based on the file type
    if attachment_type == "pdf":
        with BytesIO(response.content) as buffer:
            text = get_text_from_pdf(buffer)
    elif attachment_type == "xhtml":
        text = get_text_from_xhtml(response.content)
    elif attachment_type == "zip":
        text = get_text_from_zip(response.content)
    else:
        # Ignore unrecognized file types
        text = ''

    return text


def scrape_text_from_url(url):
    """
    Scrape the main text and all relevant attachments from a specified article URL.
    Ensures attachment links are correctly formatted and attachment types are derived accurately.

    Args:
        url (str): The URL of the article to scrape.

    Returns:
        str: Combined text from the main content and relevant attachments.
    """
    # Base URL prefix for attachment links starting with "attachment"
    base_attachment_url = "https://infostrefa.com/espi/pl/reports/view/"

    # Download the main article page content
    response = requests.get(url)
    response.raise_for_status()

    # Parse the page with BeautifulSoup
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract main text from the primary content container
    main_text_container = soup.select_one(
        "body > section.mainContainer.padding-top-0.padding-bottom-20 > div.container > div > div > div > div")
    main_text = main_text_container.get_text(strip=True) if main_text_container else ''

    # Locate all tables and target the second one containing links
    tables = soup.select(
        "body > section.mainContainer.padding-top-0.padding-bottom-20 > div.container > div > div > div > div > table")

    # Find the second table that has any <a> tags with href attributes
    found_tables = [table for table in tables if table.find('a', href=True)]

    attachment_texts = ''
    if len(found_tables) >= 2:
        # Select the second table that meets the criteria
        correct_table = found_tables[1]
        attachment_links = correct_table.select("tr > td > li > a")

        for attachment_link in attachment_links:
            # Check if the href starts with "attachment" and needs the base URL
            href = attachment_link.get('href')
            if href.startswith("attachment"):
                attachment_url = base_attachment_url + href
            else:
                attachment_url = urljoin(url, href)

            # Extract only the file extension from the filename before any comma
            filename = href.split('/')[-1]
            attachment_type = filename.split(',')[0].split('.')[-1]

            # Ignore ".xades" files, process others
            if attachment_type not in {"xades"}:
                attachment_texts += get_text_from_attachment(attachment_url)

    # Return the combined text from the main article and attachments
    return main_text + attachment_texts


def scrape_text_from_urls(df):
    """
    Scrape text data from a list of article URLs provided in a DataFrame.

    Args:
        df (pd.DataFrame): DataFrame containing a 'URL' column with the list of article URLs.

    Returns:
        dict: Dictionary mapping each article URL to its combined text content.
    """
    results = {}
    for url in df['URL']:
        results[url] = scrape_text_from_url(url)
    return results


# Usage with a specific date
date = "07-05-2024"
df = scrape_articles(date)
text_results = scrape_text_from_urls(df)

# Organize data in a JSON-friendly structure
data = [{"url": url, "content": content} for url, content in text_results.items()]

# Save the data to a JSON file
output_file = "scraped_articles.json"
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=4)

print(f"Scraped data has been saved to {output_file}")

# Option to manually enter a URL and save separately
# url_input = input("Enter a specific URL to scrape (or press Enter to skip): ").strip()
# if url_input:
#     specific_text_result = scrape_text_from_url(url_input)
#     specific_data = {
#         "url": url_input,
#         "content": specific_text_result
#     }
#     # Save the specific data to another JSON file
#     specific_output_file = "scraped_article_single.json"
#     with open(specific_output_file, 'w', encoding='utf-8') as f:
#         json.dump(specific_data, f, ensure_ascii=False, indent=4)
#
#     print(f"\nSpecific URL data has been saved to {specific_output_file}\n{'=' * 60}")
