import sys
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(options=chrome_options)
    except Exception as e:
        print(f"Failed to start Chrome WebDriver: {e}")
        try:
            print("Trying Edge...")
            from selenium.webdriver.edge.options import Options as EdgeOptions
            edge_options = EdgeOptions()
            edge_options.add_argument("--headless")
            driver = webdriver.Edge(options=edge_options)
        except Exception as e2:
            print(f"Failed to start Edge WebDriver: {e2}")
            return
            
    print("Navigating to http://127.0.0.1:8000/ ...")
    driver.get("http://127.0.0.1:8000/")
    
    print("Page Title:", driver.title)
    print("Page HTML:", driver.page_source[:500])
    
    print("\n--- Browser Console Logs ---")
    for entry in driver.get_log('browser'):
        print(entry)
        
    driver.quit()

if __name__ == "__main__":
    main()
