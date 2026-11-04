from __future__ import annotations
import asyncio, json, logging, re, time, uuid
from pathlib import Path
from typing import Any, Protocol
import fitz
from dotenv import load_dotenv
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / '.env')
MAX_FILE_BYTES = 5 * 1024 * 1024
MAX_RESUME_TOKENS = 4000
LLM_TIMEOUT_SECONDS = 8
COST_PER_1K_INPUT_TOKENS = 0.0
COST_PER_1K_OUTPUT_TOKENS = 0.0
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger('resume_analyzer_api')

class ResumeData(BaseModel):
    model_config = ConfigDict(extra='forbid')
    candidate: str = Field(min_length=2, max_length=120)
    years_of_experience: int = Field(ge=0, le=50)
    skills: list[str] = Field(min_length=1)
    summary: str = Field(min_length=5, max_length=2000)

class LLMTimeoutError(Exception): pass
class LLMRateLimitError(Exception): pass
class LLMUnavailableError(Exception): pass

class LLMClient(Protocol):
    async def extract_resume(self, resume_text: str, feedback: str = '') -> str: ...

SKILL_ALIASES = {
    'python':['python'], 'fastapi':['fastapi'], 'sql':['sql','relational database queries','database queries'],
    'rest api':['rest api','rest apis','rest endpoints','http endpoints'], 'git':['git','version control'],
    'docker':['docker','containerization','containers'], 'pandas':['pandas','dataframe operations','dataframes'],
    'excel':['excel','spreadsheets'], 'power bi':['power bi','powerbi','business intelligence dashboards'],
    'tableau':['tableau'], 'statistics':['statistics','statistical analysis'],
    'data visualization':['data visualization','visualizations','data charts'],
    'scikit-learn':['scikit-learn','sklearn'], 'tensorflow':['tensorflow'], 'pytorch':['pytorch'],
    'nlp':['nlp','natural language processing'], 'machine learning':['machine learning','predictive modeling'],
    'numpy':['numpy','numerical arrays'], 'matplotlib':['matplotlib','matplotlib plots'],
    'flask':['flask'], 'mysql':['mysql'], 'java':['java'], 'spring boot':['spring boot'],
    'postgresql':['postgresql','postgres'], 'etl':['etl','extract transform load'],
    'data cleaning':['data cleaning','cleaned datasets']
}

def contains_phrase(text: str, phrase: str) -> bool:
    return re.search(r'(?<![a-z0-9+#])' + re.escape(phrase) + r'(?![a-z0-9+#])', text) is not None

def extract_skills_with_prompt(resume_text: str, improved: bool = True) -> list[str]:
    """Offline deterministic extractor used until a real LLM adapter is configured."""
    normalized = re.sub(r'\s+', ' ', resume_text.lower())
    found=[]
    for canonical, aliases in SKILL_ALIASES.items():
        phrases = aliases if improved else [canonical]
        if any(contains_phrase(normalized, phrase) for phrase in phrases): found.append(canonical)
    return found

def candidate_name(text: str) -> str:
    for line in text.splitlines():
        line=line.strip()
        if line and len(line)<=120 and not re.search(r'resume|curriculum|skills|experience|education',line,re.I) and not line.lower().startswith('years'):
            return line
    return 'Unknown Candidate'

def improved_extraction_prompt(text: str, feedback: str='') -> str:
    return ('Extract resume facts as JSON only: candidate, years_of_experience, skills, summary. '
            'Include skills explicitly listed and skills clearly evidenced in experience/projects. '
            'Normalize aliases (REST endpoints -> REST API, HTTP endpoints -> REST API, dataframe operations -> Pandas). '
            'Do not infer skills from job titles alone. Do not invent facts. Validation feedback: '+feedback+'\nRESUME:\n'+text)

class OfflineMockLLM:
    async def extract_resume(self, resume_text: str, feedback: str='') -> str:
        await asyncio.sleep(0)
        match=re.search(r'(\d{1,2})\s*\+?\s*years?',resume_text,re.I)
        years=min(int(match.group(1)),50) if match else 0
        skills=extract_skills_with_prompt(resume_text, improved=True)
        return json.dumps({'candidate':candidate_name(resume_text),'years_of_experience':years,
                           'skills':skills,'summary':' '.join(resume_text.split())[:500] or 'No resume text supplied.'})

class SequenceMockLLM:
    def __init__(self, responses: list[str]): self.responses=list(responses); self.calls=[]
    async def extract_resume(self, resume_text: str, feedback: str='') -> str:
        self.calls.append(feedback)
        return self.responses.pop(0) if self.responses else '{}'

async def parse_resume_with_retry(text: str, llm: LLMClient, max_attempts: int=3):
    feedback=''; input_tokens=0; output_tokens=0
    for attempt in range(1,max_attempts+1):
        prompt=improved_extraction_prompt(text,feedback)
        response=await llm.extract_resume(text,feedback)
        input_tokens += max(1,len(prompt.split())); output_tokens += max(1,len(response.split()))
        try:
            data=ResumeData.model_validate_json(response)
            return data,attempt,{'input_tokens_estimated':input_tokens,'output_tokens_estimated':output_tokens}
        except ValidationError as exc:
            feedback=str(exc)
            logger.warning('validation attempt=%s failed: %s',attempt,feedback.replace('\n',' '))
    raise ValueError('LLM returned invalid resume JSON after 3 attempts: '+feedback)

