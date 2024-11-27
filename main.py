import json
from concurrent.futures import ThreadPoolExecutor
import requests
from fastapi import FastAPI, Request, HTTPException
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from typing import List, Dict

# FastAPI application
app = FastAPI()

# Utility function to convert Persian numbers to English
def persian_to_english(persian_number: str) -> str:
    persian_to_english_dict = {
        '۰': '0', '۱': '1', '۲': '2', '۳': '3', '۴': '4',
        '۵': '5', '۶': '6', '۷': '7', '۸': '8', '۹': '9'
    }
    return ''.join(persian_to_english_dict.get(char, char) for char in persian_number)

# Configure Selenium WebDriver
def configure_webdriver() -> webdriver.Chrome:
    options = Options()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--window-size=1920,1080')
    options.binary_location = "/path/to/chrome"  # Update with your Chrome binary path
    chrome_service = Service("/path/to/chromedriver")  # Update with your ChromeDriver path
    return webdriver.Chrome(service=chrome_service, options=options)

# Search for product prices on Torob
def search_torob(product_name: str) -> List[int]:
    driver = configure_webdriver()
    try:
        driver.get(f"https://torob.com/search/?query={product_name}")
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, 'div.cards > div:nth-of-type(1) a'))
        )
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        result_link = "https://torob.com" + soup.select_one('div.cards > div:nth-of-type(1) a').get('href')
        driver.get(result_link)

        # Expand price list
        button = driver.find_elements(By.CSS_SELECTOR, '.show-more-btn, .online-show-more-btn')
        if button:
            driver.execute_script("arguments[0].click();", button[0])
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'div.price-credit-btn > div.price-credit > a.price'))
            )

        # Extract prices
        prices = [
            int(persian_to_english(price.text.strip().replace(' تومان', '').replace(',', '')).strip())
            for price in BeautifulSoup(driver.page_source, 'html.parser').select('div.price-credit-btn > div.price-credit > a.price')
            if "ناموجود" not in price.text
        ]
        return prices
    except Exception as e:
        print(f"Error in search_torob: {e}")
        return []
    finally:
        driver.quit()

# Process prices based on strategy
def process_prices(prices: List[int], strategy: str) -> int:
    if not prices:
        raise ValueError("No prices available for processing.")
    unique_prices = sorted(set(prices))
    if strategy == "nofoozi":
        return min(unique_prices)
    elif strategy == "reghabati":
        avg_price = sum(unique_prices) / len(unique_prices)
        return int(-(-avg_price // 1000) * 1000)  # Round up to the nearest 1000
    else:
        raise ValueError(f"Unknown strategy: {strategy}")

# Fetch and save prices for a product
def fetch_and_save_price(product_info: Dict, strategy: str, product_prices: Dict):
    try:
        product_id = product_info["id"]
        product_name = product_info["name"]
        prices = search_torob(product_name)
        product_prices[product_id] = process_prices(prices, strategy)
    except Exception as e:
        print(f"Error processing product {product_info}: {e}")

@app.post("/upload/")
async def upload_products(request: Request):
    try:
        data = await request.json()
        products = data.get("productInfo", {})
        strategy = data.get("strategy", [{}])[0].get("strategy", None)

        if not products or not strategy:
            raise HTTPException(status_code=400, detail="Invalid data format.")

        product_prices = {}
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [
                executor.submit(fetch_and_save_price, product_info, strategy, product_prices)
                for product_info in products.values()
            ]
            for future in futures:
                future.result()

        response = requests.post(
            "http://example.com/wp-json/custom/v1/update_product_prices",
            headers={'Content-Type': 'application/json'},
            json=product_prices
        )
        if response.status_code != 200:
            raise HTTPException(status_code=response.status_code, detail=response.text)

        return {"message": "Product prices updated successfully!"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
