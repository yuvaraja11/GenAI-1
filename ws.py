
from bs4 import BeautifulSoup

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import pandas as pd
import time
import google.generativeai as genai
import re
import google.api_core.exceptions
##API_KEY = os.getenv("API_SECRET_KEY")

urls = [
    "https://www.cartier.com",
    "https://www.tiffany.com",
    "https://www.bulgari.com",
    "https://www.ralphlauren.com",
    "https://www.armani.com",
    "https://www.dior.com",
    "https://www.yvesstlaurent.com",
    "https://www.ferrari.com",
    "https://www.patek.com"
]


def fetch_content(url):
    try:
        options = Options()
        options.headless = True
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
        driver.get(url)
        time.sleep(3) 
        page_source = driver.page_source
        driver.quit()
        soup = BeautifulSoup(page_source, 'html.parser')
        return soup
    except Exception as e:
        print(f"Failed to fetch content from {url}: {e}")
        return None


def clean_data(soup):
    for script in soup(['script', 'style', 'footer', 'header', 'nav', 'aside']):
        script.decompose()
    return soup.get_text(separator=' ', strip=True)


genai.configure(api_key="AIzaSyAOF8CgV7OCgSNDxcpw_ZgbwShDMvAf4xA", transport="rest")


def call_gemini_api(prompt):
    retries = 5
    delay = 10
    while retries > 0:
        try:
            model = genai.GenerativeModel("gemini-1.5-pro")
            response = model.generate_content(prompt)
            return response.text if response else ""
        except google.api_core.exceptions.TooManyRequests as e:
            print(f"Rate limit exceeded: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)
            retries -= 1
            delay *= 2  
        except Exception as e:
            print(f"Error during API call: {e}")
            break  
    return ""  


def extract_information_with_gemini(cleaned_text, nav_link_dict = {}, previous_data=""):
    pre_prompt = f"""
    Please extract the following information from the given text:
    1. What is the company's mission statement or core values?
    2. What products or services does the company offer?
    3. When was the company founded, and who were the founders?
    4. Where is the company's headquarters located?
    5. Who are the key executives or leadership team members?
    6. Has the company received any notable awards or recognitions?
   
    Text: {cleaned_text}
    """
    res = call_gemini_api(pre_prompt).replace('*', '')
    print(res)
    link_lists = re.findall(r'https?://\S+', res)
    print(link_lists)
    return res, link_lists

def call_recur(link_lists, res):
    extracted_data = {}
    for link in link_lists:
        if "javascript:void(0)" in link:
            continue
        soup = fetch_content(link)
        if soup:
            extracted_data[link] = extract_information_with_gemini(soup.getText())[0]
    return extracted_data


def save_to_csv(data, filename="company_details_1.csv"):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)


def process_urls(urls):
    all_extracted_data = []
    failed_urls = []  
    for url in urls:
        print(f"Scraping {url}...")
        soup = fetch_content(url)
        if not soup:
            failed_urls.append(url)
            continue
        a_tags = soup.find_all('a')
        a_dict = {}
        for tag in a_tags:
            text = tag.get_text(strip=True)  
            href = tag.get('href')  
            if text and href:
                a_dict[text] = url + href
        extracted_info, link_lists = extract_information_with_gemini(soup.getText(), nav_link_dict=a_dict)
        
        
        if link_lists:
            link_data = call_recur(link_lists, extracted_info)
        else:
            link_data = {}

       
        record = {"URL": url, "Extracted Info": extracted_info}
        record.update(link_data)  
        all_extracted_data.append(record)
        
        time.sleep(2)  
    
    
    if failed_urls:
        print("The following URLs failed to load:")
        for url in failed_urls:
            print(url)

    save_to_csv(all_extracted_data)
    print("Extraction complete. Data saved to company_details.csv.")


process_urls(urls)
