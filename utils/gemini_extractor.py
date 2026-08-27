import json
from google import genai
from config.environment import Config

client = genai.Client(api_key=Config.GEMINI_API_KEY)

def extract_invoice_data(file_path: str, partners: list):
    """Sends an invoice to Gemini, mapping the correct partner code from the provided list."""
    print(f"📄 Processing: {file_path}")
    
    uploaded_file = client.files.upload(file=file_path)
    partners_info = json.dumps(partners, ensure_ascii=False, indent=2)
    
    prompt = f"""
    You are an expert AI assistant that extracts data from Japanese business invoices.
    Analyze the provided invoice document and extract the details into a strict JSON format.
    
    Here is the list of valid partners you can choose from:
    {partners_info}
    
    Match the supplier on the invoice to the correct partner from the list above and use their exact "partner_code".
    
    Return a JSON object with these exact keys:
    - partner_code: (string, e.g., "P-1001")
    - invoice_number: (string)
    - issue_date: (string formatted as YYYY-MM-DD)
    - due_date: (string formatted as YYYY-MM-DD)
    - currency: "JPY"
    - lines: An array of line items. Each line must have:
        - description (string)
        - quantity (integer or null)
        - unit (string, use "式" if the invoice does not specify a unit)
        - unit_price (integer or null)
        - amount (integer)
        - tax_code: "T10" for 10% tax rate items, or "T08" for 8% tax rate items.
    - subtotal: integer
    - tax_amount: integer
    - total_amount: integer
    
    Return ONLY valid JSON with no markdown formatting blocks or extra text.
    """

    response = client.models.generate_content(
        model="gemini-3.6-flash",
        contents=[uploaded_file, prompt]
    )
    
    client.files.delete(name=uploaded_file.name)
    
    raw_text = response.text.strip()
    if raw_text.startswith("```json"):
        raw_text = raw_text[7:]
    if raw_text.endswith("```"):
        raw_text = raw_text[:-3]
        
    return json.loads(raw_text.strip())