import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from urllib.parse import urljoin
import logging
from requests.adapters import HTTPAdapter, Retry

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ActorDataScraper:
    """Scrapes actor data from Wikipedia list pages and individual actor pages."""
    SLEEP_BETWEEN_LISTS = 1  # seconds between list page requests
    SLEEP_BETWEEN_ACTORS = 2  # seconds between actor profile requests

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'ActorDataScraper/1.0 (your-email@example.com)'
        })
        # Add retry strategy to handle transient network errors
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        self.actors_data = []

    def get_actor_names_from_list_page(self, url):
        """
        Extract actor names and Wikipedia URLs from a Wikipedia list page.
        Returns a list of dicts: [{'name': ..., 'url': ...}, ...]
        """
        try:
            logger.info(f"📥 Fetching actor list from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            # Use lxml parser for speed
            soup = BeautifulSoup(response.content, 'lxml')
            actors = []
            
            # Find all links to actor pages
            links = soup.find_all('a', href=True)
            logger.info(f"🔍 Processing {len(links)} links...")
            
            for link in links:
                href = link['href']
                # Only consider /wiki/ links that are not categories, files, etc.
                if (
                    href.startswith('/wiki/') and link.text and
                    not any(x in href.lower() for x in ['category:', 'file:', 'template:', 'help:', 'talk:', 'user:'])
                ):
                    actors.append({
                        'name': link.text.strip(),
                        'url': urljoin('https://en.wikipedia.org', href)
                    })
            
            logger.info(f"✅ Found {len(actors)} potential actors from {url}")
            return actors
        except Exception as e:
            logger.error(f"❌ Error fetching actor list from {url}: {e}")
            return []

    def extract_birth_info_from_infobox(self, soup):
        """
        Extract birth information from a Wikipedia infobox.
        Returns a dict with date_of_birth, place_of_birth, etc.
        """
        birth_info = {
            'date_of_birth': None,
            'place_of_birth': None,
            'birth_time': None,
            'full_name': None,
            'occupation': None,
            'nationality': None
        }
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            return birth_info

        for row in infobox.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
            label = th.get_text(strip=True).lower()
            value = td.get_text(" ", strip=True)
            
            # Extract birth date and place from 'born' field
            if 'born' in label:
                birth_info['date_of_birth'] = self.parse_birth_date(value)
                birth_info['place_of_birth'] = self.parse_birth_place(value)
            # Extract occupation
            elif 'occupation' in label:
                birth_info['occupation'] = value
            # Extract nationality or citizenship
            elif 'nationality' in label or 'citizenship' in label:
                birth_info['nationality'] = value
            # Extract birth place specifically (sometimes separate from 'born')
            elif 'birth place' in label or 'birthplace' in label:
                birth_info['place_of_birth'] = value
            # Extract full name or birth name
            elif 'birth name' in label or 'full name' in label:
                birth_info['full_name'] = value
                
        return birth_info

    def parse_birth_date(self, birth_text):
        """
        Extract date from birth text using common patterns.
        """
        date_patterns = [
            r'(\d{1,2}\s+\w+\s+\d{4})',      # 2 November 1965
            r'(\w+\s+\d{1,2},?\s+\d{4})',    # November 2, 1965
            r'(\d{4}-\d{2}-\d{2})',          # 1965-11-02
            r'(\d{1,2}/\d{1,2}/\d{4})',      # 02/11/1965
        ]
        for pattern in date_patterns:
            match = re.search(pattern, birth_text)
            if match:
                return match.group(1)
        return None

    def parse_birth_place(self, birth_text):
        """
        Extract place from birth text (after the date, separated by comma).
        """
        if ',' in birth_text:
            parts = birth_text.split(',')
            if len(parts) > 1:
                # Remove the first part (usually the date) and join the rest
                place = ','.join(parts[1:]).strip()
                # Clean up common prefixes
                place = re.sub(r'^in\s+', '', place, flags=re.IGNORECASE)
                return place
        return None

    def get_actor_profile(self, actor_url):
        """
        Get detailed profile of an actor from their Wikipedia page.
        Returns a dict with extracted information.
        """
        try:
            response = self.session.get(actor_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Get birth info from infobox
            birth_info = self.extract_birth_info_from_infobox(soup)
            
            # Get first paragraph as profile summary
            profile_summary = ""
            content_div = soup.find('div', class_='mw-parser-output')
            if content_div:
                first_para = content_div.find('p')
                if first_para:
                    profile_summary = first_para.get_text(strip=True)[:500]
            
            birth_info['profile_summary'] = profile_summary
            birth_info['wikipedia_url'] = actor_url
            return birth_info
        except Exception as e:
            logger.error(f"❌ Error scraping {actor_url}: {e}")
            return None

    def scrape_actors_from_urls(self, urls, limit=None):
        """
        Scrape actors from multiple Wikipedia list URLs.
        Optionally limit the number of actors processed.
        """
        all_actors = []
        
        # Process each URL with confirmation
        for i, url in enumerate(urls, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🌐 Processing URL {i}/{len(urls)}: {url}")
            logger.info(f"{'='*60}")
            
            actors = self.get_actor_names_from_list_page(url)
            all_actors.extend(actors)
            
            logger.info(f"📊 Progress: {len(all_actors)} total actors found so far")
            
            # Ask for confirmation before continuing to next URL (except for last URL)
            if i < len(urls):
                logger.info(f"⏳ Waiting {self.SLEEP_BETWEEN_LISTS} seconds before next URL...")
                time.sleep(self.SLEEP_BETWEEN_LISTS)
                
                user_input = input(f"\n🤔 Continue to next URL ({i+1}/{len(urls)})? (y/n/skip): ").lower()
                if user_input == 'n':
                    logger.info("🛑 Stopping at user request")
                    break
                elif user_input == 'skip':
                    logger.info(f"⏭️ Skipping URL {i+1}")
                    continue

        # Remove duplicates based on URL using a dict
        logger.info(f"\n🔄 Removing duplicates from {len(all_actors)} actors...")
        unique_actors = {actor['url']: actor for actor in all_actors}.values()
        actor_list = list(unique_actors)
        
        if limit:
            actor_list = actor_list[:limit]
            logger.info(f"✂️ Limited to {limit} actors for processing")
        
        logger.info(f"📋 Processing {len(actor_list)} unique actors")

        # Get detailed info for each actor with progress tracking
        successful_profiles = 0
        failed_profiles = 0
        
        for i, actor in enumerate(actor_list):
            # Progress indicator
            progress_percent = (i / len(actor_list)) * 100
            logger.info(f"\n📝 [{i+1}/{len(actor_list)}] ({progress_percent:.1f}%) Processing: {actor['name']}")
            
            profile = self.get_actor_profile(actor['url'])
            if profile:
                profile['name'] = actor['name']
                self.actors_data.append(profile)
                successful_profiles += 1
                logger.info(f"✅ Successfully extracted data for {actor['name']}")
            else:
                failed_profiles += 1
                logger.warning(f"⚠️ Failed to extract data for {actor['name']}")
            
            # Show current statistics every 10 actors
            if (i + 1) % 10 == 0:
                logger.info(f"📊 Current stats: {successful_profiles} successful, {failed_profiles} failed")
            
            time.sleep(self.SLEEP_BETWEEN_ACTORS)  # Be respectful to Wikipedia
        
        # Final summary
        logger.info(f"\n🎉 Scraping completed!")
        logger.info(f"✅ Successful profiles: {successful_profiles}")
        logger.info(f"❌ Failed profiles: {failed_profiles}")
        logger.info(f"📈 Success rate: {(successful_profiles/len(actor_list)*100):.1f}%")
        
        return self.actors_data

    def save_data(self, filename_base='bollywood_actors'):
        """
        Save scraped data in CSV and JSON formats.
        """
        if not self.actors_data:
            logger.warning("⚠️ No data to save!")
            return
            
        logger.info(f"💾 Saving data...")
        df = pd.DataFrame(self.actors_data)
        
        csv_filename = f"{filename_base}.csv"
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        logger.info(f"✅ Data saved to {csv_filename}")

        json_filename = f"{filename_base}.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.actors_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Data saved to {json_filename}")

        self.print_statistics()

    def print_statistics(self):
        """
        Print scraping statistics.
        """
        total = len(self.actors_data)
        if total == 0:
            logger.info("📊 No data to analyze")
            return
            
        with_dob = sum(1 for actor in self.actors_data if actor.get('date_of_birth'))
        with_place = sum(1 for actor in self.actors_data if actor.get('place_of_birth'))
        with_nationality = sum(1 for actor in self.actors_data if actor.get('nationality'))
        with_occupation = sum(1 for actor in self.actors_data if actor.get('occupation'))
        
        logger.info(f"\n📊 --- Scraping Statistics ---")
        logger.info(f"👥 Total actors processed: {total}")
        logger.info(f"🎂 Actors with birth date: {with_dob} ({with_dob/total*100:.1f}%)")
        logger.info(f"🌍 Actors with birth place: {with_place} ({with_place/total*100:.1f}%)")
        logger.info(f"🏳️ Actors with nationality: {with_nationality} ({with_nationality/total*100:.1f}%)")
        logger.info(f"🎭 Actors with occupation: {with_occupation} ({with_occupation/total*100:.1f}%)")

# Main execution
def main():
    """
    Main function to run the scraper with user interaction.
    """
    print("🎬 Actor Data Scraper Starting...")
    print("=" * 50)
    
    scraper = ActorDataScraper()
    
    # Wikipedia list URLs to scrape
    urls = [
        "https://en.wikipedia.org/wiki/List_of_Hindi_film_actors",
        "https://en.wikipedia.org/wiki/List_of_Indian_male_film_actors", 
        "https://en.wikipedia.org/wiki/List_of_Indian_film_actresses"
    ]
    
    print(f"📋 URLs to process: {len(urls)}")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # Ask user for limit
    try:
        limit_input = input("\n🔢 Enter limit for testing (press Enter for no limit): ").strip()
        limit = int(limit_input) if limit_input else None
        if limit:
            print(f"✂️ Processing will be limited to {limit} actors")
    except ValueError:
        limit = None
        print("⚠️ Invalid input, proceeding without limit")
    
    # Confirm start
    start_input = input("\n🚀 Start scraping? (y/n): ").lower()
    if start_input != 'y':
        print("🛑 Scraping cancelled by user")
        return
    
    # Scrape data
    scraper.scrape_actors_from_urls(urls, limit=limit)
    
    # Save data
    if scraper.actors_data:
        filename = input("\n💾 Enter filename base (press Enter for 'bollywood_actors_birth_data'): ").strip()
        if not filename:
            filename = 'bollywood_actors_birth_data'
        scraper.save_data(filename)
    else:
        print("❌ No data collected to save")

if __name__ == "__main__":
    main()
