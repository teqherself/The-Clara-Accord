# SPDX-License-Identifier: MIT
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
import pytest
from gate import Action, Gate, Denied

def setup(kind='sim.high_risk', count=4):
    g=Gate(); a=Action(kind,'synthetic','dummy','unique')
    people=[str(i) for i in range(count)]
    g.register(a,people)
    return g,a,people

def approve(g,a,people):
    for p in people: g.approve(a,p)

def test_st09_three_approvals():
    g,a,p=setup(); approve(g,a,p[:3])
    with pytest.raises(Denied): g.execute(a)
    assert not g.effects

def test_st11_revoked():
    g,a,p=setup(); approve(g,a,p); g.revoke(a,p[0])
    with pytest.raises(Denied): g.execute(a)

def test_st11_expired():
    t=[0]; g=Gate(lambda:t[0]); a=Action('sim.edit','x','v','1'); g.register(a,['h'],1); g.approve(a,'h'); t[0]=1
    with pytest.raises(Denied): g.execute(a)

def test_st12_scope_changed():
    g,a,p=setup(); approve(g,a,p)
    with pytest.raises(Denied): g.execute(replace(a,value='changed'))

def test_st16_unavailable():
    g,a,p=setup(); approve(g,a,p); g.available=False
    with pytest.raises(Denied): g.execute(a)

def test_st18_concurrent_single_use():
    g,a,p=setup(); approve(g,a,p)
    def attempt(_):
        try: g.execute(a); return True
        except Denied: return False
    with ThreadPoolExecutor(max_workers=8) as pool: results=list(pool.map(attempt,range(64)))
    assert sum(results)==1 and len(g.effects)==1

def test_st33_fifth_reviewer():
    g,a,p=setup(count=5); approve(g,a,p[:4])
    with pytest.raises(Denied): g.execute(a)

def test_st10_objection():
    g,a,p=setup(); approve(g,a,p); g.object(a)
    with pytest.raises(Denied): g.execute(a)

def test_default_deny():
    g=Gate(); a=Action('unknown','x','v','1')
    with pytest.raises(Denied): g.register(a,[])
    with pytest.raises(Denied): g.execute(a)

def test_st19_routine():
    g,a,p=setup('sim.edit',1); approve(g,a,p); assert g.execute(a)==a.digest()

def test_duplicate_approval_not_quorum():
    g,a,p=setup(); g.approve(a,p[0]); g.approve(a,p[0])
    with pytest.raises(Denied): g.execute(a)

def test_wrong_reviewer():
    g,a,p=setup()
    with pytest.raises(Denied): g.approve(a,'not-required')

def test_private_disclosure_requires_two():
    g=Gate(); a=Action('sim.private_disclosure','dummy','dummy','1')
    with pytest.raises(Denied): g.register(a,['one'])
