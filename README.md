# AI Resume Analyzer — Week 4 (Days 4–5)

A learning project that extracts structured resume information, validates model output, matches candidate skills to a job description, and exposes the workflow through FastAPI.

> **No API key required:** the default adapter is a deterministic offline mock. Scores, extraction metrics and token counts are simulated/estimated demonstrations, not real LLM or provider results.

## Features

### Day 4 — Validation and job matching
- Pydantic `ResumeData`: experience 0–50 and non-empty skills.
- JSON validation using `model_validate_json`, up to 3 attempts with validation feedback.
- Eight synthetic resumes and Python Developer / Data Analyst job descriptions.
- Candidate ranking, matched/missing skills, reasoning, repeat-run consistency and keyword baseline.

### Day 5 Part 3 — FastAPI API
- `POST /analyze`: `.txt` or `.pdf` upload OR resume text, plus a job description.
- `GET /health` and Swagger UI at `/docs`.
- File type, 5 MB file-size and estimated 4,000-token validation.
- Request ID logging and `X-Request-ID` response header.
- Retry on invalid JSON; friendly 4xx/5xx responses for input, timeout, rate-limit and invalid model output.
- Estimated token usage and estimated cost. Offline mock reports estimated cost `$0.00`.

### Day 5 Part 4 — Tests and evaluation
- Pytest + FastAPI `TestClient` with mock LLM responses.
- Success, invalid JSON then success, empty file, wrong type, missing input, size/token limit, timeout, rate limit and retry-exhaustion tests.
- Golden set of 8 synthetic resumes; baseline vs improved skill extraction precision/recall/F1/exact-match accuracy.
- Deterministic repeat-run score difference, demo script and fairness answers.

## Project structure
```text
AI-Resume-Analyzer/
├── app/main.py
├── data/resumes/                  # 8 synthetic resumes
├── data/job_descriptions/         # 2 job descriptions
├── data/resume_data.json
├── evaluation/golden_set.json
├── evaluation/evaluate_extraction.py
├── outputs/                       # rankings, validation logs and evaluation
├── tests/test_api.py
├── .env.example
├── .gitignore
├── main.py                        # Day 4 script
├── requirements.txt
├── pytest.ini
├── DEMO_SCRIPT.md
└── README.md
```

## Architecture
```text
Resume file/text + job description
               ↓
       FastAPI POST /analyze
               ↓
     File/type/size/text checks
               ↓
   Offline mock LLM adapter (replaceable)
               ↓
      JSON validation + retry
               ↓
       Pydantic ResumeData
               ↓
    Job skill matching and score
               ↓
 JSON result + token estimates + request ID
```

## Setup — Windows PowerShell / VS Code
Python 3.10+ recommended.
```powershell
git clone https://github.com/dhanushs-byte/resume-analyzer.git
cd resume-analyzer
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```
No API key is needed for offline mode. Never commit `.env`.

## Run Day 4 validation and ranking
```powershell
python main.py
```

## Run API
```powershell
uvicorn app.main:app --reload
```
- Health: http://127.0.0.1:8000/health
- Swagger UI: http://127.0.0.1:8000/docs

## Example cURL — text input
```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "resume_text=ARUN KUMAR\n3 years experience\nSkills: Python, FastAPI, SQL, REST API, Git, Docker, Pandas" \
  -F "job_description=Python Developer. Required skills: Python, FastAPI, SQL, REST API, Git, Docker."
```

## Example cURL — upload
```bash
curl -X POST "http://127.0.0.1:8000/analyze" \
  -F "resume_file=@data/resumes/resume_01.txt" \
  -F "job_description=Python Developer. Required skills: Python, FastAPI, SQL, REST API, Git, Docker."
```

