import re
import json
import requests
from bs4 import BeautifulSoup
from models import SearchResult
from utils import is_relevant_result, get_request_headers

class GoogleParser:
    """Parser for Google search results"""
    
    def __init__(self, logger=None):
        self.logger = logger or (lambda msg: None)
        self.price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'  # Match prices like $10, $10.99, $1,000
    
    def extract_prices_from_soup(self, soup, plant_name):
        """
        Comprehensive price extraction method that:
        1. Checks shopping results
        2. Checks organic results with meta titles/descriptions
        3. Checks featured snippets
        4. Goes to product pages if needed
        """
        results = []
        
        # Try shopping results first (highest priority)
        self.logger("Extracting prices from shopping results...")
        shopping_results = self._extract_shopping_results(soup, plant_name)
        results.extend(shopping_results)
        
        # Try organic results with enhanced meta extraction
        self.logger("Extracting prices from organic results...")
        organic_results = self._extract_organic_results(soup, plant_name)
        results.extend(organic_results)
        
        # Try featured snippets
        self.logger("Extracting prices from featured snippets...")
        snippet_results = self._extract_featured_snippets(soup, plant_name)
        results.extend(snippet_results)
        
        # Try meta descriptions (improved)
        self.logger("Extracting prices from meta descriptions...")
        meta_results = self._extract_meta_descriptions(soup, plant_name)
        results.extend(meta_results)
        
        # If we have fewer than 3 results, try product pages
        if len(results) < 3:
            self.logger("Not enough results, checking product pages...")
            product_urls = self._find_product_urls(soup, 3 - len(results))
            for url in product_urls:
                page_results = self._scrape_product_page(url, plant_name)
                if page_results:
                    results.extend(page_results)
                    if len(results) >= 3:
                        break
        
        # Return all unique results (up to 3)
        unique_results = []
        seen_sources = set()
        
        for result in results:
            if result.source not in seen_sources:
                unique_results.append(result)
                seen_sources.add(result.source)
                if len(unique_results) >= 3:
                    break
                    
        return unique_results
        
    def _find_product_urls(self, soup, count=3):
        """Find multiple product URLs from search results"""
        urls = []
        
        # Try shopping results first
        shopping_links = soup.select('a[href*="/url?q="]')
        for link in shopping_links:
            href = link['href']
            if '/url?q=' in href and 'webcache' not in href:
                url_match = re.search(r'/url\?q=([^&]+)', href)
                if url_match:
                    urls.append(url_match.group(1))
                    if len(urls) >= count:
                        return urls
        
        # Then try organic results
        organic_links = soup.select('div.g a[href^="http"]')
        for link in organic_links:
            if link.has_attr('href'):
                urls.append(link['href'])
                if len(urls) >= count:
                    return urls
        
        return urls

    def _extract_shopping_results(self, soup, plant_name):
        """Extract prices from Google Shopping results"""
        # Updated selectors for Google Shopping
        selectors = [
            'div.sh-dlr__list-result',  # Main shopping results
            'div.commercial-unit-desktop-top',  # Old shopping results
            'div.pla-unit',  # Product listing ads
            'div[data-docid]',  # Newer shopping results
            'div.mnr-c.pla-unit'  # Alternative product ads
        ]
        
        results = []
        
        for selector in selectors:
            shopping_divs = soup.select(selector)
            for div in shopping_divs[:5]:  # Check first 5 results for better coverage
                div_text = div.get_text()
                
                # Check if relevant to our plant
                if not is_relevant_result(plant_name, div_text):
                    continue
                
                # Find price
                price_match = re.search(self.price_pattern, div_text)
                if price_match:
                    # Get source URL
                    source = "Google Shopping"
                    link = div.select_one('a')
                    if link and link.has_attr('href'):
                        href = link['href']
                        if '/url?q=' in href:
                            url_match = re.search(r'/url\?q=([^&]+)', href)
                            if url_match:
                                url = url_match.group(1)
                                # Extract domain for cleaner display
                                domain_match = re.search(r'https?://(?:www\.)?([^/]+)', url)
                                if domain_match:
                                    domain = domain_match.group(1)
                                    source = f"{domain} - {url}"
                                else:
                                    source = f"Shopping: {url}"
                    
                    results.append(SearchResult(
                        plant_name=plant_name,
                        price=price_match.group(0),
                        source=source
                    ))
        
        return results

    def _extract_organic_results(self, soup, plant_name):
        """Extract prices from organic search results with improved meta title/description extraction"""
        selectors = [
            'div.g',  # Standard organic result
            'div.tF2Cxc',  # Newer organic result
            'div[data-hveid]',  # Generic result container
            'div.yuRUbf',  # Another organic result container
            'div#search div[data-ved]'  # Generic search result
        ]
        
        results = []
        
        for selector in selectors:
            organic_results = soup.select(selector)
            for result in organic_results[:10]:  # Check more results (10 instead of 3)
                # Check title separately for better meta extraction
                title = result.select_one('h3')
                title_text = title.get_text() if title else ""
                
                # Check meta description
                meta = result.select_one('div.VwiC3b, span.aCOpRe, div[role="heading"] + div, div.IsZvec')
                meta_text = meta.get_text() if meta else ""
                
                # Combined text for general price extraction
                result_text = title_text + " " + meta_text
                
                # Check if relevant to our plant
                if not is_relevant_result(plant_name, result_text):
                    continue
                
                # Find price in title (highest priority)
                price_match = None
                if title_text:
                    price_match = re.search(self.price_pattern, title_text)
                
                # If no price in title, check meta description
                if not price_match and meta_text:
                    price_match = re.search(self.price_pattern, meta_text)
                
                # If still no price, check full text
                if not price_match:
                    price_match = re.search(self.price_pattern, result.get_text())
                
                if price_match:
                    # Get source URL
                    source = "Organic Result"
                    link = result.select_one('a')
                    if link and link.has_attr('href'):
                        url = link['href']
                        domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                        if domain:
                            source = f"{domain.group(1)} - {url}"
                    
                    # Note where the price was found for better debugging
                    price_location = ""
                    if price_match.group(0) in title_text:
                        price_location = " (found in title)"
                    elif meta_text and price_match.group(0) in meta_text:
                        price_location = " (found in meta description)"
                    
                    results.append(SearchResult(
                        plant_name=plant_name,
                        price=price_match.group(0),
                        source=source + price_location
                    ))
        
        return results

    def _extract_featured_snippets(self, soup, plant_name):
        """Extract prices from featured snippets and knowledge panels"""
        snippet_selectors = [
            'div.kp-wholepage',  # Knowledge panel
            'div.ifM9O',  # Featured snippet
            'div.V3FYCf',  # Another featured snippet type
            'div.ULSxyf',  # Rich results
            'div.hlcw0c'  # Another possible container
        ]
        
        results = []
        
        for selector in snippet_selectors:
            snippets = soup.select(selector)
            for snippet in snippets:
                snippet_text = snippet.get_text()
                
                # Check if relevant to our plant
                if not is_relevant_result(plant_name, snippet_text):
                    continue
                
                # Find all prices in the snippet
                price_matches = re.finditer(self.price_pattern, snippet_text)
                for price_match in price_matches:
                    # Try to find context for this price (nearby text)
                    price_pos = price_match.start()
                    context_start = max(0, price_pos - 50)
                    context_end = min(len(snippet_text), price_pos + 50)
                    context = snippet_text[context_start:context_end].replace('\n', ' ').strip()
                    
                    results.append(SearchResult(
                        plant_name=plant_name,
                        price=price_match.group(0),
                        source=f"Featured Snippet: {context}..."
                    ))
        
        return results

    def _extract_meta_descriptions(self, soup, plant_name):
        """Enhanced extraction of prices from meta descriptions and other metadata"""
        # Check page metadata
        meta_tags = [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'}),
            soup.find('meta', attrs={'name': 'keywords'}),
            soup.find('meta', attrs={'property': 'og:title'})
        ]
        
        results = []
        
        # Check header metadata
        for tag in meta_tags:
            if tag and tag.has_attr('content'):
                content = tag['content']
                if is_relevant_result(plant_name, content):
                    price_match = re.search(self.price_pattern, content)
                    if price_match:
                        tag_name = tag.get('name', tag.get('property', 'meta'))
                        results.append(SearchResult(
                            plant_name=plant_name,
                            price=price_match.group(0),
                            source=f"Meta {tag_name}: {content[:50]}..."
                        ))
        
        # Check for meta data in search results
        meta_selectors = [
            'div.s',  # Common meta description container
            'span.st',  # Another meta description format
            'div.VwiC3b',  # Newer meta description format
            'div[data-content-feature="1"]',  # Another potential container
            'div.IsZvec'  # Another meta container
        ]
        
        for selector in meta_selectors:
            meta_elements = soup.select(selector)
            for meta in meta_elements:
                meta_text = meta.get_text()
                if is_relevant_result(plant_name, meta_text):
                    price_match = re.search(self.price_pattern, meta_text)
                    if price_match:
                        # Try to find the associated URL
                        parent = meta.parent
                        link = None
                        for _ in range(3):  # Look up to 3 levels up
                            if parent:
                                link = parent.select_one('a[href^="http"]')
                                if link:
                                    break
                                parent = parent.parent
                        
                        source = "Meta description"
                        if link and link.has_attr('href'):
                            url = link['href']
                            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                            if domain:
                                source = f"{domain.group(1)} Meta: {meta_text[:40]}..."
                        
                        results.append(SearchResult(
                            plant_name=plant_name,
                            price=price_match.group(0),
                            source=source
                        ))
        
        return results

    def _scrape_product_page(self, url, plant_name):
        """Scrape the product page directly for price information"""
        try:
            self.logger(f"Checking product page: {url}")
            response = requests.get(url, headers=get_request_headers(), timeout=10)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Common price selectors across e-commerce sites
                price_selectors = [
                    'span.price', 'div.price', 'span.product-price',
                    'span[itemprop="price"]', 'meta[itemprop="price"]',
                    'span.amount', 'span[class*="price"]',
                    'p.price', 'div[class*="price"]', 'span.current-price',
                    'div.productPrice', 'span.sales-price',
                    '.product-info-price', '.price-box'
                ]
                
                for selector in price_selectors:
                    price_elements = soup.select(selector)
                    for price_element in price_elements:
                        if price_element.name == 'meta' and price_element.has_attr('content'):
                            price_text = price_element['content']
                        else:
                            price_text = price_element.get_text().strip()
                        
                        price_match = re.search(self.price_pattern, price_text)
                        if price_match:
                            # Get the product title if possible
                            title = ""
                            title_selectors = ['h1', 'h1.product-title', 'h1[itemprop="name"]', '.product-title']
                            for title_selector in title_selectors:
                                title_elem = soup.select_one(title_selector)
                                if title_elem:
                                    title = title_elem.get_text().strip()
                                    break
                            
                            if title:
                                source = f"Product: {title[:30]}... - {url}"
                            else:
                                domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                                domain_text = domain.group(1) if domain else "Product page"
                                source = f"{domain_text} - {url}"
                                
                            return [SearchResult(
                                plant_name=plant_name,
                                price=price_match.group(0),
                                source=source
                            )]
                
                # Try JSON-LD data if available
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        data = json.loads(json_ld.string)
                        if isinstance(data, list):
                            data = data[0]
                        
                        # Try different possible paths for price
                        price = None
                        if 'offers' in data:
                            if isinstance(data['offers'], dict) and 'price' in data['offers']:
                                price = data['offers']['price']
                            elif isinstance(data['offers'], list) and data['offers'] and 'price' in data['offers'][0]:
                                price = data['offers'][0]['price']
                        elif 'price' in data:
                            price = data['price']
                        
                        if price:
                            # Get product name from JSON-LD if available
                            product_name = data.get('name', '')
                            domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                            domain_text = domain.group(1) if domain else "Product page"
                            
                            source = f"{domain_text} - {product_name[:30]}... - {url}"
                            return [SearchResult(
                                plant_name=plant_name,
                                price=f"${price}",
                                source=source
                            )]
                    except Exception as e:
                        self.logger(f"Error parsing JSON-LD: {str(e)}")
        
        except Exception as e:
            self.logger(f"Error scraping product page: {str(e)}")
        
        return []


