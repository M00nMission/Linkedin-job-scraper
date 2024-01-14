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
start_row = int(os.getenv('START_ROW', 1))  # Default to 1 if START_ROW is not set


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

async def get_company_website(page, company_page_link):
    if not company_page_link:
        print("No company page link provided. Skipping...")
        return None

    about_page_link = company_page_link + '/about'
    print(f"Visiting company about page: {about_page_link}")
    await page.goto(about_page_link)

    # Wait for the DOM to render
    await page.wait_for_timeout(2000)

    print("Attempting to find the company's website...")
    selector = 'dl.overflow-hidden a[href^="http"]:first-of-type'  # Selects the first link that starts with http
    website_link_element = await page.query_selector(selector)
    website_link = await website_link_element.get_attribute('href') if website_link_element else None
    print(f"Extracted website link: {website_link}")

    return website_link

async def process_csv(input_file, output_file, start_row):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await load_cookies(context)
        page = await context.new_page()

        with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
             open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
            reader = csv.DictReader(infile)
            fieldnames = reader.fieldnames + ['website_link']
            writer = csv.DictWriter(outfile, fieldnames=fieldnames)
            writer.writeheader()

            current_row = 1  # Starting from row 1
            for row in reader:
                if current_row < start_row:
                    print(f"Skipping row {current_row}: {row}")
                    current_row += 1
                    continue

                company_page_link = row.get('company_page_link')
                if not company_page_link:
                    print(f"Skipping row with missing 'company_page_link': {row}")
                    row['website_link'] = None
                else:
                    print(f"Processing row {current_row}: {company_page_link}...")
                    website_link = await get_company_website(page, company_page_link)
                    row['website_link'] = website_link
                writer.writerow(row)
                current_row += 1

        await save_cookies(context)
        await browser.close()

# Run the async main function
asyncio.run(process_csv(input_file_path, output_file_path, start_row))