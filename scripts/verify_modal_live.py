"""Check the actual federated v2 output against the independently executed Python rule."""
import csv,datetime,json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]

def main():
    live=ROOT/'results/modal-v2-live/review.json';py=ROOT/'results/modal-v2/predictions.csv'
    doc=json.loads(live.read_text(encoding='utf-8'));a={r['assessment_id']:r['verdict'] for r in doc['rows']}
    b={r['assessment_id']:r['modal_v2'] for r in csv.DictReader(py.open(encoding='utf-8'))}
    assert len(a)==len(b)==48 and a==b,'Live SQL and Python predictions differ'
    assert doc['summary']['view']=='regsentinel.change_review_modal_v2'
    result={'verified_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'view':doc['summary']['view'],'agreement':48,'n':48,'live_summary':doc['summary'],'source_sha256':{p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in [live,py,ROOT/'sql/21_change_review_modal_v2.sql',ROOT/'src/control_modal_v2.py']},'latency_note':'First recorded v2 run after restarting stopped services; not a controlled speed comparison.'}
    (ROOT/'results/modal-v2/live-agreement.json').write_text(json.dumps(result,indent=2),encoding='utf-8');print(json.dumps({'agreement':'48/48','view':result['view']}))
if __name__=='__main__':main()
