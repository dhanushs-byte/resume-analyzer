import json
import pytest
from fastapi.testclient import TestClient
import app.main as api
from app.main import app, ResumeData, SequenceMockLLM, LLMTimeoutError, LLMRateLimitError

client=TestClient(app)
VALID={'candidate':'Test Candidate','years_of_experience':2,'skills':['python','sql'],'summary':'Python developer with SQL experience.'}
JOB='Python Developer required skills: Python, SQL, FastAPI, Git.'

def test_health():
    r=client.get('/health'); assert r.status_code==200 and r.json()['status']=='ok'

def test_analyze_success_text(monkeypatch):
    monkeypatch.setattr(api,'llm_client',SequenceMockLLM([json.dumps(VALID)]))
    r=client.post('/analyze',data={'resume_text':'Test Candidate\n2 years experience\nPython SQL','job_description':JOB})
    assert r.status_code==200 and r.json()['candidate_name']=='Test Candidate'
    assert r.json()['score']==50.0 and r.json()['token_usage']['input_tokens_estimated']>0
    assert r.headers.get('x-request-id')

def test_invalid_json_then_success(monkeypatch):
    mock=SequenceMockLLM(['{bad json',json.dumps(VALID)]); monkeypatch.setattr(api,'llm_client',mock)
    r=client.post('/analyze',data={'resume_text':'Test Candidate\nPython SQL','job_description':JOB})
    assert r.status_code==200 and r.json()['attempts']==2 and mock.calls[1]

def test_empty_file_400():
    r=client.post('/analyze',data={'job_description':JOB},files={'resume_file':('empty.txt',b'','text/plain')})
    assert r.status_code==400

def test_wrong_type_415():
    r=client.post('/analyze',data={'job_description':JOB},files={'resume_file':('resume.docx',b'fake','application/octet-stream')})
    assert r.status_code==415

def test_missing_resume_422():
    assert client.post('/analyze',data={'job_description':JOB}).status_code==422

def test_oversized_file_413():
    r=client.post('/analyze',data={'job_description':JOB},files={'resume_file':('large.txt',b'x'*(5*1024*1024+1),'text/plain')})
    assert r.status_code==413

def test_too_long_resume_413():
    assert client.post('/analyze',data={'resume_text':'word '*4001,'job_description':JOB}).status_code==413

def test_timeout_503(monkeypatch):
    class Mock:
        async def extract_resume(self,text,feedback=''): raise LLMTimeoutError()
    monkeypatch.setattr(api,'llm_client',Mock())
    assert client.post('/analyze',data={'resume_text':'Test Candidate Python','job_description':JOB}).status_code==503

def test_rate_limit_503(monkeypatch):
    class Mock:
        async def extract_resume(self,text,feedback=''): raise LLMRateLimitError()
    monkeypatch.setattr(api,'llm_client',Mock())
    assert client.post('/analyze',data={'resume_text':'Test Candidate Python','job_description':JOB}).status_code==503

def test_invalid_json_after_three_502(monkeypatch):
    monkeypatch.setattr(api,'llm_client',SequenceMockLLM(['bad','bad','bad']))
    assert client.post('/analyze',data={'resume_text':'Test Candidate Python','job_description':JOB}).status_code==502

def test_resume_data_constraints():
    with pytest.raises(Exception): ResumeData.model_validate({**VALID,'years_of_experience':51})
    with pytest.raises(Exception): ResumeData.model_validate({**VALID,'skills':[]})
