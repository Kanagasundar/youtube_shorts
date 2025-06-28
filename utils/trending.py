import feedparser

def get_trending_topics():
    url = "https://trends.google.com/trends/trendingsearches/daily/rss?geo=US"
    feed = feedparser.parse(url)
    return [entry.title for entry in feed.entries[:5]]
