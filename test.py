import google.generativeai as genai

API_KEY = "AIzaSyBFdcHnWKVwWMtTqpKDDeamilyxHg69YeQ"  # Replace with your actual API key

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel("gemini-1.5-pro-latest")  # Updated model name
    response = model.generate_content("Say 'Hello, World!'")
    print("Gemini API is working:", response.text)
except Exception as e:
    print("Error:", e)
