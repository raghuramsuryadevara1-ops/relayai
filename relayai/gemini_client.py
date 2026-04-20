import json
from . import auth

GEMINI_PRESENT_PROMPT = """You are a presentation engine. 

You will receive a detailed analysis or answer that has already been prepared. 
Your job is to present it clearly and beautifully to the user.

Rules:
- Present the content exactly as-is, maintaining all code, structure, and details
- Use clean markdown formatting
- Do NOT add extra commentary or change the meaning
- Do NOT say "Here is the analysis" or similar preamble — just present the content
- If it's code, format it properly with syntax highlighting markers
"""


def speak(claude_output: str, original_query: str) -> str:
    """
    Send Claude's output to Gemini for final presentation.
    Gemini re-outputs it using its free tier tokens.
    """
    mode = auth.get_gemini_mode()

    if mode == "oauth":
        return _speak_oauth(claude_output, original_query)
    else:
        return _speak_api_key(claude_output, original_query)


def _build_gemini_prompt(claude_output: str, original_query: str) -> str:
    return f"""The user asked: {original_query}

Here is the complete answer that has been prepared:

{claude_output}

Please present this answer clearly to the user."""


def _speak_api_key(claude_output: str, original_query: str) -> str:
    """Use Gemini via API key (free tier)."""
    try:
        import google.generativeai as genai

        genai.configure(api_key=auth.get_gemini_key())
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash",
            system_instruction=GEMINI_PRESENT_PROMPT
        )

        prompt = _build_gemini_prompt(claude_output, original_query)
        response = model.generate_content(prompt)
        return response.text

    except ImportError:
        raise RuntimeError("Missing dependency. Run: pip install google-generativeai")
    except Exception as e:
        raise RuntimeError(f"Gemini API error: {e}")


def _speak_oauth(claude_output: str, original_query: str) -> str:
    """Use Gemini via Google OAuth token."""
    try:
        import requests
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request

        token_data = json.loads(auth.get_gemini_oauth_token())
        creds = Credentials(
            token=token_data["token"],
            refresh_token=token_data["refresh_token"],
            token_uri=token_data["token_uri"],
            client_id=token_data["client_id"],
            client_secret=token_data["client_secret"],
        )

        if creds.expired and creds.refresh_token:
            creds.refresh(Request())
            updated = {
                "token": creds.token,
                "refresh_token": creds.refresh_token,
                "token_uri": creds.token_uri,
                "client_id": creds.client_id,
                "client_secret": creds.client_secret,
            }
            import keyring
            keyring.set_password("relayai", "gemini_oauth_token", json.dumps(updated))

        prompt = _build_gemini_prompt(claude_output, original_query)

        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {
            "Authorization": f"Bearer {creds.token}",
            "Content-Type": "application/json",
        }
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "systemInstruction": {"parts": [{"text": GEMINI_PRESENT_PROMPT}]}
        }

        resp = requests.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        data = resp.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]

    except ImportError:
        raise RuntimeError("Missing dependency. Run: pip install google-auth requests")
    except Exception as e:
        raise RuntimeError(f"Gemini OAuth error: {e}")
