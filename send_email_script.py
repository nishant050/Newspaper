import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import concurrent.futures

# --- Configuration ---
# We define the newspapers here, now including their logo URLs
NEWSPAPERS_CONFIG = [
    {
        "name": "Hindustan Times",
        "url": "https://epaperwave.com/hindustan-times-epaper-pdf-today/",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/11/Hindustan_Times_logo.svg/1280px-Hindustan_Times_logo.svg.png"
    },
    {
        "name": "The Times of India",
        "url": "https://epaperwave.com/the-times-of-india-epaper-pdf-download/",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/99/Times_of_India_logo.svg/1920px-Times_of_India_logo.svg.png"
    },
    {
        "name": "The Mint",
        "url": "https://epaperwave.com/download-the-mint-epaper-pdf-for-free-today/",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/thumb/3/3e/The_Mint_logo.svg/1280px-The_Mint_logo.svg.png"
    },
    {
        "name": "Dainik Bhaskar",
        "url": "https://epaperwave.com/dainik-bhaskar-epaper-today-pdf/",
        "logo": "https://upload.wikimedia.org/wikipedia/en/thumb/f/fd/Dainik_Bhaskar_logo.svg/1280px-Dainik_Bhaskar_logo.svg.png"
    },
    {
        "name": "Punjab Kesari",
        "url": "https://epaperwave.com/free-punjab-kesari-epaper-pdf-download-now/",
        "logo": "https://upload.wikimedia.org/wikipedia/commons/2/25/Punjab_Kesari_logo.png"
    }
]

# --- Selenium & Scraping Functions ---
def create_driver():
    """Sets up a new Selenium WebDriver instance for Chromium."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    service = Service(executable_path="/usr/bin/chromedriver")
    return webdriver.Chrome(service=service, options=chrome_options)

def scrape_single_newspaper(newspaper_info, target_date):
    """Scrapes one newspaper URL in its own private browser."""
    driver = create_driver()
    name, url = newspaper_info["name"], newspaper_info["url"]
    date_str = target_date.strftime('%d-%m-%Y')
    try:
        driver.get(url)
        time.sleep(3)
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        paragraphs = soup.find_all('p', class_='has-text-align-center')
        for p in paragraphs:
            if p.get_text(strip=True).startswith(date_str):
                link_tag = p.find('a')
                if link_tag and link_tag.has_attr('href'):
                    return name, link_tag['href']
    finally:
        if driver:
            driver.quit()
    return name, None

def find_all_newspapers(target_date):
    """Uses a thread pool to scrape all newspapers concurrently."""
    found_papers = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(NEWSPAPERS_CONFIG)) as executor:
        future_to_newspaper = {executor.submit(scrape_single_newspaper, newspaper, target_date): newspaper for newspaper in NEWSPAPERS_CONFIG}
        for future in concurrent.futures.as_completed(future_to_newspaper):
            name, link = future.result()
            if link:
                print(f"✅ Found: {name}")
                found_papers[name] = link
            else:
                print(f"🟡 Not found: {name}")
    return found_papers

# --- Email Function ---
def send_email(recipients, found_papers, paper_date):
    """Constructs and sends the beautifully designed email."""
    # Get credentials from environment variables (how GitHub Actions provides secrets)
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_APP_PASSWORD")

    if not sender_email or not sender_password:
        print("❌ Email credentials not found in environment variables.")
        return

    subject = f"🗞️ Your Daily e-Paper Digest for {paper_date.strftime('%B %d, %Y')}"
    
    # --- Redesigned HTML Email Body ---
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .header {{ background-color: #d72938; color: white; padding: 20px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .content {{ padding: 30px; }}
            .paper-item {{ display: block; text-decoration: none; margin-bottom: 20px; }}
            .paper-item img {{ max-width: 200px; max-height: 50px; display: block; margin: 0 auto 10px auto; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>Your e-Paper Digest</h1></div>
            <div class="content">
    """

    for config in NEWSPAPERS_CONFIG:
        paper_name = config["name"]
        if paper_name in found_papers:
            raw_link = found_papers[paper_name]
            try:
                file_id = raw_link.split('/d/')[1].split('/')[0]
                viewer_url = f"https://drive.google.com/file/d/{file_id}/view"
                html_body += f'<a href="{viewer_url}" class="paper-item"><img src="{config["logo"]}" alt="{paper_name} Logo"></a>'
            except IndexError:
                continue # Skip if link format is invalid

    html_body += """
            </div>
        </div>
    </body>
    </html>
    """

    # --- Sending Logic ---
    message = MIMEMultipart()
    message["From"] = sender_email
    message["To"] = ", ".join(recipients) # Join list for email header
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, recipients, message.as_string())
        print(f"✅ Email successfully sent to: {', '.join(recipients)}")
    except Exception as e:
        print(f"❌ Failed to send email: {e}")

# --- Main Execution Block ---
if __name__ == "__main__":
    print("🚀 Starting e-paper scraping process...")
    today = datetime.now().date()
    
    found_links = find_all_newspapers(today)
    
    display_date = today
    if not any(found_links.values()):
        print("\nNo papers found for today. Checking for yesterday's papers...")
        yesterday = today - timedelta(days=1)
        found_links = find_all_newspapers(yesterday)
        display_date = yesterday

    if not any(found_links.values()):
        print("\n❌ No newspapers found for today or yesterday. No email will be sent.")
    else:
        print("\n📬 Preparing to send email with found links...")
        # The script gets the recipients from the environment variable
        recipients_str = os.environ.get("RECIPIENTS", "")
        recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
        
        if recipients_list:
            send_email(recipients_list, found_links, display_date)
        else:
            print("❌ No recipient emails found in environment variables.")