def match_resume(resume: ResumeData, job_description: str) -> dict[str,Any]:
    job_skills=set(extract_skills_with_prompt(job_description,True)); candidate_skills=set(resume.skills)
    matched=sorted(job_skills & candidate_skills); missing=sorted(job_skills-candidate_skills)
    score=round(100*len(matched)/max(1,len(job_skills)),2)
    return {'score':score,'matched_skills':matched,'missing_skills':missing,
            'reasoning':f'{len(matched)} of {len(job_skills)} job-description skills matched. The score is a transparent keyword-overlap baseline, not an assessment of overall ability.'}

def extract_text_from_upload(filename: str, content: bytes) -> str:
    suffix=Path(filename or '').suffix.lower()
    if suffix not in {'.txt','.pdf'}: raise HTTPException(415,'Unsupported file type. Upload a .txt or .pdf resume.')
    if not content: raise HTTPException(400,'The uploaded resume file is empty.')
    if len(content)>MAX_FILE_BYTES: raise HTTPException(413,'Resume file exceeds the 5 MB size limit.')
    if suffix=='.txt':
        try: return content.decode('utf-8-sig').strip()
        except UnicodeDecodeError: raise HTTPException(400,'Text resume must be UTF-8 encoded.')
    try:
        with fitz.open(stream=content,filetype='pdf') as pdf: return '\n'.join(p.get_text() for p in pdf).strip()
    except Exception: raise HTTPException(400,'Could not read the PDF. It may be damaged or encrypted.')

def validate_resume_length(text: str):
    estimate=max(1,len(text.split())*4//3)
    if estimate>MAX_RESUME_TOKENS: raise HTTPException(413,f'Resume is too long (estimated {estimate} tokens; limit is {MAX_RESUME_TOKENS}).')
    if not text.strip(): raise HTTPException(400,'Resume text is empty or contains no extractable text.')

def estimated_cost(usage):
    return round(usage['input_tokens_estimated']/1000*COST_PER_1K_INPUT_TOKENS + usage['output_tokens_estimated']/1000*COST_PER_1K_OUTPUT_TOKENS,8)

app=FastAPI(title='AI Resume Analyzer API',version='1.0.0',description='Offline demo API for resume extraction and job matching.')
llm_client: LLMClient=OfflineMockLLM()

@app.middleware('http')
async def request_logging(request: Request, call_next):
    request_id=request.headers.get('X-Request-ID') or str(uuid.uuid4()); request.state.request_id=request_id
    start=time.perf_counter(); response=await call_next(request); response.headers['X-Request-ID']=request_id
    logger.info('request_id=%s method=%s path=%s status=%s duration_ms=%.2f',request_id,request.method,request.url.path,response.status_code,(time.perf_counter()-start)*1000)
    return response

@app.exception_handler(HTTPException)
async def http_error(request: Request, exc: HTTPException):
    return JSONResponse(status_code=exc.status_code,content={'error':'request_failed','message':exc.detail,'request_id':getattr(request.state,'request_id','unknown')})

@app.get('/health')
async def health(): return {'status':'ok','mode':'offline_mock','api_key_configured':False}

@app.post('/analyze')
async def analyze(request: Request, job_description: str=Form(...), resume_file: UploadFile|None=File(default=None), resume_text: str|None=Form(default=None)):
    if not job_description.strip(): raise HTTPException(422,'job_description must not be empty.')
    if resume_file is not None and resume_text and resume_text.strip(): raise HTTPException(422,'Provide either resume_file or resume_text, not both.')
    if resume_file is None and not (resume_text and resume_text.strip()): raise HTTPException(422,'Provide a resume_file upload or resume_text.')
    raw=extract_text_from_upload(resume_file.filename or '',await resume_file.read()) if resume_file is not None else resume_text.strip()
    validate_resume_length(raw)
    try:
        parsed,attempts,usage=await asyncio.wait_for(parse_resume_with_retry(raw,llm_client,3),timeout=LLM_TIMEOUT_SECONDS)
        matched=match_resume(parsed,job_description)
    except asyncio.TimeoutError: raise HTTPException(503,'Resume analysis timed out. Please retry.')
    except LLMTimeoutError: raise HTTPException(503,'The language model timed out. Please retry.')
    except LLMRateLimitError: raise HTTPException(503,'The language model is rate limited. Please retry later.')
    except LLMUnavailableError: raise HTTPException(503,'The language model is temporarily unavailable.')
    except ValueError as exc:
        logger.error('request_id=%s invalid model output: %s',request.state.request_id,exc)
        raise HTTPException(502,'Could not produce valid structured resume data after retries.')
    return {'candidate_name':parsed.candidate,'years_of_experience':parsed.years_of_experience,'skills':parsed.skills,'summary':parsed.summary,
            **matched,'attempts':attempts,'token_usage':usage,'estimated_cost_usd':estimated_cost(usage),
            'scoring_mode':'offline_keyword_overlap','request_id':request.state.request_id}
