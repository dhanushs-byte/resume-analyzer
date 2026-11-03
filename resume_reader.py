from pathlib import Path
import re
import fitz  # PyMuPDF

SAMPLE_DIR = Path(__file__).parent / "samples"

def clean_text(text: str) -> str:
    """Normalize whitespace and remove common page headers/footers/page numbers."""
    lines = [re.sub(r"\s+", " ", line).strip() for line in text.splitlines()]
    lines = [line for line in lines if line]
    cleaned = []
    for line in lines:
        # Remove standalone page counters such as "Page 1", "1 / 2", or "1"
        if re.fullmatch(r"(?:page\s*)?\d+(?:\s*/\s*\d+)?", line, flags=re.I):
            continue
        # Remove common repeated resume headers/footers
        if re.fullmatch(r"(?:confidential|curriculum vitae|resume)\s*", line, flags=re.I):
            continue
        cleaned.append(line)
    return "\n".join(cleaned).strip()

def read_resume(path):
    """Extract resume text from PDF or TXT; return (clean_text, error_message)."""
    path = Path(path)
    if not path.exists():
        return "", f"Error - file not found: {path}"
    suffix = path.suffix.lower()
    try:
        if suffix == ".pdf":
            with fitz.open(path) as doc:
                raw = "\n".join(page.get_text("text") for page in doc)
            cleaned = clean_text(raw)
            if not cleaned:
                return "", "Error - no text found (scanned or empty PDF)"
            return cleaned, None
        elif suffix in {".txt", ".text"}:
            raw = path.read_text(encoding="utf-8", errors="replace")
            cleaned = clean_text(raw)
            if not cleaned:
                return "", "Error - text file is empty"
            return cleaned, None
        else:
            return "", f"Error - unsupported file type: {suffix}"
    except Exception as exc:
        return "", f"Error - could not read file: {exc}"

def count_tokens(text):
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # Approximation only; install tiktoken for tokenizer-based counts.
        return len(re.findall(r"\w+|[^\w\s]", text))

def main():
    for path in sorted(SAMPLE_DIR.glob("*")):
        if path.suffix.lower() not in {".pdf", ".txt", ".text"}:
            continue
        text, error = read_resume(path)
        if error:
            print(f"{path.name}: {error}")
        else:
            print(f"{path.name}: {len(text)} characters, {count_tokens(text)} tokens")

if __name__ == "__main__":
    main()
