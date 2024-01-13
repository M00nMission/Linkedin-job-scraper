import csv
import asyncio
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

async def get_company_linkedin_page(page, link):
    if not link:
        print("No link provided. Skipping...")
        return None

    print(f"Visiting job link: {link}")
    await page.goto(link)

    # Waiting for 2 seconds to allow the DOM to render
    print("Waiting for the DOM to render...")
    await page.wait_for_timeout(2000)

    print("Attempting to find the company's LinkedIn page link...")
    selector = '.job-details-jobs-unified-top-card__primary-description-without-tagline a.app-aware-link'
    company_page_link_element = await page.query_selector(selector)
    company_page_link = await company_page_link_element.get_attribute('href') if company_page_link_element else None
    print(f"Extracted company LinkedIn page link: {company_page_link}")

    return company_page_link




async def process_csv(input_file, output_file):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()

        with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
             open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['company_page_link']  # Add 'company_page_link' to fieldnames
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            for row in reader:
                link = row.get('link')
                if not link:
                    print(f"Skipping row with missing 'link': {row}")
                    row['company_page_link'] = None
                else:
                    print(f"Processing {link}...")
                    company_page_link = await get_company_linkedin_page(page, link)
                    row['company_page_link'] = company_page_link
                writer.writerow(row)

        await save_cookies(context)
        await browser.close()




# Run the async main function
asyncio.run(process_csv(input_file_path, output_file_path))
