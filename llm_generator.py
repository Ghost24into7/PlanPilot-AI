# llm_generator.py
"""
LLM Generator module.
Handles all Gemini interactions: extracting days, steps, weather needs, city extraction, plan generation.
Features universal, detailed prompt engineering tailored to query type (plan/learning/task).
Ensures creative, fun outputs for plans; resource-focused for learning.
"""

import os
import re
from typing import List, Optional
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

def extract_num_days(goal: str) -> int:
    """
    Extract number of days from goal using LLM; default 7.
    :param goal: User's goal.
    :return: Integer days (min 1).
    """
    prompt = f"Extract the number of days/period for the plan from: '{goal}'. If unclear, default 7. Output only integer."
    try:
        response = model.generate_content(prompt)
        return max(1, int(response.text.strip()))
    except Exception:
        return 7

def break_into_steps(goal: str) -> List[str]:
    """
    Break goal into 5-10 actionable steps using LLM.
    :param goal: User's goal.
    :return: List of step strings.
    """
    prompt = f"""Break this goal into 5-10 clear, actionable steps: {goal}.
    Make steps logical, sequential, fun if possible (e.g., add emojis in output).
    Output one step per line, bulleted."""
    try:
        response = model.generate_content(prompt)
        steps = [step.strip() for step in response.text.split('\n') if step.strip() and (step.startswith('-') or step.startswith('•'))]
        return steps
    except Exception:
        return []

def needs_weather(goal: str) -> bool:
    """
    Heuristic: Check if goal likely needs weather (travel/outdoor keywords).
    :param goal: User's goal.
    :return: Boolean.
    """
    keywords = ["weather", "forecast", "rain", "temp", "trip", "travel", "outdoor", "beach", "hike"]
    return any(word in goal.lower() for word in keywords)

def extract_city_for_weather(goal: str) -> Optional[str]:
    """
    Extract main city from goal for weather.
    :param goal: User's goal.
    :return: City name or None.
    """
    prompt = f"Extract the primary city/location from: {goal}. Output only the city name, or 'Unknown' if none."
    try:
        response = model.generate_content(prompt)
        city = response.text.strip()
        return city if city and city.lower() != 'unknown' else None
    except Exception:
        return None

def generate_plan(goal: str, steps: List[str], sources: List[dict], weather: Optional[str] = None, days: int = 7) -> str:
    """
    Generate tailored plan using LLM with engineered prompt.
    Detects query type: If locations/places in goal/steps/sources, include them with links/maps.
    For learning: Provide clickable resource links.
    For plans/tasks: Creative, fun, emoji-rich, easy-to-follow.
    Handles Markdown output.
    :param goal: User's goal.
    :param steps: List of steps.
    :param sources: List of source dicts.
    :param weather: Weather string.
    :param days: Number of days.
    :return: Markdown plan string.
    """
    # Prepare sources text: Tailor to type
    sources_text = ""
    has_locations = any('location' in s['content'].lower() or 'address' in s['content'].lower() for s in sources)
    is_learning = any(word in goal.lower() for word in ['learn', 'how to', 'tutorial', 'guide']) or not has_locations

    for s in sources:
        if is_learning:
            # Extract links as clickable
            links = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', s['content'])
            s['content'] = s['content'] + f"\n**Best Resource:** [Click here for more]({links[0] if links else s['url']})" if links else s['content']
        sources_text += f"Source '{s['search_query']}': {s['url']}\n{s['content']}\n\n"

    weather_text = f"\n**Weather Vibes:** {weather}" if weather else ""

    # Universal engineered prompt: Detailed, adaptive
    prompt = f"""Goal: {goal}
Steps: {', '.join(steps)}
Sources: {sources_text}
{weather_text}

Create a tailored response based on the goal type:
- If travel/plan (locations in goal/sources): Detailed {days}-day itinerary. Be creative & fun: Use emojis, exciting language (e.g., "Kick off with a sunrise hike! 🌅"), specific places/addresses/maps from sources, hours, tips. Structure: 📅 Day X: [Fun Title] - Bullets with ✅ steps, ![Place](image_placeholder) for visuals.
- If learning/task (no locations): Step-by-step guide with fun tips, embed clickable links to best resources from sources (Markdown [text](url)). Keep easy, engaging.
- Always: Realistic, use all sources, concise yet detailed. Markdown format. No apologies—deliver value!"""

    try:
        response = model.generate_content(prompt)
        plan = response.text.strip()

        # Enhance Markdown: Add emojis if missing
        plan = re.sub(r'(Day \d+:)', r'📅 \1', plan, flags=re.IGNORECASE)
        plan = re.sub(r'^(\s*-|\s*•)', r'✅ \1', plan, flags=re.MULTILINE)

        # Ensure links are Markdown if not
        plan = re.sub(r'(http[s]?://\S+)', r'[\1](\1)', plan)

        return plan
    except Exception as e:
        return f"Error generating plan: {str(e)}"