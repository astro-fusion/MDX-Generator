
Contains all the logic for parsing HTML and extracting data.

import re
from typing import Dict, List, Optional
from bs4 import BeautifulSoup
from urllib.parse import urljoin

def is_valid_celebrity_link(href: str, text: str) -> bool:
    """Check if link is valid celebrity page."""
    if not href.startswith('/wiki/') or not text:
        return False

    skip_patterns = [
        'category:', 'file:', 'template:', 'help:', 'talk:', 'user:',
        'list_of_', 'portal:', 'wikipedia:', 'special:', 'disambiguation'
    ]

    return not any(pattern in href.lower() for pattern in skip_patterns)

def get_celebrity_names_from_list_page(soup: BeautifulSoup, url: str, category_mapping: Dict) -> List[Dict]:
    """Extract celebrity names with category mapping from external file."""
    celebrities = []

    category_info = category_mapping.get(url, {
        'category_name': 'Unknown Category',
        'category_group': 'Entertainment & Media',
        'category_description': 'Automatically detected category',
        'is_primary': True,
        'region': 'Unknown',
        'language': 'English'
    })

    links = soup.find_all('a', href=True)

    for link in links:
        href = link['href']
        if is_valid_celebrity_link(href, link.text):
            celebrity_url = urljoin('https://en.wikipedia.org', href)
            celebrity_slug = href.split('/wiki/')[-1]

            celebrities.append({
                'name': link.text.strip(),
                'url': celebrity_url,
                'slug': celebrity_slug,
                'source_category': category_info['category_name'],
                'source_group': category_info['category_group'],
                'region': category_info['region'],
                'language': category_info['language'],
                'source_url': url,
                'is_primary_category': category_info['is_primary']
            })

    return celebrities

def _parse_date(text: str) -> Optional[str]:
    """Parse dates from various formats."""
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

def _parse_place(text: str) -> Optional[str]:
    """Parse birth/death place from text."""
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

def _parse_family_relations(text: str, relation_type: str) -> List[Dict]:
    """Parse family relations from infobox text."""
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

def _parse_parents(text: str) -> Dict:
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

def extract_comprehensive_info(soup: BeautifulSoup) -> Dict:
    """Extract comprehensive information from a celebrity's Wikipedia page."""
    infobox = soup.find('table', class_='infobox')
    if not infobox:
        return {}

    info = {}
    rows = infobox.find_all('tr')

    for row in rows:
        header = row.find('th')
        data = row.find('td')

        if header and data:
            header_text = header.text.strip().lower().replace(' ', '_')
            data_text = data.text.strip()
            info[header_text] = data_text

    # Extract specific fields
    date_of_birth = info.get('born')
    place_of_birth = info.get('born')
    occupation = info.get('occupation')
    nationality = info.get('nationality')
    spouse = info.get('spouse(s)')

    # Extract summary
    summary_p = soup.find('p', class_=lambda x: x is None or 'mw-empty-elt' not in x)
    summary = summary_p.text.strip() if summary_p else None

    # Extract image
    image_url = None
    image_tag = infobox.find('img')
    if image_tag and image_tag.has_attr('src'):
        image_url = urljoin('https://en.wikipedia.org/', image_tag['src'])

    return {
        "profile_summary": summary,
        "date_of_birth": _parse_date(date_of_birth) if date_of_birth else None,
        "place_of_birth": _parse_place(place_of_birth) if place_of_birth else None,
        "occupation": [o.strip() for o in occupation.split(',')] if occupation else [],
        "nationality": nationality,
        "profile_image_url": image_url,
        "external_urls": [],
        "spouse": _parse_family_relations(spouse, 'spouse') if spouse else [],
    }
