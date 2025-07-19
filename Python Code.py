import os
import sys
import subprocess
import requests
from bs4 import BeautifulSoup
from datetime import datetime

def download_live_epaper(target_date_str=None):
    """
    Fetches the live Hindustan Times e-paper page, finds the link for a
    specific date, downloads the PDF, and opens it.

    Args:
        target_date_str (str, optional): The date to search for in 'DD-MM-YYYY' format.
                                         Defaults to the current day.
    """
    # If no date is provided, use today's date
    if not target_date_str:
        target_date_str = datetime.now().strftime('%d-%m-%Y')
    
    page_url = "https://epaperwave.com/hindustan-times-epaper-pdf-today/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    try:
        print(f"🌍 Connecting to {page_url}...")
        response = requests.get(page_url, headers=headers)
        response.raise_for_status()  # This will raise an error for bad responses (4xx or 5xx)
        html_content = response.text
        print("✅ Successfully fetched live webpage content.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to connect to the webpage. Please check your internet connection. Error: {e}")
        return

    print(f"✅ Searching for newspaper: {target_date_str}")
    
    soup = BeautifulSoup(html_content, 'lxml')
    download_link = None
    paragraphs = soup.find_all('p', class_='has-text-align-center')

    for p in paragraphs:
        # Check if the text of the paragraph starts with the target date
        if p.get_text(strip=True).startswith(target_date_str):
            link_tag = p.find('a')
            if link_tag and link_tag.has_attr('href'):
                download_link = link_tag['href']
                break

    if not download_link:
        print(f"❌ Could not find the download link for {target_date_str} on the webpage.")
        return

    print(f"🔗 Link found: {download_link}")

    try:
        file_id = download_link.split('/d/')[1].split('/')[0]
        direct_download_url = f'https://drive.google.com/uc?export=download&id={file_id}'
        print(f"🔧 Prepared direct download URL.")
    except IndexError:
        print("❌ Could not parse the Google Drive link.")
        return

    file_name = f"Hindustan_Times_{target_date_str}.pdf"
    try:
        print(f"⬇️  Downloading '{file_name}'...")
        with requests.get(direct_download_url, stream=True) as r:
            r.raise_for_status()
            with open(file_name, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    f.write(chunk)
        print(f"✅ Download complete! File saved as '{file_name}'.")
    except requests.exceptions.RequestException as e:
        print(f"❌ Failed to download the file. Error: {e}")
        return

    try:
        print(f"📖 Opening '{file_name}'...")
        filepath = os.path.abspath(file_name)
        if sys.platform == "win32":
            os.startfile(filepath)
        elif sys.platform == "darwin":
            subprocess.run(["open", filepath])
        else:
            subprocess.run(["xdg-open", filepath])
    except Exception as e:
        print(f"❌ Could not open the file. Please open it manually. Error: {e}")


if __name__ == "__main__":
    # To get today's newspaper, just run the script.
    download_live_epaper()

    # To get a paper for a specific date, pass the date string.
    # download_live_epaper(target_date_str="18-07-2025")
