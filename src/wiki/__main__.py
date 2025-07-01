"""
Package entry point for the wiki scraper.

This allows running the scraper as a module:
python -m src.wiki
"""
from .cli import main

if __name__ == "__main__":
    main()
