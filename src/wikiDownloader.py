import requests
from bs4 import BeautifulSoup
import pandas as pd
import json
import time
import re
from urllib.parse import urljoin, urlparse
import logging
from requests.adapters import HTTPAdapter, Retry
from datetime import datetime
import hashlib
from typing import Dict, List, Optional, Tuple
import wikipedia

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class EnhancedActorDataScraper:
    """Enhanced scraper for comprehensive actor data from Wikipedia."""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'EnhancedActorDataScraper/2.0 (Educational Purpose)'
        })
        retries = Retry(total=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        self.session.mount('https://', HTTPAdapter(max_retries=retries))
        
        self.actors_data = []
        self.categories_data = []
        self.locations_data = []
        
        # Category mapping for different Wikipedia list pages
        self.category_mapping = {
            'List_of_Hindi_film_actors': {'group': 'Entertainment', 'category': 'Bollywood Actor'},
            'List_of_Indian_male_film_actors': {'group': 'Entertainment', 'category': 'Indian Male Actor'},
            'List_of_Indian_film_actresses': {'group': 'Entertainment', 'category': 'Indian Actress'},
            'List_of_Telugu_actors': {'group': 'Entertainment', 'category': 'Telugu Actor'},
            'List_of_Tamil_actors': {'group': 'Entertainment', 'category': 'Tamil Actor'},
            'List_of_Malayalam_actors': {'group': 'Entertainment', 'category': 'Malayalam Actor'},
            'List_of_Kannada_actors': {'group': 'Entertainment', 'category': 'Kannada Actor'},
            'List_of_Bengali_actors': {'group': 'Entertainment', 'category': 'Bengali Actor'},
        }

    def get_wikipedia_page_id(self, url: str) -> Optional[str]:
        """Extract Wikipedia page ID from URL or API."""
        try:
            # Extract page title from URL
            page_title = url.split('/wiki/')[-1]
            
            # Use Wikipedia API to get page ID
            api_url = "https://en.wikipedia.org/api/rest_v1/page/summary/" + page_title
            response = self.session.get(api_url)
            if response.status_code == 200:
                data = response.json()
                return str(data.get('pageid', ''))
        except Exception as e:
            logger.error(f"Error getting Wikipedia page ID: {e}")
        return None

    def get_actor_names_from_list_page(self, url: str) -> List[Dict]:
        """Enhanced extraction of actor names and metadata from list pages."""
        try:
            logger.info(f"📥 Fetching actor list from: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            actors = []
            page_slug = url.split('/wiki/')[-1]
            category_info = self.category_mapping.get(page_slug, {
                'group': 'Entertainment',
                'category': 'Actor'
            })
            
            # Find all links to actor pages
            links = soup.find_all('a', href=True)
            logger.info(f"🔍 Processing {len(links)} links...")
            
            for link in links:
                href = link['href']
                if (
                    href.startswith('/wiki/') and link.text and
                    not any(x in href.lower() for x in [
                        'category:', 'file:', 'template:', 'help:', 'talk:', 'user:',
                        'list_of_', 'portal:', 'wikipedia:', 'special:'
                    ])
                ):
                    actor_url = urljoin('https://en.wikipedia.org', href)
                    actor_slug = href.split('/wiki/')[-1]
                    
                    actors.append({
                        'name': link.text.strip(),
                        'url': actor_url,
                        'slug': actor_slug,
                        'source_category': category_info['category'],
                        'source_group': category_info['group'],
                        'source_url': url
                    })
            
            logger.info(f"✅ Found {len(actors)} potential actors from {url}")
            return actors
        except Exception as e:
            logger.error(f"❌ Error fetching actor list from {url}: {e}")
            return []

    def extract_comprehensive_info(self, soup: BeautifulSoup) -> Dict:
        """Extract comprehensive information from Wikipedia page."""
        info = {
            # Basic info
            'full_name': None, 'birth_name': None, 'other_names': [],
            
            # Birth/Death info
            'date_of_birth': None, 'place_of_birth': None, 'birth_time': None,
            'date_of_death': None, 'place_of_death': None,
            
            # Personal details
            'occupation': None, 'nationality': None, 'citizenship': [],
            'religion': None, 'height': None, 'weight': None,
            
            # Career info
            'years_active': None, 'debut_work': None, 'debut_year': None,
            
            # Family info
            'spouse': [], 'children': [], 'parents': {}, 'siblings': [],
            
            # External links
            'external_urls': {}, 'social_media': {},
            
            # Profile info
            'profile_summary': None, 'short_bio': None,
            'profile_image_url': None, 'profile_image_caption': None,
            
            # Categories from page
            'wikipedia_categories': []
        }
        
        # Extract from infobox
        self._extract_from_infobox(soup, info)
        
        # Extract profile image
        self._extract_profile_image(soup, info)
        
        # Extract first paragraph as summary
        self._extract_profile_summary(soup, info)
        
        # Extract Wikipedia categories
        self._extract_wikipedia_categories(soup, info)
        
        # Extract external links
        self._extract_external_links(soup, info)
        
        return info

    def _extract_from_infobox(self, soup: BeautifulSoup, info: Dict):
        """Extract information from Wikipedia infobox."""
        infobox = soup.find('table', class_='infobox')
        if not infobox:
            return
            
        for row in infobox.find_all('tr'):
            th = row.find('th')
            td = row.find('td')
            if not th or not td:
                continue
                
            label = th.get_text(strip=True).lower()
            value = td.get_text(" ", strip=True)
            
            # Birth information
            if 'born' in label:
                info['date_of_birth'] = self._parse_birth_date(value)
                info['place_of_birth'] = self._parse_birth_place(value)
            elif 'birth name' in label or 'birth_name' in label:
                info['birth_name'] = value
            elif 'other name' in label or 'also known as' in label:
                info['other_names'] = [name.strip() for name in value.split(',')]
                
            # Death information
            elif 'died' in label:
                info['date_of_death'] = self._parse_birth_date(value)
                info['place_of_death'] = self._parse_birth_place(value)
                
            # Personal details
            elif 'occupation' in label:
                info['occupation'] = value
            elif 'nationality' in label:
                info['nationality'] = value
            elif 'citizenship' in label:
                info['citizenship'] = [c.strip() for c in value.split(',')]
            elif 'religion' in label:
                info['religion'] = value
            elif 'height' in label:
                info['height'] = value
            elif 'weight' in label:
                info['weight'] = value
                
            # Career information
            elif 'years active' in label:
                info['years_active'] = value
            elif 'debut' in label:
                info['debut_work'] = value
                
            # Family information
            elif 'spouse' in label or 'partner' in label:
                info['spouse'] = self._parse_family_relations(value, 'spouse')
            elif 'children' in label:
                info['children'] = self._parse_family_relations(value, 'children')
            elif 'parent' in label:
                info['parents'] = self._parse_parents(value)

    def _extract_profile_image(self, soup: BeautifulSoup, info: Dict):
        """Extract profile image from infobox."""
        infobox = soup.find('table', class_='infobox')
        if infobox:
            img = infobox.find('img')
            if img and img.get('src'):
                # Convert to full URL
                src = img.get('src')
                if src.startswith('//'):
                    src = 'https:' + src
                elif src.startswith('/'):
                    src = 'https://en.wikipedia.org' + src
                info['profile_image_url'] = src
                info['profile_image_caption'] = img.get('alt', '')

    def _extract_profile_summary(self, soup: BeautifulSoup, info: Dict):
        """Extract profile summary from first paragraph."""
        content_div = soup.find('div', class_='mw-parser-output')
        if content_div:
            # Get first meaningful paragraph
            paragraphs = content_div.find_all('p')
            for para in paragraphs:
                text = para.get_text(strip=True)
                if len(text) > 50:  # Skip very short paragraphs
                    info['profile_summary'] = text[:1000]  # Limit length
                    info['short_bio'] = text[:300]  # Shorter version
                    break

    def _extract_wikipedia_categories(self, soup: BeautifulSoup, info: Dict):
        """Extract categories from Wikipedia page."""
        # Find category links at bottom of page
        catlinks = soup.find('div', id='catlinks')
        if catlinks:
            categories = []
            for link in catlinks.find_all('a'):
                if link.get('href', '').startswith('/wiki/Category:'):
                    category_name = link.get_text(strip=True)
                    if category_name and 'births' not in category_name.lower():
                        categories.append(category_name)
            info['wikipedia_categories'] = categories

    def _extract_external_links(self, soup: BeautifulSoup, info: Dict):
        """Extract external links and social media."""
        # Look for external links section
        external_section = soup.find('span', {'id': 'External_links'})
        if external_section:
            section = external_section.find_parent().find_next_sibling('ul')
            if section:
                for link in section.find_all('a', href=True):
                    href = link['href']
                    text = link.get_text(strip=True).lower()
                    
                    # Categorize links
                    if 'imdb.com' in href:
                        info['external_urls']['imdb'] = href
                    elif 'instagram.com' in href:
                        info['social_media']['instagram'] = href
                    elif 'twitter.com' in href or 'x.com' in href:
                        info['social_media']['twitter'] = href
                    elif 'facebook.com' in href:
                        info['social_media']['facebook'] = href

    def _parse_birth_date(self, birth_text: str) -> Optional[str]:
        """Enhanced date parsing with multiple formats."""
        date_patterns = [
            r'(\d{1,2}\s+\w+\s+\d{4})',      # 2 November 1965
            r'(\w+\s+\d{1,2},?\s+\d{4})',    # November 2, 1965
            r'(\d{4}-\d{2}-\d{2})',          # 1965-11-02
            r'(\d{1,2}/\d{1,2}/\d{4})',      # 02/11/1965
            r'(\d{1,2}-\d{1,2}-\d{4})',      # 02-11-1965
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, birth_text)
            if match:
                return match.group(1)
        return None

    def _parse_birth_place(self, birth_text: str) -> Optional[str]:
        """Enhanced place parsing."""
        if ',' in birth_text:
            parts = birth_text.split(',')
            if len(parts) > 1:
                # Remove date part and join the rest
                place_parts = []
                for part in parts[1:]:
                    cleaned = re.sub(r'^in\s+', '', part.strip(), flags=re.IGNORECASE)
                    if cleaned:
                        place_parts.append(cleaned)
                return ', '.join(place_parts) if place_parts else None
        return None

    def _parse_family_relations(self, text: str, relation_type: str) -> List[Dict]:
        """Parse family relations from infobox text."""
        relations = []
        if not text:
            return relations
            
        # Split by common separators
        items = re.split(r'[;,]|\n', text)
        for item in items:
            item = item.strip()
            if item:
                relation_info = {'name': item}
                
                # Extract dates in parentheses
                date_match = re.search(r'\(([^)]+)\)', item)
                if date_match:
                    date_info = date_match.group(1)
                    relation_info['date_info'] = date_info
                    relation_info['name'] = re.sub(r'\([^)]+\)', '', item).strip()
                
                relations.append(relation_info)
        
        return relations

    def _parse_parents(self, text: str) -> Dict:
        """Parse parent information."""
        parents = {}
        if 'father' in text.lower():
            father_match = re.search(r'father[:\s]+([^,\n]+)', text, re.IGNORECASE)
            if father_match:
                parents['father'] = father_match.group(1).strip()
        
        if 'mother' in text.lower():
            mother_match = re.search(r'mother[:\s]+([^,\n]+)', text, re.IGNORECASE)
            if mother_match:
                parents['mother'] = mother_match.group(1).strip()
        
        return parents

    def get_enhanced_actor_profile(self, actor_data: Dict) -> Optional[Dict]:
        """Get comprehensive actor profile."""
        try:
            response = self.session.get(actor_data['url'], timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'lxml')
            
            # Extract comprehensive information
            profile = self.extract_comprehensive_info(soup)
            
            # Add metadata
            profile.update({
                'name': actor_data['name'],
                'wikipedia_url': actor_data['url'],
                'wikipedia_slug': actor_data['slug'],
                'wikipedia_id': self.get_wikipedia_page_id(actor_data['url']),
                'source_category': actor_data['source_category'],
                'source_group': actor_data['source_group'],
                'data_quality_score': self._calculate_quality_score(profile),
                'last_updated': datetime.now().isoformat()
            })
            
            return profile
        except Exception as e:
            logger.error(f"❌ Error scraping {actor_data['url']}: {e}")
            return None

    def _calculate_quality_score(self, profile: Dict) -> int:
        """Calculate data quality score based on completeness."""
        score = 0
        important_fields = [
            'date_of_birth', 'place_of_birth', 'occupation',
            'profile_summary', 'nationality'
        ]
        
        for field in important_fields:
            if profile.get(field):
                score += 20
        
        # Bonus points for additional data
        if profile.get('profile_image_url'):
            score += 10
        if profile.get('external_urls'):
            score += 5
        if profile.get('spouse'):
            score += 5
        
        return min(score, 100)

    def scrape_actors_from_urls(self, urls: List[str], limit: Optional[int] = None) -> List[Dict]:
        """Enhanced scraping with comprehensive data extraction."""
        all_actors = []
        
        for i, url in enumerate(urls, 1):
            logger.info(f"\n{'='*60}")
            logger.info(f"🌐 Processing URL {i}/{len(urls)}: {url}")
            logger.info(f"{'='*60}")
            
            actors = self.get_actor_names_from_list_page(url)
            all_actors.extend(actors)
            
            logger.info(f"📊 Progress: {len(all_actors)} total actors found so far")
            
            if i < len(urls):
                time.sleep(2)  # Be respectful to Wikipedia

        # Remove duplicates based on slug
        logger.info(f"\n🔄 Removing duplicates from {len(all_actors)} actors...")
        unique_actors = {actor['slug']: actor for actor in all_actors}.values()
        actor_list = list(unique_actors)
        
        if limit:
            actor_list = actor_list[:limit]
            logger.info(f"✂️ Limited to {limit} actors for processing")
        
        logger.info(f"📋 Processing {len(actor_list)} unique actors")

        # Get detailed info for each actor
        successful_profiles = 0
        failed_profiles = 0
        
        for i, actor in enumerate(actor_list):
            progress_percent = (i / len(actor_list)) * 100
            logger.info(f"\n📝 [{i+1}/{len(actor_list)}] ({progress_percent:.1f}%) Processing: {actor['name']}")
            
            profile = self.get_enhanced_actor_profile(actor)
            if profile:
                self.actors_data.append(profile)
                successful_profiles += 1
                logger.info(f"✅ Successfully extracted data for {actor['name']} (Quality: {profile.get('data_quality_score', 0)}%)")
            else:
                failed_profiles += 1
                logger.warning(f"⚠️ Failed to extract data for {actor['name']}")
            
            if (i + 1) % 10 == 0:
                logger.info(f"📊 Current stats: {successful_profiles} successful, {failed_profiles} failed")
            
            time.sleep(3)  # Be more respectful to Wikipedia

        logger.info(f"\n🎉 Scraping completed!")
        logger.info(f"✅ Successful profiles: {successful_profiles}")
        logger.info(f"❌ Failed profiles: {failed_profiles}")
        logger.info(f"📈 Success rate: {(successful_profiles/len(actor_list)*100):.1f}%")
        
        return self.actors_data

    def generate_categories_csv(self):
        """Generate categories CSV for import."""
        categories_set = set()
        
        for actor in self.actors_data:
            # Add source category
            if actor.get('source_category'):
                categories_set.add((
                    actor['source_category'],
                    actor.get('source_group', 'Entertainment'),
                    f"Category from {actor.get('source_category')}"
                ))
            
            # Add Wikipedia categories
            for cat in actor.get('wikipedia_categories', []):
                categories_set.add((
                    cat,
                    'Wikipedia',
                    f"Wikipedia category: {cat}"
                ))
        
        categories_df = pd.DataFrame(list(categories_set), columns=[
            'category_name', 'category_group', 'category_description'
        ])
        
        # Add slug
        categories_df['category_slug'] = categories_df['category_name'].apply(
            lambda x: re.sub(r'[^a-zA-Z0-9]+', '_', x.lower()).strip('_')
        )
        
        return categories_df

    def save_enhanced_data(self, filename_base: str = 'enhanced_bollywood_data'):
        """Save all data in CSV format ready for Supabase import."""
        if not self.actors_data:
            logger.warning("⚠️ No data to save!")
            return
        
        logger.info(f"💾 Saving enhanced data...")
        
        # Prepare actors data for CSV
        actors_for_csv = []
        for actor in self.actors_data:
            csv_row = {
                'wikipedia_id': actor.get('wikipedia_id'),
                'wikipedia_slug': actor.get('wikipedia_slug'),
                'wikipedia_url': actor.get('wikipedia_url'),
                'name': actor.get('name'),
                'full_name': actor.get('full_name'),
                'birth_name': actor.get('birth_name'),
                'other_names': json.dumps(actor.get('other_names', [])),
                'date_of_birth': actor.get('date_of_birth'),
                'place_of_birth': actor.get('place_of_birth'),
                'birth_time': actor.get('birth_time'),
                'date_of_death': actor.get('date_of_death'),
                'place_of_death': actor.get('place_of_death'),
                'occupation': actor.get('occupation'),
                'nationality': actor.get('nationality'),
                'citizenship': json.dumps(actor.get('citizenship', [])),
                'religion': actor.get('religion'),
                'height': actor.get('height'),
                'weight': actor.get('weight'),
                'years_active': actor.get('years_active'),
                'debut_work': actor.get('debut_work'),
                'spouse': json.dumps(actor.get('spouse', [])),
                'children': json.dumps(actor.get('children', [])),
                'parents': json.dumps(actor.get('parents', {})),
                'siblings': json.dumps(actor.get('siblings', [])),
                'external_urls': json.dumps(actor.get('external_urls', {})),
                'social_media': json.dumps(actor.get('social_media', {})),
                'profile_summary': actor.get('profile_summary'),
                'short_bio': actor.get('short_bio'),
                'profile_image_url': actor.get('profile_image_url'),
                'profile_image_caption': actor.get('profile_image_caption'),
                'is_verified': False,
                'data_quality_score': actor.get('data_quality_score', 0),
                'last_updated': actor.get('last_updated')
            }
            actors_for_csv.append(csv_row)
        
        # Save actors CSV
        actors_df = pd.DataFrame(actors_for_csv)
        actors_csv = f"{filename_base}_actors.csv"
        actors_df.to_csv(actors_csv, index=False, encoding='utf-8')
        logger.info(f"✅ Actors data saved to {actors_csv}")
        
        # Save categories CSV
        categories_df = self.generate_categories_csv()
        categories_csv = f"{filename_base}_categories.csv"
        categories_df.to_csv(categories_csv, index=False, encoding='utf-8')
        logger.info(f"✅ Categories data saved to {categories_csv}")
        
        # Generate celebrity_categories mapping
        celebrity_categories = []
        for i, actor in enumerate(self.actors_data):
            # Add source category
            if actor.get('source_category'):
                celebrity_categories.append({
                    'celebrity_wikipedia_slug': actor.get('wikipedia_slug'),
                    'category_slug': re.sub(r'[^a-zA-Z0-9]+', '_', actor['source_category'].lower()).strip('_'),
                    'is_primary': True,
                    'confidence_score': 1.0,
                    'source': 'wikipedia_list'
                })
            
            # Add Wikipedia categories
            for cat in actor.get('wikipedia_categories', [])[:5]:  # Limit to top 5
                celebrity_categories.append({
                    'celebrity_wikipedia_slug': actor.get('wikipedia_slug'),
                    'category_slug': re.sub(r'[^a-zA-Z0-9]+', '_', cat.lower()).strip('_'),
                    'is_primary': False,
                    'confidence_score': 0.8,
                    'source': 'wikipedia_page'
                })
        
        celebrity_categories_df = pd.DataFrame(celebrity_categories)
        celebrity_categories_csv = f"{filename_base}_celebrity_categories.csv"
        celebrity_categories_df.to_csv(celebrity_categories_csv, index=False, encoding='utf-8')
        logger.info(f"✅ Celebrity categories mapping saved to {celebrity_categories_csv}")
        
        # Save complete JSON for backup
        json_filename = f"{filename_base}_complete.json"
        with open(json_filename, 'w', encoding='utf-8') as f:
            json.dump(self.actors_data, f, indent=2, ensure_ascii=False)
        logger.info(f"✅ Complete data saved to {json_filename}")
        
        self.print_enhanced_statistics()

    def print_enhanced_statistics(self):
        """Print comprehensive scraping statistics."""
        total = len(self.actors_data)
        if total == 0:
            logger.info("📊 No data to analyze")
            return
        
        # Calculate statistics
        with_dob = sum(1 for actor in self.actors_data if actor.get('date_of_birth'))
        with_place = sum(1 for actor in self.actors_data if actor.get('place_of_birth'))
        with_image = sum(1 for actor in self.actors_data if actor.get('profile_image_url'))
        with_family = sum(1 for actor in self.actors_data if actor.get('spouse') or actor.get('children'))
        with_external = sum(1 for actor in self.actors_data if actor.get('external_urls'))
        
        avg_quality = sum(actor.get('data_quality_score', 0) for actor in self.actors_data) / total
        
        logger.info(f"\n📊 --- Enhanced Scraping Statistics ---")
        logger.info(f"👥 Total actors processed: {total}")
        logger.info(f"🎂 Actors with birth date: {with_dob} ({with_dob/total*100:.1f}%)")
        logger.info(f"🌍 Actors with birth place: {with_place} ({with_place/total*100:.1f}%)")
        logger.info(f"📷 Actors with profile image: {with_image} ({with_image/total*100:.1f}%)")
        logger.info(f"👨‍👩‍👧‍👦 Actors with family info: {with_family} ({with_family/total*100:.1f}%)")
        logger.info(f"🔗 Actors with external links: {with_external} ({with_external/total*100:.1f}%)")
        logger.info(f"⭐ Average data quality score: {avg_quality:.1f}%")

def main():
    """Main function with enhanced options."""
    print("🎬 Enhanced Actor Data Scraper v2.0")
    print("=" * 50)
    
    scraper = EnhancedActorDataScraper()
    
    # Enhanced URL list
    urls = [
        "https://en.wikipedia.org/wiki/List_of_Hindi_film_actors",
        "https://en.wikipedia.org/wiki/List_of_Indian_male_film_actors", 
        "https://en.wikipedia.org/wiki/List_of_Indian_film_actresses",
        "https://en.wikipedia.org/wiki/List_of_Telugu_actors",
        "https://en.wikipedia.org/wiki/List_of_Tamil_actors",
        "https://en.wikipedia.org/wiki/List_of_Malayalam_actors",
        "https://en.wikipedia.org/wiki/List_of_Kannada_actors",
        "https://en.wikipedia.org/wiki/List_of_Bengali_actors"
    ]
    
    print(f"📋 URLs to process: {len(urls)}")
    for i, url in enumerate(urls, 1):
        print(f"  {i}. {url}")
    
    # User input for limit and filename
    try:
        limit_input = input("\n🔢 Enter limit for testing (press Enter for no limit): ").strip()
        limit = int(limit_input) if limit_input else None
    except ValueError:
        limit = None
    
    filename = input("\n💾 Enter filename base (press Enter for 'enhanced_bollywood_data'): ").strip()
    if not filename:
        filename = 'enhanced_bollywood_data'
    
    # Start scraping
    start_input = input("\n🚀 Start enhanced scraping? (y/n): ").lower()
    if start_input != 'y':
        print("🛑 Scraping cancelled by user")
        return
    
    # Scrape data
    scraper.scrape_actors_from_urls(urls, limit=limit)
    
    # Save data
    if scraper.actors_data:
        scraper.save_enhanced_data(filename)
        print(f"\n🎉 Scraping completed! Check the generated CSV files for Supabase import.")
    else:
        print("❌ No data collected to save")

if __name__ == "__main__":
    main()
