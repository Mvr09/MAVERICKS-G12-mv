from types import SimpleNamespace
from app import main


def test_detail_preserves_origin_in_priority_and_evidence(monkeypatch):
    calls=[]
    row={'supplier_id':'S024','alternate_id':None}
    def suppliers(db,context,origin=''):
        calls.append(('supplier',context,origin));return [row]
    def articles(db,context,origin=''):
        calls.append(('article',context,origin))
        return [{'id':'MOCK','analysis':{'assessments':[{'supplier_id':'S024'}]}}]
    monkeypatch.setattr(main,'suppliers_view',suppliers)
    monkeypatch.setattr(main,'articles_view',articles)
    result=main.supplier('S024',context='exercise',origin='batch:MOCK',db=SimpleNamespace())
    assert calls==[('supplier','exercise','batch:MOCK'),('article','exercise','batch:MOCK')]
    assert result['articles'][0]['id']=='MOCK'
