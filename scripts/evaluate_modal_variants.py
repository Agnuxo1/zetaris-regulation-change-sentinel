"""Reproduce all three fixed error-analysis interventions; preserve every outcome."""
import csv,json,re,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from src import control_direct as v1,control_modal_v2 as v2

def authority_facts(text):
    t=(text or '').lower().replace('non-federal entity','recipient or subrecipient')
    role=re.findall(r'\b(?:federal agency|pass-through entity|recipient|subrecipient)\b',t)
    return sorted(set(v1.facts(text))|{'role:'+r for r in role})

def main():
    reg=list(csv.DictReader((ROOT/'data/processed/compliance_register.csv').open(encoding='utf-8')))
    newp=[r for r in csv.DictReader((ROOT/'data/processed/paragraphs.csv').open(encoding='utf-8')) if r['version_date']=='2024-10-01']
    versions=json.loads((ROOT/'data/raw/ecfr/versions_title2_part200.json').read_text(encoding='utf-8'))['content_versions']
    labels={r['assessment_id']:r for r in csv.DictReader((ROOT/'eval/labeling/labels.csv').open(encoding='utf-8'))}
    ids=[r['assessment_id'] for r in reg]
    y=[]
    for r in reg:
        i=r['assessment_id']
        if i not in labels:assert any(p['section_id']==r['section_id'] and p['paragraph_text']==r['cited_text'] for p in newp)
        y.append(i in labels and labels[i]['label']=='MATERIAL')
    variants={'v1':v1.decide(reg,newp,versions),'modal_v2':v2.decide(reg,newp,versions),'authority':v1.decide(reg,newp,versions,fact_extractor=authority_facts),'distance_045':v1.decide(reg,newp,versions,max_distance=.45)}
    result={name:v2.metrics(y,[d[i]['verdict'].startswith('REVIEW') for i in ids]) for name,d in variants.items()}
    result={'kind':'exploratory_known_benchmark','n':len(ids),'methods':result,'selected':'modal_v2','reason':'One additional true material change, no additional false positive in these 48 cases; external validation still required.'}
    out=ROOT/'results/modal-v2';out.mkdir(exist_ok=True,parents=True)
    (out/'ablations.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    with (out/'ablation_predictions.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['assessment_id','truth_material',*variants])
        for i,t in zip(ids,y):w.writerow([i,int(t),*[v[i]['verdict'] for v in variants.values()]])
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
