# config/feeds.py

RSS_FEEDS = [
    {
        "name": "BBC World",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
        "region": "global",
        "source_id": "bbc",
    },
    {
        "name": "Al Jazeera",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
        "region": "middle_east",
        "source_id": "aljazeera",
    },
    {
        "name": "Deutsche Welle",
        "url": "https://rss.dw.com/xml/rss-en-all",
        "region": "europe",
        "source_id": "dw",
    },
    {
        "name": "Channel NewsAsia",
        "url": "https://www.channelnewsasia.com/api/v1/rss-outbound-feed?_format=xml",
        "region": "se_asia",
        "source_id": "cna",
    },
    {
        "name": "Dawn Pakistan",
        "url": "https://www.dawn.com/feeds/home",
        "region": "s_asia",
        "source_id": "dawn",
    },
    {
        "name": "Dept. of War",
        "url": "https://war.gov/DesktopModules/ArticleCS/RSS.ashx?max=25&ContentType=1&Site=945",
        "region": "global",
        "source_id": "dow",
        "is_military": True,
    },
    {
        "name": "Times of India",
        "url": "https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
        "region": "s_asia",
        "source_id": "toi",
        "is_military": False,
    },
    {
        "name": "New York Times",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/HomePage.xml",
        "region": "americas",
        "source_id": "nyt",
        "is_military": False,
    },
    {
        "name": "Economic Times",
        "url": "https://b2b.economictimes.indiatimes.com/rss/recentstories",
        "region": "asia",
        "source_id": "et",
        "is_military": False,
    },
]