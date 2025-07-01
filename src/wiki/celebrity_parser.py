import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from .wiki_utils import safe_find, safe_find_all, safe_get_text

def extract_comprehensive_info(soup: BeautifulSoup) -> Dict:
    info = {
        'full_name': None, 'birth_name': None, 'other_names': [],
        'date_of_birth': None, 'place_of_birth': None, 'birth_time': None,
        'date_of_death': None, 'place_of_death': None,
        'occupation': None, 'nationality': None, 'citizenship': [],
        'religion': None, 'height': None, 'weight': None,
        'years_active': None, 'debut_work': None, 'debut_year': None,
        'spouse': [], 'children': [], 'parents': {}, 'siblings': [],
        'external_urls': {}, 'social_media': {},
        'profile_summary': None, 'short_bio': None,
        'profile_image_url': None, 'profile_image_caption': None,
        'wikipedia_categories': []
    }
    extract_from_infobox(soup, info)
    extract_profile_image(soup, info)
    extract_profile_summary(soup, info)
    extract_wikipedia_categories(soup, info)
    extract_external_links(soup, info)
    return info

def extract_from_infobox(soup: BeautifulSoup, info: Dict):
    infobox = safe_find(soup, 'table', class_='infobox')
    if not infobox:
        return
    for row in safe_find_all(infobox, 'tr'):
        th = safe_find(row, 'th')
        td = safe_find(row, 'td')
        if not th or not td:
            continue
        label = safe_get_text(th, strip=True).lower()
        value = safe_get_text(td, " ", strip=True)
        if 'born' in label:
            info['date_of_birth'] = parse_date(value)
            info['place_of_birth'] = parse_place(value)
        elif 'birth name' in label or 'birth_name' in label:
            info['birth_name'] = value
        elif 'other name' in label or 'also known as' in label:
            info['other_names'] = [name.strip() for name in value.split(',')]
        elif 'died' in label:
            info['date_of_death'] = parse_date(value)
            info['place_of_death'] = parse_place(value)
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
        elif 'years active' in label:
            info['years_active'] = value
        elif 'debut' in label:
            info['debut_work'] = value
        elif 'spouse' in label or 'partner' in label:
            info['spouse'] = parse_family_relations(value, 'spouse')
        elif 'children' in label:
            info['children'] = parse_family_relations(value, 'children')
        elif 'parent' in label:
            info['parents'] = parse_parents(value)

def extract_profile_image(soup: BeautifulSoup, info: Dict):
    infobox = safe_find(soup, 'table', class_='infobox')
    if infobox:
        img = safe_find(infobox, 'img')
        if img:
            src = img.get('src', '')
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://en.wikipedia.org' + src
            info['profile_image_url'] = src
            info['profile_image_caption'] = img.get('alt', '')

def extract_profile_summary(soup: BeautifulSoup, info: Dict):
    content_div = safe_find(soup, 'div', class_='mw-parser-output')
    if content_div:
        paragraphs = safe_find_all(content_div, 'p')
        for para in paragraphs:
            text = safe_get_text(para, strip=True)
            if len(text) > 50:
                info['profile_summary'] = text[:1000]
                info['short_bio'] = text[:300]
                break

def extract_wikipedia_categories(soup: BeautifulSoup, info: Dict):
    catlinks = safe_find(soup, 'div', id='catlinks')
    if catlinks:
        categories = []
        for link in safe_find_all(catlinks, 'a'):
            href = link.get('href', '')
            if href.startswith('/wiki/Category:'):
                category_name = safe_get_text(link, strip=True)
                if category_name and 'births' not in category_name.lower():
                    categories.append(category_name)
        info['wikipedia_categories'] = categories

def extract_external_links(soup: BeautifulSoup, info: Dict):
    external_section = safe_find(soup, 'span', {'id': 'External_links'})
    if external_section:
        parent = external_section.find_parent()
        section = parent.find_next_sibling('ul') if parent else None
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

def parse_date(text: str) -> Optional[str]:
    date_patterns = [
        r'(\d{1,2}\s+\w+\s+\d{4})',
        r'(\w+\s+\d{1,2},?\s+\d{4})',
        r'(\d{4}-\d{2}-\d{2})',
        r'(\d{1,2}/\d{1,2}/\d{4})',
        r'(\d{1,2}-\d{1,2}-\d{4})'
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    return None

def parse_place(text: str) -> Optional[str]:
    if ',' in text:
        parts = text.split(',')
        if len(parts) > 1:
            place_parts = []
            for part in parts[1:]:
                cleaned = re.sub(r'^in\s+', '', part.strip(), flags=re.IGNORECASE)
                if cleaned:
                    place_parts.append(cleaned)
            return ', '.join(place_parts) if place_parts else None
    return None

def parse_family_relations(text: str, relation_type: str) -> List[Dict]:
    relations = []
    if not text:
        return relations
    items = re.split(r'[;,]|\n', text)
    for item in items:
        item = item.strip()
        if item:
            relation_info = {'name': item}
            date_match = re.search(r'\(([^)]+)\)', item)
            if date_match:
                date_info = date_match.group(1)
                relation_info['date_info'] = date_info
                relation_info['name'] = re.sub(r'\([^)]+\)', '', item).strip()
            relations.append(relation_info)
    return relations

def parse_parents(text: str) -> Dict:
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