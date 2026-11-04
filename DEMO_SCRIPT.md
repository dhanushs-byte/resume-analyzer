# Five-minute demo
1. 0:00–0:40 — Introduce the analyzer: resume extraction and job-description matching.
2. 0:40–1:30 — Run `uvicorn app.main:app --reload`; open `http://127.0.0.1:8000/docs`.
3. 1:30–2:30 — Call `POST /analyze` with `data/resumes/resume_01.txt` and the Python Developer job description. Show structured fields, score, matched/missing skills and reasoning.
4. 2:30–3:20 — Explain that scoring is offline keyword overlap; token counts are estimates and mock cost is $0.
5. 3:20–4:10 — Upload an empty `.txt` file and show HTTP 400; optionally try `.docx` for HTTP 415.
6. 4:10–5:00 — Run tests/evaluation and explain limitations and fairness.

## Can it be wrong?
Yes. Text extraction can miss information, aliases can be misunderstood, and keyword overlap cannot understand context or transferable skills. Scanned PDFs may contain no selectable text. The result is decision support, not a hiring decision.

## How do you stop bias?
Do not use protected attributes or proxies as scoring features. Evaluate extraction and ranking on representative data where lawful. Keep criteria job-related and explainable. Require human review, allow corrections, and never auto-reject candidates based only on a score.
