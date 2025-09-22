# config.py
"""
Configuration module for loading environment variables.
"""

from dotenv import load_dotenv
import os

load_dotenv()

# API Keys
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

# Ensure keys are set
if not GEMINI_API_KEY or not TAVILY_API_KEY:
    raise ValueError("Missing API keys in .env file. Please set GEMINI_API_KEY and TAVILY_API_KEY.")