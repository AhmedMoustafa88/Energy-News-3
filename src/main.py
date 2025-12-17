"""
Main orchestration script for the Electricity Meters News Bot.
Fetches news from multiple APIs, deduplicates, and sends via WhatsApp.
"""

import os
import sys
from datetime import datetime
from dotenv import load_dotenv

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from news_fetchers.newsapi_fetcher import NewsAPIFetcher
from news_fetchers.google_news_fetcher import GoogleNewsFetcher
from news_fetchers.chatgpt_fetcher import ChatGPTFetcher
from deduplicator import NewsDeduplicator
from whatsapp_sender import WhatsAppSender

# Load environment variables
load_dotenv()


def main():
    """Main orchestration function."""
    print(f"🚀 Starting news aggregation at {datetime.now()}")
    print("=" * 50)
    
    # Configuration
    DAYS_BACK = int(os.getenv("DAYS_BACK", 2))
    SIMILARITY_THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", 0.75))
    
    # Initialize fetchers
    newsapi_fetcher = NewsAPIFetcher()
    google_fetcher = GoogleNewsFetcher()
    chatgpt_fetcher = ChatGPTFetcher()
    
    # Initialize deduplicator
    deduplicator = NewsDeduplicator(similarity_threshold=SIMILARITY_THRESHOLD)
    
    # Initialize WhatsApp sender
    whatsapp_sender = WhatsAppSender()
    
    # ========== FETCH NEWS FROM ALL SOURCES ==========
    all_articles = []
    
    # 1. Fetch from NewsAPI
    print("\n📡 Fetching from NewsAPI...")
    try:
        newsapi_articles = newsapi_fetcher.fetch_news(days_back=DAYS_BACK)
        print(f"   ✅ Found {len(newsapi_articles)} articles")
        all_articles.extend(newsapi_articles)
    except Exception as e:
        print(f"   ❌ NewsAPI error: {str(e)}")
    
    # 2. Fetch from Google News (via SerpAPI)
    print("\n📡 Fetching from Google News...")
    try:
        google_articles = google_fetcher.fetch_news(days_back=DAYS_BACK)
        print(f"   ✅ Found {len(google_articles)} articles")
        all_articles.extend(google_articles)
    except Exception as e:
        print(f"   ❌ Google News error: {str(e)}")
    
    # 3. Fetch from ChatGPT
    print("\n🤖 Fetching from ChatGPT...")
    try:
        chatgpt_articles = chatgpt_fetcher.fetch_news(days_back=DAYS_BACK)
        print(f"   ✅ Found {len(chatgpt_articles)} articles")
        all_articles.extend(chatgpt_articles)
    except Exception as e:
        print(f"   ❌ ChatGPT error: {str(e)}")
    
    print(f"\n📊 Total articles before deduplication: {len(all_articles)}")
    
    # ========== DEDUPLICATE ==========
    print("\n🔄 Deduplicating articles...")
    unique_articles = deduplicator.deduplicate(all_articles)
    stats = deduplicator.get_stats()
    
    duplicates_removed = len(all_articles) - len(unique_articles)
    print(f"   ✅ Unique articles: {len(unique_articles)}")
    print(f"   🗑️  Duplicates removed: {duplicates_removed}")
    print(f"   📈 Deduplication stats: {stats}")
    
    # ========== ENHANCE WITH CHATGPT ANALYSIS ==========
    analysis = ""
    if unique_articles:
        print("\n🧠 Generating AI analysis...")
        try:
            analysis = chatgpt_fetcher.enhance_articles(unique_articles)
            if analysis:
                print("   ✅ Analysis generated successfully")
            else:
                print("   ⚠️  No analysis generated")
        except Exception as e:
            print(f"   ❌ Analysis error: {str(e)}")
    
    # ========== FORMAT MESSAGE ==========
    print("\n📝 Formatting message...")
    message = whatsapp_sender.format_message(unique_articles, analysis)
    
    # Print preview
    print("\n" + "=" * 50)
    print("📋 MESSAGE PREVIEW:")
    print("=" * 50)
    preview_length = 2000
    print(message[:preview_length] + "..." if len(message) > preview_length else message)
    print("=" * 50)
    print(f"📏 Total message length: {len(message)} characters")
    
    # ========== SEND VIA WHATSAPP ==========
    print("\n📱 Sending via WhatsApp...")
    results = whatsapp_sender.send(message)
    
    # ========== SUMMARY ==========
    print("\n" + "=" * 50)
    print("✅ PROCESS COMPLETED!")
    print("=" * 50)
    
    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_fetched": len(all_articles),
        "unique_articles": len(unique_articles),
        "duplicates_removed": duplicates_removed,
        "sources": {
            "newsapi": len([a for a in unique_articles if a.get('fetched_from') == 'NewsAPI']),
            "google_news": len([a for a in unique_articles if a.get('fetched_from') == 'Google News']),
            "chatgpt": len([a for a in unique_articles if a.get('fetched_from') == 'ChatGPT'])
        },
        "send_results": results
    }
    
    print(f"\n📈 Final Report:")
    for key, value in summary.items():
        print(f"   {key}: {value}")
    
    return summary


if __name__ == "__main__":
    result = main()
