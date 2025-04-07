import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")