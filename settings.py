import os

try:

    from dotenv import load_dotenv
    load_dotenv()

except ImportError:

    print("python-dotenv not found. Environment variables must be set manually.")


def get_typhoon_ocr_api_key():

    """Retrieves the TYPHOON_OCR_API_KEY from environment variables."""
    if os.getenv("TYPHOON_OCR_API_KEY"):
        print(f"TYPHOON_OCR_API_KEY: {os.getenv("TYPHOON_OCR_API_KEY")}")
    else:
        print("TYPHOON_OCR_API_KEY is not present")
    return os.getenv("TYPHOON_OCR_API_KEY")

typhoon_ocr_api_key = get_typhoon_ocr_api_key()