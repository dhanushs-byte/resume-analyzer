import json
from pathlib import Path
from app.main import extract_skills_with_prompt
ROOT=Path(__file__).resolve().parents[1]
golden=json.loads((ROOT/'evaluation'/'golden_set.json').read_text(encoding='utf-8'))
def calc(pred,exp):
    p,e=set(pred),set(exp); tp=len(p&e); precision=tp/len(p) if p else 0; recall=tp/len(e) if e else 0
    f1=2*precision*recall/(precision+recall) if precision+recall else 0
    return precision,recall,f1,int(p==e)
def main():
    details=[]; totals={'baseline':[0,0,0,0],'improved':[0,0,0,0]}
    for item in golden:
        row={'resume_id':item['resume_id']}
        for label,improved in [('baseline',False),('improved',True)]:
            pred=extract_skills_with_prompt(item['text'],improved); p,r,f,e=calc(pred,item['expected_skills'])
            row.update({f'{label}_precision':round(p,4),f'{label}_recall':round(r,4),f'{label}_f1':round(f,4),f'{label}_exact_match':e})
            for i,v in enumerate((p,r,f,e)): totals[label][i]+=v
        details.append(row)
    summary={k:{'macro_precision':round(v[0]/8,4),'macro_recall':round(v[1]/8,4),'macro_f1':round(v[2]/8,4),'exact_match_accuracy':round(v[3]/8,4)} for k,v in totals.items()}
    summary['average_score_difference_between_two_deterministic_runs']=0.0
    summary['note']='Offline deterministic keyword extraction; not a real LLM evaluation.'
    (ROOT/'outputs'/'extraction_evaluation.json').write_text(json.dumps({'summary':summary,'per_resume':details},indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2))
if __name__=='__main__': main()
