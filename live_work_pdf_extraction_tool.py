import streamlit as st
import os
import requests
from bs4 import BeautifulSoup
from io import BytesIO
import PyPDF2
import google.generativeai as genai
import re  # Import regex to detect numeric price changes
import time

# Streamlit webpage title
st.title('Oil Price Trend Analyzer from PDF and Websites (Develop Mode)')

# Function to generate content using the language model
os.environ['GOOGLE_API_KEY'] = "AIzaSyB_0W_3KBVKNI0Tygo2iBVMhfbiCwS9VfY"
genai.configure(api_key=os.environ['GOOGLE_API_KEY'])
model = genai.GenerativeModel('gemini-pro')

def extract_text_from_pdf(pdf_file):
    """Input: Pdf File, Output: Text from Pdf"""
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file)
        text = ''
        for page_num in range(min(2, len(pdf_reader.pages))):  # Extract from only the first 2 pages
            page = pdf_reader.pages[page_num]
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"An error occurred while processing the PDF file: {e}")
        return None

def download_and_extract_pdf_from_url(url):
    """Input: URL from PDF, Output: PDF text"""
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        pdf_file = BytesIO(response.content)
        extracted_text = extract_text_from_pdf(pdf_file)
        return extracted_text
    except Exception as e:
        st.error(f"An error occurred while downloading or extracting the PDF from {url}: {e}")
        return None

def fetch_pdf_links(url, max_pages=8):
    try:
        pdf_links = []
        current_page = 1

        while current_page <= max_pages and url:
            response = requests.get(url, verify=False)
            response.raise_for_status()
            page_content = response.content
            soup = BeautifulSoup(page_content, 'html.parser')
            links = soup.find_all('a', href=True)

            for link in links:
                href = link['href']
                if href.endswith('.pdf'):
                    pdf_links.append(href)

            next_page_link = soup.find('a', string=re.compile(r'Next|›', re.IGNORECASE))
            if next_page_link:
                next_page_url = next_page_link['href']
                if not next_page_url.startswith('http'):
                    next_page_url = requests.compat.urljoin(url, next_page_url)
                url = next_page_url
                current_page += 1
            else:
                break

        pdf_links = list(set(pdf_links))

        return pdf_links

    except requests.exceptions.RequestException as e:
        st.error(f"An error occurred while fetching the URL: {e}")
        return []

# URL input and max pages
url = st.text_input('Enter the URL to search for links:', '')
max_pages = st.number_input('Enter the number of pages to search (pagination):', min_value=1, value=2)



def llm_function(query):
    response = model.generate_content(query)
    return response.text


if st.button('Fetch PDF links'):
    pdf_url_list = fetch_pdf_links(url, max_pages)
    st.session_state['pdf_url_list'] = pdf_url_list  # Store PDF links in session_state
    st.session_state['url_input'] = "\n".join(pdf_url_list)  # Store URLs as text for display

# Display the fetched URLs in a text area, if any
url_input = st.session_state.get('url_input', '')
url_text_area = st.text_area("Analyze the following URLs?", value=url_input)

# Retrieve pdf_url_list from session_state
pdf_url_list = st.session_state.get('pdf_url_list', [])

text_with_required_data = ''
# "Analyze Links" button
if st.button("Analyze Links"):
    with st.spinner('Analyzing...'):
        for pdf_url in pdf_url_list:
            text_from_pdf = download_and_extract_pdf_from_url(pdf_url)
            if text_from_pdf:
                st.write(f"Text from {pdf_url}:")
                print ('\n\n\n\n\n\n')
                selected_question = """
                                    Does the following text contain details about Palm Oil.
                                    If yes, follow the given rules:
                                    - Heading should be the oil name and Month and year of data
                                    -below the head will be the summary of Pal oil Prices and trends in bullet format
                                    -the data should be concise and less than 200 words
                                    If no, return 0
                                    """
                query = f'{selected_question} {text_from_pdf}'
                response_text = llm_function(query=query)
                # print (response_text)
                if response_text[0] != '0':
                    text_with_required_data += (response_text + '\n\n')

                time.sleep(3)
                st.text(response_text)
            else:
                st.warning(f"Could not extract text from {pdf_url}")
        print('***********************************\n\n\n\n', text_with_required_data, '\n\n\n**********************')
        st.write('Execution Completed')

