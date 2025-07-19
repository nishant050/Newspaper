# App.py 

import streamlit as st 
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

# --- Page & App Configuration --- 
st.set_page_config( 
    page_title="e-Paper Hub", 
    page_icon="🗞️", 
    layout="centered" 
) 

NEWSPAPERS_TO_SCRAPE = [ 
    {"name": "Hindustan Times", "url": "https://epaperwave.com/hindustan-times-epaper-pdf-today/"}, 
    {"name": "The Times of India", "url": "https://epaperwave.com/the-times-of-india-epaper-pdf-download/"}, 
    {"name": "The Mint", "url": "https://epaperwave.com/download-the-mint-epaper-pdf-for-free-today/"}, 
    {"name": "Dainik Bhaskar", "url": "https://epaperwave.com/dainik-bhaskar-epaper-today-pdf/"}, 
    {"name": "Punjab Kesari", "url": "https://epaperwave.com/free-punjab-kesari-epaper-pdf-download-now/"} 
] 

# --- Session State Initialization --- 
if 'found_links' not in st.session_state: 
    st.session_state.found_links = {} 
if 'last_scrape_date' not in st.session_state: 
    st.session_state.last_scrape_date = None 

# --- Selenium & Scraping Functions --- 
@st.cache_resource
def create_driver(): 
    """Sets up and returns a new Selenium WebDriver instance.""" 
    chrome_options = Options() 
    chrome_options.add_argument("--headless") 
    chrome_options.add_argument("--no-sandbox") 
    chrome_options.add_argument("--disable-dev-shm-usage") 
    chrome_options.add_argument("--disable-gpu") 
    # The following two lines are for Streamlit Community Cloud compatibility
    # You might need to adjust them for your local environment
    chrome_options.binary_location = "/usr/bin/chromium" 
    service = Service(executable_path="/usr/bin/chromedriver") 
    driver = webdriver.Chrome(service=service, options=chrome_options) 
    return driver 

def scrape_single_newspaper(newspaper_info, target_date): 
    driver = create_driver() 
    name, url = newspaper_info["name"], newspaper_info["url"] 
    date_str = target_date.strftime('%d-%m-%Y') 
    try: 
        driver.get(url) 
        time.sleep(3) # Wait for the page to load dynamically
        html_content = driver.page_source 
        soup = BeautifulSoup(html_content, 'html.parser') 
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

def find_all_newspapers(target_date, status_log): 
    found_links = {} 
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(NEWSPAPERS_TO_SCRAPE)) as executor: 
        future_to_newspaper = {executor.submit(scrape_single_newspaper, newspaper, target_date): newspaper for newspaper in NEWSPAPERS_TO_SCRAPE} 
        for future in concurrent.futures.as_completed(future_to_newspaper): 
            try:
                name, link = future.result() 
                if link: 
                    status_log.write(f"✅ Found: **{name}**") 
                    found_links[name] = link 
                else: 
                    status_log.write(f"🟡 Not found: {name}")
            except Exception as e:
                newspaper_name = future_to_newspaper[future]['name']
                status_log.write(f"❌ Error scraping {newspaper_name}: {e}")
    return found_links 

# --- Email Function --- 
def send_email(recipient_email, links_dict, paper_date): 
    """Constructs and sends an email with the newspaper links.""" 
    try: 
        # Get credentials from Streamlit Secrets 
        sender_email = st.secrets["SENDER_EMAIL"] 
        sender_password = st.secrets["SENDER_APP_PASSWORD"] 
        
        # Create email content 
        subject = f"Your e-Papers for {paper_date.strftime('%B %d, %Y')}" 
        
        html_body = f"<html><body><h2>Here are your e-paper links for {paper_date.strftime('%B %d, %Y')}:</h2><ul>" 
        for name, viewer_url in links_dict.items(): 
            html_body += f'<li><a href="{viewer_url}">{name}</a></li>' 
        html_body += "</ul><p>Powered by e-Paper Hub.</p></body></html>" 

        # Set up the email message 
        message = MIMEMultipart() 
        message["From"] = sender_email 
        message["To"] = recipient_email 
        message["Subject"] = subject 
        message.attach(MIMEText(html_body, "html")) 
        
        # Send the email via Gmail's SMTP server 
        with smtplib.SMTP("smtp.gmail.com", 587) as server: 
            server.starttls() 
            server.login(sender_email, sender_password) 
            server.sendmail(sender_email, recipient_email, message.as_string()) 
        
        return True 
    except Exception as e: 
        st.error(f"Failed to send email: {e}") 
        return False 

# --- Main App Logic --- 
st.title("🗞️ Daily e-Paper Hub") 

today = datetime.now().date() 

# Scrape only if the date has changed
if st.session_state.last_scrape_date != today: 
    with st.status("Finding all latest newspapers...", expanded=True) as status: 
        found_today = find_all_newspapers(today, status) 
        if not any(found_today.values()): 
            status.write("No papers found for today. Checking yesterday...") 
            yesterday = today - timedelta(days=1) 
            found_yesterday = find_all_newspapers(yesterday, status) 
            st.session_state.found_links = found_yesterday 
            st.session_state.last_scrape_date = yesterday 
        else: 
            st.session_state.found_links = found_today 
            st.session_state.last_scrape_date = today 
        status.update(label="Search complete!", state="complete") 

# --- Display Logic --- 
if not st.session_state.found_links or not any(st.session_state.found_links.values()): 
    st.warning("Could not find any newspapers for today or yesterday. The website might be updating.") 
else: 
    display_date = st.session_state.last_scrape_date 
    st.success(f"Showing newspapers found for **{display_date.strftime('%B %d, %Y')}**.") 
    
    available_papers_urls = {} 
    
    cols = st.columns(2) 
    col_index = 0 
    for name, link in sorted(st.session_state.found_links.items()): 
        if link: 
            try: 
                # Extract Google Drive file ID from the link
                file_id = link.split('/d/')[1].split('/')[0] 
                viewer_url = f"https://drive.google.com/file/d/{file_id}/view" 
                available_papers_urls[name] = viewer_url 
                
                with cols[col_index % 2]: 
                    st.link_button(f"📰 Open {name}", viewer_url, use_container_width=True) 
                col_index += 1 
            except IndexError: 
                # If the link format is unexpected, skip this paper
                continue 
    
    # --- Email Section --- 
    if available_papers_urls: 
        st.divider() 
        st.subheader("📧 Get Links by Email") 
        
        # Use the recipient from secrets as the default value for the text input 
        default_email = st.secrets.get("RECIPIENT_EMAIL", "") 
        email_input = st.text_input("Enter your email address:", value=default_email, placeholder="you@example.com") 
        
        if st.button("Email Today's Links", use_container_width=True, type="primary"): 
            if email_input: 
                with st.spinner("Sending email..."): 
                    if send_email(email_input, available_papers_urls, display_date): 
                        st.success(f"Email successfully sent to {email_input}!") 
            else: 
                st.error("Please enter a valid email address.")
