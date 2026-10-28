"""Modal-aware candidate: the unchanged aligner with explicit will/can facts.

Keeps the original view and decision rule reproducible. This is a versioned
candidate learned from known error analysis, not an untouched blind test.
"""
from __future__ import annotations
import argparse,csv,hashlib,json,re,random
from pathlib import Path
from . import control_direct as v1

ROOT=Path(__file__).resolve().parents[1]
MODALS=re.compile(r'\b(?:will|can)\b')

def facts(text: str) -> list[str]:
    return sorted(set(v1.facts(text)) | set(MODALS.findall((text or '').lower())))

def decide(register,newp,versions):
    return v1.decide(register,newp,versions,fact_extractor=facts)

def metrics(y,p):
    tp=sum(a and b for a,b in zip(y,p));fp=sum(not a and b for a,b in zip(y,p));fn=sum(a and not b for a,b in zip(y,p))
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else 0,recall=tp/(tp+fn) if tp+fn else 0,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0,flagged=sum(p))

def offline(out:Path):
    reg=list(csv.DictReader((ROOT/'data/processed/compliance_register.csv').open(encoding='utf-8')))
    newp=[r for r in csv.DictReader((ROOT/'data/processed/paragraphs.csv').open(encoding='utf-8')) if r['version_date']=='2024-10-01']
    versions=json.loads((ROOT/'data/raw/ecfr/versions_title2_part200.json').read_text(encoding='utf-8'))['content_versions']
    labels={r['assessment_id']:r for r in csv.DictReader((ROOT/'eval/labeling/labels.csv').open(encoding='utf-8'))}
    base,cand=v1.decide(reg,newp,versions),decide(reg,newp,versions)
    ids=[r['assessment_id'] for r in reg];truth=[]
    for r in reg:
        i=r['assessment_id']
        if i not in labels:
            assert any(p['section_id']==r['section_id'] and p['paragraph_text']==r['cited_text'] for p in newp)
        truth.append(i in labels and labels[i]['label']=='MATERIAL')
    pb=[base[i]['verdict'].startswith('REVIEW') for i in ids];pc=[cand[i]['verdict'].startswith('REVIEW') for i in ids]
    groups={}
    for i,r in enumerate(reg):groups.setdefault(r['section_id'],[]).append(i)
    rng=random.Random(20261028);keys=sorted(groups);d=[]
    for _ in range(2000):
        ix=[i for k in rng.choices(keys,k=len(keys)) for i in groups[k]]
        d.append(metrics([truth[i] for i in ix],[pc[i] for i in ix])['f1']-metrics([truth[i] for i in ix],[pb[i] for i in ix])['f1'])
    d.sort();out.mkdir(parents=True,exist_ok=True)
    result={'candidate':'modal_v2','baseline':'v1','n':len(ids),'kind':'exploratory_existing_benchmark','source':'official eCFR text; fictional register; existing independent-annotator labels','baseline_metrics':metrics(truth,pb),'candidate_metrics':metrics(truth,pc),'delta_f1_ci95_section_bootstrap':[d[50],d[1949]],'changed_cases':[i for i in ids if base[i]['verdict']!=cand[i]['verdict']],'sql_view':'regsentinel.change_review_modal_v2','sql_live_verified':False}
    with (out/'predictions.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['assessment_id','section','truth_material','v1','modal_v2'])
        for i,r,t in zip(ids,reg,truth):w.writerow([i,r['section_id'],int(t),base[i]['verdict'],cand[i]['verdict']])
    (out/'results.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2));return result

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=ROOT/'results/modal-v2');args=ap.parse_args();offline(args.out)

if __name__=='__main__':main()
