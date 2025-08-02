import google.generativeai as genai
import os

if __name__ == "__main__":
    # Configure Gemini API key from environment variables
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if api_key:
        genai.configure(api_key=api_key)
    for model in genai.list_models():
        print(model)
