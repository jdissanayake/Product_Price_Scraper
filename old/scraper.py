import time
import random
import requests
import re
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

from models import SearchResult, get_default_retailers
from parsers import GoogleParser, RetailerParser
from utils import random_delay, format_search_term, get_random_user_agent, get_request_headers

class PlantPriceScraper:
    """Main scraper class that handles both Selenium and BeautifulSoup scraping approaches"""
    
    def __init__(self, logger=None):
        self.logger = logger or (lambda msg: None)  # Default logger does nothing
        self.driver = None
        self.running = False
        self.paused_for_captcha = False
        self.google_parser = GoogleParser(logger=self.logger)
        self.retailers = get_default_retailers()
    
    def start(self):
        """Initialize the scraper"""
        self.running = True
        self.paused_for_captcha = False
    
    def stop(self):
        """Stop the scraper"""
        self.running = False
        self.close_driver()
    
    def setup_driver(self):
        """Set up the Selenium WebDriver"""
        self.logger("Setting up browser...")
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--window-size=1200,800")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument(f"user-agent={get_random_user_agent()}")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.logger("Browser setup complete.")
    
    def detect_captcha(self):
        """Detect if Google is showing a CAPTCHA or verification page"""
        try:
            captcha_indicators = [
                "//form[contains(@action, 'CaptchaRedirect')]",
                "//input[@id='captcha']",
                "//div[contains(text(), 'unusual traffic')]",
                "//div[contains(text(), 'verify you are a human')]",
                "//div[@id='recaptcha']",
                "//iframe[contains(@src, 'recaptcha')]",
                "//h1[contains(text(), 'Before you continue')]"
            ]
            
            for indicator in captcha_indicators:
                elements = self.driver.find_elements(By.XPATH, indicator)
                if elements:
                    return True
            
            page_title = self.driver.title.lower()
            page_text = self.driver.find_element(By.TAG_NAME, "body").text.lower()
            
            captcha_phrases = [
                "verify", "robot", "captcha", "unusual traffic", 
                "verify you're a human", "security check", "automated query"
            ]
            
            if any(phrase in page_title for phrase in captcha_phrases):
                return True
                
            if any(phrase in page_text for phrase in captcha_phrases):
                return True
                
            return False
            
        except Exception as e:
            self.logger(f"Error checking for CAPTCHA: {str(e)}")
            return False
    
    def set_paused_for_captcha(self, paused):
        """Set the paused_for_captcha flag"""
        self.paused_for_captcha = paused
    
    def search_plant_selenium(self, plant_name):
        """Search for a plant price using Selenium browser automation"""
        try:
            # Random delay
            random_delay(2, 5, self.logger)
            
            # Construct search URL
            search_term = format_search_term(plant_name)
            url = f"https://www.google.com.au/search?q={search_term}&gl=au&hl=en&num=30"  # Increased results per page
            
            self.logger(f"Searching Google for: {plant_name}")
            self.driver.get(url)
            
            # Check if there's a CAPTCHA
            if self.detect_captcha():
                self.logger("CAPTCHA detected!")
                self.paused_for_captcha = True
                return [SearchResult(
                    plant_name=plant_name,
                    price="Paused for CAPTCHA", 
                    source="Google"
                )]
            
            # Wait for results to load
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
            except:
                self.logger("No search results found or page structure changed")
                return [SearchResult(
                    plant_name=plant_name,
                    price="No results", 
                    source="Google"
                )]
            
            # Get the page HTML
            page_html = self.driver.page_source
            
            # Use BeautifulSoup for parsing
            soup = BeautifulSoup(page_html, 'html.parser')
            
            # First source: Direct retailers (both from search results and direct queries)
            retailer_results = self.search_direct_retailers(plant_name)
            
            # Second source: Google results (with enhanced meta data extraction)
            google_results = self.google_parser.extract_prices_from_soup(soup, plant_name)
            
            # Third source: Marketplaces (specifically eBay/Amazon)
            marketplace_results = self.search_online_marketplaces(plant_name, priority_marketplaces=True)
            
            # Combine results ensuring we get different sources
            results = []
            
            # First, add retailer results
            results.extend(retailer_results)
            
            # Next, add unique Google results
            existing_sources = {r.source for r in results}
            for result in google_results:
                if result.source not in existing_sources:
                    results.append(result)
                    existing_sources.add(result.source)
            
            # Finally, ensure at least one marketplace result (if we have less than 3 results)
            if len(results) < 3 and marketplace_results:
                for result in marketplace_results:
                    if result.source not in existing_sources:
                        results.append(result)
                        existing_sources.add(result.source)
                        if len(results) >= 3:
                            break
            
            # If we still don't have 3 results, try specialty sites
            if len(results) < 3:
                specialty_results = self.search_specialty_sites(plant_name)
                for result in specialty_results:
                    if result.source not in existing_sources:
                        results.append(result)
                        existing_sources.add(result.source)
                        if len(results) >= 3:
                            break
            
            return results
            
        except Exception as e:
            self.logger(f"Error in Selenium search: {str(e)}")
            return [SearchResult(
                plant_name=plant_name,
                price="Error", 
                source=f"Error: {str(e)}"
            )]
    
    def search_plant_bs4(self, plant_name):
        """Search for a plant price using direct requests and BeautifulSoup"""
        try:
            # Random delay
            random_delay(1, 3, self.logger)
            
            # Construct search URL
            search_term = format_search_term(plant_name)
            url = f"https://www.google.com.au/search?q={search_term}&gl=au&hl=en&num=30"  # Increased results per page
            
            self.logger(f"Searching Google for: {plant_name}")
            
            # Make the request
            response = requests.get(url, headers=get_request_headers(), timeout=10)
            
            # Initialize results
            retailer_results = []
            google_results = []
            marketplace_results = []
            
            # Process Google search results
            if response.status_code != 200:
                self.logger(f"Google search failed with status code: {response.status_code}")
            else:
                # Parse the HTML
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Check for CAPTCHA
                if "unusual traffic" in soup.text.lower() or "captcha" in soup.text.lower() or "verify you're a human" in soup.text.lower():
                    self.logger("CAPTCHA detected in BS4 search. Trying direct retailer websites...")
                else:
                    # Extract results with enhanced meta data extraction
                    google_results = self.google_parser.extract_prices_from_soup(soup, plant_name)
            
            # First source: Direct retailers
            retailer_results = self.search_direct_retailers(plant_name)
            
            # Third source: Specifically target eBay/Amazon for third price
            marketplace_results = self.search_online_marketplaces(plant_name, priority_marketplaces=True)
            
            # Combine results ensuring we get different sources
            results = []
            
            # First, add retailer results
            results.extend(retailer_results)
            
            # Next, add unique Google results
            existing_sources = {r.source for r in results}
            for result in google_results:
                if result.source not in existing_sources:
                    results.append(result)
                    existing_sources.add(result.source)
            
            # Finally, ensure at least one marketplace result (if we have less than 3 results)
            if len(results) < 3 and marketplace_results:
                for result in marketplace_results:
                    if result.source not in existing_sources:
                        results.append(result)
                        existing_sources.add(result.source)
                        if len(results) >= 3:
                            break
            
            # If we still don't have 3 results, try specialty sites
            if len(results) < 3:
                specialty_results = self.search_specialty_sites(plant_name)
                for result in specialty_results:
                    if result.source not in existing_sources:
                        results.append(result)
                        existing_sources.add(result.source)
                        if len(results) >= 3:
                            break
            
            return results
            
        except Exception as e:
            self.logger(f"Error in BS4 search: {str(e)}")
            # Still try direct retailers even if there's an error
            return self.search_direct_retailers(plant_name)
    
    def search_direct_retailers(self, plant_name):
        """Search specific retailer websites directly"""
        results = []
        
        for retailer in self.retailers:
            try:
                self.logger(f"Checking {retailer.name}...")
                time.sleep(random.uniform(1, 2))
                
                # Get search URL for this retailer
                url = retailer.get_search_url(plant_name.replace(' ', '+'))
                
                # Make the request
                response = requests.get(url, headers=get_request_headers(), timeout=10)
                
                if response.status_code == 200:
                    # Parse the result
                    parser = RetailerParser(retailer, logger=self.logger)
                    result = parser.parse_product_page(response.text, plant_name)
                    
                    if result:
                        results.append(result)
                    
            except Exception as e:
                self.logger(f"Error searching {retailer.name}: {str(e)}")
        
        # If no results from any retailer, return a not found result
        if not results:
            results.append(SearchResult(
                plant_name=plant_name,
                price="Not found",
                source="No price found from any retailer"
            ))
        
        return results
    
    def search_bing(self, plant_name):
        """Search Bing for plant prices"""
        try:
            self.logger(f"Searching Bing for: {plant_name}")
            
            # Construct search URL for Bing
            search_term = format_search_term(plant_name, include_buy=True)
            url = f"https://www.bing.com/search?q={search_term}&cc=au"
            
            # Make the request
            response = requests.get(url, headers=get_request_headers(), timeout=10)
            
            if response.status_code != 200:
                self.logger(f"Bing search failed with status code: {response.status_code}")
                return []
            
            # Parse the HTML
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Extract prices - try to find product listings first
            results = []
            price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
            
            # Look for Bing Shopping results
            shopping_results = soup.select('div.b_ad li.b_adLastChild, div.cico')
            for result in shopping_results:
                result_text = result.get_text()
                price_match = re.search(price_pattern, result_text)
                if price_match and any(word.lower() in result_text.lower() for word in plant_name.split()):
                    # Try to find the link
                    link = result.find('a')
                    source = "Bing Shopping"
                    if link and link.has_attr('href'):
                        source = f"Bing Shopping: {link['href']}"
                    
                    results.append(SearchResult(
                        plant_name=plant_name,
                        price=price_match.group(0),
                        source=source
                    ))
            
            # Look for organic results with meta title/description
            organic_results = soup.select('li.b_algo')
            for result in organic_results[:10]:  # Look at top 10 results
                # Check title and meta description
                title = result.select_one('h2')
                meta = result.select_one('p')
                
                if title:
                    title_text = title.get_text()
                    price_match = re.search(price_pattern, title_text)
                    if price_match and any(word.lower() in title_text.lower() for word in plant_name.split()):
                        link = title.find('a')
                        source = "Bing Result"
                        if link and link.has_attr('href'):
                            source = f"Bing Result: {link['href']}"
                        
                        results.append(SearchResult(
                            plant_name=plant_name,
                            price=price_match.group(0),
                            source=source
                        ))
                        continue
                
                if meta:
                    meta_text = meta.get_text()
                    price_match = re.search(price_pattern, meta_text)
                    if price_match and any(word.lower() in meta_text.lower() for word in plant_name.split()):
                        link = title.find('a') if title else None
                        source = "Bing Result"
                        if link and link.has_attr('href'):
                            source = f"Bing Result: {link['href']}"
                        
                        results.append(SearchResult(
                            plant_name=plant_name,
                            price=price_match.group(0),
                            source=source
                        ))
            
            return results[:3]  # Return top 3 results
            
        except Exception as e:
            self.logger(f"Error in Bing search: {str(e)}")
            return []
    
    def search_specialty_sites(self, plant_name):
        """Search specialty plant websites directly"""
        self.logger(f"Searching specialty plant sites for: {plant_name}")
        
        specialty_sites = [
            {
                "name": "Plantary",
                "url": f"https://plantary.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-grid-item",
                "price_selector": "span.price"
            },
            {
                "name": "Plant Farm",
                "url": f"https://www.plant-farm.com.au/search?type=product&q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-item",
                "price_selector": "span.price"
            },
            {
                "name": "Little Succers",
                "url": f"https://littlesuccers.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-details",
                "price_selector": "span.price"
            },
            {
                "name": "Plants in a Box",
                "url": f"https://plantsinabox.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.productitem",
                "price_selector": "span.price"
            },
            {
                "name": "Seed World",
                "url": f"https://seedworld.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product",
                "price_selector": "span.price"
            },
            # Additional specialty sites
            {
                "name": "The Succulent Garden",
                "url": f"https://thesucculentgarden.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.grid-product",
                "price_selector": "span.price"
            },
            {
                "name": "Collectors Corner",
                "url": f"https://collectorscorner.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-item",
                "price_selector": "span.price"
            },
            {
                "name": "Huge Cactus",
                "url": f"https://hugecactus.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-item",
                "price_selector": "span.price"
            },
            {
                "name": "Hello Succulents",
                "url": f"https://hellosucculents.com.au/?s={plant_name.replace(' ', '+')}&post_type=product",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "li.product",
                "price_selector": "span.woocommerce-Price-amount"
            }
        ]
        
        results = []
        
        for site in specialty_sites:
            try:
                self.logger(f"Checking {site['name']}...")
                random_delay(1, 2, self.logger)
                
                response = requests.get(site["url"], headers=get_request_headers(), timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for products
                    products = soup.select(site["product_selector"])
                    self.logger(f"Found {len(products)} products on {site['name']}")
                    
                    for product in products[:3]:  # Check first 3 products
                        # Try to get price using the specific selector first
                        price_element = None
                        if "price_selector" in site:
                            price_element = product.select_one(site["price_selector"])
                        
                        if price_element:
                            price_text = price_element.get_text().strip()
                            price_match = re.search(site["price_pattern"], price_text)
                        else:
                            product_text = product.get_text().strip()
                            price_match = re.search(site["price_pattern"], product_text)
                            
                        # Check if product is relevant and has a price
                        if price_match and any(word.lower() in product.get_text().lower() for word in plant_name.split()):
                            # Get URL if possible
                            product_url = site["url"]
                            a_tags = product.select('a')
                            if a_tags and a_tags[0].has_attr('href'):
                                href = a_tags[0]['href']
                                if href.startswith('/'):
                                    domain = re.search(r'https?://(?:www\.)?([^/]+)', site["url"])
                                    if domain:
                                        product_url = f"https://{domain.group(1)}{href}"
                                else:
                                    product_url = href
                            
                            self.logger(f"Found {site['name']} product with price: {price_match.group(0)}")
                            results.append(SearchResult(
                                plant_name=plant_name,
                                price=price_match.group(0),
                                source=f"{site['name']} - {product_url}"
                            ))
                            break  # Only get one result per specialty site
                    
            except Exception as e:
                self.logger(f"Error searching {site['name']}: {str(e)}")
        
        return results
    
    def search_online_marketplaces(self, plant_name, priority_marketplaces=False):
        """
        Search online marketplaces for plant prices
        
        Args:
            plant_name: Name of the plant to search for
            priority_marketplaces: If True, prioritize eBay and Amazon results
        """
        self.logger(f"Searching online marketplaces for: {plant_name}")
        
        # If we want to prioritize eBay and Amazon, put them first
        if priority_marketplaces:
            marketplaces = [
                {
                    "name": "eBay Australia",
                    "url": f"https://www.ebay.com.au/sch/i.html?_nkw={plant_name.replace(' ', '+')}+plant&_sacat=0",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "li.s-item",
                    "title_selector": "div.s-item__title",
                    "price_selector": "span.s-item__price",
                    "link_selector": "a.s-item__link"
                },
                {
                    "name": "Amazon Australia",
                    "url": f"https://www.amazon.com.au/s?k={plant_name.replace(' ', '+')}+plant",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "div.s-result-item[data-component-type='s-search-result']",
                    "title_selector": "h2 a span",
                    "price_selector": "span.a-price-whole",
                    "link_selector": "h2 a.a-link-normal"
                },
                {
                    "name": "Etsy",
                    "url": f"https://www.etsy.com/au/search?q={plant_name.replace(' ', '+')}+plant",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "div.wt-grid__item-xs-6",
                    "title_selector": "h3",
                    "price_selector": "span.currency-value",
                    "link_selector": "a.listing-link"
                }
            ]
        else:
            marketplaces = [
                {
                    "name": "Etsy",
                    "url": f"https://www.etsy.com/au/search?q={plant_name.replace(' ', '+')}+plant",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "div.wt-grid__item-xs-6",
                    "title_selector": "h3",
                    "price_selector": "span.currency-value",
                    "link_selector": "a.listing-link"
                },
                {
                    "name": "eBay Australia",
                    "url": f"https://www.ebay.com.au/sch/i.html?_nkw={plant_name.replace(' ', '+')}+plant&_sacat=0",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "li.s-item",
                    "title_selector": "div.s-item__title",
                    "price_selector": "span.s-item__price",
                    "link_selector": "a.s-item__link"
                },
                {
                    "name": "Amazon Australia",
                    "url": f"https://www.amazon.com.au/s?k={plant_name.replace(' ', '+')}+plant",
                    "price_pattern": r'\$\d+(?:\.\d{2})?',
                    "product_selector": "div.s-result-item[data-component-type='s-search-result']",
                    "title_selector": "h2 a span",
                    "price_selector": "span.a-price-whole",
                    "link_selector": "h2 a.a-link-normal"
                }
            ]
        
        results = []
        
        for marketplace in marketplaces:
            try:
                self.logger(f"Checking {marketplace['name']}...")
                random_delay(1, 2, self.logger)
                
                # Set specific headers for marketplaces to avoid bot detection
                headers = get_request_headers()
                if "ebay" in marketplace["url"]:
                    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                    headers["Referer"] = "https://www.ebay.com.au/"
                elif "amazon" in marketplace["url"]:
                    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                    headers["Referer"] = "https://www.amazon.com.au/"
                elif "etsy" in marketplace["url"]:
                    headers["Accept"] = "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8"
                    headers["Referer"] = "https://www.etsy.com/"
                
                response = requests.get(marketplace["url"], headers=headers, timeout=15)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    # Look for products
                    products = soup.select(marketplace["product_selector"])
                    self.logger(f"Found {len(products)} products on {marketplace['name']}")
                    
                    found_products = 0
                    for product in products[:10]:  # Check first 10 products
                        # Try specific selectors first for more accurate results
                        title_elem = product.select_one(marketplace["title_selector"])
                        price_elem = product.select_one(marketplace["price_selector"])
                        link_elem = product.select_one(marketplace["link_selector"])
                        
                        if title_elem and price_elem:
                            title_text = title_elem.get_text().strip()
                            price_text = price_elem.get_text().strip()
                            
                            # Improved relevance check
                            plant_words = [word.lower() for word in plant_name.split() if len(word) > 2]
                            title_lower = title_text.lower()
                            
                            # Count matching words for better relevance
                            matching_words = sum(1 for word in plant_words if word in title_lower)
                            is_relevant = matching_words >= len(plant_words) * 0.5  # At least half the words match
                            
                            if is_relevant:
                                # Extract price using regex if needed
                                price_match = re.search(marketplace["price_pattern"], price_text)
                                if not price_match:
                                    price_match = re.search(marketplace["price_pattern"], product.get_text().strip())
                                
                                if price_match:
                                    product_url = marketplace["url"]
                                    if link_elem and link_elem.has_attr('href'):
                                        product_url = link_elem['href']
                                        if not product_url.startswith('http'):
                                            # Handle relative URLs
                                            if "ebay" in marketplace["url"]:
                                                product_url = f"https://www.ebay.com.au{product_url}"
                                            elif "amazon" in marketplace["url"]:
                                                product_url = f"https://www.amazon.com.au{product_url}"
                                            elif "etsy" in marketplace["url"]:
                                                product_url = f"https://www.etsy.com{product_url}"
                                    
                                    self.logger(f"Found {marketplace['name']} product: {title_text} - {price_match.group(0)}")
                                    results.append(SearchResult(
                                        plant_name=plant_name,
                                        price=price_match.group(0),
                                        source=f"{marketplace['name']} - {title_text[:30]}... - {product_url}"
                                    ))
                                    found_products += 1
                                    if found_products >= 2 and priority_marketplaces:  # Get two results per marketplace when prioritizing
                                        break
                                    elif found_products >= 1 and not priority_marketplaces:  # Otherwise just get one
                                        break
                        
                        # If specific selectors failed, try generic text search as fallback
                        if found_products == 0:
                            product_text = product.get_text()
                            plant_words = [word.lower() for word in plant_name.split() if len(word) > 2]
                            product_lower = product_text.lower()
                            
                            # Count matching words for better relevance
                            matching_words = sum(1 for word in plant_words if word in product_lower)
                            is_relevant = matching_words >= len(plant_words) * 0.5  # At least half the words match
                            
                            if is_relevant:
                                price_match = re.search(marketplace["price_pattern"], product_text)
                                if price_match:
                                    a_tags = product.select('a')
                                    product_url = marketplace["url"]
                                    if a_tags and a_tags[0].has_attr('href'):
                                        product_url = a_tags[0]['href']
                                    
                                    # Extract a simple title from the product text
                                    title_extract = product_text[:50].strip().replace('\n', ' ')
                                    
                                    results.append(SearchResult(
                                        plant_name=plant_name,
                                        price=price_match.group(0),
                                        source=f"{marketplace['name']} - {title_extract}... - {product_url}"
                                    ))
                                    found_products += 1
                                    if found_products >= 2 and priority_marketplaces:
                                        break
                                    elif found_products >= 1 and not priority_marketplaces:
                                        break
                    
            except Exception as e:
                self.logger(f"Error searching {marketplace['name']}: {str(e)}")
        
        # For priority marketplaces, make sure results are eBay/Amazon first if available
        if priority_marketplaces and results:
            priority_results = []
            other_results = []
            
            for result in results:
                if "eBay" in result.source or "Amazon" in result.source:
                    priority_results.append(result)
                else:
                    other_results.append(result)
            
            # Return priority results first, then others
            return priority_results + other_results
        else:
            return results
    
    def close_driver(self):
        """Close the Selenium WebDriver if it exists"""
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.logger("Browser closed.")
            except Exception as e:
                self.logger(f"Error closing browser: {str(e)}")