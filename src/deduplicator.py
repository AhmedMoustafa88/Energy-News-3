"""
Advanced deduplication engine for news articles.
Uses multiple strategies to identify and remove duplicate content.
"""

import re
import hashlib
from typing import List, Dict, Set
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from difflib import SequenceMatcher


class NewsDeduplicator:
    """
    Advanced deduplication engine for news articles.
    Uses multiple strategies to identify and remove duplicate content.
    """
    
    def __init__(self, similarity_threshold: float = 0.75):
        """
        Initialize deduplicator.
        
        Args:
            similarity_threshold: Minimum similarity ratio to consider as duplicate (0-1)
        """
        self.similarity_threshold = similarity_threshold
        self.seen_urls: Set[str] = set()
        self.seen_titles: Set[str] = set()
        self.seen_hashes: Set[str] = set()
        self.title_list: List[str] = []  # For fuzzy matching
        
    def deduplicate(self, articles: List[Dict]) -> List[Dict]:
        """
        Remove duplicate articles using multiple strategies.
        
        Args:
            articles: List of articles from all sources
            
        Returns:
            Deduplicated list of articles
        """
        if not articles:
            return []
        
        # Reset state
        self.seen_urls = set()
        self.seen_titles = set()
        self.seen_hashes = set()
        self.title_list = []
        
        unique_articles = []
        
        # Sort by source priority (NewsAPI > Google News > ChatGPT)
        source_priority = {'NewsAPI': 1, 'Google News': 2, 'ChatGPT': 3}
        sorted_articles = sorted(
            articles, 
            key=lambda x: source_priority.get(x.get('fetched_from', ''), 4)
        )
        
        for article in sorted_articles:
            if self._is_unique(article):
                unique_articles.append(article)
                self._mark_as_seen(article)
        
        # Sort by date (newest first)
        unique_articles = self._sort_by_date(unique_articles)
        
        return unique_articles
    
    def _is_unique(self, article: Dict) -> bool:
        """
        Check if article is unique using multiple strategies.
        
        Strategies:
        1. URL normalization and matching
        2. Title similarity matching
        3. Content hash matching
        4. Fuzzy title matching
        """
        # Skip articles without title
        title = article.get('title', '')
        if not title or len(title) < 10:
            return False
        
        # Strategy 1: URL Check
        url = article.get('url', '')
        if url:
            normalized_url = self._normalize_url(url)
            if normalized_url and normalized_url in self.seen_urls:
                return False
        
        # Strategy 2: Exact Title Check
        normalized_title = self._normalize_text(title)
        if normalized_title and normalized_title in self.seen_titles:
            return False
        
        # Strategy 3: Content Hash Check
        content_hash = self._generate_content_hash(article)
        if content_hash in self.seen_hashes:
            return False
        
        # Strategy 4: Fuzzy Title Matching
        if self._has_similar_title(title):
            return False
        
        return True
    
    def _mark_as_seen(self, article: Dict):
        """Mark article identifiers as seen."""
        # Add normalized URL
        url = article.get('url', '')
        if url:
            normalized_url = self._normalize_url(url)
            if normalized_url:
                self.seen_urls.add(normalized_url)
        
        # Add normalized title
        title = article.get('title', '')
        normalized_title = self._normalize_text(title)
        if normalized_title:
            self.seen_titles.add(normalized_title)
            self.title_list.append(normalized_title)
        
        # Add content hash
        content_hash = self._generate_content_hash(article)
        self.seen_hashes.add(content_hash)
    
    def _normalize_url(self, url: str) -> str:
        """
        Normalize URL to catch duplicates with different tracking parameters.
        
        Removes:
        - Tracking parameters (utm_*, fbclid, etc.)
        - Protocol differences (http vs https)
        - Trailing slashes
        - www prefix variations
        """
        if not url:
            return ""
        
        try:
            # Parse URL
            parsed = urlparse(url.lower().strip())
            
            # Remove tracking parameters
            tracking_params = {
                'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
                'fbclid', 'gclid', 'msclkid', 'ref', 'source', 'mc_cid', 'mc_eid',
                '_ga', '_gl', 'ncid', 'sr_share', 'ocid', 'cvid', 'ei', 'oref'
            }
            
            query_params = parse_qs(parsed.query)
            filtered_params = {
                k: v for k, v in query_params.items() 
                if k.lower() not in tracking_params
            }
            
            # Reconstruct URL
            clean_query = urlencode(filtered_params, doseq=True) if filtered_params else ''
            
            # Normalize domain (remove www.)
            domain = parsed.netloc.replace('www.', '')
            
            # Remove trailing slash from path
            path = parsed.path.rstrip('/')
            
            # Reconstruct normalized URL
            normalized = urlunparse((
                '',  # No protocol
                domain,
                path,
                '',
                clean_query,
                ''  # No fragment
            ))
            
            return normalized.strip('/')
            
        except Exception:
            return url.lower().strip()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison."""
        if not text:
            return ""
        
        # Convert to lowercase
        text = text.lower()
        
        # Remove special characters and extra whitespace
        text = re.sub(r'[^\w\s]', '', text)
        text = re.sub(r'\s+', ' ', text)
        
        return text.strip()
    
    def _generate_content_hash(self, article: Dict) -> str:
        """Generate a hash based on article content."""
        # Combine key fields
        title = article.get('title', '')
        description = article.get('description', '')
        content = f"{title}{description}"
        normalized = self._normalize_text(content)
        
        # Generate MD5 hash
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _has_similar_title(self, title: str) -> bool:
        """Check if a similar title already exists using fuzzy matching."""
        if not title:
            return False
        
        normalized_new = self._normalize_text(title)
        
        if len(normalized_new) < 20:
            return False  # Skip very short titles for fuzzy matching
        
        for seen_title in self.title_list:
            # Quick length check first
            if abs(len(normalized_new) - len(seen_title)) > len(normalized_new) * 0.5:
                continue
                
            similarity = SequenceMatcher(None, normalized_new, seen_title).ratio()
            if similarity >= self.similarity_threshold:
                return True
        
        return False
    
    def _sort_by_date(self, articles: List[Dict]) -> List[Dict]:
        """Sort articles by publication date (newest first)."""
        def parse_date(article):
            date_str = article.get('published_at', '')
            if not date_str:
                return ''
            # Return as-is for string comparison (ISO format sorts correctly)
            return date_str
        
        return sorted(articles, key=parse_date, reverse=True)
    
    def get_stats(self) -> Dict:
        """Return deduplication statistics."""
        return {
            'unique_urls': len(self.seen_urls),
            'unique_titles': len(self.seen_titles),
            'unique_hashes': len(self.seen_hashes)
        }
