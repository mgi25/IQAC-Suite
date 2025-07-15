import google.generativeai as genai
genai.configure(api_key="AIzaSyD1jp9F1JKK0pO0LeL6ifxOrxI0rlkzPRc")
for model in genai.list_models():
    print(model)
