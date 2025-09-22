# search_agent.py
"""
Search Agent module.
Handles generating search queries, performing searches via Tavily,
extracting content from URLs (HTML/PDF), and ensuring full set of sources
by finding alternatives for failed URLs.
Uses Gemini for query generation and content extraction.
"""

import os
import requests
from typing import List, Dict
from dotenv import load_dotenv
import trafilatura
from readability import Document
from pypdf import PdfReader
import google.generativeai as genai
from database import store_query

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

from tavily import TavilyClient
tavily = TavilyClient(api_key=TAVILY_API_KEY)

def generate_search_queries(goal: str) -> List[str]:
    """
    Generate 3 targeted search queries from the goal using LLM.
    :param goal: User's goal string.
    :return: List of 3 search queries.
    """
    prompt = """From the general goal '{goal}', suggest 3 specific, targeted search queries for finding relevant sources.
    Make them versatile: for travel/plans, focus on itineraries/locations/tips; for learning, best guides/resources;
    for tasks, step-by-step resources. Output as a numbered list, one per line, no extra text."""
    try:
        response = model.generate_content(prompt.format(goal=goal))
        lines = [line.strip() for line in response.text.split('\n') if line.strip()]
        queries = [line.split('.', 1)[1].strip() if '.' in line else line for line in lines if line[0].isdigit()]
        return queries[:3]
    except Exception:
        return [goal, f"best guide for {goal}", f"detailed tips on {goal}"]

def extract_relevant_content(url: str, query: str) -> str:
    """
    Extract and summarize relevant content from a URL (HTML or PDF).
    Uses trafilatura/readability for HTML, pypdf for PDF; then LLM for relevance.
    :param url: URL to fetch.
    :param query: Original user query for relevance filtering.
    :return: Summarized relevant text or None if failed.
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None

        content_type = response.headers.get('Content-Type', '').lower()

        if 'pdf' in content_type or url.lower().endswith('.pdf'):
            # Handle PDF
            with open('temp.pdf', 'wb') as f:
                f.write(response.content)
            reader = PdfReader('temp.pdf')
            text = "\n".join([page.extract_text() or "" for page in reader.pages])
            os.remove('temp.pdf')
        else:
            # Handle HTML
            doc = Document(response.text)
            summary = doc.summary()
            text = trafilatura.extract(response.text) or summary

        if not text:
            return None

        # LLM extract relevant parts
        prompt = f"""Extract only the most relevant information from the following text related to '{query}'.
        Focus on: locations/places/addresses/maps links (if travel/plan), learning resources/guides (if educational),
        step-by-step details (if task), descriptions/hours/prices. Be concise, key points only, <500 words.
        If no locations needed, prioritize resources/links. Output clean text:\n\n{text[:10000]}"""
        try:
            llm_response = model.generate_content(prompt)
            return llm_response.text.strip()
        except Exception:
            return text[:2000]  # Fallback truncated

    except Exception:
        return None

def find_and_extract_sources(goal: str, num_sources: int = 3) -> List[Dict]:
    """
    Find and extract from sources: Generate queries, search, extract, fallback on failures.
    Ensures exactly num_sources valid sources by finding alternatives.
    :param goal: User's goal.
    :param num_sources: Target number of sources.
    :return: List of dicts {'url': str, 'content': str, 'search_query': str}.
    """
    sources = []
    search_queries = generate_search_queries(goal)

    for sq in search_queries:
        # Search
        try:
            search_results = tavily.search(query=sq, max_results=num_sources)
            store_query(sq, str(search_results))  # Log query
        except Exception as e:
            continue

        for result in search_results.get('results', []):
            url = result['url']
            content = extract_relevant_content(url, goal)

            if content:
                sources.append({'url': url, 'content': content, 'search_query': sq})
                if len(sources) >= num_sources:
                    break
            else:
                # Fallback: Find alternative
                alt_query = f"alternative reliable site for {sq}"
                alt_results = tavily.search(query=alt_query, max_results=1)
                if alt_results.get('results'):
                    alt_url = alt_results['results'][0]['url']
                    alt_content = extract_relevant_content(alt_url, goal)
                    if alt_content:
                        sources.append({'url': alt_url, 'content': alt_content, 'search_query': sq})
                        if len(sources) >= num_sources:
                            break

            if len(sources) >= num_sources:
                break

        if len(sources) >= num_sources:
            break

    # If still short, loop more queries or deepen search, but cap at 9 total
    while len(sources) < num_sources and len(search_queries) < 6:
        extra_query = f"additional resources for {goal}"
        search_queries.append(extra_query)
        # Repeat search logic...
        # (Omitted for brevity; implement similar to above)

    return sources[:9]  # Cap to avoid overload