"""
Week 4 - Day 4: AI Resume Analyzer (offline demonstration)
No API key is required. The mock LLM is deterministic and clearly marked as simulated.
For a real LLM, replace mock_extract_response() and mock_match_response() with API calls.
"""
from pathlib import Path
from typing import List
import json, csv, re, logging
from pydantic import BaseModel, Field, ValidationError, ConfigDict

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
OUT = ROOT / "outputs"
OUT.mkdir(exist_ok=True)

logging.basicConfig(
    filename=OUT / "validation_attempts.log",
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    filemode="w"
)
logger = logging.getLogger("resume_analyzer")

class ResumeData(BaseModel):
    model_config = ConfigDict(extra="forbid")
    candidate: str = Field(min_length=2)
    years_of_experience: int = Field(ge=0, le=50)
    skills: List[str] = Field(min_length=1)
    summary: str = Field(min_length=5)

def mock_extract_response(resume_text: str, attempt: int, previous_error: str = "") -> str:
    """Simulates an LLM response. First messy-resume response is intentionally invalid."""
    if not resume_text.strip():
        return "{}"
    if attempt == 1 and "MESSY" in resume_text:
        return json.dumps({
            "candidate": "Alex Example",
            "years_of_experience": 75,
            "skills": ["Python", "SQL"],
            "summary": "Experienced developer with backend skills."
        })
    return json.dumps({
        "candidate": "Alex Example",
        "years_of_experience": 5,
        "skills": ["Python", "SQL", "Git"],
        "summary": "Developer experienced in Python and data processing."
    })

def validate_with_retry(resume_text: str, max_attempts: int = 3):
    """Validate JSON; send the previous validation error back on each retry."""
    previous_error = ""
    for attempt in range(1, max_attempts + 1):
        raw = mock_extract_response(resume_text, attempt, previous_error)
        # Estimated token usage for this offline mock (not provider-reported usage).
        input_tokens = max(1, len(resume_text.split()) + len(previous_error.split()))
        output_tokens = max(1, len(raw.split()))
        try:
            data = ResumeData.model_validate_json(raw)
            logger.info("attempt=%s status=success input_tokens_est=%s output_tokens_est=%s",
                        attempt, input_tokens, output_tokens)
            print(f"Attempt {attempt}: success")
            return {"success": True, "data": data.model_dump(),
                    "attempts": attempt, "token_usage": {
                        "input_tokens_estimated": input_tokens,
                        "output_tokens_estimated": output_tokens}}
        except ValidationError as exc:
            previous_error = str(exc)
            logger.warning("attempt=%s status=validation_error error=%s input_tokens_est=%s output_tokens_est=%s",
                           attempt, previous_error.replace("\\n", " "),
                           input_tokens, output_tokens)
            if attempt == 1 and "75" in raw:
                print("Attempt 1: validation error (years_of_experience must be <= 50)")
            else:
                print(f"Attempt {attempt}: validation error")
    return {"success": False, "error": "Validation failed after 3 attempts.",
            "details": previous_error, "attempts": max_attempts}

def normalize_skill(skill: str) -> str:
    return re.sub(r"[^a-z0-9+#. ]", "", skill.lower()).strip()

def score_candidate(resume: dict, job: dict) -> dict:
    """Offline deterministic stand-in for an LLM score; temperature-0 repeat is identical."""
    skills = {normalize_skill(s) for s in resume["skills"]}
    required = [normalize_skill(s) for s in job["required_skills"]]
    preferred = [normalize_skill(s) for s in job.get("preferred_skills", [])]
    matched = [s for s in job["required_skills"] if normalize_skill(s) in skills]
    missing = [s for s in job["required_skills"] if normalize_skill(s) not in skills]
    preferred_matched = [s for s in job.get("preferred_skills", []) if normalize_skill(s) in skills]
    required_score = (len(matched) / len(required) * 80) if required else 0
    preferred_score = (len(preferred_matched) / len(preferred) * 10) if preferred else 0
    experience_score = min(resume["years_of_experience"], 5) / 5 * 10
    score = round(min(100, required_score + preferred_score + experience_score), 2)
    reasoning = (f"Matched {len(matched)}/{len(required)} required skills; "
                 f"{len(preferred_matched)} preferred skills matched; "
                 f"{resume['years_of_experience']} years of experience contributed to the score.")
    return {"candidate": resume["candidate"], "score": score,
            "matched_skills": ", ".join(matched) or "None",
            "missing_skills": ", ".join(missing) or "None",
            "reasoning": reasoning}

def keyword_score(resume: dict, job: dict) -> float:
    """Simple deterministic bonus baseline: percentage of required keywords present."""
    skills = {normalize_skill(s) for s in resume["skills"]}
    required = [normalize_skill(s) for s in job["required_skills"]]
    return round(100 * sum(s in skills for s in required) / len(required), 2)

def main():
    print("TASK 1 - VALIDATION AND RETRY")
    messy = "MESSY RESUME: Alex Example, 75 years experience, Python and SQL developer."
    result = validate_with_retry(messy)
    (OUT / "messy_resume_validation.json").write_text(json.dumps(result, indent=2), encoding="utf-8")

    print("\\nEmpty resume test:")
    empty_result = validate_with_retry("")
    (OUT / "empty_resume_validation.json").write_text(json.dumps(empty_result, indent=2), encoding="utf-8")
    print("Empty resume result:", empty_result["error"])

    print("\\nTASK 2 - JOB MATCHING (OFFLINE SIMULATION)")
    candidates = json.loads((DATA / "resume_data.json").read_text(encoding="utf-8"))
    all_rows = []
    for job_name in ["Python Developer", "Data Analyst"]:
        job_file = DATA / "job_descriptions" / (job_name.lower().replace(" ", "_") + ".json")
        job = json.loads(job_file.read_text(encoding="utf-8"))
        for resume in candidates:
            first = score_candidate(resume, job)
            second = score_candidate(resume, job)  # temperature=0 consistency check
            first["repeat_score"] = second["score"]
            first["consistent"] = first["score"] == second["score"]
            first["keyword_match_score"] = keyword_score(resume, job)
            first["job"] = job_name
            all_rows.append(first)

    # Rank independently within each job.
    all_rows.sort(key=lambda r: (r["job"], -r["score"], r["candidate"]))
    output_csv = OUT / "candidate_rankings.csv"
    fields = ["job", "rank", "candidate", "score", "repeat_score", "consistent",
              "keyword_match_score", "matched_skills", "missing_skills", "reasoning"]
    with output_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for job_name in ["Python Developer", "Data Analyst"]:
            group = [r for r in all_rows if r["job"] == job_name]
            for rank, row in enumerate(group, 1):
                writer.writerow({"job": job_name, "rank": rank, **{k: row[k] for k in fields if k in row}})

    print("\\nRanking preview:")
    for job_name in ["Python Developer", "Data Analyst"]:
        print(f"\\n{job_name}")
        for rank, row in enumerate([r for r in all_rows if r["job"] == job_name], 1):
            print(f"{rank}. {row['candidate']}: LLM-simulated={row['score']}, "
                  f"keyword={row['keyword_match_score']}, consistent={row['consistent']}")
    print("\\nSaved:", output_csv)
    print("NOTE: All scores are deterministic offline demonstration scores, not actual LLM/API results.")

if __name__ == "__main__":
    main()
