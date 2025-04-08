import tkinter as tk
from tkinter import scrolledtext, ttk, messagebox, filedialog
import pandas as pd
import threading
import re
import webbrowser

from scraper import PlantPriceScraper
from utils import extract_url_from_source, open_url
from models import SearchResult, PlantPriceResults

class PlantPriceScraperApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Plant Price Scraper")
        self.root.geometry("950x650")
        self.root.minsize(900, 600)
        
        # Set green theme colors
        self.colors = {
            "dark_green": "#2E8B57",  # Sea Green
            "medium_green": "#3CB371",  # Medium Sea Green
            "light_green": "#98FB98",  # Pale Green
            "very_light_green": "#F0FFF0",  # Honeydew
            "accent": "#FF6347",  # Tomato (for accent/warning)
            "text": "#333333",  # Dark gray for text
            "bg": "#FCFCFC"  # Almost white background
        }
        
        # Configure ttk styles
        self.configure_styles()
        
        # Create menu
        self.create_menu()
        
        # Create main frame
        main_frame = ttk.Frame(root, style="Main.TFrame", padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create paned window (splitter)
        paned = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Left panel - Plant Names
        left_frame = ttk.LabelFrame(paned, text="Plant Names", style="Green.TLabelframe")
        paned.add(left_frame, weight=1)
        
        # Plant names text area
        self.plant_names_text = scrolledtext.ScrolledText(left_frame, font=("Helvetica", 10))
        self.plant_names_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.plant_names_text.config(bg=self.colors["very_light_green"], fg=self.colors["text"])
        
        # Add placeholder text
        placeholder = "Enter plant names here (one per line)"
        self.plant_names_text.insert(tk.END, placeholder)
        self.plant_names_text.config(fg='gray')
        
        # Bind focus events for placeholder behavior
        self.plant_names_text.bind('<FocusIn>', self._on_focus_in)
        self.plant_names_text.bind('<FocusOut>', self._on_focus_out)
        
        # Store placeholder text as instance variable
        self.placeholder = placeholder
        
        # Right panel
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)  # Give right panel more weight for better display
        
        # Results frame
        results_frame = ttk.LabelFrame(right_frame, text="Results", style="Green.TLabelframe")
        results_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Results treeview with container frame for responsiveness
        tree_container = ttk.Frame(results_frame)
        tree_container.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Configure columns with dynamic width
        self.results_tree = ttk.Treeview(
            tree_container, 
            columns=("plant", "price1", "source1", "price2", "source2", "price3", "source3"),
            show="headings",
            style="Results.Treeview"
        )
        
        # Configure columns - added plant name column for better visibility
        self.results_tree.heading("plant", text="Plant Name")
        self.results_tree.heading("price1", text="Price 1")
        self.results_tree.heading("source1", text="Source 1")
        self.results_tree.heading("price2", text="Price 2")
        self.results_tree.heading("source2", text="Source 2")
        self.results_tree.heading("price3", text="Price 3")
        self.results_tree.heading("source3", text="Source 3")
        
        # Configure column widths and weights
        self.results_tree.column("plant", width=150, minwidth=100)
        self.results_tree.column("price1", width=70, minwidth=60)
        self.results_tree.column("source1", width=180, minwidth=140)
        self.results_tree.column("price2", width=70, minwidth=60)
        self.results_tree.column("source2", width=180, minwidth=140)
        self.results_tree.column("price3", width=70, minwidth=60)
        self.results_tree.column("source3", width=180, minwidth=140)
        
        # Pack treeview with scrollbars
        self.results_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add vertical scrollbar to treeview
        tree_y_scrollbar = ttk.Scrollbar(tree_container, orient="vertical", command=self.results_tree.yview)
        tree_y_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.results_tree.configure(yscrollcommand=tree_y_scrollbar.set)
        
        # Add horizontal scrollbar for wide content
        tree_x_scrollbar = ttk.Scrollbar(results_frame, orient="horizontal", command=self.results_tree.xview)
        tree_x_scrollbar.pack(fill=tk.X)
        self.results_tree.configure(xscrollcommand=tree_x_scrollbar.set)
        
        # Add binding for clicking on the source column
        self.results_tree.bind('<Double-1>', self.on_tree_double_click)
        
        # Add tooltip to indicate clickable links
        tooltip_frame = ttk.Frame(results_frame)
        tooltip_frame.pack(fill=tk.X, padx=5)
        
        link_icon = ttk.Label(tooltip_frame, text="🔗", font=('Arial', 10))
        link_icon.pack(side=tk.LEFT, padx=(0, 5))
        
        ttk.Label(
            tooltip_frame, 
            text="Double-click on source to open URL", 
            font=('Arial', 9, 'italic'),
            foreground=self.colors["dark_green"]
        ).pack(side=tk.LEFT)
        
        # Log frame
        log_frame = ttk.LabelFrame(right_frame, text="Log", style="Green.TLabelframe")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Log text area
        self.log_text = scrolledtext.ScrolledText(log_frame, height=8, font=("Helvetica", 9))
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        self.log_text.config(bg=self.colors["very_light_green"], fg=self.colors["text"])
        
        # Bottom frame for buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        # Search method selection
        method_frame = ttk.LabelFrame(button_frame, text="Search Method", style="Green.TLabelframe")
        method_frame.pack(side=tk.LEFT, padx=5)
        
        self.method_var = tk.StringVar(value="selenium")
        ttk.Radiobutton(
            method_frame, 
            text="Selenium Browser", 
            variable=self.method_var, 
            value="selenium",
            style="Green.TRadiobutton"
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        ttk.Radiobutton(
            method_frame, 
            text="BeautifulSoup", 
            variable=self.method_var, 
            value="bs4",
            style="Green.TRadiobutton"
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        # CAPTCHA handling
        captcha_frame = ttk.LabelFrame(button_frame, text="CAPTCHA Handling", style="Green.TLabelframe")
        captcha_frame.pack(side=tk.LEFT, padx=5)
        
        self.captcha_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            captcha_frame, 
            text="Pause for CAPTCHAs", 
            variable=self.captcha_var,
            style="Green.TCheckbutton"
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        # Buttons frame (right side)
        btn_container = ttk.Frame(button_frame)
        btn_container.pack(side=tk.RIGHT, padx=5)
        
        # Buttons
        self.start_button = ttk.Button(
            btn_container, 
            text="Start Scraping", 
            command=self.start_scraping,
            style="Green.TButton"
        )
        self.start_button.pack(side=tk.RIGHT, padx=5)
        
        self.continue_button = ttk.Button(
            btn_container, 
            text="Continue After CAPTCHA", 
            command=self.continue_after_captcha, 
            state=tk.DISABLED,
            style="Green.TButton"
        )
        self.continue_button.pack(side=tk.RIGHT, padx=5)
        
        self.stop_button = ttk.Button(
            btn_container, 
            text="Stop", 
            command=self.stop_scraping, 
            state=tk.DISABLED,
            style="Green.TButton"
        )
        self.stop_button.pack(side=tk.RIGHT, padx=5)
        
        # Progress and status frame
        progress_frame = ttk.Frame(main_frame)
        progress_frame.pack(fill=tk.X, pady=(5, 0))
        
        # Progress bar
        self.progress = ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='determinate',
            style="Green.Horizontal.TProgressbar"
        )
        self.progress.pack(fill=tk.X, side=tk.TOP)
        
        # Status label
        self.status_label = ttk.Label(
            progress_frame, 
            text="Ready", 
            anchor=tk.W,
            foreground=self.colors["dark_green"],
            font=("Helvetica", 9, "italic")
        )
        self.status_label.pack(fill=tk.X, side=tk.TOP, pady=(2, 0))
        
        # Initialize scraper
        self.scraper = PlantPriceScraper(logger=self.log)
        
        # Initialize other variables
        self.running = False
        self.paused_for_captcha = False
        self.results = {}  # Dictionary of plant_name -> PlantPriceResults
        self.current_plant = ""
        self.remaining_plants = []
        
        # Sample plant names for testing
        sample_plants = """Echeveria Elegans
Haworthia Fasciata
Crassula Ovata (Jade Plant)
Sedum Morganianum
"""
        self.plant_names_text.delete("1.0", tk.END)
        self.plant_names_text.insert(tk.END, sample_plants)
        self.plant_names_text.config(fg='black')

    def configure_styles(self):
        """Configure custom ttk styles with green theme"""
        style = ttk.Style()
        style.configure("TButton", background="green", foreground="white", font=("Arial", 12))
        style.configure("TLabel", background="white", foreground="green", font=("Arial", 10))

    def create_menu(self):
        """Create the application menu"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Import Plant List", command=self.import_plant_list)
        file_menu.add_command(label="Save Results", command=self.save_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.destroy)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Sites menu
        sites_menu = tk.Menu(menubar, tearoff=0)
        sites_menu.add_command(label="Check Bunnings", command=lambda: self.open_site("https://www.bunnings.com.au/our-range/garden/plants"))
        sites_menu.add_command(label="Check Flower Power", command=lambda: self.open_site("https://www.flowerpower.com.au/plants"))
        sites_menu.add_command(label="Check Garden Express", command=lambda: self.open_site("https://www.gardenexpress.com.au/"))
        sites_menu.add_separator()
        sites_menu.add_command(label="Check eBay Plants", command=lambda: self.open_site("https://www.ebay.com.au/b/Plants-Seeds-Bulbs/181003/bn_2210994"))
        sites_menu.add_command(label="Check Amazon Plants", command=lambda: self.open_site("https://www.amazon.com.au/Plants/b?node=6997022051"))
        menubar.add_cascade(label="Sites", menu=sites_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Help", command=self.show_help)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)

    def open_site(self, url):
        """Open a website in the default browser"""
        webbrowser.open(url)

    def log(self, message):
        """Add message to log area and scroll to end"""
        timestamp = pd.Timestamp.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def start_scraping(self):
        """Start the scraping process in a new thread"""
        # Get plant names
        plant_text = self.plant_names_text.get("1.0", tk.END).strip()
        if not plant_text or plant_text == self.placeholder:
            messagebox.showwarning("No Plants", "Please enter plant names first.", parent=self.root)
            return
        
        plant_names = [name.strip() for name in plant_text.split('\n') if name.strip()]
        if not plant_names:
            messagebox.showwarning("No Plants", "Please enter plant names first.", parent=self.root)
            return
        
        # Clear previous results if starting fresh
        if not self.paused_for_captcha:
            for item in self.results_tree.get_children():
                self.results_tree.delete(item)
            self.log_text.delete("1.0", tk.END)
            self.results = {}  # Dictionary of plant_name -> PlantPriceResults
            self.remaining_plants = plant_names.copy()
        
        # Update UI state
        self.start_button.config(state=tk.DISABLED)
        self.stop_button.config(state=tk.NORMAL)
        self.continue_button.config(state=tk.DISABLED)
        self.running = True
        self.paused_for_captcha = False
        self.scraper.start()
        
        if not self.paused_for_captcha:
            self.progress['value'] = 0
            
        self.status_label.config(text="Initializing...")
        
        # Start scraping in a new thread
        threading.Thread(target=self.scraping_thread, args=(self.remaining_plants,), daemon=True).start()

    def scraping_thread(self, plant_names):
        """Scraping process that runs in a separate thread"""
        try:
            if self.method_var.get() == "selenium" and not self.scraper.driver:
                self.scraper.setup_driver()
            
            total_plants = len(plant_names)
            
            for i, plant_name in enumerate(plant_names):
                if not self.running or not self.scraper.running:
                    break
                
                self.current_plant = plant_name
                
                # Update status
                self.root.after(0, lambda: self.status_label.config(text=f"Searching for: {plant_name} ({i+1}/{total_plants})"))
                self.root.after(0, lambda: self.log(f"Searching for: {plant_name}"))
                
                # Search for plant price
                if self.method_var.get() == "selenium":
                    result = self.scraper.search_plant_selenium(plant_name)
                else:
                    result = self.scraper.search_plant_bs4(plant_name)
                
                # Check if paused for CAPTCHA
                if self.scraper.paused_for_captcha:
                    self.paused_for_captcha = True
                    self.remaining_plants = plant_names[i:]
                    self.root.after(0, lambda: self.continue_button.config(state=tk.NORMAL))
                    self.root.after(0, lambda: self.status_label.config(text="CAPTCHA detected! Please solve it manually."))
                    self.root.after(0, lambda: messagebox.showinfo("CAPTCHA Detected", 
                                                           "Please solve the CAPTCHA in the browser window.\n\n" +
                                                           "After solving, click 'Continue After CAPTCHA' button to resume.", 
                                                           parent=self.root))
                    break
                
                # Add to results (we want to collect multiple results per plant)
                if result:
                    # Initialize PlantPriceResults if this is the first result for this plant
                    if plant_name not in self.results:
                        self.results[plant_name] = PlantPriceResults(plant_name)
                    
                    # Add all results to this plant's collection
                    for res in result:
                        if isinstance(res, SearchResult) or isinstance(res, dict):
                            self.results[plant_name].add_result(res)
                    
                    # Update the treeview with the current results for this plant
                    self.update_treeview_for_plant(plant_name)
                    
                    # If we don't have enough results yet and we're using BeautifulSoup, try additional search methods
                    if not self.results[plant_name].has_enough_results() and self.method_var.get() == "bs4":
                        self.log(f"Not enough results for {plant_name}. Trying additional search methods...")
                        
                        # Try specialty plant sites for more results
                        specialty_results = self.scraper.search_specialty_sites(plant_name)
                        if specialty_results:
                            for res in specialty_results:
                                self.results[plant_name].add_result(res)
                            self.update_treeview_for_plant(plant_name)
                            
                        # If still not enough, try online marketplaces
                        if not self.results[plant_name].has_enough_results():
                            # Use priority_marketplaces=True to focus on eBay/Amazon for third price
                            marketplace_results = self.scraper.search_online_marketplaces(plant_name, priority_marketplaces=True)
                            if marketplace_results:
                                for res in marketplace_results:
                                    self.results[plant_name].add_result(res)
                                self.update_treeview_for_plant(plant_name)
                
                # Update progress
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
            self.root.after(0, lambda: messagebox.showerror("Error", f"An error occurred: {str(e)}", parent=self.root))
        
        finally:
            if not self.paused_for_captcha:
                self.scraper.close_driver()
                self.root.after(0, lambda: self.start_button.config(state=tk.NORMAL))
                self.root.after(0, lambda: self.stop_button.config(state=tk.DISABLED))
                self.running = False
                self.scraper.running = False

    def update_treeview_for_plant(self, plant_name):
        """Update the treeview with the current results for a plant"""
        # Remove any existing entry for this plant
        for item in self.results_tree.get_children():
            if self.results_tree.item(item)['values'][0] == plant_name:
                self.results_tree.delete(item)
                break
        
        # Get the plant's results
        plant_results = self.results.get(plant_name)
        if not plant_results:
            # Insert a row with "No results found" if no results exist
            self.results_tree.insert("", tk.END, 
                                   values=[plant_name, "N/A", "No results found", "N/A", "N/A", "N/A", "N/A"])
            return
            
        # Get top 3 results (pad with empty results if less than 3)
        top_results = plant_results.get_top_results(3)
        
        # Prepare values list with plant name and 3 prices + 3 sources
        values = [plant_name]
        for i in range(3):
            if i < len(top_results):
                result = top_results[i]
                source_text = result.source
                if "http" in source_text:
                    source_text = "🔗 " + source_text
                values.extend([result.price, source_text])
            else:
                # Fill with N/A if we don't have enough results
                values.extend(["N/A", "N/A"])
                
        # Insert into treeview
        self.results_tree.insert("", tk.END, values=values)
        
        # Alternate row colors for better readability
        for i, item in enumerate(self.results_tree.get_children()):
            if i % 2 == 0:
                self.results_tree.item(item, tags=("evenrow",))
            else:
                self.results_tree.item(item, tags=("oddrow",))

    def continue_after_captcha(self):
        """Continue scraping after CAPTCHA is solved"""
        if self.paused_for_captcha:
            self.log("Continuing after CAPTCHA...")
            self.paused_for_captcha = False
            self.scraper.set_paused_for_captcha(False)
            self.continue_button.config(state=tk.DISABLED)
            self.start_scraping()

    def stop_scraping(self):
        """Stop the scraping process"""
        self.running = False
        self.scraper.stop()
        self.status_label.config(text="Stopping... Please wait.")
        self.log("Stopping scraping...")
        self.paused_for_captcha = False
        self.continue_button.config(state=tk.DISABLED)

    def import_plant_list(self):
        """Import a list of plant names from a file"""
        filetypes = (("Text files", "*.txt"), ("CSV files", "*.csv"), ("All files", "*.*"))
        filename = filedialog.askopenfilename(
            title="Open Plant List", 
            filetypes=filetypes,
            parent=self.root
        )
        
        if filename:
            try:
                if filename.endswith('.csv'):
                    df = pd.read_csv(filename)
                    if 'name' in df.columns:
                        plants = df['name'].tolist()
                    else:
                        plants = df.iloc[:, 0].tolist()
                else:  # Assume text file
                    with open(filename, 'r') as f:
                        plants = [line.strip() for line in f.readlines() if line.strip()]
                
                # Clear current plant list and add new ones
                self.plant_names_text.delete("1.0", tk.END)
                self.plant_names_text.insert(tk.END, "\n".join(plants))
                self.plant_names_text.config(fg='black')
                self.log(f"Imported {len(plants)} plant names from {filename}")
            except Exception as e:
                messagebox.showerror("Import Error", f"Could not import plant list: {str(e)}", parent=self.root)

    def save_results(self):
        """Save the scraped results to a file"""
        if not self.results:
            messagebox.showwarning("No Results", "There are no results to save.", parent=self.root)
            return
        
        filetypes = (("CSV files", "*.csv"), ("Excel files", "*.xlsx"), ("All files", "*.*"))
        filename = filedialog.asksaveasfilename(
            title="Save Results",
            defaultextension=".csv",
            filetypes=filetypes,
            parent=self.root
        )
        
        if filename:
            try:
                # Convert results to a list of dictionaries
                result_dicts = [plant_results.to_dict() for plant_results in self.results.values()]
                
                # Create DataFrame
                df = pd.DataFrame(result_dicts)
                
                if filename.endswith('.xlsx'):
                    df.to_excel(filename, index=False)
                else:  # Default to CSV
                    df.to_csv(filename, index=False)
                
                self.log(f"Results saved to {filename}")
                messagebox.showinfo("Save Successful", f"Results saved to {filename}", parent=self.root)
            except Exception as e:
                messagebox.showerror("Save Error", f"Could not save results: {str(e)}", parent=self.root)

    def prompt_save_results(self):
        """Ask user if they want to save results after scraping completes"""
        if not self.results:
            return
            
        answer = messagebox.askyesno(
            "Save Results", 
            "Scraping completed! Would you like to save the results?",
            parent=self.root
        )
        
        if answer:
            self.save_results()

    def show_about(self):
        """Show the about dialog"""
        about_text = """Plant Price Scraper

Version 1.0
        
This application helps find and compare plant prices from various online sources.
        
Features:
- Search using Selenium browser or BeautifulSoup
- Direct retailer website searches
- Multiple sources for each plant
- CAPTCHA handling
- Export results to CSV/Excel
"""
        messagebox.showinfo("About Plant Price Scraper", about_text, parent=self.root)

    def show_help(self):
        """Show the help dialog"""
        help_text = """Plant Price Scraper Help
        
1. Enter plant names (one per line) in the left panel
2. Select search method:
   - Selenium Browser: Uses a real browser (slower but more reliable)
   - BeautifulSoup: Uses direct HTTP requests (faster but may trigger CAPTCHAs)
3. Configure CAPTCHA handling:
   - Check 'Pause for CAPTCHAs' to manually solve CAPTCHAs
   - Uncheck to skip when CAPTCHAs are detected
4. Click 'Start Scraping' to begin
5. Results will appear in the table
6. Use the menu to save results or import plant lists
        
Tips:
- For best results, use specific plant names
- Double-click on a source to open its URL
- Results include prices from retailers, Google, and marketplaces
- The 'Save Results' option will export all data to CSV or Excel
"""
        messagebox.showinfo("Plant Price Scraper Help", help_text, parent=self.root)

    def on_tree_double_click(self, event):
        """Handle double-click on treeview items"""
        region = self.results_tree.identify_region(event.x, event.y)
        if region == "cell":
            column = self.results_tree.identify_column(event.x)
            column_index = int(column.replace('#', ''))
            
            # Only source columns (3, 5, 7) are clickable - source1, source2, source3
            if column_index in [3, 5, 7]:
                selection = self.results_tree.selection()
                if not selection:
                    return
                    
                item = selection[0]
                values = self.results_tree.item(item)['values']
                
                # Get the source from the appropriate column
                source_index = column_index - 1  # Convert to 0-based index
                if source_index >= len(values):
                    return
                    
                source = values[source_index]
                
                # Extract URL from source text
                url = extract_url_from_source(source)
                if url:
                    self.log(f"Opening URL: {url}")
                    open_url(url)

    def _on_focus_in(self, event):
        """Clear placeholder text when text area gains focus"""
        if self.plant_names_text.get("1.0", tk.END).strip() == self.placeholder:
            self.plant_names_text.delete("1.0", tk.END)
            self.plant_names_text.config(fg=self.colors["text"])

    def _on_focus_out(self, event):
        """Restore placeholder text if text area is empty"""
        if not self.plant_names_text.get("1.0", tk.END).strip():
            self.plant_names_text.insert("1.0", self.placeholder)
            self.plant_names_text.config(fg='gray')