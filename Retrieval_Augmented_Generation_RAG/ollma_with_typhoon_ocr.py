import os
from ollama import chat
from typhoon_ocr import ocr_document
from dotenv import load_dotenv
load_dotenv()

# Example: https://ollama.com/scb10x/typhoon-ocr1.5-3b
print("Ollama model: ", os.getenv("OLLAMA_MODEL"))
context = input("Enter your context: ")
response = chat(
    model=os.getenv("OLLAMA_MODEL"),
    messages=[
        {
            'role': 'user', 
            'content': context
        }
    ],
)
print(response.message.content)

