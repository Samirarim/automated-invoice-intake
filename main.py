import os
import json
import argparse
from pathlib import Path

from utils.api_client import get_partners, submit_invoice
from utils.ai_extractor import extract_invoice_data
from utils.invoice_validator import validate_invoice


def process_invoices(invoice_dir: str, dry_run: bool = False):
    print("--- Starting Invoice Processing Agent ---")

    partners = get_partners()
    if not partners:
        print("Stopping execution because partner list could not be retrieved.")
        return 1

    invoice_paths = sorted(
        path for path in Path(invoice_dir).iterdir()
        if path.suffix.lower() in {".pdf", ".jpg", ".jpeg", ".png"}
    )
    review_queue = []
    results = []

    for invoice_path in invoice_paths:
        print(f"\n--- Processing {invoice_path.name} ---")
        try:
            extracted_data = extract_invoice_data(str(invoice_path), partners)
            errors = validate_invoice(extracted_data, partners)
        except Exception as error:
            errors = [f"processing error: {error}"]
            extracted_data = None

        if errors:
            print(f"REVIEW REQUIRED: {', '.join(errors)}")
            review_queue.append({
                "file": invoice_path.name,
                "errors": errors,
                "extracted_data": extracted_data,
            })
            results.append({"file": invoice_path.name, "result": "review"})
            continue

        if dry_run:
            print("VALIDATED (dry run; not submitted)")
            results.append({"file": invoice_path.name, "result": "validated"})
        else:
            if submit_invoice(extracted_data):
                results.append({"file": invoice_path.name, "result": "submitted"})
            else:
                review_queue.append({
                    "file": invoice_path.name,
                    "errors": ["accounting API rejected or could not receive invoice"],
                    "extracted_data": extracted_data,
                })
                results.append({"file": invoice_path.name, "result": "review"})

    with open("review_queue.json", "w", encoding="utf-8") as review_file:
        json.dump(review_queue, review_file, indent=2, ensure_ascii=False)

    print(f"\nProcessed: {len(results)} | Review required: {len(review_queue)}")
    print("Review queue written to review_queue.json")
    return 0 if not review_queue else 2


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI-assisted invoice intake")
    parser.add_argument("--invoice-dir", default="invoices")
    parser.add_argument("--dry-run", action="store_true")
    arguments = parser.parse_args()
    raise SystemExit(process_invoices(arguments.invoice_dir, arguments.dry_run))