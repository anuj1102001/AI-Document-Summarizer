import os

from dotenv import load_dotenv
from google import genai

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found.")

client = genai.Client(api_key=API_KEY)


def summarize_text(text: str, style: str = "bullet") -> str:

    if style == "bullet":
        instruction = "Summarize the following text into clear and concise bullet points."

    elif style == "short":
        instruction = "Summarize the following text in one short paragraph."

    elif style == "detailed":
        instruction = "Provide a detailed summary of the following text."

    elif style == "simple":
        instruction = "Explain the following text in very simple language that a 10-year-old can understand."

    else:
        instruction = "Summarize the following text."

    prompt = f"""
{instruction}

Text:
{text}
"""

    response = client.models.generate_content(
        model="gemini-3.5-flash",
        contents=prompt,
    )

    return response.text