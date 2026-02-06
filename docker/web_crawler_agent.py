from firecrawl import Firecrawl
from tavily import TavilyClient
from pydantic  import BaseModel, Field
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
import os
from typing import List
from datetime import datetime

load_dotenv()
llm_api_key = os.getenv("FPT_CLOUD_API_KEY")
firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
tavily_api_key = os.getenv("TAVILY_API_KEY")
MODEL_NAME = "Qwen2.5-Coder-32B-Instruct"

tavily_client = TavilyClient(api_key=tavily_api_key)
app = Firecrawl(api_key=firecrawl_api_key)

BASE_URL = "https://www.toyota.com.vn/"

llm = ChatOpenAI(
    model=MODEL_NAME,
    api_key=llm_api_key,
    base_url="https://mkp-api.fptcloud.com/v1",
    max_tokens = 1024,
    temperature=0.7,
)

class WebsiteInfo(BaseModel):
    title: str = Field(..., description="The title of the website")
    main_topics: List[str] = Field(..., description="A list of main topics covered on the website")
    key_points: List[str] = Field(..., description="A list of key points about the website. Important takeaways or features.")
    short_summary: str = Field(..., description="A brief summary of the website in 2-3 sentences.")

# class RelevantURLs(BaseModel):
#     urls: List[str] = Field(..., description="List of URLs relevant to the user query")

# url_selector_llm = llm.with_structured_output(RelevantURLs)
structure_llm = llm.with_structured_output(WebsiteInfo)

# def map_site_urls(base_url: str) -> List[str]:
#     urls = app.map(
#         url=base_url,
#     )

#     print(f"Mapped urls: {urls}\n")
#     print(f"type of data: {type(urls)}\n")

#     if not urls:
#         raise RuntimeError("No URLs found during map.")

#     print(f"*** Mapped {len(urls.links)} URLs ***")
#     return urls

# def search_relevant_pages(base_url: str, query: str):
#     """
#     Search the web for the query but restrict to base_url domain.
#     Returns a list of dict results with 'url' and optionally 'markdown'.
#     """

#     search_query = f"{query} site:{base_url}"

#     print(f"Searching for: {search_query}")

#     # Perform search with scraping into markdown
#     results = app.search(
#         query=search_query,
#         limit = 5,
#         sources=["web"],
#         scrape_options={
#             "formats": [{"type": "markdown"}],
#             "onlyMainContent": True,
#         },
#     )

#     print(f"Search results: {results}\n")

#     if not results:
#         raise RuntimeError("No search results found for query.")

#     # Each item in results.data["web"] should contain scraped fields
#     web_results = results.web
#     print(f"Found {len(web_results)} search results within domain {base_url}")

#     return web_results

def tavily_search_relevant_pages(base_url: str, query: str):
    search_query = f"{query} site: {base_url}"
    print(f"Searching for: {search_query}\n")

    response = tavily_client.search(
        query=search_query,
        search_depth="advanced",
        include_answer="basic",
        chunk_per_source=5,
    )

    print(f"Tavily search results: {response}\n")

    if "results" not in response:
        raise RuntimeError("No search results found for query.")

    results = response["results"]
    # Sort iteratively, every dict in results, in descending order of score
    sorted_results_by_score = sorted(results, key=lambda x: x.get("score", 0), reverse=True)

    top2 = sorted_results_by_score[:2]
    print(f"Top 2 search results by score: {top2}\n")

    top2_urls = [result["url"] for result in top2]
    print("\nTop 2 URLs selected from Tavily:")
    for result in top2:
        print(f"- {result['url']} (score={result['score']})")
    print("\n")

    return top2_urls

def scrape_urls(urls: List[str]) -> List[str]:
    pages = []
    for url in urls:
        result = app.scrape(
            url=url,
            formats=[{"type": "markdown"}],
            only_main_content=True,
            timeout=120000,
        )

        if result and hasattr(result, "markdown"):
            pages.append(result.markdown)
        
        if not pages:
            raise RuntimeError("Failed to scrape selected URLs.")
        
    return "\n".join(pages)

# def select_relevant_urls(urls: List[str], query: str, max_urls: int = 5) -> List[str]:
#     # url_list_text = "\n".join(url for url, _ in urls)

#     prompt = f"""
#     You are selecting webpages from a website.

#     User query:
#     {query}

#     Website URLs:
#     {urls}

#     Select up to {max_urls} URLs that contains the most relevant and latest information.
#     ONLY select URLs that have the same domain as the base url {BASE_URL}.
#     DO NOT select URLs that does not exist, can not be accessed or contain invalid information.
#     """

#     result = url_selector_llm.invoke(prompt)
#     return result.urls[:max_urls]

# def aggregate_markdown(search_results):
#     combined = []

