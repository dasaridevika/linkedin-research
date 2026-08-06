import os
import streamlit as st
from dotenv import load_dotenv

# Load env file if present (useful for local development)
load_dotenv()

def get_config(key, default=None):
    """
    Retrieve configuration from:
    1. Streamlit Session State (entered via UI)
    2. Environment variables
    3. Streamlit Secrets (if deployed)
    """
    # Check session state first (explicit user override in UI)
    if st and "api_keys" in st.session_state and st.session_state.api_keys.get(key):
        return st.session_state.api_keys.get(key)
    
    # Check standard environment variables
    env_val = os.getenv(key)
    if env_val:
        return env_val
        
    # Check Streamlit secrets
    try:
        if st and hasattr(st, "secrets") and key in st.secrets:
            return st.secrets[key]
    except Exception:
        pass
        
    return default

def is_configured():
    """Check if minimum required configurations (Gemini and Search) are available."""
    has_gemini = bool(get_config("GEMINI_API_KEY") or get_config("GOOGLE_API_KEY"))
    has_search = bool(get_config("TAVILY_API_KEY") or get_config("SERPER_API_KEY"))
    return has_gemini and has_search
