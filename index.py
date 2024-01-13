import csv
import json
from playwright.async_api import async_playwright
from dotenv import load_dotenv
import os
import time
import asyncio

# Load environment variables from .env file
load_dotenv()

COOKIES_FILE_PATH = './cookies.json'
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
JOB_SEARCH_URI = os.getenv("JOB_SEARCH_URI")
CSV_FILE_NAME = f"sales-development-rep_{time.strftime('%m%d')}.csv"

async def save_cookies(page):
    print("Saving cookies...")
    with open(COOKIES_FILE_PATH, 'w') as file:
        cookies = await page.context.cookies()  # Await this call
        json.dump(cookies, file)


async def load_cookies(context):
    print("Loading cookies...")
    try:
        with open(COOKIES_FILE_PATH, 'r') as file:
            contents = file.read()
            if contents:  # Check if the file is not empty
                cookies = json.loads(contents)
                await context.add_cookies(cookies)
                print("Cookies loaded successfully.")
            else:
                print("Cookies file is empty. Starting a new session.")
    except FileNotFoundError:
        print("Cookies file not found. Starting a new session.")
    except json.JSONDecodeError:
        print("Error reading cookies file. Starting a new session.")


async def capture_dom_and_save(page):
    print("Capturing DOM content...")

    # Retrieve the full HTML content of the page
    dom_content = await page.content()

    # Save the HTML content to a file
    with open("DOM.html", "w", encoding="utf-8") as file:
        file.write(dom_content)

    print("DOM content saved to DOM.html")

async def scrape_jobs_on_page(page):
    # Function to handle console messages
    def handle_console_message(msg):
        print("Browser console:", msg.text)

    # Add event listener to capture console messages
    page.on("console", handle_console_message)

    print("Scraping jobs on current page...")

    # Wait for the initial jobs to load
    await page.wait_for_selector("a.job-card-container__link.job-card-list__title", timeout=30000)
    print("Initial jobs loaded.")

    # Scroll within the jobs list container
    last_job_count = 0
    while True:
        job_elements = await page.query_selector_all(
            'div.job-card-container.relative.job-card-list.job-card-container--clickable')

        # Scroll down within the container
        await page.evaluate('''() => {
            console.log('Evaluating the page');
            const container = document.querySelector('.jobs-search-results-list');
            const scrollHeight = 1000;
            if (container) {
                console.log('Found container: ', container);
                console.log(`scrollHeight: `, scrollHeight);
                container.scrollBy(0, container.scrollHeight);
            } else {
                console.log('No container');
            }
        }''')

        # Wait for new jobs to load after scrolling
        await page.wait_for_timeout(2000)

        # Check if new jobs are loaded
        new_job_elements = await page.query_selector_all(
            'div.job-card-container.relative.job-card-list.job-card-container--clickable')
        if len(new_job_elements) == last_job_count:
            break  # Stop if no new jobs are loaded
        last_job_count = len(new_job_elements)

    print(f"Number of job elements found: {len(job_elements)}")

    # Process each job element
    jobs = []
    for job_element in job_elements:
        print("Processing a job element...")
        title_element = await job_element.query_selector("a.job-card-container__link.job-card-list__title")
        company_element = await job_element.query_selector("span.job-card-container__primary-description")
        location_element = await job_element.query_selector("ul.job-card-container__metadata-wrapper li.job-card-container__metadata-item")
        salary_element = await job_element.query_selector("ul.job-card-container__metadata-wrapper li:nth-of-type(2)")

        title = await title_element.inner_text() if title_element else "Title not specified"
        company = await company_element.inner_text() if company_element else "Company not specified"
        location = await location_element.inner_text() if location_element else "Location not specified"
        salary = await salary_element.inner_text() if salary_element else "Salary not specified"
        href = await title_element.get_attribute("href")
        job_link = f"https://www.linkedin.com{href}" if href else "No link available"

        jobs.append({
            'title': title,
            'company': company,
            'location': location,
            'salary': salary,
            'link': job_link
        })

    print(f"Found {len(jobs)} job(s) on this page matching the criteria.")
    return jobs



async def read_existing_jobs(filename):
    existing_jobs = set()
    try:
        with open(filename, mode='r', newline='', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                existing_jobs.add((row['title'], row['company'], row['link']))
    except FileNotFoundError:
        pass
    return existing_jobs

async def write_to_csv(jobs, existing_jobs):
    print(f"Writing {len(jobs)} job(s) to CSV...")

    # Define the CSV fieldnames
    fieldnames = ['title', 'company', 'location', 'salary', 'benefits', 'link']

    # Check if the CSV file exists and if not, initialize it with the header
    file_exists = os.path.exists(CSV_FILE_NAME)
    if not file_exists:
        with open(CSV_FILE_NAME, mode='w', newline='', encoding='utf-8') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

    # Filter out jobs that are already in the CSV
    new_jobs = [job for job in jobs if (job['title'], job['company'], job['link']) not in existing_jobs]
    if not new_jobs:
        print("No new jobs to write.")
        return

    # Append new jobs to the CSV
    with open(CSV_FILE_NAME, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=fieldnames)
        writer.writerows(new_jobs)

    # Update the existing jobs set with the new job details
    existing_jobs.update((job['title'], job['company'], job['link']) for job in new_jobs)


async def run():
    print("Launching browser...")
    playwright = await async_playwright().start()
    browser = await playwright.chromium.launch(headless=False)
    context = await browser.new_context()

    # Load cookies to see if we can bypass login
    await load_cookies(context)

    page = await context.new_page()
    print("Navigating to LinkedIn...")
    await page.goto("https://linkedin.com")

    # Check if login is needed
    if "feed" not in page.url:
        print("Logging in...")
        await page.wait_for_selector('#session_key')
        await page.fill('#session_key', LINKEDIN_EMAIL)

        await page.wait_for_selector('#session_password')
        await page.fill('#session_password', LINKEDIN_PASSWORD)

        await page.click("button[data-id='sign-in-form__submit-btn']")
        # Wait for potential CAPTCHA, increase if needed
        await page.wait_for_timeout(20000)

    # Save cookies after login for future sessions
    await save_cookies(page)

    # Read existing jobs from the CSV to avoid duplicates
    existing_jobs = await read_existing_jobs(CSV_FILE_NAME)

    # Navigate to the job search URL
    print(f"Navigating to job search URL: {JOB_SEARCH_URI}")
    await page.goto(JOB_SEARCH_URI)
    # await capture_dom_and_save(page)

    # Process each page
    current_page = 1
    while True:
        print(f"Processing page {current_page}...")
        jobs = await scrape_jobs_on_page(page)
        await write_to_csv(jobs, existing_jobs)

        # Check for and click the next page button
        next_page_button = await page.query_selector(f"button[aria-label='Page {current_page + 1}']")
        if not next_page_button:
            print("No more pages to process.")
            break
        await next_page_button.click()
        await page.wait_for_timeout(5000)  # Wait for the next page to load
        current_page += 1

    # Save cookies at the end of the session
    await save_cookies(page)
    print("Script completed. Keep the browser open for inspection.")


# Running the script
if __name__ == "__main__":
    print("Starting script...")
    asyncio.run(run())
    print("The script has finished. The browser remains open for inspection.")



