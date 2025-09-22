# search_agent.py
"""
Search Agent module.
Handles generating search queries, performing web searches with Tavily,
extracting content from URLs, and finding alternative URLs if extraction fails.
"""

import os
import requests
from tavily import TavilyClient
from readability import Document
import trafilatura
from pypdf import PdfReader
import tempfile
import json
from datetime import datetime
from config import TAVILY_API_KEY, GEMINI_API_KEY
import google.generativeai as genai
import re
from database import store_query
# Configure APIs
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')
tavily = TavilyClient(api_key=TAVILY_API_KEY)

def generate_search_queries(goal):
    """
    Generate 3 specific search queries from the goal using Gemini.
    Universal for any query type.
    
    Args:
        goal (str): User's goal.
    
    Returns:
        list: List of 3 search queries.
    """
    prompt = f"""From the general goal '{goal}', suggest 3 specific, targeted search queries for finding relevant sources 
    (e.g., locations, details, itineraries, tips, learning resources, videos, courses, general info). Make them versatile 
    for ANY type of goal, including travel, learning, tasks, or anything else. Prioritize high-quality, authoritative sites.
    Output as a numbered list, one per line."""
    try:
        response = model.generate_content(prompt)
        queries = [q.strip() for q in response.text.split('\n') if q.strip() and q[0].isdigit()]
        return [q.split('.', 1)[1].strip() for q in queries[:3]]
    except Exception:
        return [goal, f"best guide for {goal}", f"detailed resources for {goal}"]

def extract_relevant_content(url, query):
    """
    Extract relevant content from a URL, handling HTML and PDF.
    Universal extraction focused on key details.
    
    Args:
        url (str): URL to extract from.
        query (str): Original query for relevance filtering.
    
    Returns:
        str or None: Extracted relevant text.
    """
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'pdf' in content_type or url.endswith('.pdf'):
            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
                tmp.write(response.content)
                tmp_path = tmp.name
            reader = PdfReader(tmp_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            os.unlink(tmp_path)
        else:
            doc = Document(response.text)
            summary = doc.summary()
            text = trafilatura.extract(response.text) or summary
        
        if not text:
            return None
        
        # Use Gemini to extract relevant parts universally
        prompt = f"""Extract only the most relevant information from the following text related to '{query}'. 
        Focus on key details: names of locations/places (if relevant to query), addresses, Google Maps/business links, 
        opening hours, descriptions, learning resources/videos/courses (with direct URLs if available), tips, general info. 
        If the query is about learning/videos/courses, highlight best resource links. Be concise, output only key points, 
        no more than 500 words. If no locations involved, omit them entirely.
        
        Text: {text[:10000]}"""
        try:
            gemini_response = model.generate_content(prompt)
            return gemini_response.text
        except Exception:
            return text[:2000]
    except Exception:
        return None

def find_and_extract_sources(goal, num_sources=3):
    """
    Find and extract sources using refined queries. If extraction fails for a source,
    automatically find and use the most relevant alternative URL.
    Universal for any goal.
    
    Args:
        goal (str): User's goal.
        num_sources (int): Number of sources to aim for.
    
    Returns:
        list: List of dicts with 'url', 'content', 'search_query'.
    """
    sources = []
    search_queries = generate_search_queries(goal)
    
    for sq in search_queries:
        search_results = tavily.search(query=sq, max_results=num_sources)
        store_query(sq, json.dumps(search_results), datetime.now().isoformat())  # Store query
        
        for result in search_results['results']:
            url = result['url']
            content = extract_relevant_content(url, goal)
            
            if content:
                sources.append({'url': url, 'content': content, 'search_query': sq})
            else:
                # Find alternative
                alt_search = tavily.search(query=f"alternative high-quality site for {sq} {goal}", max_results=1)
                if alt_search['results']:
                    alt_url = alt_search['results'][0]['url']
                    alt_content = extract_relevant_content(alt_url, goal)
                    if alt_content:
                        sources.append({'url': alt_url, 'content': alt_content, 'search_query': sq})
                    else:
                        # Fallback to next result if available
                        continue
                else:
                    continue
            
            if len(sources) >= num_sources:
                break
        
        if len(sources) >= num_sources:
            break
    
    # Ensure exactly num_sources by adding more if needed
    while len(sources) < num_sources:
        fallback_query = f"additional relevant resources for {goal}"
        fallback_results = tavily.search(query=fallback_query, max_results=1)
        if fallback_results['results']:
            fb_url = fallback_results['results'][0]['url']
            fb_content = extract_relevant_content(fb_url, goal)
            if fb_content:
                sources.append({'url': fb_url, 'content': fb_content, 'search_query': fallback_query})
    
    return sources[:num_sources]