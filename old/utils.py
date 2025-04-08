import random
import time
import re
import webbrowser
import urllib.parse

# Collection of user agents for rotating in requests
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0",
    # Added newer user agents
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.110 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 12_0_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:94.0) Gecko/20100101 Firefox/94.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/96.0.4664.45 Safari/537.36 Edg/96.0.1054.29",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
]

def get_random_user_agent():
    """Return a random user agent from the list"""
    return random.choice(USER_AGENTS)

def random_delay(min_seconds=1, max_seconds=3, logger=None):
    """Sleep for a random amount of time to avoid detection"""
    delay = random.uniform(min_seconds, max_seconds)
    if logger:
        logger(f"Waiting {delay:.1f} seconds...")
    time.sleep(delay)

def format_search_term(plant_name, include_buy=True, location="australia"):
    """
    Format a plant name for search queries
    
    Args:
        plant_name: The name of the plant to search for
        include_buy: Whether to include "buy" in the search term
        location: The location for pricing (default: australia)
    
    Returns:
        Formatted search term optimized for plant price results
    """
    # Clean the plant name
    clean_name = plant_name.strip()
    
    # Determine if this is likely a botanical name (contains italicized parts)
    is_botanical = bool(re.search(r'\b[A-Z][a-z]+ [a-z]+\b', clean_name))
    
    # Different formatting for botanical vs common names
    if is_botanical:
        terms = clean_name.replace(' ', '+')
        if include_buy:
            terms += "+price+buy+" + location
        else:
            terms += "+price+" + location
    else:
        terms = clean_name.replace(' ', '+')
        if include_buy:
            terms += "+plant+price+" + location + "+buy"
        else:
            terms += "+plant+price+" + location
    
    # URL encode to handle special characters properly
    return urllib.parse.quote_plus(terms)

def is_relevant_result(plant_name, result_text):
    """
    Check if a search result is relevant to the plant we're looking for.
    Excludes results from specific websites and irrelevant content.
    
    Args:
        plant_name: The name of the plant to check relevance for
        result_text: The text of the search result to check
    
    Returns:
        Boolean indicating if the result is relevant
    """
    # Convert both strings to lowercase for case-insensitive comparison
    result_text = result_text.lower()
    plant_name = plant_name.lower()
    
    # Check if the result is from excluded websites
    excluded_sites = [
        'succulentsonline.com.au',
        'wikipedia.org',
        'wikimedia.org',
        'inaturalist.org',
        'flickr.com',
        'pinterst.com'
    ]
    
    if any(site in result_text for site in excluded_sites):
        return False
    
    # Break the plant name into words and check presence
    plant_words = [word for word in plant_name.split() if len(word) > 2]
    
    # For plant names with 3+ words, require at least 2/3 of words to be present
    if len(plant_words) >= 3:
        matches = sum(1 for word in plant_words if word in result_text)
        if matches < len(plant_words) * 0.67:  # At least 2/3 of words must match
            return False
    # For plant names with 1-2 words, require all words to be present
    else:
        if not all(word in result_text for word in plant_words):
            return False
    
    # Exclude common irrelevant results
    irrelevant_terms = [
        'wikipedia',
        'images',
        'pictures',
        'how to grow',
        'care guide',
        'plant care',
        'identification',
        'poison',
        'toxic',
        'nursery locations',
        'store hours',
        'contact us',
        'about us'
    ]
    
    # Count how many irrelevant terms appear
    irrelevant_matches = sum(1 for term in irrelevant_terms if term in result_text)
    
    # If more than 2 irrelevant terms, consider it not relevant
    if irrelevant_matches > 2:
        return False
    
    # Check for price indicators to increase confidence
    price_indicators = ['$', 'price', 'cost', 'buy', 'purchase', 'shop', 'sale']
    has_price_indicator = any(indicator in result_text for indicator in price_indicators)
    
    # If it's a very short result and has no price indicators, be cautious
    if len(result_text) < 100 and not has_price_indicator:
        return False
        
    return True

def extract_url_from_source(source_text):
    """
    Extract URL from a source description text
    
    Args:
        source_text: The source text that may contain a URL
        
    Returns:
        Extracted URL or None if no URL found
    """
    # If source starts with 🔗, remove it first
    if source_text and source_text.startswith('🔗'):
        source_text = source_text[1:].strip()
    
    # Try to find URL in the source text
    url_match = re.search(r'https?://[^\s]+', source_text)
    if url_match:
        # Clean up the URL (remove trailing punctuation, etc.)
        url = url_match.group(0)
        # Remove trailing punctuation that might be part of the text, not the URL
        url = re.sub(r'[.,;:)]$', '', url)
        return url
    
    # If no direct URL found, check if there's a domain reference
    domain_match = re.search(r'([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)', source_text)
    if domain_match:
        domain = domain_match.group(0)
        # Check if it looks like a valid domain with common TLDs
        if re.search(r'\.(com|net|org|edu|gov|au|co|io)$', domain):
            return f"https://www.{domain}"
    
    return None

def open_url(url):
    """Open a URL in the default web browser"""
    try:
        webbrowser.open(url)
        return True
    except Exception as e:
        print(f"Error opening URL: {e}")
        return False

def format_price(price_text):
    """
    Format a price string for consistent display
    
    Args:
        price_text: Raw price text from a website
        
    Returns:
        Formatted price string (e.g., "$10.99")
    """
    if not price_text or price_text == "N/A" or price_text == "Not found":
        return price_text
    
    # Try to extract a price using regex
    price_match = re.search(r'\$?\s*(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)', price_text)
    if price_match:
        price = price_match.group(1)
        
        # Remove any commas
        price = price.replace(',', '')
        
        # Convert to float and format
        try:
            price_float = float(price)
            return f"${price_float:.2f}"
        except ValueError:
            # If conversion fails, just add $ symbol if missing
            if not price_text.startswith('$'):
                return f"${price}"
            return price_text
    
    # If no match, return original with $ if needed
    if not price_text.startswith('$') and any(c.isdigit() for c in price_text):
        return f"${price_text}"
    
    return price_text

def get_request_headers():
    """Get headers for HTTP requests with a random user agent"""
    return {
        'User-Agent': get_random_user_agent(),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://www.google.com/',
        'DNT': '1',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'cross-site',
        'Cache-Control': 'max-age=0'
    }

def clean_plant_name(plant_name):
    """
    Clean a plant name for better search results
    
    Args:
        plant_name: Raw plant name
        
    Returns:
        Cleaned plant name
    """
    # Remove extra whitespace
    clean_name = ' '.join(plant_name.split())
    
    # Remove common prefixes/suffixes that aren't part of plant names
    prefixes = ['the ', 'a ', 'an ']
    for prefix in prefixes:
        if clean_name.lower().startswith(prefix):
            clean_name = clean_name[len(prefix):]
    
    # Remove content in parentheses if it contains certain keywords
    clean_name = re.sub(r'\([^)]*(?:care|grow|water|sun|shade|indoor|outdoor)[^)]*\)', '', clean_name)
    
    # Clean up after removing parentheses
    clean_name = ' '.join(clean_name.split())
    
    return clean_name