"""
Planner module.
Handles breaking goals into steps, weather fetching, and generating the final plan
using advanced, universal prompt engineering for ANY query type.
"""

import os
import re
from datetime import datetime, timedelta
import requests
from config import GEMINI_API_KEY
import google.generativeai as genai

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def needs_weather(goal):
    """
    Heuristic to check if goal requires weather info.
    
    Args:
        goal (str): User's goal.
    
    Returns:
        bool: True if weather needed.
    """
    weather_keywords = ["weather", "forecast", "climate", "rain", "temperature", "trip", "travel", "outdoor", "event"]
    return any(word in goal.lower() for word in weather_keywords)

def get_weather(city, days=7):
    """
    Fetch weather forecast using Open-Meteo API.
    
    Args:
        city (str): City name.
        days (int): Number of days.
    
    Returns:
        str or None: Formatted forecast.
    """
    try:
        geocode_url = f"https://geocoding-api.open-meteo.com/v1/search?name={city}&count=1&language=en&format=json"
        geocode_response = requests.get(geocode_url)
        if geocode_response.status_code != 200 or not geocode_response.json().get('results'):
            return None
        coords = geocode_response.json()['results'][0]
        latitude = coords['latitude']
        longitude = coords['longitude']

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
                weather_desc = {
                    0: "Clear sky ☀️",
                    1: "Mainly clear 🌤️",
                    2: "Partly cloudy ⛅",
                    3: "Overcast ☁️",
                    61: "Light rain 🌦️",
                    63: "Moderate rain 🌧️",
                    80: "Rain showers 🌦️"
                }.get(weather_code, "Unknown ❓")
                forecast.append(f"{date}: {min_temp}°C to {max_temp}°C, {weather_desc}")
            return "\n".join(forecast)
        else:
            return None
    except Exception:
        return None

def extract_num_days(goal):
    """
    Extract number of days/periods from goal. Defaults to 1 for non-plan queries.
    
    Args:
        goal (str): User's goal.
    
    Returns:
        int: Number of days/periods.
    """
    prompt = f"Extract the number of days/periods for the plan or guide from this goal: '{goal}'. If not specified, unclear, or not applicable (e.g., single task/learning), default to 1. Output only the integer number."
    try:
        response = model.generate_content(prompt)
        return max(1, int(response.text.strip()))
    except Exception:
        return 1

def break_into_steps(goal):
    """
    Break goal into 5-10 actionable steps. Universal for any goal.
    
    Args:
        goal (str): User's goal.
    
    Returns:
        list: List of steps.
    """
    prompt = f"Break the following goal into 5-10 actionable, fun, and easy-to-understand steps: '{goal}'. Make them creative, engaging, and suitable for ANY goal (travel, learning, tasks, etc.)."
    try:
        response = model.generate_content(prompt)
        steps = response.text.split('\n')
        return [step.strip() for step in steps if step.strip()]
    except Exception:
        return []

def generate_plan(goal, steps, sources, weather=None, days=1):
    """
    Generate a tailored response for ANY query type. Links places to Google business pages,
    resources to direct URLs. No images.
    
    Args:
        goal (str): User's goal.
        steps (list): Actionable steps.
        sources (list): Extracted sources.
        weather (str, optional): Weather forecast.
        days (int): Number of days/periods.
    
    Returns:
        str: Generated response in markdown.
    """
    sources_text = "\n\n".join([f"Source from '{s['search_query']}': {s['url']}\n{s['content']}" for s in sources])
    weather_text = f"Weather forecast:\n{weather}" if weather else ""
    
    universal_prompt = f"""You are a creative, fun Task Planning Agent. Based on the user's goal: '{goal}', create a tailored, universal response for ANY query type (travel, learning, tasks, etc.).

Universal Guidelines (apply to ALL responses):
- Tailor perfectly to the query:
  - **Travel/Events/Plans with locations**: Create a detailed, realistic day-by-day itinerary for {days} days/periods. Assign activities logically. Use fun, engaging language with emojis and motivational tips.
  - **Learning/Courses/Videos/Tasks**: Provide a step-by-step guide framed as an exciting adventure. Highlight best resources (e.g., videos, courses) with clickable Markdown links [Resource Name](direct_URL_from_sources).
  - **General/Other**: Deliver an engaging, structured response with relevant details and links, tailored to the goal.
- **Linking**:
  - For locations/restaurants/businesses (if relevant): Link names to Google business pages using [Place Name](https://www.google.com/search?q=Place+Name+location).
  - For learning resources/videos/courses: Use direct URLs from sources as [Resource Name](direct_URL).
  - Ensure ALL mentioned places/businesses are linked to Google searches.
- **No locations if irrelevant**: Omit locations entirely if the goal doesn't involve them (e.g., learning, abstract tasks).
- **No images**: Do not include image placeholders or references.
- Use provided sources for specifics/links/resources (assume current/sufficient). Do not say you need more data.
- Structure:
  - Plans: 📅 Day 1: Fun overview... then ✅ bullet points with emojis/links.
  - Learning/Tasks: 🎯 Step 1: Fun description... with emojis/links.
  - General: Logical sections with emojis/links.
- Use emojis for visual appeal. Output clean Markdown.

Actionable steps: {', '.join(steps)}
Sources (use for specifics, direct links, Google links for places): {sources_text}
{weather_text if needs_weather(goal) else ''}

Generate the response now!"""
    
    try:
        response = model.generate_content(universal_prompt)
        plan = response.text
        # Auto-enhance with emojis if missing
        plan = re.sub(r'(Day \d+:)', r'📅 \1', plan)
        plan = re.sub(r'(- |• )', r'✅ \1', plan)
        plan = re.sub(r'(Step \d+:)', r'🎯 \1', plan)
        return plan
    except Exception as e:
        return f"Error generating response: {str(e)}"