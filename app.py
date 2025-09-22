# app.py
"""
Main Flask application for the Task Planning Agent Dashboard.
Handles routing, API endpoints, and integrates with agents and generators.
Uses Flask for the web server, Jinja2 for templating, and serves static files.
"""

import os
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, jsonify, send_from_directory
from dotenv import load_dotenv
from werkzeug.utils import secure_filename

# Import custom modules
from database import init_db, store_plan, store_query, get_all_plans
from search_agent import find_and_extract_sources
from llm_generator import (
    extract_num_days, break_into_steps, generate_plan,
    needs_weather, extract_city_for_weather
)
from weather import get_weather

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'  # For any future file uploads, though not used yet
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Ensure upload folder exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Initialize database on startup
init_db()

@app.route('/')
def index():
    """
    Render the main dashboard HTML.
    Displays input form for goal, history of plans, and handles JS for interactions.
    """
    return render_template('index.html')

@app.route('/api/generate-plan', methods=['POST'])
def generate_plan_endpoint():
    """
    API endpoint to generate a plan based on user goal.
    Handles JSON input with 'goal' key.
    Returns JSON with status, plan (in Markdown), and any errors.
    Integrates searching, weather, and plan generation with progress simulation.
    """
    data = request.get_json()
    goal = data.get('goal', '').strip()

    if not goal:
        return jsonify({'status': 'error', 'message': 'Please enter a goal.'}), 400

    try:
        # Step 1: Extract days and steps (quick LLM calls)
        days = extract_num_days(goal)
        steps = break_into_steps(goal)

        if not steps:
            return jsonify({'status': 'error', 'message': 'Failed to break goal into steps.'}), 500

        # Simulate progress: Yield search progress
        progress = {
            'stage': 'searching',
            'message': 'Breaking down your goal and searching for the best resources...',
            'sources': []
        }
        # In a real async setup, this would stream; here, we'll collect and return all at once
        # But for animation, client JS will poll or use SSE; simplified to single response with stages

        # Step 2: Find sources with fallback for failed URLs
        sources = find_and_extract_sources(goal, num_sources=3)  # Ensures full set with alternatives

        progress['sources'] = [
            {'url': s['url'], 'search_query': s['search_query']} for s in sources
        ]
        progress['stage'] = 'summarizing'
        progress['message'] = 'Summarizing key details from sources...'

        # Store queries (from search_agent)
        # Already handled in find_and_extract_sources via store_query

        # Step 3: Weather if needed
        weather = None
        if needs_weather(goal):
            city = extract_city_for_weather(goal)
            if city:
                weather = get_weather(city, days)
                if not weather:
                    progress['warnings'] = progress.get('warnings', []) + ['Weather fetch failed.']

        progress['stage'] = 'generating'
        progress['message'] = "Crafting your personalized, fun plan... Hang tight!"

        # Step 4: Generate plan
        plan = generate_plan(goal, steps, sources, weather, days)

        if "Error" in plan:
            return jsonify({'status': 'error', 'message': plan}), 500

        # Store plan
        store_plan(goal, plan)

        return jsonify({
            'status': 'success',
            'plan': plan,  # Markdown ready for client rendering
            'days': days,
            'progress': progress
        })

    except Exception as e:
        return jsonify({'status': 'error', 'message': f'Generation failed: {str(e)}'}), 500

@app.route('/api/history')
def history():
    """
    API endpoint to fetch all stored plans for history display.
    Returns JSON list of plans with goal, plan, timestamp.
    """
    plans = get_all_plans()
    return jsonify([{'goal': g, 'plan': p, 'timestamp': t} for g, p, t in plans])

@app.route('/static/<path:filename>')
def static_files(filename):
    """
    Serve static files (CSS, JS, images).
    """
    return send_from_directory('static', filename)

if __name__ == '__main__':
    app.run(debug=os.getenv('FLASK_DEBUG', 'True').lower() == 'true', host='0.0.0.0', port=5000)