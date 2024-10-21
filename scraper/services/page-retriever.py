import asyncio
import aiohttp
from sqlalchemy import create_engine, Column, Integer, String, select
from bs4 import BeautifulSoup
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import ollama
from langchain_chroma import Chroma
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.embeddings.base import Embeddings

Base = declarative_base()

class OllamaEmbedding(Embeddings):
    def embed_documents(self, texts):
        return [generate_ollama_embedding(text) for text in texts]

    def embed_query(self, text):
        return generate_ollama_embedding(text)

ollama_embeddings = OllamaEmbedding()
chroma_db = Chroma(embedding_function=ollama_embeddings, collection_name="scraped_content", persist_directory="./chroma_db")

class ScrapedUrl(Base):
    __tablename__ = 'scraped_urls'
    id = Column(Integer, primary_key=True)
    url = Column(String, unique=True)

engine = create_engine('postgresql://postgres:postgres@localhost:5432/scraper')
Session = sessionmaker(bind=engine)

def split_text(content):
    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    return splitter.split_text(content)

def create_documents_from_content(content, url):
    text_chunks = split_text(content)
    documents = [{"page_content": chunk, "metadata": {"source": url}} for chunk in text_chunks]
    return documents

def generate_ollama_embedding(text):
    try:
        response = ollama.embed(text)  
        return response["embedding"]  
    except Exception as e:
        print(f"Error generating embedding: {str(e)}")
        return None


def get_all_urls():
    session = Session()
    try:
        query = select(ScrapedUrl.url)
        result = session.execute(query)
        urls = [row[0] for row in result]
        return urls
    finally:
        session.close()

def parse_text(content):
    soup = BeautifulSoup(content, 'html.parser')
    for scripts_or_style in soup(['script', 'style', 'nav', 'footer', 'header']):
        scripts_or_style.decompose()
    text = soup.get_text(separator=' ')
    cleaned_text = ' '.join(text.split())
    return cleaned_text

stored_documents = []

async def scrape_content(url, session):
    try:
        async with session.get(url) as response:
            if response.status == 200:
                content = await response.text()
                parsed_content = parse_text(content)
                
                documents = create_documents_from_content(parsed_content, url)

                for doc in documents:
                    embedding = generate_ollama_embedding(doc["page_content"])
                    if embedding is not None:
                        chroma_db.add_texts(texts=[doc["page_content"]], embeddings=[embedding], metadatas=[doc["metadata"]])
                        stored_documents.append(doc) 

                print(f"Successfully scraped and embedded content from {url}")
                return parsed_content
            else:
                print(f"Failed to scrape {url}. Status code: {response.status}")
                return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None
    
async def scrape_urls(urls):
    async with aiohttp.ClientSession() as session:
        tasks = [scrape_content(url, session) for url in urls]
        try:
            return await asyncio.gather(*tasks)
        except Exception as e:
            print(f"Error in scraping tasks: {str(e)}")


def query_chroma_db(query):
    results = chroma_db.similarity_search(query, k=5)  
    
    for result in results:
        print(f"Source: {result['metadata']['source']}")
        print(f"Content: {result['page_content']}\n")
    
    return results

def main():
    urls = get_all_urls()
    if urls:
        asyncio.run(scrape_urls(urls))
        chroma_db.persist()  
        print("Scraping completed and data persisted.")
    else:
        print("No URLs found.")

    for doc in stored_documents:
        print(f"Source: {doc['metadata']['source']}, Content: {doc['page_content']}")

if __name__ == "__main__":
    main()
