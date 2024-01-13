import asyncio
import csv
import os
from dotenv import load_dotenv
from playwright.async_api import async_playwright

load_dotenv()

INPUT_CSV = os.getenv("INPUT_CSV")
OUTPUT_CSV = os.getenv("OUTPUT_CSV")


async def lookup_ticker(page, company_name):
    # Clear the search input and type the company name
    await page.fill('#yfin-usr-qry', company_name)

    # Wait a bit for suggestions to load (adjust as needed)
    await asyncio.sleep(1)

    # Attempt to get the ticker symbol from the first suggestion
    ticker_elements = await page.query_selector_all('.modules-module_quoteSymbol__BGsyF')
    ticker = await ticker_elements[0].inner_text() if ticker_elements else None

    return ticker


async def process_csv(input_file, output_file, page):
    with open(input_file, mode='r', newline='', encoding='utf-8') as infile, \
            open(output_file, mode='w', newline='', encoding='utf-8') as outfile:
        reader = csv.DictReader(infile)
        # Insert 'ticker' right after 'company' in the fieldnames list
        fieldnames = reader.fieldnames
        company_index = fieldnames.index('company')
        fieldnames.insert(company_index + 1, 'ticker')

        writer = csv.DictWriter(outfile, fieldnames=fieldnames)
        writer.writeheader()

        for row in reader:
            print(f"Looking up ticker for {row['company']}...")
            ticker = await lookup_ticker(page, row['company'])
            if ticker and ticker != 'PRIVATE':
                row['ticker'] = ticker
                writer.writerow(row)
                print(f"Ticker found: {ticker}")
            else:
                row['ticker'] = ''
                writer.writerow(row)
                print(f"No valid ticker found for {row['company']}, skipping.")


async def main():
    input_csv = INPUT_CSV
    output_csv = OUTPUT_CSV

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://finance.yahoo.com/')

        await process_csv(input_csv, output_csv, page)

        # Close the browser after processing
        await browser.close()

    print("Processing completed.")


# Run the async main function
asyncio.run(main())