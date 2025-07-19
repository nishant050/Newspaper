import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import concurrent.futures

# --- Configuration ---
# This section now has the correct URLs restored.
NEWSPAPERS_CONFIG = [
    {
        "name": "Hindustan Times",
        "url": "https://epaperwave.com/hindustan-times-epaper-pdf-today/",
        "logo_path": "assets/hindustan_times.png",
        "logo_cid": "ht_logo"
    },
    {
        "name": "The Times of India",
        "url": "https://epaperwave.com/the-times-of-india-epaper-pdf-download/",
        "logo_path": "assets/times_of_india.png",
        "logo_cid": "toi_logo"
    },
    {
        "name": "The Mint",
        "url": "https://epaperwave.com/download-the-mint-epaper-pdf-for-free-today/",
        "logo_path": "assets/the_mint.png",
        "logo_cid": "mint_logo"
    },
    {
        "name": "Dainik Bhaskar",
        "url": "https://epaperwave.com/dainik-bhaskar-epaper-today-pdf/",
        "logo_path": "assets/dainik_bhaskar.png",
        "logo_cid": "db_logo"
    },
    {
        "name": "Punjab Kesari",
        "url": "https://epaperwave.com/free-punjab-kesari-epaper-pdf-download-now/",
        "logo_path": "assets/punjab_kesari.png",
        "logo_cid": "pk_logo"
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
    chrome_options.binary_location = "/usr/bin/chromium-browser"
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
    sender_email = os.environ.get("SENDER_EMAIL")
    sender_password = os.environ.get("SENDER_APP_PASSWORD")
    if not sender_email or not sender_password:
        print("❌ Email credentials not found.")
        return

    subject = f"🗞️ Your Daily e-Paper Digest for {paper_date.strftime('%B %d, %Y')}"
    
    message = MIMEMultipart('related')
    message["From"] = sender_email
    message["To"] = ", ".join(recipients)
    message["Subject"] = subject
    
    msg_alternative = MIMEMultipart('alternative')
    message.attach(msg_alternative)

    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; background-color: #f4f4f4; margin: 0; padding: 20px; }}
            .container {{ max-width: 600px; margin: auto; background: #ffffff; border-radius: 8px; box-shadow: 0 4px 10px rgba(0,0,0,0.1); }}
            .header {{ background-color: #d72938; color: white; padding: 20px; text-align: center; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
            .header h1 {{ margin: 0; font-size: 28px; }}
            .content {{ padding: 30px; display: flex; flex-wrap: wrap; justify-content: space-around; }}
            .paper-item {{ text-decoration: none; margin-bottom: 25px; width: 45%; }}
            .logo-container {{
                height: 80px;
                display: flex;
                align-items: center;
                justify-content: center;
                border: 1px solid #e0e0e0;
                border-radius: 6px;
                padding: 10px;
                transition: box-shadow 0.2s;
            }}
            .logo-container:hover {{ box-shadow: 0 2px 8px rgba(0,0,0,0.15); }}
            .logo-container img {{
                max-width: 100%;
                max-height: 100%;
                object-fit: contain;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header"><h1>Your e-Paper Digest</h1></div>
            <div class="content">
    """

    image_attachments = {}
    for config in NEWSPAPERS_CONFIG:
        paper_name = config["name"]
        if paper_name in found_papers:
            raw_link = found_papers[paper_name]
            try:
                file_id = raw_link.split('/d/')[1].split('/')[0]
                viewer_url = f"https://drive.google.com/file/d/{file_id}/view"
                html_body += f'<a href="{viewer_url}" class="paper-item"><div class="logo-container"><img src="cid:{config["logo_cid"]}"></div></a>'
                
                with open(config["logo_path"], 'rb') as f:
                    image_attachments[config["logo_cid"]] = f.read()
            except (IndexError, FileNotFoundError):
                continue
    
    html_body += """
            </div>
        </div>
    </body>
    </html>
    """
    
    msg_alternative.attach(MIMEText(html_body, 'html'))

    for cid, img_data in image_attachments.items():
        img = MIMEImage(img_data)
        img.add_header('Content-ID', f'<{cid}>')
        message.attach(img)
        
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
        recipients_str = os.environ.get("RECIPIENTS", "")
        recipients_list = [email.strip() for email in recipients_str.split(',') if email.strip()]
        if recipients_list:
            send_email(recipients_list, found_links, display_date)
        else:
            print("❌ No recipient emails found in environment variables.")