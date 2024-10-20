import asyncio
import aiohttp
from bs4 import BeautifulSoup
from sqlalchemy import create_engine, Column, Integer, String, select
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from concurrent.futures import ThreadPoolExecutor
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings import LlamaCppEmbeddings
from langchain.vectorstores import Chroma
from langchain.document_loaders import TextLoader

Base = declarative_base()

class ScrapedUrl(Base):
    __tablename__ = 'scraped_urls'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)

engine = create_engine('postgresql://postgres:postgres@localhost:5432/scraper')
Session = sessionmaker(bind=engine)

def get_all_urls():
    session = Session()
    try:
        query = select(ScrapedUrl.url)
        result = session.execute(query)
        urls = [row[0] for row in result]
        return urls
    finally:
        session.close()

async def scrape_content(url, session):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                html = await response.text()
                soup = BeautifulSoup(html, 'html.parser')
                
                for element in soup(['script', 'style', 'nav', 'footer', 'header']):
                    element.decompose()
                
                text = soup.get_text(separator='\n', strip=True)
                
                cleaned_text = '\n'.join(line for line in text.splitlines() if line.strip())
                
                print(f"Scraped content for {url}:")
                print(cleaned_text[:500] + "..." if len(cleaned_text) > 500 else cleaned_text)
                print("\n" + "="*50 + "\n")
                
                return cleaned_text
            else:
                print(f"Failed to scrape {url}. Status code: {response.status}")
                return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

async def scrape_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_content(url, session) for url in urls]
        return await asyncio.gather(*tasks)

def run_scraper(urls):
    return asyncio.run(scrape_urls(urls))

def process_scraped_content(scraped_contents):
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        length_function=len,
    )
    
    chunks = text_splitter.create_documents(scraped_contents)
    
    embeddings = LlamaCppEmbeddings(
        model_path="ollama/llama2",
        n_ctx=2048,
        n_threads=4,
    )
    
    vectorstore = Chroma.from_documents(chunks, embeddings)
    
    return vectorstore

def main():
    urls = get_all_urls()
    print(f"Found URLs: {len(urls)}")
    
    num_threads = min(32, len(urls))
    
    chunk_size = len(urls) // num_threads
    url_chunks = [urls[i:i + chunk_size] for i in range(0, len(urls), chunk_size)]
    
    with ThreadPoolExecutor(max_workers=num_threads) as executor:
        scraped_contents = list(executor.map(run_scraper, url_chunks))
    
    all_scraped_contents = [content for chunk in scraped_contents for content in chunk if content]
    
    vectorstore = process_scraped_content(all_scraped_contents)
    
    print("Vector store created successfully.")
    
    query = "What is machine learning?"
    results = vectorstore.similarity_search(query)
    
    print(f"Results for query '{query}':")
    for doc in results:
        print(doc.page_content)
        print("---")

if __name__ == "__main__":
    main()