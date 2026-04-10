from google import genai
from dotenv import load_dotenv

load_dotenv()
client = genai.Client()

for m in client.models.list_models():
    if "flash" in m.name:
        print(m.name)
