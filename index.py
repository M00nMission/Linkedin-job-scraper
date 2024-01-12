import json
from playwright.sync_api import sync_playwright
from dotenv import load_dotenv
import os
import time

# Load environment variables from .env file
load_dotenv()

COOKIES_FILE_PATH = './cookies.json'

# Get LinkedIn credentials from environment variables
LINKEDIN_EMAIL = os.getenv("LINKEDIN_EMAIL")
LINKEDIN_PASSWORD = os.getenv("LINKEDIN_PASSWORD")
JOB_SEARCH_URI = os.getenv("JOB_SEARCH_URI")

def save_cookies(page):
    with open(COOKIES_FILE_PATH, 'w') as file:
        json.dump(page.context.cookies(), file)

def load_cookies(context):
    try:
        with open(COOKIES_FILE_PATH, 'r') as file:
            contents = file.read()
            if contents:  # Check if the file is not empty
                cookies = json.loads(contents)
                context.add_cookies(cookies)
            else:
                print("Cookies file is empty. Starting a new session.")
    except FileNotFoundError:
        print("Cookies file not found. Starting a new session.")
    except json.JSONDecodeError:
        print("Error reading cookies file. Starting a new session.")

def run(playwright):
    browser = playwright.chromium.launch(headless=False)  # headless=False to see the browser
    context = browser.new_context()

    # Load cookies
    load_cookies(context)

    page = context.new_page()
    page.goto("https://linkedin.com")  # Navigate to LinkedIn

    # Check if already logged in using cookies
    if "feed" not in page.url:
        # Wait for the username and password fields and fill them
        page.wait_for_selector('#session_key')
        page.fill('#session_key', LINKEDIN_EMAIL)

        page.wait_for_selector('#session_password')
        page.fill('#session_password', LINKEDIN_PASSWORD)

        # Click the login button
        page.click("button[data-id='sign-in-form__submit-btn']")

        # Wait for potential CAPTCHA for 20 seconds
        time.sleep(20)

    # Save cookies
    save_cookies(page)

    page.goto(JOB_SEARCH_URI)

    # browser.close()

with sync_playwright() as playwright:
    run(playwright)
