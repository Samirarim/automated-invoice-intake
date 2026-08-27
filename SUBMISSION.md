# Submission

- Name: Samira Kabir Rima
- Submission date (YYYY-MM-DD): 2026-08-27
- Hours actually spent: 6hrs
- Repository / how to run it: See `README.md`; start `sample/accounting_api.py`, then run `main.py`.

## 1. Understanding the request

The client wants to reduce manual invoice entry and avoid duplicate or incorrect payments while continuing to use the existing accounting system. I built a small intake agent that reads Japanese PDF and image invoices, maps suppliers to the accounting partner master, validates the extracted data, and submits only internally consistent invoices.

## 2. What you would have asked the client

| What you wanted to ask                                  | The assumption you made                                                                            | Why                                                                                                             |
| ------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| Which fields are mandatory for accounting?              | The fields accepted by the supplied API are mandatory.                                             | The API is the only executable contract available.                                                              |
| What accuracy is required before automatic posting?     | Automatic posting requires passing deterministic checks; uncertain or rejected items go to review. | A wrong payment is more expensive than a manual review.                                                         |
| How should handwritten or unreadable fields be handled? | Preserve the extracted result and route it to `review_queue.json`.                                 | There is no human-review system specification in the assignment.                                                |
| Should duplicate invoice numbers be blocked globally?   | Use the API's supplier-plus-invoice-number duplicate rule.                                         | The API defines the behavior we must respect.                                                                   |
| Which LLM/OCR service is approved?                      | Use Gemini multimodal extraction with the applicant's own API key.                                 | It handles Japanese PDFs and images with one integration and avoids a separate OCR pipeline for this prototype. |

## 3. Scoping decisions

**What you built**

- Multimodal extraction for all PDFs and common image formats.
- Supplier matching against the accounting API partner master.
- Deterministic validation of dates, partners, tax codes, subtotal, tax, and total.
- Batch processing with `--dry-run`.
- Accounting API submission and a `review_queue.json` output for failures.

**What you left out, and why**

- A web review screen: the assignment has only 12 files, so a review queue is enough to demonstrate the boundary within the time limit.
- Persistent job storage and distributed workers: unnecessary for the sample volume.
- Production authentication, monitoring, and retry queues: these need deployment and operational decisions not defined by the mock API.

## 4. Design and technology choices

The flow is:

`invoice file -> rotating Gemini/Groq extraction -> Python validation -> accounting API or review queue`

I chose Python because it is concise, works directly with the supplied API, and has a mature HTTP and environment-variable ecosystem. Gemini was chosen for all invoice formats, including PDFs. Groq's OpenAI-compatible vision endpoint is used for image invoices. Calls alternate between configured providers, and a failed call falls back to the other provider. Groq is not selected for PDFs because this endpoint accepts image inputs rather than PDF files. This reduces dependence on one provider and can lower cost when a suitable lower-cost provider is used.

The model is an assistant, not the final authority. It proposes structured fields; Python recalculates accounting amounts using the API's per-tax-code floor rounding rule. The accounting API remains the system of record.

## 5. How you used AI, and how you checked it

**What you delegated to AI**

I instructed each configured provider to identify the supplier, invoice metadata, line items, tax codes, and integer JPY amounts, and to return only the requested JSON shape. I supplied the valid partner list so the model could return an exact `partner_code`.

**How you verified the output**

Before submission, Python checks required fields, partner membership, real ISO dates, due-date ordering, known tax codes, line amounts, subtotal, tax per tax code, and total. API responses are also checked; rejected or unavailable submissions enter the review queue.

**A case where the AI got it wrong**

The implementation treats any mismatch as a review case rather than assuming the model is correct. A useful production test would deliberately alter a line amount or tax code and verify that no POST is made.

## 6. Integrating with the accounting system

The client fetches the partner master before processing, sends the required API key header, uses integer JPY amounts and `YYYY-MM-DD` dates, and accepts the API's duplicate and amount-mismatch responses. The batch continues processing other files when one invoice fails.

| Invoice                            | Result    | How you handled it                                                         |
| ---------------------------------- | --------- | -------------------------------------------------------------------------- |
| Any valid extraction               | Submitted | Passed local checks, then POSTed to `/invoices`.                           |
| Invalid or inconsistent extraction | Review    | Stored source filename, errors, and extracted data in `review_queue.json`. |
| Duplicate or API rejection         | Review    | Kept the API response outcome and did not mark it submitted.               |

## 7. Cost, limits, and risk in production

- **Cost per invoice**: one model request, alternating between Gemini and Groq when both keys are configured. The exact cost depends on image/PDF tokens and selected models; measure provider token usage rather than guessing.
- **Monthly cost at 1,000 invoices per month**: approximately 1,000 model requests, split roughly 500/500 between providers, plus storage and API traffic. Actual cost must be calculated from the selected models' current pricing.
- **Processing time per invoice**: normally seconds, dominated by upload and model latency; batch throughput can be increased with bounded concurrency.
- **Where this breaks first**: ambiguous handwriting, poor scans, unfamiliar tax treatment, supplier-master changes, model schema drift, and API rate limits.
- **How you would find out if something was registered incorrectly**: retain the source file, extracted JSON, validation results, API response/accounting ID, and a correlation ID; reconcile posted totals against the source and alert on validation or duplicate rates.

## 8. What you would do with another 8 hours

1. Add a small review UI with field corrections and approve/reject actions.
2. Add a fixture-based evaluation set for all 12 invoices with field-level accuracy and amount-reconciliation metrics.
3. Add durable job state, bounded retries, structured logs, and monitoring for production operation.
