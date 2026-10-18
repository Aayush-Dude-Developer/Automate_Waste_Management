from google import genai
from google.genai import errors

from config import settings


def main() -> int:
    api_key = settings.GEMINI_API_KEY
    if not api_key:
        print("GEMINI_API_KEY is missing from the environment and configured .env file.")
        return 1

    try:
        client = genai.Client(api_key=api_key)
        response = client.interactions.create(
            model="gemini-3.8-flash",
            input="Reply with exactly GEMINI_OK",
        )
    except errors.APIError as exc:
        print(f"Gemini API request failed: {exc}")
        return 1

    print(response.output_text or "Gemini returned an empty response.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
