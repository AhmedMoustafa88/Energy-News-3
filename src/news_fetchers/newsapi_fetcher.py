"""
NewsAPI.org fetcher for electricity meters news.
"""

import os
import requests
from datetime import datetime, timedelta
from typing import List, Dict


class NewsAPIFetcher:
    """Fetch news from NewsAPI.org"""
    
    def __init__(self):
        self.api_key = os.getenv("NEWSAPI_KEY")
        self.base_url = "https://newsapi.org/v2/everything"
        
    def fetch_news(self, days_back: int = 2) -> List[Dict]:
        """
        Fetch electricity meters news for MEA region.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of news articles with standardized format
        """
        if not self.api_key:
            print("   ⚠️  Warning: NEWSAPI_KEY not set")
            return []
        
        # Calculate date range
        today = datetime.now()
        from_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
        
        # Search queries for comprehensive coverage
        search_queries = [
            'electricity meter Middle East',
            'smart meter Africa',
            'electricity metering UAE Saudi',
            'smart grid Africa',
            'utility meter Nigeria South Africa',
            'prepaid electricity meter Africa',
            'AMI metering Middle East',
            'electricity meter Egypt Morocco Kenya'
        ]
        
        all_articles = []
        seen_urls = set()
        
        for query in search_queries:
            try:
                params = {
                    'q': query,
                    'from': from_date,
                    'to': to_date,
                    'language': 'en',
                    'sortBy': 'publishedAt',
                    'pageSize': 20,
                    'apiKey': self.api_key
                }
                
                response = requests.get(self.base_url, params=params, timeout=10)
                
                if response.status_code == 200:
                    data = response.json()
                    articles = data.get('articles', [])
                    
                    for article in articles:
                        url = article.get('url', '')
                        if url and url not in seen_urls:
                            standardized = self._standardize_article(article)
                            if standardized:
                                all_articles.append(standardized)
                                seen_urls.add(url)
                                
                elif response.status_code == 401:
                    print(f"   ❌ NewsAPI authentication failed. Check API key.")
                    break
                elif response.status_code == 429:
                    print(f"   ⚠️  NewsAPI rate limit reached.")
                    break
                else:
                    print(f"   ⚠️  NewsAPI error for '{query}': {response.status_code}")
                    
            except requests.exceptions.Timeout:
                print(f"   ⚠️  NewsAPI timeout for '{query}'")
                continue
            except Exception as e:
                print(f"   ❌ NewsAPI exception for '{query}': {str(e)}")
                continue
        
        return all_articles
    
    def _standardize_article(self, article: Dict) -> Dict:
        """Convert NewsAPI article to standardized format."""
        try:
            title = article.get('title', '')
            
            # Skip articles with no title or removed content
            if not title or title == '[Removed]':
                return None
            
            return {
                'title': title.strip(),
                'description': (article.get('description') or '').strip(),
                'url': (article.get('url') or '').strip(),
                'source': article.get('source', {}).get('name', 'Unknown'),
                'published_at': article.get('publishedAt', ''),
                'fetched_from': 'NewsAPI',
                'content': (article.get('content') or '')
            }
        except Exception:
            return None
