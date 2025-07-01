import pandas as pd
from pathlib import Path
from .scraper import RobustWikiScraper

def main():
    print("🎬 Robust Wikipedia Celebrity Scraper v3.0")
    print("=" * 60)
    list_folder = Path(__file__).parent / "List"
    csv_files = sorted(list_folder.glob("*.csv"))
    print(f"📁 Found {len(csv_files)} CSV files in {list_folder}:")
    total_rows = 0
    file_rows = []
    for csv_file in csv_files:
        try:
            df = pd.read_csv(csv_file)
            row_count = len(df)
            print(f"  - {csv_file.name}: {row_count} rows")
            total_rows += row_count
            file_rows.append((csv_file, row_count))
        except Exception as e:
            print(f"  - {csv_file.name}: Error reading file ({e})")
    print(f"\n📊 Total number of list items to download: {total_rows}")
    proceed = input("\n▶️  Continue with download? (y/n): ").lower()
    if proceed != 'y':
        print("🛑 Exiting.")
        return
    for csv_file, row_count in file_rows:
        output_file = Path("scraped_data") / f"{csv_file.stem}_celebrities.csv"
        if output_file.exists():
            print(f"⏭️  Skipping {csv_file.name} (output already exists)")
            continue
        try:
            scraper = RobustWikiScraper()
        except Exception as e:
            print(f"❌ Error initializing scraper: {e}")
            return
        urls = list(scraper.category_mapping.keys())
        if not urls:
            print("❌ No URLs found in category mapping!")
            return
        print(f"📋 Found {len(urls)} URLs in category mapping:")
        for i, url in enumerate(urls, 1):
            category_info = scraper.category_mapping[url]
            print(f"  {i:2d}. {category_info['category_name']} ({category_info['region']}) - {url}")
        print("\n🔧 Scraping Options:")
        limit = None
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
        print(f"\n🚀 Ready to scrape {len(urls)} URLs")
        print(f"⚙️ Rate limit: {scraper.config['rate_limit']['delay_between_requests']}s between requests")
        print(f"📁 Output directory: {scraper.output_dir}")
        start_input = input("\n▶️  Start scraping? (y/n): ").lower()
        if start_input != 'y':
            print("🛑 Scraping cancelled")
            return
        try:
            scraper.scrape_from_urls(urls, limit=limit)
            print(f"\n🎉 Scraping completed successfully!")
            print(f"📂 Check output files in: {scraper.output_dir}")
        except KeyboardInterrupt:
            print("\n⚠️ Scraping interrupted by user")
            print("📊 Progress has been saved and can be resumed later")
        except Exception as e:
            print(f"❌ Scraping failed: {e}")

if __name__ == "__main__":
    main()