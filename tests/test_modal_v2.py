import csv,json
from pathlib import Path
from src import control_direct as v1
from src import control_modal_v2 as v2
from src.sentinel import review

ROOT=Path(__file__).resolve().parents[1]

def test_modal_boundary_and_case():
    assert v2.facts('The recipient WILL provide evidence; it can apply.')==['can','will']
    assert v2.facts('willing cancellation')==[]
    assert v2.facts(None)==[]

def test_unchanged_and_threshold_behaviour():
    reg=[dict(assessment_id='a',section_id='s',cited_text='Costs can be approved.')]
    new=[dict(section_id='s',ordinal='1',paragraph_text='Costs can be approved.')]
    assert v2.decide(reg,new,[])['a']['verdict']=='UNCHANGED'
    assert v2.decide(reg,[],[])['a']['verdict']=='REVIEW_NOT_FOUND'

def test_modal_change_adds_review_without_changing_v1():
    reg=[dict(assessment_id='a',section_id='s',cited_text='The agency will act and should document.')]
    new=[dict(section_id='s',ordinal='1',paragraph_text='The agency should act and should document.')]
    assert v1.decide(reg,new,[])['a']['verdict']=='EDITORIAL_ONLY'
    assert v2.decide(reg,new,[])['a']['verdict']=='REVIEW_MATERIAL'

def test_actual_cases_and_preserved_baseline(tmp_path):
    r=v2.offline(tmp_path)
    assert r['baseline_metrics']['f1']==16/22
    assert r['candidate_metrics']['tp']==17 and r['candidate_metrics']['fp']==9
    assert r['changed_cases']==['NCHA-037']

def test_sql_candidate_matches_modal_vocabulary():
    text=(ROOT/'sql/21_change_review_modal_v2.sql').read_text(encoding='utf-8')
    assert 'change_review_modal_v2' in text
    assert text.count('may|will|can|should')==2

def test_review_reports_the_selected_view(tmp_path):
    class RecordedSource:
        def sql(self, statement):
            assert 'regsentinel.change_review_modal_v2' in statement
            rows=json.loads((ROOT/'results/latest/review.json').read_text(encoding='utf-8'))['rows']
            return {'rows':rows,'server_ms':0,'wall_s':0}
    summary=review(RecordedSource(),tmp_path,'regsentinel.change_review_modal_v2')
    assert summary['view']=='regsentinel.change_review_modal_v2'

def test_review_rejects_unregistered_view(tmp_path):
    import pytest
    with pytest.raises(ValueError):
        review(None,tmp_path,'unregistered')
