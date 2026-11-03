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
