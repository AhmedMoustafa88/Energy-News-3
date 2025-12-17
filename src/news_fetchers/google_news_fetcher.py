"""
Google News fetcher using SerpAPI.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict


class GoogleNewsFetcher:
    """Fetch news from Google News using SerpAPI"""
    
    def __init__(self):
        self.api_key = os.getenv("SERPAPI_KEY")
        self.base_url = "https://serpapi.com/search"
        
    def fetch_news(self, days_back: int = 2) -> List[Dict]:
        """
        Fetch electricity meters news from Google News for MEA region.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of news articles with standardized format
        """
        if not self.api_key:
            print("   ⚠️  Warning: SERPAPI_KEY not set")
            return []
        
        # Search queries targeting MEA region
        search_queries = [
            'electricity meter Middle East Africa',
            'smart meter deployment UAE Saudi Arabia',
            'electricity metering project Africa',
            'smart grid Nigeria South Africa Egypt',
            'utility smart meter GCC',
            'prepaid meter Africa',
            'AMR AMI meter Middle East'
        ]
        
        # MEA country codes for Google News
        country_configs = [
            {'gl': 'ae', 'location': 'United Arab Emirates'},
            {'gl': 'sa', 'location': 'Saudi Arabia'},
            {'gl': 'za', 'location': 'South Africa'},
            {'gl': 'ng', 'location': 'Nigeria'},
            {'gl': 'eg', 'location': 'Egypt'},
            {'gl': 'ke', 'location': 'Kenya'},
        ]
        
        all_articles = []
        seen_urls = set()
        
        for query in search_queries:
            for config in country_configs[:3]:  # Limit to avoid rate limits
                try:
                    params = {
                        'engine': 'google_news',
                        'q': query,
                        'gl': config['gl'],
                        'hl': 'en',
                        'api_key': self.api_key
                    }
                    
                    response = requests.get(self.base_url, params=params, timeout=15)
                    
                    if response.status_code == 200:
                        data = response.json()
                        news_results = data.get('news_results', [])
                        
                        for article in news_results:
                            url = article.get('link', '')
                            if url and url not in seen_urls:
                                standardized = self._standardize_article(article, days_back)
                                if standardized:
                                    all_articles.append(standardized)
                                    seen_urls.add(url)
                                    
                    elif response.status_code == 401:
                        print(f"   ❌ SerpAPI authentication failed. Check API key.")
                        return all_articles
                    else:
                        print(f"   ⚠️  SerpAPI error: {response.status_code}")
                        
                except requests.exceptions.Timeout:
                    print(f"   ⚠️  SerpAPI timeout for '{query}'")
                    continue
                except Exception as e:
                    print(f"   ❌ SerpAPI exception: {str(e)}")
                    continue
        
        return all_articles
    
    def _standardize_article(self, article: Dict, days_back: int) -> Dict:
        """Convert Google News article to standardized format."""
        try:
            # Filter by date if available
            date_str = article.get('date', '')
            
            # Check if article is within date range
            if not self._is_within_date_range(date_str, days_back):
                return None
            
            title = article.get('title', '')
            if not title:
                return None
            
            return {
                'title': title.strip(),
                'description': (article.get('snippet') or '').strip(),
                'url': (article.get('link') or '').strip(),
                'source': article.get('source', {}).get('name', 'Unknown') if isinstance(article.get('source'), dict) else str(article.get('source', 'Unknown')),
                'published_at': date_str,
                'fetched_from': 'Google News',
                'content': (article.get('snippet') or '')
            }
        except Exception:
            return None
    
    def _is_within_date_range(self, date_str: str, days_back: int) -> bool:
        """Check if article date is within the specified range."""
        if not date_str:
            return True  # Include if no date available
        
        # Handle relative dates like "2 hours ago", "1 day ago"
        date_str_lower = date_str.lower()
        
        if 'hour' in date_str_lower or 'minute' in date_str_lower:
            return True
        elif 'day' in date_str_lower:
            try:
                days = int(''.join(filter(str.isdigit, date_str_lower)))
                return days <= days_back
            except ValueError:
                return True
        elif 'week' in date_str_lower:
            return False  # More than a week old
        
        return True
