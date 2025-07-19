# App.py

import streamlit as st
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import time
import streamlit.components.v1 as components

# --- Page Configuration ---
st.set_page_config(
    page_title="HT e-Paper Finder",
    page_icon="📰",
    layout="centered"
)

# --- Selenium Setup for Streamlit Cloud ---
@st.cache_resource
def get_driver():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium" 
    
    service = Service(executable_path="/usr/bin/chromedriver")
    
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- Backend Function using Selenium ---
def get_epaper_link_for_date(target_date, status_log):
    driver = None
    try:
        driver = get_driver()
        target_date_str = target_date.strftime('%d-%m-%Y')
        page_url = "https://epaperwave.com/hindustan-times-epaper-pdf-today/"
        
        status_log.write(f"🤖 Launching virtual browser for **{target_date.strftime('%B %d, %Y')}**...")
        
        driver.get(page_url)
        
        time.sleep(5) 
        
        html_content = driver.page_source
        status_log.write("✅ Virtual browser successfully loaded the page.")
        
    except Exception as e:
        status_log.write(f"❌ Browser automation failed. Error: {e}")
        if driver:
            driver.quit()
        return None

    # --- THIS IS THE CORRECTED LINE ---
    soup = BeautifulSoup(html_content, 'html.parser')
    
    paragraphs = soup.find_all('p', class_='has-text-align-center')
    for p in paragraphs:
        if p.get_text(strip=True).startswith(target_date_str):
            link_tag = p.find('a')
            if link_tag and link_tag.has_attr('href'):
                status_log.write(f"✅ Found the link for **{target_date.strftime('%B %d, %Y')}**!")
                return link_tag['href']

    status_log.write(f"🟡 Paper for **{target_date.strftime('%B %d, %Y')}** not found on the page.")
    return None


# --- Main App ---
st.title("📰 Hindustan Times e-Paper Finder")

found_link = None
found_date = None

with st.status("🚀 Initializing process...", expanded=True) as status:
    today = datetime.now().date()
    link = get_epaper_link_for_date(today, status)
    if link:
        found_link = link
        found_date = today

    if not found_link:
        status.write("---")
        yesterday = today - timedelta(days=1)
        link = get_epaper_link_for_date(yesterday, status)
        if link:
            found_link = link
            found_date = yesterday

# --- Redirect or Show Error ---
if found_link:
    try:
        file_id = found_link.split('/d/')[1].split('/')[0]
        viewer_url = f"https://drive.google.com/file/d/{file_id}/view"

        st.success(f"✅ Success! Found the e-paper for **{found_date.strftime('%B %d, %Y')}**.")
        st.info("Redirecting you to the newspaper now...")
        time.sleep(2) 

        components.html(
            f'<script>window.location.replace("{viewer_url}");</script>',
            height=0
        )
    except IndexError:
        st.error("The link found was not a valid Google Drive link.")
else:
    st.error("Sorry, the e-paper for today or yesterday could not be found.")