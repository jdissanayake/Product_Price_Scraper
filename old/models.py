import datetime

class SearchResult:
    """Represents a search result for a plant price"""
    def __init__(self, plant_name, price, source, source_type=None, relevance_score=0):
        self.plant_name = plant_name
        self.price = self._standardize_price(price)
        self.source = source
        # New fields to better track result types
        self.source_type = source_type or self._determine_source_type(source)
        self.relevance_score = relevance_score
        self.timestamp = datetime.datetime.now()  # Using datetime instead of pd.Timestamp
        
    def _standardize_price(self, price):
        """Standardize price format"""
        if isinstance(price, str):
            # Remove any extra spaces
            price = price.strip()
            
            # Make sure price has $ symbol
            if price != "N/A" and price != "Not found" and price != "Error" and not price.startswith('$'):
                price = '$' + price
                
            # Add .00 if it's a whole dollar amount without cents
            if price.startswith('$') and price[1:].isdigit():
                price = price + '.00'
        
        return price
    
    def _determine_source_type(self, source):
        """Categorize the source based on its text content"""
        source_lower = source.lower()
        
        # Determine source type based on text content
        if any(retailer in source_lower for retailer in ['bunnings', 'flower power', 'garden express']):
            return 'retailer'
        elif any(marketplace in source_lower for marketplace in ['ebay', 'amazon', 'etsy']):
            return 'marketplace'
        elif 'google' in source_lower or 'shopping' in source_lower:
            return 'search'
        elif any(specialty in source_lower for specialty in [
            'plantary', 'plant farm', 'little succers', 'plants in a box', 
            'seed world', 'succulent garden', 'collectors corner'
        ]):
            return 'specialty'
        else:
            return 'other'
    
    def to_dict(self):
        """Convert to dictionary for DataFrame creation"""
        return {
            "plant_name": self.plant_name,
            "price": self.price,
            "source": self.source,
            "source_type": self.source_type
        }
    
    def __str__(self):
        """String representation for debugging"""
        return f"{self.plant_name} - {self.price} from {self.source} ({self.source_type})"
        
class PlantPriceResults:
    """Stores multiple price results for a single plant"""
    def __init__(self, plant_name):
        self.plant_name = plant_name
        self.results = []  # List of SearchResult objects
        
    def add_result(self, result):
        """Add a search result to this plant's results"""
        if isinstance(result, SearchResult):
            self.results.append(result)
        else:
            # Convert dict to SearchResult if needed
            source_type = result.get("source_type", None)
            
            # If source_type not provided, determine based on source
            if not source_type and "source" in result:
                source = result.get("source", "")
                if any(retailer in source.lower() for retailer in ['bunnings', 'flower power', 'garden express']):
                    source_type = 'retailer'
                elif any(marketplace in source.lower() for marketplace in ['ebay', 'amazon', 'etsy']):
                    source_type = 'marketplace'
            
            self.results.append(SearchResult(
                plant_name=result.get("plant_name", self.plant_name),
                price=result.get("price", "N/A"),
                source=result.get("source", "Unknown"),
                source_type=source_type
            ))
            
    def get_top_results(self, count=3):
        """
        Get the top N results with prioritization:
        1. At least one retailer if available
        2. At least one general search result if available  
        3. At least one marketplace (specifically eBay/Amazon) if available
        """
        # If we have fewer than requested results, return all of them
        if len(self.results) <= count:
            return self.results
            
        # Group results by source type
        retailer_results = [r for r in self.results if r.source_type == 'retailer']
        search_results = [r for r in self.results if r.source_type == 'search']
        specialty_results = [r for r in self.results if r.source_type == 'specialty']
        
        # Specifically identify eBay and Amazon results
        marketplace_results = []
        for r in self.results:
            if r.source_type == 'marketplace':
                if 'ebay' in r.source.lower() or 'amazon' in r.source.lower():
                    marketplace_results.append(r)
        
        # Other marketplace results
        other_marketplace_results = [r for r in self.results if r.source_type == 'marketplace' 
                                    and r not in marketplace_results]
        
        # Other results
        other_results = [r for r in self.results if r.source_type == 'other']
        
        # Build prioritized results
        prioritized_results = []
        
        # First, add a retailer result if available
        if retailer_results:
            prioritized_results.append(retailer_results[0])
            
        # Then, add a search result if available
        if search_results:
            # Don't add if it's from same source as a retailer we already added
            if not any(r.source == search_results[0].source for r in prioritized_results):
                prioritized_results.append(search_results[0])
        
        # Then, add an eBay or Amazon result if available
        if marketplace_results:
            # Don't add if it's from same source as what we already added
            if not any(r.source == marketplace_results[0].source for r in prioritized_results):
                prioritized_results.append(marketplace_results[0])
        
        # If we need more results, add from specialty sites
        while len(prioritized_results) < count and specialty_results:
            result = specialty_results.pop(0)
            if not any(r.source == result.source for r in prioritized_results):
                prioritized_results.append(result)
        
        # If we still need more, add from other marketplace results
        while len(prioritized_results) < count and other_marketplace_results:
            result = other_marketplace_results.pop(0)
            if not any(r.source == result.source for r in prioritized_results):
                prioritized_results.append(result)
        
        # If we still need more, add from other results
        while len(prioritized_results) < count and other_results:
            result = other_results.pop(0)
            if not any(r.source == result.source for r in prioritized_results):
                prioritized_results.append(result)
        
        # If we still need more, add remaining results from any category
        remaining_results = [r for r in self.results if r not in prioritized_results]
        while len(prioritized_results) < count and remaining_results:
            prioritized_results.append(remaining_results.pop(0))
            
        return prioritized_results[:count]
    
    def to_dict(self):
        """Convert to dictionary with multiple prices and sources"""
        result = {"plant_name": self.plant_name}
        
        # Add price1, price2, price3 and source1, source2, source3
        top_results = self.get_top_results(3)
        for i, res in enumerate(top_results, 1):
            result[f"price{i}"] = res.price
            result[f"source{i}"] = res.source
            result[f"source_type{i}"] = res.source_type
            
        # Fill in empty slots with N/A
        for i in range(len(top_results) + 1, 4):
            result[f"price{i}"] = "N/A"
            result[f"source{i}"] = "N/A"
            result[f"source_type{i}"] = "N/A"
            
        return result
        
    def has_enough_results(self):
        """Check if we have enough diverse results (at least one from each major category)"""
        if len(self.results) < 3:
            return False
            
        source_types = set(r.source_type for r in self.results)
        
        # Check if we have at least one retailer and one marketplace
        has_retailer = 'retailer' in source_types
        has_marketplace = 'marketplace' in source_types
        
        return has_retailer and has_marketplace
    
    def get_stats(self):
        """Get statistics about the prices found"""
        if not self.results:
            return {
                "count": 0,
                "min": "N/A",
                "max": "N/A",
                "avg": "N/A"
            }
            
        # Extract numeric prices
        numeric_prices = []
        for result in self.results:
            price = result.price
            if isinstance(price, str) and price.startswith('$'):
                try:
                    # Remove $ and convert to float
                    numeric_price = float(price.replace('$', '').replace(',', ''))
                    numeric_prices.append(numeric_price)
                except ValueError:
                    continue
        
        if not numeric_prices:
            return {
                "count": len(self.results),
                "min": "N/A",
                "max": "N/A",
                "avg": "N/A"
            }
            
        return {
            "count": len(self.results),
            "min": f"${min(numeric_prices):.2f}",
            "max": f"${max(numeric_prices):.2f}",
            "avg": f"${sum(numeric_prices)/len(numeric_prices):.2f}"
        }

