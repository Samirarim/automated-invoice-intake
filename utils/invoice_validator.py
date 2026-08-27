from datetime import date
from math import floor

TAX_RATES = {"T10": 0.10, "T08": 0.08}
REQUIRED_FIELDS = (
    "partner_code",
    "invoice_number",
    "issue_date",
    "due_date",
    "lines",
    "subtotal",
    "tax_amount",
    "total_amount",
)


def validate_invoice(invoice: dict, partners: list) -> list[str]:
    """Return actionable validation errors before an invoice reaches the API."""
    errors = []
    if not isinstance(invoice, dict):
        return ["extraction result is not a JSON object"]

    for field in REQUIRED_FIELDS:
        if field not in invoice:
            errors.append(f"missing field: {field}")

    partner_codes = {partner.get("partner_code") for partner in partners}
    if invoice.get("partner_code") not in partner_codes:
        errors.append("partner_code is not present in the accounting partner master")

    parsed_dates = {}
    for field in ("issue_date", "due_date"):
        try:
            parsed_dates[field] = date.fromisoformat(invoice[field])
        except (KeyError, TypeError, ValueError):
            errors.append(f"{field} must be a real date in YYYY-MM-DD format")

    if parsed_dates.get("due_date") and parsed_dates.get("issue_date"):
        if parsed_dates["due_date"] < parsed_dates["issue_date"]:
            errors.append("due_date is earlier than issue_date")

    lines = invoice.get("lines")
    if not isinstance(lines, list) or not lines:
        errors.append("lines must contain at least one item")
        return errors

    line_total = 0
    subtotal_by_code = {}
    for index, line in enumerate(lines):
        if not isinstance(line, dict):
            errors.append(f"lines[{index}] is not an object")
            continue
        tax_code = line.get("tax_code")
        amount = line.get("amount")
        if tax_code not in TAX_RATES:
            errors.append(f"lines[{index}] has unknown tax code: {tax_code}")
        if not isinstance(amount, int) or isinstance(amount, bool):
            errors.append(f"lines[{index}].amount must be an integer")
            continue
        line_total += amount
        subtotal_by_code[tax_code] = subtotal_by_code.get(tax_code, 0) + amount

    if isinstance(invoice.get("subtotal"), int) and invoice["subtotal"] != line_total:
        errors.append(f"subtotal mismatch: expected {line_total}, received {invoice['subtotal']}")

    expected_tax = sum(
        floor(subtotal * TAX_RATES[tax_code])
        for tax_code, subtotal in subtotal_by_code.items()
        if tax_code in TAX_RATES
    )
    if isinstance(invoice.get("tax_amount"), int) and invoice["tax_amount"] != expected_tax:
        errors.append(f"tax mismatch: expected {expected_tax}, received {invoice['tax_amount']}")

    expected_total = line_total + expected_tax
    if isinstance(invoice.get("total_amount"), int) and invoice["total_amount"] != expected_total:
        errors.append(
            f"total mismatch: expected {expected_total}, received {invoice['total_amount']}"
        )

    return errors
