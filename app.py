# app.py
"""
Flask application for the Task Planning Agent Dashboard.
This is the main entry point that handles routes, integrates with other modules,
and serves the advanced UI.
"""

import os
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from werkzeug.utils import secure_filename
import uuid
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import modules after app init to avoid circular imports
from database import init_db, store_plan, get_all_plans, store_query
from search_agent import generate_search_queries, find_and_extract_sources
from planner import extract_num_days, break_into_steps, needs_weather, get_weather, generate_plan

# Initialize database
init_db()

@app.route('/')
def index():
    """
    Render the main dashboard page.
    """
    return render_template('index.html')

@app.route('/generate_plan', methods=['POST'])
def generate_plan_endpoint():
    """
    Endpoint to generate a plan based on user goal.
    Handles the full workflow: search, extraction, planning.
    Returns progress updates and final plan via JSON for real-time UI updates.
    """
    data = request.json
    goal = data.get('goal', '').strip()
    if not goal:
        return jsonify({'error': 'Please enter a goal.'}), 400

    # Generate unique session ID for progress tracking
    session_id = str(uuid.uuid4())

    # Step 1: Extract days
    days = extract_num_days(goal)

    # Step 2: Break into steps
    steps = break_into_steps(goal)
    if not steps:
        return jsonify({'error': 'Failed to break goal into steps.'}), 500

    # Emit progress (via SSE or polling, but for simplicity, return in batches)
    progress = {'session_id': session_id, 'step': 'searching', 'message': 'Generating search queries...', 'sources': []}

    # Step 3: Find and extract sources with replacements for failures
    sources = find_and_extract_sources(goal, num_sources=3)
    if len(sources) < 2:
        # Ensure at least 2 by searching more if needed
        while len(sources) < 2:
            additional_query = f"additional resources for {goal}"
            additional_sources = find_and_extract_sources(additional_query, num_sources=1)
            sources.extend(additional_sources)
            sources = sources[:3]  # Cap at 3

    # Update progress with sources
    progress['sources'] = [{'url': s['url'], 'search_query': s['search_query']} for s in sources]
    progress['message'] = 'Sources extracted. Fetching weather if needed...'

    # Step 4: Get weather if needed
    weather = None
    if needs_weather(goal):
        city_prompt = f"Extract the main city from this goal: {goal}. Output only the city name."
        try:
            from google.generativeai import GenerativeModel
            import google.generativeai as genai
            genai.configure(api_key=os.getenv('GEMINI_API_KEY'))
            model = GenerativeModel('gemini-1.5-flash')
            city_response = model.generate_content(city_prompt)
            city = city_response.text.strip()
            if city:
                weather = get_weather(city, days)
        except Exception as e:
            pass  # Weather optional

    progress['message'] = 'Generating your personalized plan...'

    # Step 5: Generate plan
    plan = generate_plan(goal, steps, sources, weather, days)
    if "Error" in plan:
        return jsonify({'error': plan}), 500

    # Store plan
    timestamp = datetime.now().isoformat()
    store_plan(goal, plan, timestamp)

    # Final progress
    progress['step'] = 'complete'
    progress['plan'] = plan
    progress['days'] = days

    return jsonify(progress)

@app.route('/history')
def history():
    """
    Endpoint to fetch history of plans.
    """
    plans = get_all_plans()
    return jsonify([{'goal': g, 'plan': p, 'timestamp': t} for g, p, t in plans])

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve static files (CSS, JS, etc.).
    """
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)