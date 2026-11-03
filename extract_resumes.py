from pathlib import Path
import json
import os
from openai import OpenAI
from resume_reader import read_resume, SAMPLE_DIR, count_tokens

ROOT = Path(__file__).parent
PROMPT_PATH = ROOT / "prompts" / "system_prompt_v1.txt"
SCHEMA_PATH = ROOT / "schema.json"
OUTPUT_DIR = ROOT / "outputs"
MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

def main():
    if not os.getenv("OPENAI_API_KEY"):
        raise SystemExit("Missing OPENAI_API_KEY. Set it in your terminal before running.")
    client = OpenAI()
    system_prompt = PROMPT_PATH.read_text(encoding="utf-8")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    OUTPUT_DIR.mkdir(exist_ok=True)

    combined = {}
    for path in sorted(SAMPLE_DIR.glob("*")):
        if path.suffix.lower() not in {".pdf", ".txt", ".text"}:
            continue
        text, error = read_resume(path)
        if error:
            combined[path.name] = {"error": error}
            print(f"{path.name}: {error}")
            continue

        print(f"{path.name}: {len(text)} characters, {count_tokens(text)} tokens")
        response = client.chat.completions.create(
            model=MODEL,
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": schema
            },
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "Extract information from this resume text:\n\n" + text}
            ]
        )
        result = json.loads(response.choices[0].message.content)
        combined[path.name] = result
        (OUTPUT_DIR / f"{path.stem}.json").write_text(
            json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        print(json.dumps(result, indent=2, ensure_ascii=False))

    (OUTPUT_DIR / "extraction_results.json").write_text(
        json.dumps(combined, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(f"\nSaved results to: {OUTPUT_DIR}")

if __name__ == "__main__":
    main()
