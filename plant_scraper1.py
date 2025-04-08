import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import pandas as pd
import threading
import time
import re
import random
import requests
import json
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import webbrowser
import os

class PlantPriceScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plant Price Scraper")
        self.root.geometry("1200x700")
        self.root.minsize(1000, 600)
        
        if os.path.exists("logo.png"):
            self.root.iconphoto(True, tk.PhotoImage(file="logo.png"))
        
        self.create_menu()
        
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        left_frame = ttk.LabelFrame(paned, text="Plant Names")
        paned.add(left_frame, weight=1)
        
        self.plant_names_text = scrolledtext.ScrolledText(left_frame)
        self.plant_names_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        placeholder = "Enter plant names here (one per line)"
        self.plant_names_text.insert(tk.END, placeholder)
        self.plant_names_text.config(fg='gray')
        
        self.plant_names_text.bind('<FocusIn>', self._on_focus_in)
        self.plant_names_text.bind('<FocusOut>', self._on_focus_out)
        
        self.placeholder = placeholder
        
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        columns_frame = ttk.LabelFrame(right_frame, text="Select Columns to Display")
        columns_frame.pack(fill=tk.X, pady=5)
        
        # Removed marketplace_price and marketplace_source
        self.column_vars = {
            "plant": tk.BooleanVar(value=True),
            "price1": tk.BooleanVar(value=True),
            "source1": tk.BooleanVar(value=True),
            "price2": tk.BooleanVar(value=True),
            "source2": tk.BooleanVar(value=True),
            "price3": tk.BooleanVar(value=True),
            "source3": tk.BooleanVar(value=True)
        }
        
        for col, var in self.column_vars.items():
            ttk.Checkbutton(columns_frame, text=col.replace('_', ' ').title(), 
                            variable=var, command=self.update_tree_columns).pack(side=tk.LEFT, padx=2)
        
        results_frame = ttk.LabelFrame(right_frame, text="Results")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.results_tree = ttk.Treeview(results_frame, 
                                        columns=list(self.column_vars.keys()), 
                                        show="headings")
        for col in self.column_vars:
            self.results_tree.heading(col, text=col.replace('_', ' ').title())
            self.results_tree.column(col, width=150 if "source" in col else 80, 
                                    stretch=tk.YES if col == "plant" else tk.NO)
        
        self.update_tree_columns()
        
        self.results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.results_tree.bind('<Double-1>', self.on_tree_double_click)
        
        ttk.Label(results_frame, text="Double-click on source to open URL", 
                  font=('Arial', 8, 'italic')).pack(anchor='w', padx=5)
        
        tree_scrollbar = ttk.Scrollbar(results_frame, orient="vertical", command=self.results_tree.yview)
        tree_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.configure(yscrollcommand=tree_scrollbar.set)
        
        exclude_frame = ttk.LabelFrame(right_frame, text="Excluded URLs (one per line)")
        exclude_frame.pack(fill=tk.BOTH, pady=5)
        
        self.exclude_text = scrolledtext.ScrolledText(exclude_frame, height=3)
        self.exclude_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.exclude_text.insert(tk.END, "succulentsonline.com.au")
        
        log_frame = ttk.LabelFrame(right_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        method_frame = ttk.LabelFrame(button_frame, text="Search Method")
        method_frame.pack(side=tk.LEFT, padx=5)
        
        self.method_var = tk.StringVar(value="selenium")
        ttk.Radiobutton(method_frame, text="Selenium Browser", variable=self.method_var, value="selenium").pack(side=tk.LEFT, padx=5)
        ttk.Radiobutton(method_frame, text="BeautifulSoup", variable=self.method_var, value="bs4").pack(side=tk.LEFT, padx=5)
        
        captcha_frame = ttk.LabelFrame(button_frame, text="CAPTCHA Handling")
        captcha_frame.pack(side=tk.LEFT, padx=5)
        
        self.captcha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(captcha_frame, text="Pause for CAPTCHAs", variable=self.captcha_var).pack(side=tk.LEFT, padx=5)
        
        self.start_button = ttk.Button(button_frame, text="Start Scraping", command=self.start_scraping)
        self.start_button.pack(side=tk.RIGHT, padx=5)
        
        self.continue_button = ttk.Button(button_frame, text="Continue After CAPTCHA", command=self.continue_after_captcha, state=tk.DISABLED)
        self.continue_button.pack(side=tk.RIGHT, padx=5)
        
        self.stop_button = ttk.Button(button_frame, text="Stop", command=self.stop_scraping, state=tk.DISABLED)
        self.stop_button.pack(side=tk.RIGHT, padx=5)
        
        self.progress = ttk.Progressbar(main_frame, orient=tk.HORIZONTAL, length=100, mode='determinate')
        self.progress.pack(fill=tk.X)
        
        self.status_label = ttk.Label(main_frame, text="Ready", anchor=tk.W)
        self.status_label.pack(fill=tk.X)
        
        self.running = False
        self.paused_for_captcha = False
        self.driver = None
        self.results = []
        self.current_plant = ""
        self.remaining_plants = []
        
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Safari/605.1.15",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:90.0) Gecko/20100101 Firefox/90.0"
        ]
        
        sample_plants = """Aloe Vera
Echeveria Elegans
Haworthia Fasciata
Crassula Ovata (Jade Plant)
"""
        self.plant_names_text.insert(tk.END, sample_plants)

    def create_menu(self):
        menubar = tk.Menu(self.root)
        
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import Plant List", command=self.import_plant_list)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        sites_menu = tk.Menu(menubar, tearoff=0)
        sites_menu.add_command(label="Check Bunnings", command=lambda: self.open_site("https://www.bunnings.com.au/our-range/garden/plants"))
        sites_menu.add_command(label="Check Flower Power", command=lambda: self.open_site("https://www.flowerpower.com.au/plants"))
        sites_menu.add_command(label="Check Garden Express", command=lambda: self.open_site("https://www.gardenexpress.com.au/"))
        menubar.add_cascade(label="Sites", menu=sites_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def open_site(self, url):
        webbrowser.open(url)

    def log(self, message):
        self.log_text.insert(tk.END, message + "\n")
        self.log_text.see(tk.END)

    def update_tree_columns(self):
        displayed_cols = [col for col, var in self.column_vars.items() if var.get()]
        self.results_tree["displaycolumns"] = displayed_cols

    def start_scraping(self):
        plant_text = self.plant_names_text.get("1.0", tk.END).strip()
        if not plant_text or plant_text == self.placeholder:
            messagebox.showwarning("No Plants", "Please enter plant names first.")
            return
        
        plant_names = [name.strip() for name in plant_text.split('\n') if name.strip()]
        if not plant_names:
            messagebox.showwarning("No Plants", "Please enter plant names first.")
            return
        
        exclude_text = self.exclude_text.get("1.0", tk.END).strip()
        self.excluded_sites = [site.strip() for site in exclude_text.split('\n') if site.strip()]
        
        if not self.paused_for_captcha:
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.log_text.delete("1.0", tk.END)
            self.results = []
            self.remaining_plants = plant_names.copy()
        
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.continue_button.config(state=tk.DISABLED)
        self.running = True
        self.paused_for_captcha = False
        
        if not self.paused_for_captcha:
            self.progress['value'] = 0
            
        self.status_label.config(text="Initializing...")
        
        threading.Thread(target=self.scraping_thread, args=(self.remaining_plants,), daemon=True).start()

    def scraping_thread(self, plant_names):
        try:
            if self.method_var.get() == "selenium" and not self.driver:
                self.setup_driver()
            
            total_plants = len(plant_names)
            
            for i, plant_name in enumerate(plant_names):
                if not self.running:
                    break
                
                self.current_plant = plant_name
                
                self.root.after(0, lambda: self.status_label.config(text=f"Searching for: {plant_name} ({i+1}/{total_plants})"))
                self.root.after(0, lambda: self.log(f"Searching for: {plant_name}"))
                
                if self.method_var.get() == "selenium":
                    main_results = self.search_plant_selenium(plant_name)
                else:
                    main_results = self.search_plant_bs4(plant_name)
                
                if self.paused_for_captcha:
                    self.remaining_plants = plant_names[i:]
                    self.root.after(0, lambda: self.continue_button.config(state=tk.NORMAL))
                    break
                
                result_dict = {"plant_name": plant_name}
                for idx, result in enumerate(main_results[:3], 1):
                    result_dict[f"price{idx}"] = result.get("price", "Not found")
                    # Extract only the URL if present
                    source = result.get("source", "")
                    url_match = re.search(r'https?://[^\s]+', source)
                    result_dict[f"source{idx}"] = url_match.group(0) if url_match else source
                
                self.results.append(result_dict)
                
                values = []
                for col in self.column_vars.keys():
                    if col == "plant":
                        values.append(plant_name)
                    elif "source" in col:
                        value = result_dict.get(col, "")
                        if "http" in value:
                            value = "🔗 " + value
                        values.append(value)
                    else:
                        values.append(result_dict.get(col, ""))
                
                self.root.after(0, lambda v=values: self.results_tree.insert("", tk.END, values=v))
                
                progress_value = int((i + 1) / total_plants * 100)
                self.root.after(0, lambda v=progress_value: self.progress.config(value=v))
            
            if self.running and not self.paused_for_captcha:
                self.root.after(0, lambda: self.status_label.config(text="Scraping completed!"))
                self.root.after(0, lambda: self.log("Scraping completed!"))
                self.root.after(0, self.prompt_save_results)
            elif not self.paused_for_captcha:
                self.root.after(0, lambda: self.status_label.config(text="Scraping stopped by user."))
        
        except Exception as e:
            import traceback
            error_msg = f"Error: {str(e)}\n{traceback.format_exc()}"
            self.root.after(0, lambda: self.log(error_msg))
            self.root.after(0, lambda: self.status_label.config(text="Error occurred!"))
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}"))
        
        finally:
            if not self.paused_for_captcha:
                self.close_driver()
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.running = False

    def setup_driver(self):
        self.log("Setting up browser...")
        chrome_options = Options()
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option('useAutomationExtension', False)
        chrome_options.add_argument("--window-size=1200,800")
        chrome_options.add_argument("--disable-notifications")
        chrome_options.add_argument(f"user-agent={random.choice(self.user_agents)}")
        
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        self.log("Browser setup complete.")

    def detect_captcha(self):
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
            self.log(f"Error checking for CAPTCHA: {str(e)}")
            return False

    def continue_after_captcha(self):
        if self.paused_for_captcha:
            self.log("Continuing after CAPTCHA...")
            self.paused_for_captcha = False
            self.continue_button.config(state=tk.DISABLED)
            self.start_scraping()

    def stop_scraping(self):
        self.running = False
        self.status_label.config(text="Stopping... Please wait.")
        self.log("Stopping scraping...")
        self.paused_for_captcha = False
        self.continue_button.config(state=tk.DISABLED)

    def search_plant_selenium(self, plant_name):
        try:
            delay = random.uniform(2, 5)
            self.log(f"Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            
            search_term = plant_name.replace(' ', '+') + "+plant+price+australia+buy"
            url = f"https://www.google.com.au/search?q={search_term}&gl=au&hl=en"
            
            self.log(f"Searching Google for: {plant_name}")
            self.driver.get(url)
            
            if self.detect_captcha():
                if self.captcha_var.get():
                    self.log("CAPTCHA detected! Please solve it in the browser window.")
                    self.log("After solving, click 'Continue After CAPTCHA' button to resume.")
                    self.root.after(0, lambda: self.status_label.config(text="CAPTCHA detected! Please solve it manually."))
                    self.root.after(0, lambda: messagebox.showinfo("CAPTCHA Detected", 
                                                           "Please solve the CAPTCHA in the browser window.\n\n" +
                                                           "After solving, click 'Continue After CAPTCHA' button to resume."))
                    self.paused_for_captcha = True
                    return [{"plant_name": plant_name, "price": "Paused for CAPTCHA", "source": "Google"}]
                else:
                    self.log("CAPTCHA detected but automatic handling disabled. Skipping.")
                    return [{"plant_name": plant_name, "price": "CAPTCHA detected", "source": "Google"}]
            
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "search"))
                )
            except:
                self.log("No search results found or page structure changed")
                return [{"plant_name": plant_name, "price": "No results", "source": "Google"}]
            
            page_html = self.driver.page_source
            soup = BeautifulSoup(page_html, 'html.parser')
            
            results = self.enhanced_extract_prices_from_soup(soup, plant_name)
            if len(results) < 3:
                retailer_results = self.search_direct_retailers(plant_name)
                results.extend(retailer_results)
            
            return results[:3]
            
        except Exception as e:
            self.log(f"Error in Selenium search: {str(e)}")
            return [{"plant_name": plant_name, "price": "Error", "source": f"Error: {str(e)}"}]

    def search_plant_bs4(self, plant_name):
        try:
            delay = random.uniform(1, 3)
            self.log(f"Waiting {delay:.1f} seconds...")
            time.sleep(delay)
            
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Referer': 'https://www.google.com/',
                'DNT': '1',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1'
            }
            
            search_term = plant_name.replace(' ', '+') + "+plant+price+australia+buy"
            url = f"https://www.google.com.au/search?q={search_term}&gl=au&hl=en"
            
            self.log(f"Searching Google for: {plant_name}")
            response = requests.get(url, headers=headers, timeout=10)
            
            if response.status_code != 200:
                self.log(f"Google search failed with status code: {response.status_code}")
                return self.search_direct_retailers(plant_name)
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            if "unusual traffic" in soup.text.lower() or "captcha" in soup.text.lower() or "verify you're a human" in soup.text.lower():
                self.log("CAPTCHA detected in BS4 search. Trying direct retailer websites...")
                return self.search_direct_retailers(plant_name)
            
            results = self.enhanced_extract_prices_from_soup(soup, plant_name)
            if len(results) < 3:
                retailer_results = self.search_direct_retailers(plant_name)
                results.extend(retailer_results)
            
            return results[:3]
            
        except Exception as e:
            self.log(f"Error in BS4 search: {str(e)}")
            return self.search_direct_retailers(plant_name)

    def enhanced_extract_prices_from_soup(self, soup, plant_name):
        price_pattern = r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?'
        
        shopping_results = self._extract_shopping_results(soup, plant_name, price_pattern)
        
        organic_results = self._extract_organic_results(soup, plant_name, price_pattern, limit=10)
        
        combined_results = shopping_results + organic_results
        
        if len(combined_results) < 3:
            meta_results = self._extract_meta_descriptions(soup, plant_name, price_pattern)
            combined_results.extend(meta_results)
        
        if len(combined_results) < 3:
            product_url = self._find_first_product_url(soup)
            if product_url:
                product_results = self._scrape_product_page(product_url, plant_name)
                combined_results.extend(product_results)
        
        return combined_results[:3] if combined_results else [{
            "plant_name": plant_name,
            "price": "Not found",
            "source": "No price found on search page or product page"
        }]

    def _find_first_product_url(self, soup):
        shopping_links = soup.select('a[href*="/url?q="]')
        for link in shopping_links:
            href = link['href']
            if '/url?q=' in href and 'webcache' not in href:
                url_match = re.search(r'/url\?q=([^&]+)', href)
                if url_match:
                    return url_match.group(1)
        
        organic_links = soup.select('div.g a[href^="http"]')
        for link in organic_links[:3]:
            if link.has_attr('href'):
                return link['href']
        
        return None

    def _scrape_product_page(self, url, plant_name):
        try:
            headers = {
                'User-Agent': random.choice(self.user_agents),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            }
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')
                
                price_selectors = [
                    'span.price', 'div.price', 'span.product-price',
                    'span[itemprop="price"]', 'meta[itemprop="price"]',
                    'span.amount', 'span[class*="price"]'
                ]
                
                for selector in price_selectors:
                    price_element = soup.select_one(selector)
                    if price_element:
                        price_text = price_element.get_text().strip()
                        price_match = re.search(r'\$\d{1,3}(?:,\d{3})*(?:\.\d{2})?', price_text)
                        if price_match:
                            return [{
                                "plant_name": plant_name,
                                "price": price_match.group(0),
                                "source": url  # Only URL
                            }]
                
                json_ld = soup.find('script', type='application/ld+json')
                if json_ld:
                    try:
                        data = json.loads(json_ld.string)
                        if isinstance(data, list):
                            data = data[0]
                        if 'offers' in data and 'price' in data['offers']:
                            return [{
                                "plant_name": plant_name,
                                "price": f"${data['offers']['price']}",
                                "source": url  # Only URL
                            }]
                    except:
                        pass
        
        except Exception as e:
            self.log(f"Error scraping product page: {str(e)}")
        
        return [{
            "plant_name": plant_name,
            "price": "Not found",
            "source": "No price found on product page"  # No URL prefix
        }]

    def _extract_shopping_results(self, soup, plant_name, price_pattern):
        selectors = [
            'div.sh-dlr__list-result',
            'div.commercial-unit-desktop-top',
            'div.pla-unit'
        ]
        
        results = []
        
        for selector in selectors:
            shopping_divs = soup.select(selector)
            for div in shopping_divs[:3]:
                div_text = div.get_text()
                
                if not self.is_relevant_result(plant_name, div_text):
                    continue
                
                price_match = re.search(price_pattern, div_text)
                if price_match:
                    source = "Google Shopping"
                    link = div.select_one('a')
                    if link and link.has_attr('href'):
                        href = link['href']
                        if '/url?q=' in href:
                            url_match = re.search(r'/url\?q=([^&]+)', href)
                            if url_match:
                                source = url_match.group(1)  # Only URL
                    
                    results.append({
                        "plant_name": plant_name,
                        "price": price_match.group(0),
                        "source": source
                    })
        
        return results

    def _extract_organic_results(self, soup, plant_name, price_pattern, limit=10):
        selectors = [
            'div.g',
            'div.tF2Cxc',
            'div[data-hveid]'
        ]
        
        results = []
        
        for selector in selectors:
            organic_results = soup.select(selector)
            for result in organic_results[:limit]:
                result_text = result.get_text()
                
                if not self.is_relevant_result(plant_name, result_text):
                    continue
                
                price_match = re.search(price_pattern, result_text)
                if price_match:
                    source = "Organic Result"
                    link = result.select_one('a')
                    if link and link.has_attr('href'):
                        url = link['href']
                        source = url  # Only URL
                    
                    results.append({
                        "plant_name": plant_name,
                        "price": price_match.group(0),
                        "source": source
                    })
        
        return results

    def _extract_meta_descriptions(self, soup, plant_name, price_pattern):
        meta_tags = [
            soup.find('meta', attrs={'name': 'description'}),
            soup.find('meta', attrs={'property': 'og:description'})
        ]
        
        results = []
        
        for tag in meta_tags:
            if tag and tag.has_attr('content'):
                content = tag['content']
                if self.is_relevant_result(plant_name, content):
                    price_match = re.search(price_pattern, content)
                    if price_match:
                        results.append({
                            "plant_name": plant_name,
                            "price": price_match.group(0),
                            "source": "Meta description"
                        })
        
        return results

    def is_relevant_result(self, plant_name, result_text):
        result_text = result_text.lower()
        plant_name = plant_name.lower()
        
        if hasattr(self, 'excluded_sites'):
            if any(site in result_text for site in self.excluded_sites):
                return False
        
        plant_words = plant_name.split()
        if not all(word in result_text for word in plant_words):
            return False
        
        irrelevant_terms = [
            'wikipedia',
            'images',
            'pictures',
            'how to grow',
            'care guide',
            'plant care'
        ]
        
        if any(term in result_text for term in irrelevant_terms):
            return False
            
        return True

    def search_direct_retailers(self, plant_name):
        retailers = [
            {
                "name": "Bunnings",
                "url": f"https://www.bunnings.com.au/search/products?q={plant_name.replace(' ', '%20')}&category=Plants",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "article.product",
                "alt_selectors": ["div.product-list article", "div[data-product-card]"]
            },
            {
                "name": "Flower Power",
                "url": f"https://www.flowerpower.com.au/search?q={plant_name.replace(' ', '+')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-item-info",
                "alt_selectors": ["li.product-item"]
            },
            {
                "name": "Garden Express",
                "url": f"https://www.gardenexpress.com.au/search/{plant_name.replace(' ', '%20')}",
                "price_pattern": r'\$\d+(?:\.\d{2})?',
                "product_selector": "div.product-item",
                "alt_selectors": ["div.product-grid div"]
            }
        ]
        
        results = []
        
        for retailer in retailers:
            try:
                self.log(f"Checking {retailer['name']}...")
                time.sleep(random.uniform(1, 2))
                
                headers = {
                    'User-Agent': random.choice(self.user_agents),
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                }
                
                response = requests.get(retailer["url"], headers=headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    products = soup.select(retailer["product_selector"])
                    
                    if not products:
                        for alt_selector in retailer["alt_selectors"]:
                            products = soup.select(alt_selector)
                            if products:
                                break
                    
                    for product in products[:1]:
                        product_text = product.get_text()
                        
                        if self.is_relevant_result(plant_name, product_text):
                            price_match = re.search(retailer["price_pattern"], product_text)
                            if price_match:
                                product_url = retailer["url"]
                                a_tags = product.select('a')
                                if a_tags and a_tags[0].has_attr('href'):
                                    product_url = a_tags[0]['href']
                                    if not product_url.startswith('http'):
                                        product_url = f"https://{retailer['name'].lower().replace(' ', '')}.com.au" + product_url
                                
                                results.append({
                                    "plant_name": plant_name,
                                    "price": price_match.group(0),
                                    "source": product_url  # Only URL
                                })
                                break
                    
            except Exception as e:
                self.log(f"Error searching {retailer['name']}: {str(e)}")
        
        if not results:
            results.append({
                "plant_name": plant_name,
                "price": "Not found",
                "source": "No price found from any retailer"
            })
        
        return results

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
                self.log("Browser closed.")
            except Exception as e:
                self.log(f"Error closing browser: {str(e)}")

    def import_plant_list(self):
        filetypes = (("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(title="Open Plant List", filetypes=filetypes)
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filename)
                    if 'name' in df.columns:
                        plants = df['name'].tolist()
                    else:
                        plants = df.iloc[:, 0].tolist()
                else:
                    with open(filename, 'r') as f:
                        plants = [line.strip() for line in f.readlines() if line.strip()]
                
                self.plant_names_text.delete("1.0", tk.END)
                self.plant_names_text.insert(tk.END, "\n".join(plants))
                self.log(f"Imported {len(plants)} plant names from {filename}")
            except Exception as e:
                messagebox.showerror("Import Error", f"Could not import plant list: {str(e)}")

    def save_results(self):
        if not self.results:
            messagebox.showwarning("No Results", "There are no results to save.")
            return
        
        export_dialog = tk.Toplevel(self.root)
        export_dialog.title("Select Columns to Export")
        export_dialog.geometry("300x400")
        export_dialog.transient(self.root)
        export_dialog.grab_set()
        
        export_vars = {col: tk.BooleanVar(value=True) for col in self.column_vars.keys()}
        for col, var in export_vars.items():
            ttk.Checkbutton(export_dialog, text=col.replace('_', ' ').title(), 
                            variable=var).pack(anchor='w', padx=10, pady=2)
        
        def on_export():
            selected_cols = [col for col, var in export_vars.items() if var.get()]
            if not selected_cols:
                messagebox.showwarning("No Columns", "Please select at least one column to export.")
                return
            
            filetypes = (("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*"))
            filename = filedialog.asksaveasfilename(
                title="Save Results",
                defaultextension=".csv",
                filetypes=filetypes
            )
            
            if filename:
                try:
                    df = pd.DataFrame(self.results)
                    df = df.rename(columns={"plant_name": "plant"})
                    expected_cols = list(self.column_vars.keys())
                    for col in expected_cols:
                        if col not in df.columns:
                            df[col] = ""
                    df_export = df[selected_cols]
                    
                    if filename.endswith('.xlsx'):
                        df_export.to_excel(filename, index=False)
                    else:
                        df_export.to_csv(filename, index=False)
                    
                    self.log(f"Results saved to {filename} with columns: {', '.join(selected_cols)}")
                    messagebox.showinfo("Save Successful", f"Results saved to {filename}")
                    export_dialog.destroy()
                except Exception as e:
                    messagebox.showerror("Save Error", f"Could not save results: {str(e)}")
        
        ttk.Button(export_dialog, text="Export", command=on_export).pack(pady=10)

    def prompt_save_results(self):
        if not self.results:
            return
            
        answer = messagebox.askyesno(
            "Save Results", 
            "Scraping completed! Would you like to save the results?"
        )
        
        if answer:
            self.save_results()

    def show_about(self):
        about_text = """Plant Price Scraper
        
Version 1.2
Developed by Jayasanka Dissanayake
        
This application scrapes plant prices from various online sources.
        
Features:
- Search using Selenium browser or BeautifulSoup
- Direct retailer website searches
- Custom excluded URLs
- Column selection for display and export
- CAPTCHA handling
- Export results to CSV/Excel
"""
        messagebox.showinfo("About Plant Price Scraper", about_text)

    def show_help(self):
        help_text = """Plant Price Scraper Help
        
1. Enter plant names (one per line) in the left panel
2. Add URLs to exclude in the 'Excluded URLs' box (one per line)
3. Select columns to display using checkboxes
4. Select search method:
   - Selenium Browser: Uses a real browser (slower but more reliable)
   - BeautifulSoup: Uses direct HTTP requests (faster but may trigger CAPTCHAs)
5. Configure CAPTCHA handling:
   - Check 'Pause for CAPTCHAs' to manually solve CAPTCHAs
   - Uncheck to skip when CAPTCHAs are detected
6. Click 'Start Scraping' to begin
7. Results will show up to 3 prices
8. Use the menu to save results (select columns to export) or import plant lists
        
Tips:
- For best results, use specific plant names
- Add unwanted sites to the excluded URLs box
- Double-click sources to open URLs
- Price 2 will check top 10 results if needed
"""
        messagebox.showinfo("Plant Price Scraper Help", help_text)

    def on_tree_double_click(self, event):
        region = self.results_tree.identify_region(event.x, event.y)
        if region == "cell":
            column_id = self.results_tree.identify_column(event.x)
            col_index = int(column_id.replace('#', '')) - 1
            column_name = self.results_tree["columns"][col_index]
            if "source" in column_name:
                item = self.results_tree.selection()
                if item:
                    values = self.results_tree.item(item[0], 'values')
                    source = values[col_index]
                    url_match = re.search(r'https?://[^\s]+', source)
                    if url_match:
                        webbrowser.open(url_match.group(0))
                    else:
                        self.log(f"No valid URL found in {column_name}: {source}")

    def _on_focus_in(self, event):
        if self.plant_names_text.get("1.0", tk.END).strip() == self.placeholder:
            self.plant_names_text.delete("1.0", tk.END)
            self.plant_names_text.config(fg='black')

    def _on_focus_out(self, event):
        if not self.plant_names_text.get("1.0", tk.END).strip():
            self.plant_names_text.insert("1.0", self.placeholder)
            self.plant_names_text.config(fg='gray')

if __name__ == "__main__":
    root = tk.Tk()
    app = PlantPriceScraperApp(root)
    root.mainloop()