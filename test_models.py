import google.generativeai as genai

# Replace this with your actual key from MakerSuite (starts with AIza...)
API_KEY = "AIzaSyC2fHV0doSNWTjVlgjErz2YiMcNiN341K8"

genai.configure(api_key=API_KEY)

try:
    models = genai.list_models()
    for model in models:
        print("✅ Model:", model.name)
except Exception as e:
    print("❌ ERROR:", e)