## Example response shape
```json
{
  "candidate_name": "ARUN KUMAR",
  "years_of_experience": 3,
  "skills": ["python", "fastapi", "sql", "rest api", "git", "docker", "pandas"],
  "score": 100.0,
  "matched_skills": ["docker", "fastapi", "git", "python", "rest api", "sql"],
  "missing_skills": [],
  "reasoning": "6 of 6 job-description skills matched. The score is a transparent keyword-overlap baseline, not an assessment of overall ability.",
  "attempts": 1,
  "token_usage": {"input_tokens_estimated": 70, "output_tokens_estimated": 20},
  "estimated_cost_usd": 0.0,
  "scoring_mode": "offline_keyword_overlap",
  "request_id": "generated-request-id"
}
```
Exact estimated token counts vary with prompt/output. This is a response schema illustration.

## Tests and coverage
```powershell
pytest
pytest --cov=app --cov-report=term-missing
```

## Skill extraction evaluation
```powershell
python -m evaluation.evaluate_extraction
```
Metrics are written to `outputs/extraction_evaluation.json`. They are computed on the eight synthetic examples with deterministic local matching, not on a real LLM. Do not present the assignment PDF's illustrative values as measured results.

### Local evaluation snapshot

- Baseline macro precision: **1.0000**
- Baseline macro recall: **0.9750**
- Improved macro precision: **1.0000**
- Improved macro recall: **1.0000**
- Repeat-run average score difference: **0.0000**

The golden set includes an alias case (`REST endpoints` as evidence for `REST API`), which the literal baseline misses and the alias-aware extractor captures. These are synthetic offline measurements, not real LLM benchmark results.

## Failure cases
| Failure case | HTTP | Message |
|---|---:|---|
| Empty uploaded file | 400 | The uploaded resume file is empty. |
| Unsupported extension | 415 | Upload a `.txt` or `.pdf` resume. |
| File larger than 5 MB | 413 | Resume file exceeds the 5 MB size limit. |
| Resume over estimated token limit | 413 | Resume is too long; reduce its length. |
| LLM timeout / rate limit | 503 | Friendly retry-later message. |
| Invalid model JSON after 3 attempts | 502 | Could not produce valid structured resume data after retries. |
| Missing resume | 422 | Provide a resume file or resume text. |

## Environment variables
Copy `.env.example` to `.env`. Offline mock mode does not require a secret. If adding a real provider adapter, read the key from `.env`, never return or log it, and keep `.env` out of Git.

## Limitations
- The default adapter is a deterministic mock, not a real LLM call.
- Token counts are estimates; provider-reported usage is unavailable in mock mode.
- Cost is zero only because no paid provider is called.
- PyMuPDF extracts selectable PDF text; scanned/image-only PDFs need OCR and may return empty text.
- Keyword overlap cannot fully understand semantic equivalence, seniority, experience quality or transferable skills.
- Eight synthetic resumes are too few to establish generalization or fairness.
- Resume scores must never be the sole basis for hiring decisions.

## Fairness note
1. Automated scores may reproduce bias in historical hiring data and disadvantage underrepresented groups.
2. Resume wording, career gaps, education access and language differences can affect scores even when job ability is similar.
3. A score is decision support only; it must not be the sole reason to reject or shortlist a candidate.
4. A human reviewer should check evidence against job-related criteria, investigate anomalies, provide accommodations and allow corrections.

## Five-minute demo and interview questions
See [DEMO_SCRIPT.md](DEMO_SCRIPT.md). It covers uploading a resume, showing structured output/score/reasoning, demonstrating a failure case, and answering “Can it be wrong?” and “How do you stop bias?”.

## Pull request workflow
```powershell
git checkout -b feature/resume-analyzer-day5
git add .
git commit -m "Add FastAPI analyzer, tests and evaluation"
git push -u origin feature/resume-analyzer-day5
```
Open a PR from `feature/resume-analyzer-day5` into `main`, review it, then merge. PR comparison: https://github.com/dhanushs-byte/resume-analyzer/compare/main...feature/resume-analyzer-day5

## License
Educational and demonstration use.
