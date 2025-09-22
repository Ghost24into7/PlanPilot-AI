import streamlit as st
import sqlite3
import os
import requests
from tavily import TavilyClient
import trafilatura
from readability import Document
from pypdf import PdfReader
import google.generativeai as genai
from datetime import datetime, timedelta
import re

# Placeholders for API keys - replace with actual keys
GEMINI_API_KEY=""
TAVILY_API_KEY=""

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')  # Free tier model

# Tavily client
tavily = TavilyClient(api_key=TAVILY_API_KEY)

# Database setup
DB_FILE = "task_plans.db"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS plans
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  goal TEXT,
                  plan TEXT,
                  timestamp TEXT)''')  # Changed to TEXT for timestamp
    c.execute('''CREATE TABLE IF NOT EXISTS queries
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  query TEXT,
                  results TEXT,
                  timestamp TEXT)''')  # Changed to TEXT for timestamp
    conn.commit()
    conn.close()

init_db()

# Function to check if goal requires weather info (simple heuristic)
def needs_weather(goal):
    weather_keywords = ["weather", "forecast", "climate", "rain", "temperature", "trip", "travel", "outdoor"]
    return any(word in goal.lower() for word in weather_keywords)

# Function to get weather forecast (using Open-Meteo)
def get_weather(city, days=7):
    try:
        # Step 1: Get coordinates for the city using Open-Meteo's geocoding API
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geocode_response = requests.get(geocode_url)
        if geocode_response.status_code != 200 or not geocode_response.json().get('results'):
            return None
        coords = geocode_response.json()['results'][0]
        latitude = coords['latitude']
        longitude = coords['longitude']

        # Step 2: Get weather forecast
        weather_url = f"https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&daily=temperature_2m_max,temperature_2m_min,weathercode&timezone=auto&forecast_days={days}"
        response = requests.get(weather_url)
        if response.status_code == 200:
            data = response.json()['daily']
            forecast = []
            for i in range(days):
                date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
                max_temp = data['temperature_2m_max'][i]
                min_temp = data['temperature_2m_min'][i]
                weather_code = data['weathercode'][i]
                # Simplified weather description (based on WMO weather codes)
                weather_desc = {
                    0: "Clear sky",
                    1: "Mainly clear",
                    2: "Partly cloudy",
                    3: "Overcast",
                    61: "Light rain",
                    63: "Moderate rain",
                    80: "Rain showers"
                }.get(weather_code, "Unknown")
                forecast.append(f"{date}: {min_temp}°C to {max_temp}°C, {weather_desc}")
            return "\n".join(forecast)
        else:
            return None
    except Exception as e:
        return None

# Function to extract number of days from goal
def extract_num_days(goal):
    prompt = f"Extract the number of days for the plan from this goal: '{goal}'. If not specified or unclear, default to 7. Output only the integer number."
    try:
        response = model.generate_content(prompt)
        num_days = int(response.text.strip())
        return max(1, num_days)  # At least 1 day
    except Exception as e:
        return 7

# Universal function to generate specific search queries
def generate_search_queries(goal):
    prompt = f"From the general goal '{goal}', suggest 3 specific, targeted search queries for finding relevant sources (e.g., locations, details, itineraries, tips). Make them versatile for any type of goal. Output as a numbered list, one per line."
    try:
        response = model.generate_content(prompt)
        queries = [q.strip() for q in response.text.split('\n') if q.strip() and q[0].isdigit()]
        return [q.split('.', 1)[1].strip() for q in queries[:3]]  # Extract after number.
    except Exception as e:
        # Universal fallback to generic
        return [goal, f"best tips for {goal}", f"detailed guide for {goal}"]

# Function to extract relevant content from URL
def extract_relevant_content(url, query):
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return None
        
        content_type = response.headers.get('Content-Type', '').lower()
        
        if 'pdf' in content_type or url.endswith('.pdf'):
            # Handle PDF
            with open('temp.pdf', 'wb') as f:
                f.write(response.content)
            reader = PdfReader('temp.pdf')
            text = ""
            for page in reader.pages:
                text += page.extract_text() + "\n"
            os.remove('temp.pdf')
        else:
            # Handle HTML
            doc = Document(response.text)
            summary = doc.summary()
            text = trafilatura.extract(response.text) or summary
        
        if not text:
            return None
        
        # Advanced strategy: Use Gemini to extract only relevant parts to avoid overload
        prompt = f"Extract only the most relevant information from the following text related to '{query}'. Focus on names of locations/places, addresses, Google Maps links, opening hours, descriptions, images URLs if available. Be concise, output only key points, no more than 500 words:\n\n{text[:10000]}"  # Limit input to avoid 429
        try:
            response = model.generate_content(prompt)
            relevant_text = response.text
        except Exception as e:
            relevant_text = text[:2000]  # Fallback to truncated text
        
        return relevant_text
    except Exception as e:
        return None

# Function to search and extract sources with refined queries
def find_and_extract_sources(goal, num_sources=3):
    sources = []
    search_queries = generate_search_queries(goal)
    try:
        for sq in search_queries:
            search_results = tavily.search(query=sq, max_results=num_sources)
            store_query(sq, str(search_results))  # Store each query and results
            
            for result in search_results['results']:
                url = result['url']
                content = extract_relevant_content(url, goal)
                if content:
                    sources.append({'url': url, 'content': content, 'search_query': sq})
                else:
                    # If failed, try to find alternative URL
                    alt_search = tavily.search(query=f"alternative site for {sq}", max_results=1)
                    if alt_search['results']:
                        alt_url = alt_search['results'][0]['url']
                        alt_content = extract_relevant_content(alt_url, goal)
                        if alt_content:
                            sources.append({'url': alt_url, 'content': alt_content, 'search_query': sq})
                if len(sources) >= num_sources * len(search_queries):  # Limit total sources
                    break
            if len(sources) >= num_sources * len(search_queries):
                break
    except Exception as e:
        st.error(f"Search failed: {str(e)}")
    
    return sources[:9]  # Cap at reasonable number to avoid overload

# Function to break goal into steps using Gemini
def break_into_steps(goal):
    prompt = f"Break the following general goal into 5-10 actionable steps: {goal}"
    try:
        response = model.generate_content(prompt)
        steps = response.text.split('\n')
        return [step.strip() for step in steps if step.strip()]
    except Exception as e:
        return []

# Function to generate day-by-day plan
def generate_plan(goal, steps, sources, weather=None, days=7):
    sources_text = "\n\n".join([f"Source from '{s['search_query']}': {s['url']}\n{s['content']}" for s in sources])
    weather_text = f"Weather forecast:\n{weather}" if weather else ""
    
    prompt = f"""Based on the general goal: {goal}
Actionable steps: {', '.join(steps)}
Sources with details (use these to recommend specific places, locations, links, hours, dishes, images): {sources_text}
{weather_text}

You must create a detailed, realistic day-by-day itinerary using the provided sources. Assume the information from sources is current and sufficient. Do not say you cannot create a plan or need more data—use what's available to build it.
For a {days}-day plan, assign activities to each day logically. Include:
- Specific names/locations from sources (e.g., addresses, Google Maps links).
- Relevant details like hours, descriptions.
- Relevant emojis for days and steps.
- Suggest 100% relevant image descriptions or placeholders for locations (e.g., 'Image of [place]: scenic view of the restaurant') since direct image fetching may not be available; in the plan, mark as ![Place Name](image_placeholder).

Structure as: Day 1: [emoji] Overview... then bullet points for steps with emojis and links/images where possible."""
    
    try:
        response = model.generate_content(prompt)
        plan = response.text
        # Enhance with emojis if not already
        plan = re.sub(r'(Day \d+:)', r'📅 \1', plan)
        plan = re.sub(r'(- |• )', r'✅ \1', plan)
        return plan
    except Exception as e:
        return f"Error generating plan: {str(e)}"

# Database functions
def store_plan(goal, plan):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()  # Convert to ISO 8601 string
    c.execute("INSERT INTO plans (goal, plan, timestamp) VALUES (?, ?, ?)", (goal, plan, timestamp))
    conn.commit()
    conn.close()

def store_query(query, results):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    timestamp = datetime.now().isoformat()  # Convert to ISO 8601 string
    c.execute("INSERT INTO queries (query, results, timestamp) VALUES (?, ?, ?)", (query, str(results), timestamp))
    conn.commit()
    conn.close()

def get_all_plans():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute("SELECT goal, plan, timestamp FROM plans ORDER BY timestamp DESC")
    plans = c.fetchall()
    conn.close()
    return plans

# Streamlit app
st.title("Task Planning Agent")

# Input goal
goal = st.text_input("Enter your natural language goal:")

if st.button("Generate Plan"):
    if not goal:
        st.error("Please enter a goal.")
    else:
        with st.spinner("Processing..."):
            # Extract number of days
            days = extract_num_days(goal)
            
            # Break into steps
            steps = break_into_steps(goal)
            if not steps:
                st.error("Failed to break goal into steps.")
            else:
                # Find sources with refined searches
                sources = find_and_extract_sources(goal)
                if len(sources) < 2:
                    st.warning("Limited sources found, proceeding with available.")
                
                # Get weather if needed
                weather = None
                if needs_weather(goal):
                    # Extract city from goal
                    city_prompt = f"Extract the main city from this goal: {goal}. Output only the city name."
                    try:
                        city_response = model.generate_content(city_prompt)
                        city = city_response.text.strip()
                        if city:
                            weather = get_weather(city, days)
                            if not weather:
                                st.warning("Failed to fetch weather forecast.")
                    except Exception as e:
                        st.warning("Failed to extract city or fetch weather.")
                
                # Generate plan
                plan = generate_plan(goal, steps, sources, weather, days)
                if "Error" in plan:
                    st.error(plan)
                else:
                    st.markdown("### Generated Plan")
                    st.markdown(plan)
                    
                    # Store plan
                    store_plan(goal, plan)

# Display history
st.markdown("### History of Plans")
plans = get_all_plans()
for g, plan, timestamp in plans:
    with st.expander(f"Goal: {g} (Created: {timestamp})"):
        st.markdown(plan)