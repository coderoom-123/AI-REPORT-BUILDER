import os
from dotenv import load_dotenv
load_dotenv()

print("🔑 Groq API Key:", "YES" if os.getenv("GROQ_API_KEY") else "NO")

from openai import OpenAI

try:
    client = OpenAI(
        api_key=os.getenv("GROQ_API_KEY"),
        base_url="https://api.groq.com/openai/v1"
    )
    
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[{"role": "user", "content": "Say 'Groq is working!' in one sentence."}],
        max_tokens=50
    )
    
    print("✅ Response:", response.choices[0].message.content)
    print("✅ Groq is ready!")
    
except Exception as e:
    print("❌ Error:", e)