#     for item in search_results:
#         # item.markdown is provided if scrape_options included markdown
#         md = getattr(item, "markdown", None)
#         if md:
#             combined.append(md)

#     if not combined:
#         raise RuntimeError("No markdown content returned from search results.")

#     return "\n".join(combined)


# def scrape_selected_urls(urls: List[str]) -> str:
#     pages = []

#     for url in urls:
#         result = app.scrape(
#             url=url,
#             formats=[{"type": "markdown"}],
#             only_main_content=True,
#             timeout=120000,
#         )

#         if result and hasattr(result, "markdown"):
#             pages.append(result.markdown)

#     if not pages:
#         raise RuntimeError("Failed to scrape selected URLs.")

#     return "\n\n".join(pages)


# def summarise_website(base_url: str, query: str):
#     urls = map_site_urls(base_url)
#     relevant_urls = select_relevant_urls(urls, query)
    
#     print("Selected URLs:")
#     for u in relevant_urls:
#         print(" -", u)

#     combined_markdown = scrape_selected_urls(relevant_urls)

#     if not combined_markdown.strip():
#         raise RuntimeError("No markdown content found in the crawled pages.")

#     prompt = f"""
#     "### TASK",
#     "",
#     You are an expert web analyst. Carefully read the website content provided below and answer the user's query on that content.
#     The user query is
#     {query}
#     "",

#     "### INSTRUCTIONS",
#     "",
#     "- Based ONLY on website content, extract the most revelant information to answer the query.", 
#     "- Answer must be clear and concise. Focus on extracting key information.",
#     "- Ignore navigation menus, ads, and unrelated sections. Focus on the main content that is relevant to the query.",
#     "- When user asks about a price of a car, list out all the models if not specified and their respective prices.",
#     "",

#     Website Content:
#     {combined_markdown}
#     """
    
#     return structure_llm.invoke(prompt)

def summarise_website(base_url: str, query: str):
    # Search and scrape content
    top_urls = tavily_search_relevant_pages(base_url, query)
    combined_markdown = scrape_urls(top_urls)

    prompt = f"""
        ### TASK
        You are an expert web analyst, carefully read the website content provided below and answer the following user query.

        User query:
        {query}

        ### INSTRUCTIONS
        - Only use the provided website content.
        - Extract the most relevant information to answer the query.
        - Pick the latest information if multiple conflicting data points exist based on the year or date.
        - Answer must be clear and concise. Focusing on the main component of the query.
        - Ignore navigation menus, ads, unrelated sections.
        - If asking about prices, list all models and prices.

        ### WEBSITE CONTENT
        {combined_markdown}
    """

    return structure_llm.invoke(prompt)


def save_summary_to_file(summary: WebsiteInfo, selected_urls:List[str], url: str, output_dir: str = "crawled_summaries"):
    os.makedirs(output_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    file_path = os.path.join(output_dir, f"summary_{timestamp}.md")

    with open(file_path, "w", encoding="utf-8") as f:
        f.write("Website Summary\n\n")
        f.write(f"Source Domain: {url}\n\n")

        f.write("## Selected URLs\n")
        for url in selected_urls:
            f.write(f"- {url}\n")
        f.write("\n")

        f.write("# Title\n")
        f.write(f"{summary.title}\n\n")

        f.write("# Short Summary\n")

        f.write(f"{summary.short_summary}\n\n")

        f.write("# Main Topics\n")
        for topic in summary.main_topics:
            f.write(f"- {topic}\n")
        f.write("\n")

        f.write("# Key Points\n")
        for point in summary.key_points:
            f.write(f"- {point}\n")

    return file_path


def main():

    print("Welcome to the Toyota Web Crawler Agent!")
    print("---------------------------------------\n")
    print("Please enter your questions about Toyota Vietnam's website.")
    print("---------------------------------------\n")
    print("Type 'exit' or 'quit' to end the program.")
    print("---------------------------------------\n")

    query = input("Enter your question: ").strip()
    while True:
        if not query:
            print("Please enter a valid question.\n")
            continue

        if query.lower() in ["exit", "quit"]:
            print("Exiting...")
            break

        top_urls = tavily_search_relevant_pages(BASE_URL, query)

        if not BASE_URL or not query:
            raise ValueError("Base URL and query cannot be empty")

        print("Crawling for relevant pages...\n")
        summary = summarise_website(BASE_URL, query)

        print(f"Summary preview: {summary}\n")

        print("Saving summary...")
        output_path = save_summary_to_file(summary, top_urls, BASE_URL)

        print("\nDone!")
        print(f"Summary saved to: {output_path}")

        query = input("Enter your question: ").strip()


if __name__ == "__main__":
    main()

    
    # Improve: make it a loop to allow multiple queries until user exits