import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options

from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

from playwright.sync_api import sync_playwright

from bs4 import BeautifulSoup
import pandas as pd
import time






def setup_page():
    st.set_page_config(
        page_title="Race Timing Scraper",
        page_icon="✨",
        layout="centered",
        initial_sidebar_state="expanded"
    )
    st.title("Race Timing Data Scraper")
 
    # Sidebar for API Key and User Info
    st.sidebar.header("About App")
    st.sidebar.markdown('This is an app that scrapes result data from FIS races created by <a href="https://ai.jdavis.xyz" target="_blank">0xjdavis</a>.', unsafe_allow_html=True)
     
    # Calendly
    st.sidebar.markdown("""
        <hr />
        <center>
        <div style="border-radius:8px;padding:8px;background:#fff";width:100%;">
        <img src="https://avatars.githubusercontent.com/u/98430977" alt="Oxjdavis" height="100" width="100" border="0" style="border-radius:50%"/>
        <br />
        <span style="height:12px;width:12px;background-color:#77e0b5;border-radius:50%;display:inline-block;"></span> <b style="color:#31333F">I'm available for new projects!</b><br />
        <a href="https://calendly.com/0xjdavis" target="_blank"><button style="background:#126ff3;color:#fff;border: 1px #126ff3 solid;border-radius:8px;padding:8px 16px;margin:10px 0">Schedule a call</button></a><br />
        </div>
        </center>
        <br />
    """, unsafe_allow_html=True)
    
    # Copyright
    st.sidebar.caption("©️ Copyright 2024 J. Davis") 

    
    return st.empty()
    
def setup_selenium():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.binary_location = "/usr/bin/chromium-browser"
    
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        st.error(f"Error setting up Chrome driver: {str(e)}")
        return None
        
def setup_browser():
    try:
        playwright = sync_playwright().start()
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page()
        return playwright, browser, page
    except Exception as e:
        st.error(f"Error setting up browser: {str(e)}")
        return None, None, None

def fetch_data(page, url):
    try:
        page.goto(url)
        page.wait_for_selector('.compact-styled-table', timeout=10000)
        return page.content()
    except Exception as e:
        st.error(f"Error fetching data: {str(e)}")
        return None



def parse_race_data(html_content):
    soup = BeautifulSoup(html_content, 'html.parser')
    
    if st.session_state.debug_mode:
        st.text("Parsing HTML content...")
    
    # Find all tables with the race data
    tables = soup.find_all('table', {'class': 'compact-styled-table'})
    
    if st.session_state.debug_mode:
        st.text(f"Found {len(tables)} race data tables")
    
    if not tables:
        st.error("No race data tables found")
        return None
    
    # Process each table to find the one with race results
    for table in tables:
        rows = table.find_all('tr')
        if not rows:
            continue
            
        # Get headers from the first row
        header_row = rows[0]
        headers = [th.get_text(strip=True) for th in header_row.find_all(['th', 'td'])]
        
        # Skip tables with no proper headers
        if not headers or len(headers) < 2:
            continue
            
        if st.session_state.debug_mode:
            st.text(f"Processing table with headers: {headers}")
        
        # Extract data rows
        data_rows = []
        for row in rows[1:]:  # Skip header row
            cols = row.find_all(['td', 'th'])
            if cols:
                row_data = [col.get_text(strip=True) for col in cols]
                if any(row_data):  # Only add non-empty rows
                    data_rows.append(row_data)
        
        if data_rows:
            try:
                df = pd.DataFrame(data_rows, columns=headers)
                # Remove any empty rows or columns
                df = df.dropna(how='all').dropna(axis=1, how='all')
                return df
            except Exception as e:
                if st.session_state.debug_mode:
                    st.text(f"Error processing table: {str(e)}")
                continue
    
    st.error("No valid race data found in any table")
    return None

def main():
    container = setup_page()
    
    # Initialize session state for debug mode
    if 'debug_mode' not in st.session_state:
        st.session_state.debug_mode = False
    
    # URL input
    url = st.text_input(
        "Enter Race Timing URL",
        value="https://www.live-timing.com/race2.php?r=288556"
    )
    
    # Debug mode toggle
    st.session_state.debug_mode = st.checkbox("Enable Debug Mode", value=True)
    
    # Scraping frequency
    update_frequency = st.slider(
        "Update Frequency (seconds)",
        min_value=5,
        max_value=60,
        value=10
    )
    
    if st.button("Start Scraping"):
        if st.session_state.debug_mode:
            st.text(f"Attempting to scrape: {url}")
        
        # Setup Selenium
        driver = setup_selenium()
        if not driver:
            st.error("Failed to initialize Chrome driver")
            return
        
        try:
            # Fetch data using Selenium
            html_content = fetch_data(driver, url)
            
            if html_content:
                if st.session_state.debug_mode:
                    st.text(f"Retrieved {len(html_content)} characters of HTML")
                
                df = parse_race_data(html_content)
                
                if df is not None:
                    st.success("Data successfully scraped!")
                    
                    # Add export button and data display in columns
                    col1, col2 = st.columns([1, 3])
                    
                    with col1:
                        # Create CSV export button
                        csv_data = df.to_csv(index=False).encode('utf-8')
                        timestamp = time.strftime("%Y%m%d_%H%M%S")
                        filename = f"race_data_{timestamp}.csv"
                        
                        st.download_button(
                            label="📥 Export to CSV",
                            data=csv_data,
                            file_name=filename,
                            mime="text/csv"
                        )
                    
                    with col2:
                        # Display data
                        st.dataframe(df)
                    
                    # Basic statistics
                    st.subheader("Race Statistics")
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.metric("Total Entries", len(df))
                    
                    with col2:
                        time_columns = [col for col in df.columns if 'time' in col.lower()]
                        if time_columns:
                            try:
                                best_time = df[time_columns[0]].min()
                                st.metric("Best Time", best_time)
                            except:
                                pass
                
                else:
                    st.error("Failed to parse data from the page")
                    if st.session_state.debug_mode:
                        st.text("HTML Preview (first 1000 characters):")
                        st.code(html_content[:1000], language='html')
        
        finally:
            # Clean up
            driver.quit()

if __name__ == "__main__":
    main()
