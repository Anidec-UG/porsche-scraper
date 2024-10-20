import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urlunparse, urljoin
import xml.etree.ElementTree as ET
import re
from colorama import Fore, Back, Style
import colorama
from sqlalchemy import create_engine, Column, Integer, String, func, exists
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

colorama.init()

Base = declarative_base()

class ScrapedUrl(Base):
    __tablename__ = 'scraped_urls'

    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)
    sitemap_type = Column(String) 

engine = create_engine('postgresql://postgres:postgres@localhost:5432/scraper')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)

async def scrape_url(url, browser):
    page = await browser.new_page()
    try:
        print(f"Attempting to scrape: {url}")
        response = await page.goto(url)
        if response.status == 200:
            content = await page.content()
            print(f"Successfully scraped: {url}")
            return content
        else:
            print(f"Failed to scrape {url}. Status code: {response.status}")
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None
    finally:
        await page.close()

def parse_sitemap(content):
    try:
        root = ET.fromstring(content)
        urls = []
        for elem in root.iter():
            if elem.tag.endswith('loc'):
                urls.append(elem.text)
        return urls
    except ET.ParseError as e:
        urls = re.findall(r'<loc>(.*?)</loc>', content)
        return urls

async def scrape_sitemaps(base_url, browser, session):
    sitemap_urls = [
        urljoin(base_url, "sitemap.xml"),
        urljoin(base_url, "sitemap_index.xml"),
        urljoin(base_url, "sitemaps/sitemap.xml"),
    ]
    
    all_urls = set()
    processed_sitemaps = set()

    async def process_sitemap(url, level=0):
        if url in processed_sitemaps:
            return
        
        processed_sitemaps.add(url)
        content = await scrape_url(url, browser)
        
        if content:
            urls = parse_sitemap(content)
            for sub_url in urls:
                if sub_url.endswith('.xml') or sub_url.endswith('.smap'):
                    sitemap_type = f'level_{level}_sitemap'
                    if not session.query(exists().where(ScrapedUrl.url == sub_url)).scalar():
                        new_sitemap = ScrapedUrl(url=sub_url, sitemap_type=sitemap_type)
                        session.add(new_sitemap)
                        print(f"Sitemap added to DB: {sub_url} (Type: {sitemap_type})")
                        await process_sitemap(sub_url, level + 1)
                else:
                    all_urls.add(sub_url)
                    if not session.query(exists().where(ScrapedUrl.url == sub_url)).scalar():
                        new_page = ScrapedUrl(url=sub_url, sitemap_type='page')
                        session.add(new_page)
                        print(f"Page added to DB: {sub_url}")
        else:
            print(f"No content returned for sitemap: {url}")
        
        try:
            session.commit()
        except IntegrityError:
            session.rollback()
            print(f"Duplicate entry found, skipping: {sub_url}")
    
    for sitemap_url in sitemap_urls:
        await process_sitemap(sitemap_url)
    
    return list(all_urls), list(processed_sitemaps)

async def main():
    base_url = "https://www.porsche.com"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        try:
            session = Session()
            urls, processed_sitemaps = await scrape_sitemaps(base_url, browser, session)
            
            print(Fore.GREEN + "Processed sitemaps:")
            print(Fore.CYAN + "\n".join(processed_sitemaps))
            
            print(Fore.GREEN + f"\nFound {len(urls)} URLs in total")
            
            page_count = session.query(ScrapedUrl).filter_by(sitemap_type='page').count()
            sitemap_counts = session.query(ScrapedUrl.sitemap_type, func.count(ScrapedUrl.id)).filter(ScrapedUrl.sitemap_type.like('level_%')).group_by(ScrapedUrl.sitemap_type).all()
            
            print(Fore.GREEN + f"\nStatistiken aus der Datenbank:")
            print(Fore.CYAN + f"Seiten: {page_count}")
            for sitemap_type, count in sitemap_counts:
                print(Fore.CYAN + f"{sitemap_type}: {count}")

            sample_sitemaps = session.query(ScrapedUrl).filter(ScrapedUrl.sitemap_type.like('level_%')).limit(5).all()
            print(Fore.GREEN + "\nBeispiel-Sitemaps aus der Datenbank:")
            for sitemap in sample_sitemaps:
                print(Fore.CYAN + f"{sitemap.sitemap_type}: {sitemap.url}")
        finally:
            await browser.close()
            session.close()

if __name__ == "__main__":
    asyncio.run(main())