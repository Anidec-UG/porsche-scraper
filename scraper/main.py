import argparse

def parse_arguments():
    parser = argparse.ArgumentParser(description="Web Scraper with customizable options")
    
    parser.add_argument("url", type=str, help="The URL to scrape")
    
    parser.add_argument("-t", "--threads", type=int, default=1,
                        help="Number of threads to use (default: 1)")
    
    parser.add_argument("-d", "--depth", type=int, default=1,
                        help="Depth of crawling (default: 1)")
    return parser.parse_args()

def main():
    args = parse_arguments()
    print(args)
    print(f"URL to scrape: {args.url}")
    print(f"Number of threads: {args.threads}")
    print(f"Crawling depth: {args.depth}")

if __name__ == "__main__":
    main()