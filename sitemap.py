import requests
import re
from urllib.parse import urlparse
from datetime import datetime
import subprocess
import time

# Constants
SITEMAP_URL = "https://developer.toradex.com/sitemap.xml"
PDF_PREFIX = "Torizon"

def is_numeric(s):
    try:
        float(s)
        return True
    except ValueError:
        return False

def run_wkhtmltopdf(txt_filename, pdf_filename, max_retries=2):
    for attempt in range(1, max_retries + 1):
        try:
            print(f"Attempt {attempt}: Creating {pdf_filename} from {txt_filename}...")
            command = f"wkhtmltopdf $(cat {txt_filename}) {pdf_filename}"
            subprocess.run(command, shell=True, check=True)
            print(f"Successfully created {pdf_filename}")
            return
        except subprocess.CalledProcessError as e:
            print(f"Error: Failed to create {pdf_filename} on attempt {attempt}. Error: {e}")
            if attempt < max_retries:
                print("Retrying...")
                time.sleep(2)
            else:
                print(f"Failed to create {pdf_filename} after {max_retries} attempts.")
                raise

today_date = datetime.now().strftime("%m%d%y")

response = requests.get(SITEMAP_URL)
if response.status_code != 200:
    print(f"Failed to fetch {SITEMAP_URL}")
    exit(1)

urls = re.findall(r'<loc>(.*?)</loc>', response.text)

url_groups = {}

for url in urls:
    parsed_url = urlparse(url)
    path_parts = parsed_url.path.strip('/').split('/')
    if len(path_parts) > 1:
        top_level_dir = path_parts[0]
        if not is_numeric(path_parts[1]):
            if top_level_dir not in url_groups:
                url_groups[top_level_dir] = []
            url_groups[top_level_dir].append(url)

for top_level_dir, dir_urls in url_groups.items():
    txt_filename = f"{top_level_dir}_urls_{today_date}.txt"
    
    first_url = dir_urls[0]
    domain = urlparse(first_url).netloc.replace('.', '-')
    
    pdf_filename = f"{PDF_PREFIX}-{domain}-{today_date}.pdf"
    
    print(f"Processing directory: {top_level_dir}")
    
    with open(txt_filename, 'w') as f:
        for dir_url in dir_urls:
            f.write(dir_url + '\n')
    
    try:
        run_wkhtmltopdf(txt_filename, pdf_filename)
    except Exception as e:
        print(f"Final error: Could not create PDF for {top_level_dir}. Skipping.")
