"""
ChatGPT-based news fetcher and analyzer.
"""

import os
import json
from datetime import datetime, timedelta
from typing import List, Dict

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None


class ChatGPTFetcher:
    """Use ChatGPT to find and analyze electricity meter news."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.client = None
        
        if self.api_key and OpenAI:
            self.client = OpenAI(api_key=self.api_key)
        
    def fetch_news(self, days_back: int = 2) -> List[Dict]:
        """
        Use ChatGPT to identify electricity meter news for MEA region.
        
        Args:
            days_back: Number of days to look back
            
        Returns:
            List of news articles with standardized format
        """
        if not self.client:
            print("   ⚠️  Warning: OPENAI_API_KEY not set or OpenAI not installed")
            return []
        
        today = datetime.now()
        from_date = (today - timedelta(days=days_back)).strftime('%Y-%m-%d')
        to_date = today.strftime('%Y-%m-%d')
        
        prompt = f"""
You are a news research assistant. Based on your knowledge, provide recent news about 
electricity meters, smart meters, and metering solutions in the Middle East and Africa region.

Date range: {from_date} to {to_date}

Focus on:
- Smart meter deployments and rollouts
- Electricity metering infrastructure projects
- Utility company announcements about metering
- Government tenders and initiatives for meters
- Technology partnerships in metering sector
- Prepaid meter installations
- AMI/AMR implementations

Countries: UAE, Saudi Arabia, Qatar, Kuwait, Bahrain, Oman, Egypt, 
South Africa, Nigeria, Kenya, Morocco, Ghana, Tanzania, Ethiopia

IMPORTANT: Return your response as a valid JSON object with this structure:
{{
    "articles": [
        {{
            "title": "Article headline",
            "description": "Brief 2-3 sentence summary",
            "url": "https://source-url.com/article",
            "source": "Publication name",
            "published_at": "YYYY-MM-DD",
            "relevance_score": 0.95
        }}
    ]
}}

Only include articles you are confident about with real URLs.
If you don't have recent information, return: {{"articles": []}}
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a specialized news researcher for the energy and utilities sector. Always respond with valid JSON only."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=3000,
                temperature=0.3,
                response_format={"type": "json_object"}
            )
            
            content = response.choices[0].message.content

            
            # Parse JSON response
            try:
                parsed = json.loads(content)
                articles = parsed.get('articles', [])
                
                return [self._standardize_article(a) for a in articles if self._standardize_article(a)]
                
            except json.JSONDecodeError as e:
                print(f"   ⚠️  ChatGPT returned invalid JSON: {str(e)}")
                return []
                
        except Exception as e:
            print(f"   ❌ ChatGPT exception: {str(e)}")
            return []
    
    def _standardize_article(self, article: Dict) -> Dict:
        """Convert ChatGPT article to standardized format."""
        try:
            title = article.get('title', '')
            if not title:
                return None
                
            return {
                'title': title.strip(),
                'description': (article.get('description') or '').strip(),
                'url': (article.get('url') or '').strip(),
                'source': article.get('source', 'Unknown'),
                'published_at': article.get('published_at', ''),
                'fetched_from': 'ChatGPT',
                'content': (article.get('description') or ''),
                'relevance_score': article.get('relevance_score', 0.5)
            }
        except Exception:
            return None
    
    def enhance_articles(self, articles: List[Dict]) -> str:
        """
        Use ChatGPT to create a summary and analysis of the collected articles.
        
        Args:
            articles: List of deduplicated articles
            
        Returns:
            Formatted summary string for WhatsApp
        """
        if not self.client or not articles:
            return ""
        
        # Prepare articles text
        articles_text = "\n".join([
            f"- {a['title']} ({a['source']}): {a.get('description', '')[:200]}"
            for a in articles[:15]  # Limit to top 15
        ])
        
        prompt = f"""
Analyze these electricity meter news articles for the Middle East and Africa region 
and provide a brief executive summary:

Articles:
{articles_text}

Provide:
1. **Key Trends** (2-3 bullet points)
2. **Notable Developments** (highlight 2-3 most significant news items)
3. **Market Outlook** (1-2 sentences)

Keep the response concise (under 400 words) and suitable for WhatsApp.
Use emojis sparingly for better readability.
Format in plain text, not markdown.
"""
        
        try:
            response = self.client.chat.completions.create(
                model="gpt-4-turbo-preview",
                messages=[
                    {
                        "role": "system",
                        "content": "You are an energy sector analyst specializing in metering and smart grid technologies. Provide concise, actionable insights."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=800,
                temperature=0.5
            )
            
            return response.choices[0].message.content

            
        except Exception as e:
            print(f"   ❌ ChatGPT enhancement exception: {str(e)}")
            return ""
