import base64
import json
from pathlib import Path

import requests
from google import genai

from config.environment import Config


EXTRACTION_PROMPT = """
You are an expert assistant extracting Japanese business invoice data.
Return ONLY valid JSON with these exact keys:
partner_code, invoice_number, issue_date, due_date, currency, lines,
subtotal, tax_amount, total_amount.

Choose partner_code only from this partner master:
{partners}

Each line must contain description (string), quantity (integer or null),
unit (string, use 式 when absent), unit_price (integer or null), amount
(integer), and tax_code (T10 or T08). Dates must be YYYY-MM-DD. Currency is JPY.
Do not guess unreadable values: return null where the schema permits it.
"""


class ProviderError(RuntimeError):
    pass


def _parse_json(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    try:
        value = json.loads(cleaned.strip())
    except json.JSONDecodeError as error:
        raise ProviderError(f"provider returned invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise ProviderError("provider returned JSON that is not an object")
    return value


def _prompt(partners: list) -> str:
    return EXTRACTION_PROMPT.format(
        partners=json.dumps(partners, ensure_ascii=False, indent=2)
    )


class GeminiProvider:
    name = "gemini"

    def __init__(self):
        if not Config.GEMINI_API_KEY:
            raise ProviderError("GEMINI_API_KEY is not configured")
        self.client = genai.Client(api_key=Config.GEMINI_API_KEY)

    def extract(self, file_path: str, partners: list) -> dict:
        uploaded_file = None
        try:
            uploaded_file = self.client.files.upload(file=file_path)
            response = self.client.models.generate_content(
                model=Config.GEMINI_MODEL,
                contents=[uploaded_file, _prompt(partners)],
            )
            return _parse_json(response.text)
        except Exception as error:
            if isinstance(error, ProviderError):
                raise
            raise ProviderError(f"Gemini failed: {error}") from error
        finally:
            if uploaded_file is not None:
                try:
                    self.client.files.delete(name=uploaded_file.name)
                except Exception:
                    pass


class GroqProvider:
    name = "groq"

    def __init__(self):
        if not Config.GROQ_API_KEY:
            raise ProviderError("GROQ_API_KEY is not configured")

    def extract(self, file_path: str, partners: list) -> dict:
        path = Path(file_path)
        if path.suffix.lower() not in {".jpg", ".jpeg", ".png", ".webp"}:
            raise ProviderError("Groq provider supports image invoices only")

        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        mime_type = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".webp": "image/webp",
        }[path.suffix.lower()]
        payload = {
            "model": Config.GROQ_MODEL,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": _prompt(partners)},
                    {"type": "image_url", "image_url": {
                        "url": f"data:{mime_type};base64,{encoded}"
                    }},
                ],
            }],
        }
        try:
            response = requests.post(
                Config.GROQ_API_URL,
                headers={
                    "Authorization": f"Bearer {Config.GROQ_API_KEY}",
                    "Content-Type": "application/json",
                },
                json=payload,
                timeout=90,
            )
            response.raise_for_status()
            return _parse_json(response.json()["choices"][0]["message"]["content"])
        except Exception as error:
            if isinstance(error, ProviderError):
                raise
            raise ProviderError(f"Groq failed: {error}") from error


class RotatingInvoiceExtractor:
    """Alternates providers per invoice and falls back on provider failure."""

    def __init__(self):
        self.provider_names = [name for name in ("gemini", "groq") if self._configured(name)]
        if not self.provider_names:
            raise ProviderError("Configure at least one of GEMINI_API_KEY or GROQ_API_KEY")
        self.next_provider = 0

    @staticmethod
    def _configured(name: str) -> bool:
        return bool(
            Config.GEMINI_API_KEY if name == "gemini" else Config.GROQ_API_KEY
        )

    def extract_invoice_data(self, file_path: str, partners: list) -> dict:
        first = self.provider_names[self.next_provider % len(self.provider_names)]
        self.next_provider += 1
        ordered = [first] + [name for name in self.provider_names if name != first]
        errors = []
        for provider_name in ordered:
            try:
                provider = GeminiProvider() if provider_name == "gemini" else GroqProvider()
                result = provider.extract(file_path, partners)
                print(f"AI provider: {provider_name}")
                return result
            except ProviderError as error:
                errors.append(f"{provider_name}: {error}")
        raise ProviderError("; ".join(errors))


extractor = None


def extract_invoice_data(file_path: str, partners: list):
    global extractor
    if extractor is None:
        extractor = RotatingInvoiceExtractor()
    print(f"Processing: {file_path}")
    return extractor.extract_invoice_data(file_path, partners)
