import asyncio
from playwright.async_api import async_playwright
from urllib.parse import urlparse, urlunparse, urljoin
import xml.etree.ElementTree as ET
import re
from colorama import Fore, Back, Style
import colorama

colorama.init()

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

async def scrape_sitemaps(base_url, browser):
    sitemap_urls = [
        urljoin(base_url, "sitemap.xml"),
        urljoin(base_url, "sitemap_index.xml"),
        urljoin(base_url, "sitemaps/sitemap.xml"),
    ]
    
    all_urls = set()
    first_level_sitemaps = set()
    nested_sitemaps = set()
    
    async def process_sitemap(url, is_first_level=False):
        content = await scrape_url(url, browser)
        if content:
            urls = parse_sitemap(content)
            for url in urls:
                if url.endswith('.xml'):
                    if is_first_level:
                        first_level_sitemaps.add(url)
                    else:
                        nested_sitemaps.add(url)
                    await process_sitemap(url)
                else:
                    all_urls.add(url)
        else:
            print(f"No content returned for sitemap: {url}")
    
    for sitemap_url in sitemap_urls:
        await process_sitemap(sitemap_url, is_first_level=True)
    
    return list(all_urls), list(first_level_sitemaps), list(nested_sitemaps)

async def main():
    base_url = "https://www.porsche.com"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        try:
            urls, first_level_sitemaps, nested_sitemaps = await scrape_sitemaps(base_url, browser)
            print(urls)
            
            print(Fore.GREEN + "First level sitemaps:")
            print(Fore.CYAN + (first_level_sitemaps))
            
            print(Fore.GREEN + "\nNested sitemaps:")
            print(Fore.CYAN + "\n".join(nested_sitemaps))
            
            print(Fore.GREEN + f"\nFound {len(urls)} URLs in total")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(main())