class RetailerParser:
    """Parser for specific retailer websites"""
    
    def __init__(self, retailer, logger=None):
        self.retailer = retailer
        self.logger = logger or (lambda msg: None)
    
    def parse_product_page(self, response_text, plant_name):
        """Parse a retailer product page for relevant price information"""
        soup = BeautifulSoup(response_text, 'html.parser')
        
        # Look for products
        products = soup.select(self.retailer.product_selector)
        
        # If main selector doesn't work, try alternatives
        if not products:
            for alt_selector in self.retailer.alt_selectors:
                products = soup.select(alt_selector)
                if products:
                    break
        
        # Try to find the most relevant product
        relevant_products = []
        for product in products[:5]:  # Check first 5 products
            product_text = product.get_text()
            
            # Find the title element if possible
            title_elements = product.select('h2, h3, h4, a[class*="title"], div[class*="title"]')
            product_title = ""
            if title_elements:
                product_title = title_elements[0].get_text().strip()
            
            # Calculate relevance score based on presence of plant name words
            plant_words = [word.lower() for word in plant_name.split() if len(word) > 2]
            product_text_lower = product_text.lower()
            title_lower = product_title.lower() if product_title else ""
            
            # Count matching words in title and full text, giving title matches more weight
            title_matches = sum(1 for word in plant_words if word in title_lower)
            text_matches = sum(1 for word in plant_words if word in product_text_lower)
            
            # Relevance score: title matches are worth more
            relevance_score = (title_matches * 2) + text_matches
            
            # Extract price
            price_match = re.search(self.retailer.price_pattern, product_text)
            
            if price_match and relevance_score > 0:
                # Get URL if possible
                product_url = self.retailer.get_search_url(plant_name)
                a_tags = product.select('a')
                if a_tags and a_tags[0].has_attr('href'):
                    product_url = a_tags[0]['href']
                    if not product_url.startswith('http'):
                        # Try to build full URL from relative path
                        if product_url.startswith('/'):
                            domain = re.search(r'https?://(?:www\.)?([^/]+)', self.retailer.url_template)
                            if domain:
                                product_url = f"https://{domain.group(1)}{product_url}"
                        else:
                            # Default fallback if we can't build a proper URL
                            domain = self.retailer.name.lower().replace(' ', '')
                            product_url = f"https://www.{domain}.com.au/{product_url}"
                
                relevant_products.append({
                    'relevance': relevance_score,
                    'product': product,
                    'price': price_match.group(0),
                    'title': product_title or f"Product from {self.retailer.name}",
                    'url': product_url
                })
        
        # Sort by relevance score and get the most relevant product
        if relevant_products:
            relevant_products.sort(key=lambda x: x['relevance'], reverse=True)
            best_match = relevant_products[0]
            
            return SearchResult(
                plant_name=plant_name,
                price=best_match['price'],
                source=f"{self.retailer.name} - {best_match['title'][:30]}... - {best_match['url']}"
            )
        
        return None