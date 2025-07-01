from bs4 import BeautifulSoup

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
            info['date_of_birth'] = self._parse_date(value)
            info['place_of_birth'] = self._parse_place(value)
        elif 'birth name' in label or 'birth_name' in label:
            info['birth_name'] = value
        elif 'other name' in label or 'also known as' in label:
            info['other_names'] = [name.strip() for name in value.split(',')]
        
        # Death information
        elif 'died' in label:
            info['date_of_death'] = self._parse_date(value)
            info['place_of_death'] = self._parse_place(value)
        
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
        paragraphs = content_div.find_all('p')
        for para in paragraphs:
            text = para.get_text(strip=True)
            if len(text) > 50:
                info['profile_summary'] = text[:1000]
                info['short_bio'] = text[:300]
                break

def _extract_wikipedia_categories(self, soup: BeautifulSoup, info: Dict):
    """Extract categories from Wikipedia page."""
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
  external_section = soup.find('span', {'id': 'External_links'})
  if external_section:
      section = external_section.find_parent().find_next_sibling('ul')
      if section:
          for link in section.find_all('a', href=True):
              href = link['href']
              text = link.get_text(strip=True).lower()
              
              if 'imdb.com' in href:
                  info['external_urls']['imdb'] = href
              elif 'instagram.com' in href:
                  info['social_media']['instagram'] = href
              elif 'twitter.com' in href or 'x.com' in href:
                  info['social_media']['twitter'] = href
              elif 'facebook.com' in href:
                  info['social_media']['facebook'] = href