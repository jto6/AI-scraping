import asyncio
import os
import sys
import tempfile
from PyPDF2 import PdfMerger, PdfReader
import pyppeteer
import re
from urllib.parse import urlparse

async def convert_url_to_pdf(page, url, output_path):
    try:
        await page.goto(url, {'waitUntil': 'networkidle2', 'timeout': 60000})
        await page.pdf({
            'path': output_path,
            'format': 'A4',
            'printBackground': True,
            'displayHeaderFooter': True,
            'margin': {'top': '1cm', 'right': '1cm', 'bottom': '1cm', 'left': '1cm'}
        })
        return True
    except Exception as e:
        print(f"Error converting {url}: {str(e)}")
        return False

def count_words_in_pdf(pdf_path):
    reader = PdfReader(pdf_path)
    text = ""
    for page in reader.pages:
        text += page.extract_text()
    words = re.findall(r'\w+', text)
    return len(words)

def get_url_structure(url):
    parsed = urlparse(url)
    return os.path.dirname(parsed.path)

def structures_differ(s1, s2):
    """
    Determines if 2 directory structures differ "enough".

    The current test is if there is a change in the directory after ignoring
    any changes in the bottom 1 level of directories between the two

    eg, A/B/C/D and A/B/C/E are similar, whereas
    A/B/C/D and A/B/E/F differ

    Parameters:
    s1 (str): The first structure
    s2 (str): The second structure

    Returns:
    bool: True if they differ enought, else False
    """
    parts1 = s1.rstrip('/').split('/')
    parts2 = s2.rstrip('/').split('/')

    # Find the structure depth to check to
    check_depth = max(len(parts1)-1, len(parts2)-1)

    # Compare the directories of both structures up to the check depth
    return parts1[:check_depth] != parts2[:check_depth]

def group_pdfs(pdf_info, word_limit=100000, tolerance=0.2):
    groups = []
    current_group = []
    current_words = 0
    current_structure = None

    for pdf, words, structure, url in pdf_info:
        if not current_group:
            current_group.append((pdf, words))
            current_words = 0
        elif current_words + words <= word_limit * (1 - tolerance):
            # Always include if total size is < 80% of the limit
            current_group.append((pdf, words))
        elif current_words + words > word_limit * (1 + tolerance):
            # Always start a new group if > 120% of the limit
            groups.append(current_group)
            current_group = [(pdf, words)]
            current_words = 0
        else:
            # In tolerance range, check if structures differ enough to break

            print(f"csz: {current_words} nsz: {words} url: {url} from {current_structure} to {structure}")
            if structures_differ(structure, current_structure):
                groups.append(current_group)
                current_group = [(pdf, words)]
                current_words = 0
            else:
                current_group.append((pdf, words))

        current_words += words
        current_structure = structure

    if current_group:
        groups.append(current_group)

    return groups

async def main(input_file, output_pdf, verbose=False):
    browser = await pyppeteer.launch(headless=True, args=['--no-sandbox'])
    pdf_info = []

    with tempfile.TemporaryDirectory() as temp_dir:
        with open(input_file, 'r') as f:
            urls = [line.strip().rstrip("\\") for line in f if line.strip().rstrip("\\")]

        for idx, url in enumerate(urls):
            print(f"Processing ({idx+1}/{len(urls)}): {url}")
            page = await browser.newPage()
            temp_path = os.path.join(temp_dir, f"page_{idx}.pdf")

            success = False
            for attempt in range(1, 3):
                if await convert_url_to_pdf(page, url, temp_path):
                    word_count = count_words_in_pdf(temp_path)
                    structure = get_url_structure(url)
                    pdf_info.append((temp_path, word_count, structure, url))
                    print(f"  Words in this PDF: {word_count}")
                    print(f"  URL structure: {structure}")
                    success = True
                    break
                print(f"Retrying ({attempt}/2)...")

            await page.close()
            if not success:
                print(f"Failed to process {url} after 2 attempts")

        grouped_pdfs = group_pdfs(pdf_info)

        for group_idx, group in enumerate(grouped_pdfs):
            merger = PdfMerger()
            total_words = sum(words for _, words in group)
            urls_in_group = [url for pdf_path, _, _, url in pdf_info if pdf_path in [g[0] for g in group]]

            if len(grouped_pdfs) > 1:
                output_filename = f"{os.path.splitext(output_pdf)[0]}_{group_idx+1}.pdf"
            else:
                output_filename = output_pdf

            for pdf_path, _ in group:
                merger.append(pdf_path)

            with open(output_filename, 'wb') as f:
                merger.write(f)

            print(f"Created {output_filename} with {total_words} words")

            if verbose:
                print("URLs included in this PDF:")
                for url in urls_in_group:
                    print(f"  - {url}")

    await browser.close()
    print(f"Successfully created {len(grouped_pdfs)} combined PDF{'s' if len(grouped_pdfs) > 1 else ''}")

if __name__ == "__main__":
    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print("Usage: python script.py <input_file> <output_pdf> [--verbose]")
        sys.exit(1)

    input_file = sys.argv[1]
    output_pdf = sys.argv[2]
    verbose_mode = "--verbose" in sys.argv

    asyncio.run(main(input_file, output_pdf, verbose=verbose_mode))