class Retailer:
    """Represents a plant retailer website"""
    def __init__(self, name, url_template, price_pattern, product_selector, alt_selectors=None):
        self.name = name
        self.url_template = url_template
        self.price_pattern = price_pattern
        self.product_selector = product_selector
        self.alt_selectors = alt_selectors or []
        
    def get_search_url(self, plant_name):
        """Generate search URL for the given plant name"""
        return self.url_template.format(plant_name=plant_name.replace(' ', '%20'))
    
    def __str__(self):
        """String representation for debugging"""
        return f"Retailer: {self.name}"

# List of default retailers to search
def get_default_retailers():
    return [
        Retailer(
            name="Bunnings",
            url_template="https://www.bunnings.com.au/search/products?q={plant_name}&category=Plants",
            price_pattern=r'\$\d+(?:\.\d{2})?',
            product_selector="article.product",
            alt_selectors=["div.product-list article", "div[data-product-card]"]
        ),
        Retailer(
            name="Flower Power",
            url_template="https://www.flowerpower.com.au/search?q={plant_name}",
            price_pattern=r'\$\d+(?:\.\d{2})?',
            product_selector="div.product-item-info",
            alt_selectors=["li.product-item"]
        ),
        Retailer(
            name="Garden Express",
            url_template="https://www.gardenexpress.com.au/search/{plant_name}",
            price_pattern=r'\$\d+(?:\.\d{2})?',
            product_selector="div.product-item",
            alt_selectors=["div.product-grid div"]
        ),
        # Added additional popular retailers
        Retailer(
            name="The Plant People",
            url_template="https://www.theplantpeople.com.au/search?q={plant_name}",
            price_pattern=r'\$\d+(?:\.\d{2})?',
            product_selector="div.product",
            alt_selectors=["div.product-grid-item"]
        ),
        Retailer(
            name="Garden World",
            url_template="https://www.gardenworld.com.au/?s={plant_name}&post_type=product",
            price_pattern=r'\$\d+(?:\.\d{2})?',
            product_selector="li.product",
            alt_selectors=["ul.products li"]
        )
    ]