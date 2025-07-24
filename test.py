import google.generativeai as genai
import os

if __name__ == "__main__":
    # Configure Gemini API key from environment variable
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    for model in genai.list_models():
        print(model)
