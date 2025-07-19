# App.py

import streamlit as st
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

# --- Selenium Setup ---
# FIX 1: The @st.cache_resource decorator has been REMOVED.
# This function now creates a NEW driver instance every time it's called.
def create_driver():
    """Sets up and returns a new Selenium WebDriver instance."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.binary_location = "/usr/bin/chromium"
    
    service = Service(executable_path="/usr/bin/chromedriver")
    driver = webdriver.Chrome(service=service, options=chrome_options)
    return driver

# --- Backend Scraping Functions ---

def scrape_single_newspaper(newspaper_info, target_date):
    """
    Scrapes a single newspaper URL in its own private browser instance.
    """
    driver = create_driver()  # Each thread gets its own driver.
    name = newspaper_info["name"]
    url = newspaper_info["url"]
    date_str = target_date.strftime('%d-%m-%Y')

    try:
        driver.get(url)
        time.sleep(3)
        html_content = driver.page_source
        soup = BeautifulSoup(html_content, 'html.parser')

        paragraphs = soup.find_all('p', class_='has-text-align-center')
        for p in paragraphs:
            if p.get_text(strip=True).startswith(date_str):
                link_tag = p.find('a')
                if link_tag and link_tag.has_attr('href'):
                    return name, link_tag['href']
    except Exception:
        return name, None
    finally:
        # FIX 2: Ensure the private browser instance for this thread is closed.
        if driver:
            driver.quit()
            
    return name, None

def find_all_newspapers(target_date, status_log):
    """
    Uses a thread pool to scrape all newspapers concurrently.
    """
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
            except Exception:
                status_log.write(f"❌ Error scraping one of the newspapers.")
    return found_links

# --- Main App Logic ---

st.title("🗞️ Daily e-Paper Hub")

today = datetime.now().date()

if st.session_state.last_scrape_date != today:
    with st.status("Finding all latest newspapers... This may take a moment.", expanded=True) as status:
        found_today = find_all_newspapers(today, status)
        
        if not any(found_today.values()):
             status.write("---")
             status.write("No papers found for today. Checking for yesterday's papers...")
             time.sleep(2)
             yesterday = today - timedelta(days=1)
             found_yesterday = find_all_newspapers(yesterday, status)
             st.session_state.found_links = found_yesterday
             st.session_state.last_scrape_date = yesterday
        else:
             st.session_state.found_links = found_today
             st.session_state.last_scrape_date = today

        status.update(label="Search complete!", state="complete", expanded=False)

# --- Display Logic ---

if not st.session_state.found_links:
    st.warning("Could not find any newspapers for today or yesterday.")
else:
    display_date = st.session_state.last_scrape_date
    st.success(f"Showing newspapers found for **{display_date.strftime('%B %d, %Y')}**.")
    
    available_papers = {name: link for name, link in st.session_state.found_links.items() if link}
    
    if not available_papers:
         st.warning("Process completed, but no valid newspaper links were available.")
    else:
        cols = st.columns(2)
        col_index = 0
        for name, link in sorted(available_papers.items()):
            try:
                file_id = link.split('/d/')[1].split('/')[0]
                viewer_url = f"https://drive.google.com/file/d/{file_id}/view"
                
                with cols[col_index % 2]:
                    st.link_button(f"📰 Open {name}", viewer_url, use_container_width=True)
                col_index += 1
            except IndexError:
                continue