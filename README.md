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
