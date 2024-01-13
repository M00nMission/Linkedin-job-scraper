import csv
import asyncio
from urllib.parse import urlparse
from playwright.async_api import async_playwright
import os
from dotenv import load_dotenv
import json

load_dotenv()

COOKIES_FILE_PATH = './cookies.json'
input_file_path = os.getenv('INPUT_CSV')
output_file_path = os.getenv('OUTPUT_CSV')

async def save_cookies(context):
    print("Saving cookies...")
    with open(COOKIES_FILE_PATH, 'w') as file:
        cookies = await context.cookies()
        json.dump(cookies, file)

async def load_cookies(context):
    print("Loading cookies...")
    try:
        with open(COOKIES_FILE_PATH, 'r') as file:
            contents = file.read()
            if contents:
                cookies = json.loads(contents)
                await context.add_cookies(cookies)
                print("Cookies loaded successfully.")
            else:
                print("Cookies file is empty. Starting a new session.")
    except FileNotFoundError:
        print("Cookies file not found. Starting a new session.")
    except json.JSONDecodeError:
        print("Error reading cookies file. Starting a new session.")

async def get_domain_from_linkedin(page, link):
    print(f"Visiting job link: {link}")
    await page.goto(link)

    print("Attempting to find the company's LinkedIn life page link...")
    await page.click('a.app-aware-link', timeout=30000)
    print("Clicked on the company's LinkedIn life page link.")

    print("Attempting to find the 'Visit website' link...")
    website_link_elements = await page.query_selector_all('a[rel="noopener noreferrer"][target="_blank"]')

    website_url = None
    for element in website_link_elements:
        text = await element.text_content()
        if "visit website" in text.lower():
            website_url = await element.get_attribute('href')
            break

    if website_url:
        print(f"Extracted 'Visit website' URL: {website_url}")
        domain = urlparse(website_url).netloc
        print(f"Extracted domain from URL: {domain}")
    else:
        print("'Visit website' link not found. Skipping...")
        domain = None

    return domain

async def process_csv(input_file, output_file):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()

        with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
             open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['domain']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                print(f"Processing {row['link']}...")
                domain = await get_domain_from_linkedin(page, row['link'])
                row['domain'] = domain
                writer.writerow(row)

        await save_cookies(context)
        await browser.close()

# Run the async main function
asyncio.run(process_csv(input_file_path, output_file_path))
