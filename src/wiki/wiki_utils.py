from bs4 import BeautifulSoup, Tag
from typing import Optional, Dict, List

def safe_find(element: Optional[Tag], name: str, **kwargs) -> Optional[Tag]:
    if element and hasattr(element, "find"):
        return element.find(name, **kwargs)
    return None

def safe_find_all(element: Optional[Tag], name: str, **kwargs) -> List[Tag]:
    if element and hasattr(element, "find_all"):
        return element.find_all(name, **kwargs)
    return []

def safe_get_text(element: Optional[Tag], *args, **kwargs) -> str:
    if element and hasattr(element, "get_text"):
        return element.get_text(*args, **kwargs)
    return ""

def safe_get_attr(element: Optional[Tag], attr: str) -> Optional[str]:
    if element and hasattr(element, "get"):
        return element.get(attr)
    return None