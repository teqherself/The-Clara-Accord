# SPDX-License-Identifier: MIT
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import get_context
from dataclasses import replace
import sqlite3
import pytest
from gate import Gate, Action, Denied
ADMIN='a'*64

def setup(tmp_path,count=4,clock=None):
    path=str(tmp_path/'gate.db'); g=Gate(path,ADMIN,**({'clock':clock} if clock else {})); a=Action('sim.high_risk','synthetic','dummy','1')
    p={str(i):g.add_actor(ADMIN,str(i),'reviewer') for i in range(count)}; r=g.add_actor(ADMIN,'r','requester'); lead=g.add_actor(ADMIN,'lead','lead'); g.register(ADMIN,a,p,'r','lead')
    return g,a,p,r,lead

def approve(g,a,p):
    for k,v in p.items(): g.approve(a,k,v)

def attempt(args):
    path,a,r=args
    try: Gate(path).execute(a,'r',r); return 1
    except Denied: return 0

def test_concurrent_process_restart(tmp_path):
    g,a,p,r,_=setup(tmp_path); approve(g,a,p)
    with ProcessPoolExecutor(max_workers=4, mp_context=get_context('spawn')) as pool: assert sum(pool.map(attempt,[(g.path,a,r)]*32))==1
    assert attempt((g.path,a,r))==0
    with sqlite3.connect(g.path) as c: assert c.execute('SELECT count(*) FROM effects').fetchone()==(1,)

@pytest.mark.parametrize('mode',['missing','revoked','changed','wrong_token','unknown','expired','objected','overdue','five_required'])
def test_denials(tmp_path,mode):
    t=[100]; g,a,p,r,lead=setup(tmp_path,5 if mode=='five_required' else 4,lambda:t[0]); approve(g,a,p)
    if mode in ('missing','revoked','five_required'): g.revoke(a,'0',p['0'])
    if mode=='changed': a=replace(a,value='changed')
    if mode=='wrong_token': r='wrong'
    if mode=='unknown': a=replace(a,kind='unknown')
    if mode=='expired': t[0]=161
    if mode in ('objected','overdue'):
        oid=g.object(a,'r',r,1)
        if mode=='overdue': t[0]=102; assert oid in g.overdue('lead',lead)
    with pytest.raises(Denied): g.execute(a,'r',r)

def test_closure_requires_fresh_approval(tmp_path):
    g,a,p,r,lead=setup(tmp_path); approve(g,a,p); oid=g.object(a,'r',r)
    with pytest.raises(Denied): g.close(oid,'r',r,'evidence_resolved')
    g.close(oid,'lead',lead,'evidence_resolved')
    with pytest.raises(Denied): g.execute(a,'r',r)
    approve(g,a,p); assert g.execute(a,'r',r)==a.digest()

def test_admin_separation(tmp_path):
    g,a,p,r,_=setup(tmp_path)
    with pytest.raises(Denied): g.add_actor(r,'evil','reviewer')
    with pytest.raises(Denied): g.approve(a,'0',r)

def test_atomic_rollback(tmp_path):
    g,a,p,r,_=setup(tmp_path); approve(g,a,p)
    with sqlite3.connect(g.path) as c: c.execute("CREATE TRIGGER fail_audit BEFORE INSERT ON audit WHEN NEW.event='executed' BEGIN SELECT RAISE(ABORT,'failure'); END")
    with pytest.raises(Denied): g.execute(a,'r',r)
    with sqlite3.connect(g.path) as c:
        assert c.execute('SELECT count(*) FROM effects').fetchone()==(0,); c.execute('DROP TRIGGER fail_audit')
    assert g.execute(a,'r',r)==a.digest()


def test_requester_scope(tmp_path):
    g,a,p,r,_=setup(tmp_path); approve(g,a,p); other=g.add_actor(ADMIN,'other','requester')
    with pytest.raises(Denied): g.execute(a,'other',other)
    assert g.execute(a,'r',r)==a.digest()

def test_assigned_review_lead(tmp_path):
    g,a,p,r,lead=setup(tmp_path); oid=g.object(a,'r',r); other=g.add_actor(ADMIN,'other','lead')
    with pytest.raises(Denied): g.close(oid,'other',other,'evidence_resolved')
    g.close(oid,'lead',lead,'evidence_resolved')
