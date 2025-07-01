"""
This module provides a command-line interface for the scraper.
"""
import logging
from pathlib import Path
import pandas as pd
from .scraper import WikiScraper
from . import utils

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def main():
    """Main function with enhanced CLI interface."""
    print("🎬 Robust Wikipedia Celebrity Scraper v3.0")
    print("=" * 60)

    # List available mapping files
    list_folder = Path(__file__).parent / "List"
    csv_files = sorted(list_folder.glob("*.csv"))

    if not csv_files:
        print(f"❌ No CSV mapping files found in {list_folder}. Exiting.")
        return

    print("📁 Found the following mapping files:")
    for i, csv_file in enumerate(csv_files, 1):
        try:
            df = pd.read_csv(csv_file)
            row_count = len(df)
            print(f"  {i:2d}. {csv_file.name}: {row_count} URLs")
        except Exception as e:
            print(f"  - {csv_file.name}: Error reading file ({e})")

    # Ask user to select a mapping file
    selected_index = -1
    while selected_index == -1:
        try:
            selection = input(f"\n▶️  Select a mapping file to process (1-{len(csv_files)}): ")
            selected_index = int(selection.strip()) - 1
            if not (0 <= selected_index < len(csv_files)):
                print(f"⚠️ Invalid selection. Please enter a number between 1 and {len(csv_files)}.")
                selected_index = -1
        except ValueError:
            print("⚠️ Invalid input. Please enter a number.")

    selected_csv = csv_files[selected_index]
    print(f"✅ Using mapping file: {selected_csv.name}")

    # Initialize scraper and load the selected mapping
    try:
        scraper = WikiScraper(config_file='scraping_config.json')
        scraper.config['categories']['mapping_file'] = str(selected_csv)
        scraper.category_mapping = utils.load_category_mapping(scraper.config)

    except Exception as e:
        print(f"❌ Error initializing scraper: {e}")
        return

    urls = list(scraper.category_mapping.keys())
    if not urls:
        print("❌ No URLs found in the selected category mapping file!")
        return

    print(f"\n📋 Found {len(urls)} URLs in {selected_csv.name}:")
    for i, url in enumerate(urls, 1):
        category_info = scraper.category_mapping[url]
        print(f"  {i:2d}. {category_info.get('category_name', 'N/A')} ({category_info.get('region', 'N/A')}) - {url}")

    # Get user preferences
    print("\n🔧 Scraping Options:")

    limit = None  # No limit by default

    # URL selection
    url_selection = input("🎯 Scrape all URLs or select specific ones? [all/select]: ").lower().strip()

    if url_selection == 'select':
        print("📝 Select URLs (comma-separated numbers, e.g., 1,3,5):")
        try:
            selection = input("Selection: ").strip()
            indices = [int(x.strip()) - 1 for x in selection.split(',')] 
            selected_urls = [urls[i] for i in indices if 0 <= i < len(urls)]
            urls = selected_urls
            print(f"✅ Selected {len(urls)} URLs")
        except (ValueError, IndexError):
            print("⚠️ Invalid selection, using all URLs")

    # Confirm and start
    print(f"\n🚀 Ready to scrape {len(urls)} URLs")
    print(f"⚙️ Rate limit: {scraper.config['rate_limit']['delay_between_requests']}s between requests")
    print(f"📁 Output directory: {scraper.output_dir}")

    start_input = input("\n▶️  Start scraping? (y/n): ").lower()
    if start_input != 'y':
        print("🛑 Scraping cancelled")
        return

    # Start scraping
    try:
        scraper.scrape_from_urls(urls, limit=limit)
        print(f"\n🎉 Scraping completed successfully!")
        print(f"📂 Check output files in: {scraper.output_dir}")
    except KeyboardInterrupt:
        print("\n⚠️ Scraping interrupted by user")
        print("📊 Progress has been saved and can be resumed later")
    except Exception as e:
        logger.error(f"❌ Error during scraping: {e}")
        print(f"❌ Scraping failed: {e}")

if __name__ == "__main__":
    main()