import os
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq

# Load .env file from the project root or current directory
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Retrieve Groq API Key (checking both customary key and the exact name found in .env)
api_key = os.getenv("Groq") or os.getenv("GROQ_API_KEY")

if not api_key:
    raise ValueError("Groq API key not found. Please set 'Groq' or 'GROQ_API_KEY' in the .env file.")

# Initialize the Groq client
client = Groq(api_key=api_key)

def list_groq_models():
    print("Fetching available Groq models...\n")
    models = client.models.list()
    # Sort model IDs alphabetically
    model_ids = sorted([model.id for model in models.data])
    for model_id in model_ids:
        print(f"- {model_id}")
    print(f"\nTotal models found: {len(model_ids)}")

if __name__ == "__main__":
    list_groq_models()
