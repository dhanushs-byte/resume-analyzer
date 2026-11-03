# AI Resume Analyzer — Task 1 & Task 2

## Project structure
- `resume_reader.py` — PDF/text extraction, cleaning, validation, character/token counts.
- `generate_samples.py` — regenerates the 8 synthetic sample resumes.
- `extract_resumes.py` — runs schema-constrained JSON extraction (temperature 0).
- `schema.json` — extraction schema.
- `prompts/system_prompt_v1.txt` — versioned system prompt.
- `samples/` — 7 text-readable resumes plus 1 image-only scanned PDF.
- `outputs/` — generated JSON results and manual review template.

## Setup (Windows PowerShell)
```powershell
git checkout -b feature/resume-analyzer
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Set your API key:
```powershell
$env:OPENAI_API_KEY="YOUR_API_KEY"
```

Run input handling:
```powershell
python resume_reader.py
```

Run extraction:
```powershell
python extract_resumes.py
```

The extraction script uses OpenAI's JSON Schema response format with temperature 0.
It skips files with no extractable text and records a clear error for scanned PDFs.
The script writes one JSON file per readable resume and a combined `extraction_results.json`.

## Expected behavior
- Text and text-based PDF files are extracted and cleaned.
- The image-only `resume_08_scanned.pdf` returns: `Error - no text found (scanned or empty PDF)`.
- Character and token counts are printed for each readable resume.
- Token count uses `tiktoken` when available; otherwise a documented regex approximation is used.

## Manual verification (required)
Open `outputs/manual_review_template.csv`. Compare the model JSON against the source text for 3 resumes. Mark each field as correct/incorrect and record every incorrect or unsupported field. Put the total in `outputs/manual_error_count.txt`.

Do not report an error count until you have actually compared the model outputs with the source resumes. The sample files are synthetic and contain no personal data.

## Prompt versioning
The prompt is stored at `prompts/system_prompt_v1.txt`. If you change its wording, save it as a new version (for example `system_prompt_v2.txt`) and commit both the prompt and a short change note.

# Week 4 - Day 4: LLM Fundamentals — AI Resume Analyzer (Part 2)

## Important: API-key-free submission
This project runs offline. It uses a deterministic mock LLM so that validation, retry logic, matching, ranking, logging and output files can be demonstrated without an API key. **The scores are simulated and must not be presented as real LLM/API evaluations.**

## Tasks covered
- Pydantic `ResumeData` with years constrained to 0–50 and a non-empty skills list.
- JSON validation using `model_validate_json`.
- Up to 3 attempts, with the previous validation error passed into the retry function.
- Clear failure object for invalid/empty input.
- Per-attempt estimated token usage logged to `outputs/validation_attempts.log`.
- Eight sample dummy resumes matched against Python Developer and Data Analyst descriptions.
- Deterministic temperature-0 consistency check (same pair is scored twice).
- Candidate ranking CSV and keyword-match baseline.
- Four-line fairness note.

## Run in VS Code / Windows
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

## Expected validation behavior
```text
TASK 1 - VALIDATION AND RETRY
Attempt 1: validation error (years_of_experience must be <= 50)
Attempt 2: success
...
Empty resume result: Validation failed after 3 attempts.
```

The empty resume deliberately fails all three attempts and returns a failure object.

## Output files
- `outputs/candidate_rankings.csv` — 16 rows (8 candidates × 2 jobs), with rank, score, matched/missing skills and reasoning.
- `outputs/validation_attempts.log` — every validation attempt and estimated token usage.
- `outputs/messy_resume_validation.json` — successful retry result.
- `outputs/empty_resume_validation.json` — clear failure result.
- `outputs/fairness_note.txt` — four-line fairness note.

## Replace mock functions with a real LLM
When an API key is available, replace `mock_extract_response()` and the deterministic `score_candidate()` logic with provider calls. Validate the returned JSON with `ResumeData.model_validate_json()`. Do not treat estimated token counts as provider-reported usage.

