Plant Price Scraper

Version: 1.2
Author: Jayasanka Dissanayake
Last Updated: April 08, 2025

Overview
--------
The Plant Price Scraper is a Python-based desktop application designed to scrape plant prices from online sources in Australia. It uses web scraping techniques with either Selenium (browser-based) or BeautifulSoup (HTTP requests) to gather pricing data from Google search results and direct retailer websites like Bunnings, Flower Power, and Garden Express. Results are displayed in a GUI and can be exported to CSV or Excel files.

This tool is ideal for gardeners, plant enthusiasts, or businesses looking to compare plant prices across multiple online platforms efficiently.

Features
--------
- Dual Scraping Methods: Choose between Selenium (slower, more reliable) or BeautifulSoup (faster, lightweight).
- Direct Retailer Search: Scrapes prices directly from popular Australian plant retailers.
- Custom Exclusions: Exclude specific URLs (e.g., irrelevant sites) from search results.
- CAPTCHA Handling: Option to pause for manual CAPTCHA solving (Selenium only).
- Flexible Output: Display up to 3 prices per plant with source URLs; export results to CSV or Excel.
- GUI Interface: Built with Tkinter for easy interaction, including plant list input, column selection, and progress tracking.
- URL-Only Sources: Exports clean URLs (e.g., https://www.bunnings.com.au/...) without additional prefixes.

Requirements
------------
- Python: 3.8 or higher
- Operating System: Windows, macOS, or Linux
- Dependencies:
  - tkinter (usually included with Python)
  - pandas
  - requests
  - beautifulsoup4
  - selenium
  - webdriver_manager

Installation
------------
1. Clone or Download:
   - Download the script (plant_scraper1.py) from this repository or copy it to your local machine.

2. Install Python:
   - Ensure Python 3.8+ is installed. Download from https://www.python.org/downloads/.

3. Install Dependencies:
   - Open a terminal in the project directory (D:\PlantScraper) and run:
     pip install pandas requests beautifulsoup4 selenium webdriver_manager

4. Optional - Logo:
   - Place a logo.png file in the project directory to set a custom window icon (otherwise, the default Tkinter icon is used).

Usage
-----
1. Run the Application:
   - Navigate to the project directory in a terminal:
     cd D:\PlantScraper
   - Execute the script:
     python plant_scraper1.py

2. Interface Overview:
   - Left Panel: Enter plant names (one per line).
   - Right Panel:
     - Columns: Select which columns to display (Plant, Price1, Source1, etc.).
     - Results: View scraped data in a table.
     - Excluded URLs: Add URLs to skip (e.g., succulentsonline.com.au).
     - Log: Monitor scraping progress and errors.
   - Bottom Controls:
     - Search Method: Choose Selenium or BeautifulSoup.
     - CAPTCHA Handling: Enable/disable pausing for CAPTCHAs.
     - Buttons: Start, Stop, Continue After CAPTCHA.

3. Scraping:
   - Enter plant names (e.g., "Aloe Vera", "Echeveria Elegans").
   - Optionally add excluded URLs.
   - Select your search method and CAPTCHA preference.
   - Click "Start Scraping".
   - Results will populate the table with up to 3 prices and their URLs per plant.

4. Exporting Results:
   - After scraping, choose "File > Save Results" or wait for the prompt.
   - Select columns to export and save as .csv or .xlsx.

5. Interacting with Results:
   - Double-click a source URL in the table to open it in your browser.

Example Input
-------------
Aloe Vera
Echeveria Elegans
Haworthia Fasciata
Crassula Ovata (Jade Plant)

Example Output (CSV)
--------------------
Plant              | Price1  | Source1                            | Price2  | Source2                            | Price3  | Source3
-------------------|---------|------------------------------------|---------|------------------------------------|---------|------------------------------------
Aloe Vera         | $12.95  | https://www.bunnings.com.au/...   | $15.00  | https://www.flowerpower.com.au/... | Not found | No price found from any retailer
Echeveria Elegans | $8.50   | https://www.gardenexpress.com.au/... | $9.95 | https://www.mudgeesucculents.com.au/... | $10.00 | https://www.bunnings.com.au/...

Tips
----
- Specific Names: Use precise plant names for better results (e.g., "Crassula Ovata" instead of "Jade").
- Exclusions: Add irrelevant sites to the "Excluded URLs" box to filter noise.
- Selenium: Use for sites requiring JavaScript; expect a browser window to open.
- BeautifulSoup: Faster but may fail on JavaScript-heavy pages or trigger CAPTCHAs.

Troubleshooting
---------------
- AttributeError: Ensure all dependencies are installed and the script is complete.
- No Results: Check internet connection, site availability, or try the other scraping method.
- CAPTCHA Issues: Enable "Pause for CAPTCHAs" with Selenium to solve manually.
- Export Fails: Verify you have write permissions in the save directory.

Limitations
-----------
- Google Dependency: Relies on Google search results, which may change structure or block requests.
- Retailer Support: Limited to predefined retailers (Bunnings, Flower Power, Garden Express).
- Rate Limiting: Excessive scraping may trigger CAPTCHAs or IP bans.

Contributing
------------
Feel free to fork this project, submit pull requests, or report issues. Suggestions for additional retailers or features are welcome!

License
-------
This project is open-source and available under the MIT License. Use it freely, but credit the author where appropriate.

Contact
-------
For support or inquiries, reach out to Jayasanka Dissanayake via [jayasanka9810@gmail.com (replace with your contact if desired).
