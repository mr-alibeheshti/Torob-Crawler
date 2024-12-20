# Torob Price Crawler API

This project is a **web scraping** built using FastAPI and Selenium to fetch and process product prices from the [Torob](https://torob.com) website. It allows uploading product data via a POST request, processes prices based on a strategy, and updates prices on a WordPress website.

---

## Features

- **Web scraping**: Automates fetching product prices from Torob.
- **Price strategies**: Supports two pricing strategies:
  - `nofoozi`: Returns the lowest price.
  - `reghabati`: Calculates the average price rounded up to the nearest 1000.
- **Concurrent processing**: Uses multithreading for efficient scraping of multiple products.
- **WordPress integration**: Sends updated product prices to a WordPress endpoint.

---

## Requirements

### Python Libraries
Install the following dependencies using `pip`:

```plaintext
fastapi
uvicorn
selenium
beautifulsoup4
requests
