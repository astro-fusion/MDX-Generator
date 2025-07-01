# Robust Wikipedia Celebrity Scraper v3.0

A powerful, modular Wikipedia scraper with incremental saving, rate limiting, and resume capability.

## 🌟 Features

- **Incremental Saving**: Files saved after each URL batch
- **Rate Limiting**: Respectful to Wikipedia servers
- **Resume Capability**: Continue from where you left off
- **Modular Configuration**: Easy to add new regions/categories
- **Multiple Output Formats**: CSV files ready for Supabase import
- **Progress Tracking**: Detailed logging and progress states
- **Error Recovery**: Robust error handling and retries

## 🚀 Quick Start

1. **Install Dependencies**
pip install -r requirements.txt
text

2. **Configure Your Project**
- Edit `scraping_config.json` for rate limits and settings
- Add URLs to `category_mapping.csv` for your target categories

3. **Run the Scraper**
python enhanced_wiki_scraper.py
text

## 📁 Configuration Files

### scraping_config.json
- `project_name`: Output file prefix
- `rate_limit`: Control request frequency
- `incremental`: Enable/disable incremental saving
- `scraping`: Timeout and retry settings

### category_mapping.csv
Add your Wikipedia list URLs with metadata:
- `url`: Wikipedia list page URL
- `category_name`: Category for celebrities
- `category_group`: Broader group classification
- `region`: Geographic region
- `language`: Primary language

## 📊 Output Files

For each URL batch, the scraper creates:
- `*_celebrities.csv`: Main celebrity data
- `*_categories.csv`: Category definitions
- `*_celebrity_categories.csv`: Celebrity-category relationships
- `progress_state.json`: Resume state

## 🔧 Advanced Usage

### Resume Interrupted Scraping
Simply run the script again - it will resume automatically

python enhanced_wiki_scraper.py
text

### Custom Rate Limiting
{
"rate_limit": {
"delay_between_requests": 5.0,
"delay_between_batches": 15.0
}
}
text

### Add New Categories
1. Add URL to `category_mapping.csv`
2. Set appropriate metadata (region, language, etc.)
3. Run scraper - it will automatically process new URLs

## 🌍 Supported Categories

### Entertainment
- Bollywood/Indian Cinema
- Hollywood
- Regional Cinema (Telugu, Tamil, etc.)
- TV Actors

### Sports
- Cricket
- Football/Soccer
- Olympic Athletes
- Regional Sports

### Easy to Extend
- Politicians
- Scientists
- Musicians
- Business Leaders

## 📋 Supabase Import

The generated CSV files are ready for direct import into Supabase:

1. Import `*_categories.csv` first
2. Import `*_celebrities.csv` second
3. Map relationships using `*_celebrity_categories.csv`

## 🛡️ Rate Limiting & Ethics

This scraper includes built-in rate limiting to be respectful to Wikipedia:
- 3-second delays between requests
- 10-second delays between URL batches
- Automatic retry with backoff
- Progress saving to avoid re-scraping

## 🔍 Troubleshooting

### Common Issues
- **"No URLs found"**: Check `category_mapping.csv` format
- **Slow performance**: Increase rate limiting delays
- **Memory issues**: Reduce batch sizes in config

### Resume Failed Scraping
The scraper automatically saves progress and can resume from interruptions.

## 📈 Performance Tips

1. **Start Small**: Test with limits before full scraping
2. **Monitor Rate Limits**: Adjust delays based on response times
3. **Use Incremental Saving**: Enabled by default for data safety
4. **Check Progress Logs**: Monitor success rates and adjust

## 🤝 Contributing

Feel free to extend this scraper for new categories, regions, or data sources!
