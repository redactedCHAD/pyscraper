import os
import agentql
from playwright.sync_api import sync_playwright
import csv
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get USERNAME and PASSWORD from environment variables
EMAIL = os.getenv("EMAIL")
PASSWORD = os.getenv("PASSWORD")
os.environ["AGENTQL_API_KEY"] = os.getenv("AGENTQL_API_KEY")

INITIAL_URL = "https://www.idealist.org/"
URL = "https://www.idealist.org/jobs"

EMAIL_INPUT_QUERY = """
{
    login_form {
        email_input
        continue_btn
    }
}
"""

VERIFY_QUERY = """
{
    login_form {
        verify_not_robot_checkbox
    }
}
"""

PASSWORD_INPUT_QUERY = """
{
    login_form {
        password_input
        continue_btn
    }
}
"""

JOB_POSTS_QUERY = """
{
    job_posts[] {
        org_name
        job_title
        salary
        location
        contract_type(Contract or Full time)
        location_type(remote or on-site or hybrid)
        date_posted
    }
}
"""

PAGINATION_QUERY = """
{
    pagination {
        next_page_btn    
    }
}
"""

def login(page):
    # Use query_elements() method to locate "Log In" button on the page
    response = page.query_elements(EMAIL_INPUT_QUERY)
    response.login_form.email_input.fill(EMAIL)
    page.wait_for_timeout(1000)

    # Verify Human
    verify_response = page.query_elements(VERIFY_QUERY)
    verify_response.login_form.verify_not_robot_checkbox.click()
    page.wait_for_timeout(1000)

    # Continue Next Step
    response.login_form.continue_btn.click()

    # Input Password
    password_response = page.query_elements(PASSWORD_INPUT_QUERY)
    password_response.login_form.password_input.fill(PASSWORD)
    page.wait_for_timeout(1000)
    password_response.login_form.continue_btn.click()
    page.wait_for_page_ready_state()

    # Save login state
    page.context.storage_state(path="idealist_login.json")

def fetch_job_posts(page):
    job_posts_response = page.query_elements(JOB_POSTS_QUERY)
    job_posts_data = job_posts_response.job_posts.to_data()
    print(f"Total number of job posts: {len(job_posts_data)}")
    return job_posts_data

def save_to_csv(job_posts_data):
    # Define the CSV file name
    csv_file = 'job_posts.csv'
    
    # Check if the file exists to determine if we need to write headers
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.writer(file)
        
        # Write headers if the file is new
        if not file_exists:
            writer.writerow(['Organization Name', 'Job Title', 'Salary', 'Location', 'Contract Type', 'Location Type', 'Date Posted'])
        
        # Write job posts data
        for job in job_posts_data:
            writer.writerow([job['org_name'], job['job_title'], job['salary'], job['location'], job['contract_type'], job['location_type'], job['date_posted']])

def main():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        
        # Initialize context variable
        context = None
        
        if not os.path.exists("idealist_login.json"):
            print("No login state found, logging in...")
            page = agentql.wrap(browser.new_page())
            page.goto(INITIAL_URL)
            login(page)
            # Create a new context after logging in
            context = browser.new_context(storage_state="idealist_login.json")
        else:
            print("Loading existing login state...")
            context = browser.new_context(storage_state="idealist_login.json")

        # Now that context is guaranteed to be defined, create a new page
        page = agentql.wrap(context.new_page())
        page.goto(URL)

        previous_url = None  # Initialize previous URL

        # Handle pagination
        while True:
            current_url = page.url  # Get the current URL
            job_posts_data = fetch_job_posts(page)
            save_to_csv(job_posts_data)

            # Check for pagination
            paginations = page.query_elements(PAGINATION_QUERY)
            next_page_btn = paginations.pagination.next_page_btn
            
            if next_page_btn:
                next_page_btn.click()
                page.wait_for_page_ready_state()
            else:
                break

            # Check if the current URL is the same as the previous URL
            if current_url == previous_url:
                print("Reached the last page.")
                break
            
            previous_url = current_url  # Update previous URL

if __name__ == "__main__":
    main() 
