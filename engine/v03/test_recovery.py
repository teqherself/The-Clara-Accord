# SPDX-License-Identifier: MIT
"""Maintenance regressions for the synthetic governance service."""
import os
import sqlite3
import pytest
from service import ProtectedGate, Action, Denied, OutcomeUncertain, CORE_ROLES, maintenance_step

ADMIN = 'a' * 64
YEAR = 31536000

def setup(tmp_path):
    now = [1000.0]
    g = ProtectedGate(str(tmp_path / 'gate.db'), os.urandom(32), ADMIN, lambda: now[0])
    people = {str(i): g.add_actor(ADMIN, str(i), 'reviewer', role) for i, role in enumerate(CORE_ROLES)}
    tokens = {name: g.add_actor(ADMIN, name, role) for name, role in
              (('r', 'requester'), ('lead', 'lead'), ('backup', 'lead'))}
    action = Action('sim.high_risk', 'synthetic', 'dummy', '1')
    g.register(ADMIN, action, people, 'r', 'lead', 3600, backup='backup')
    return g, now, action, people, tokens

def approve(g, a, people):
    for name, token in people.items():
        g.approve(a, name, token)

def rows(g, sql):
    c = sqlite3.connect(g.path)
    try: return c.execute(sql).fetchall()
    finally: c.close()

def break_checkpoint(g, call):
    real = g.checkpoint
    def fail(_): raise OSError('simulated disk failure')
    g.checkpoint = fail
    try:
        with pytest.raises(OutcomeUncertain): call()
    finally: g.checkpoint = real

def test_clock_recovery_invalidates_pending_permission(tmp_path):
    g, now, a, p, t = setup(tmp_path); approve(g, a, p)
    oid = g.object(a, 'r', t['r'], 10)
    now[0] += YEAR; g.maintenance(YEAR); now[0] -= YEAR
    with pytest.raises(Denied): g.alerts('lead', t['lead'])
    with pytest.raises(Denied): g.recover_clock('wrong')
    g.recover_clock(ADMIN)
    assert oid in g.alerts('lead', t['lead'])
    with pytest.raises(Denied): g.execute(a, 'r', t['r'])
    with pytest.raises(Denied): g.approve(a, '0', p['0'])
    assert ('admin','ok') in rows(g, "SELECT actor,outcome FROM audit WHERE event='clock_recovered'")

def test_clock_recovery_refused_when_clock_is_fine(tmp_path):
    g, *_ = setup(tmp_path)
    with pytest.raises(Denied): g.recover_clock(ADMIN)

def test_checkpoint_reconciliation_keeps_effect_single(tmp_path):
    g, now, a, p, t = setup(tmp_path); approve(g, a, p)
    pending = Action('sim.edit','x','y','2')
    g.register(ADMIN,pending,['0'],'r','lead',backup='backup')
    oid = g.object(pending,'r',t['r'])
    break_checkpoint(g, lambda: g.execute(a, 'r', t['r']))
    with pytest.raises(Denied): g.alerts('lead', t['lead'])
    with pytest.raises(Denied): g.reconcile_checkpoint('wrong')
    assert g.reconcile_checkpoint(ADMIN)==1
    with pytest.raises(Denied): g.execute(a, 'r', t['r'])
    with pytest.raises(Denied): g.approve(pending,'0',p['0'])
    assert rows(g, 'SELECT count(*) FROM effects') == [(1,)]
    assert rows(g, 'SELECT count(*) FROM objections WHERE closed=0') == [(1,)]
    with pytest.raises(Denied): g.reconcile_checkpoint(ADMIN)

def test_reconciliation_rejects_database_rollback(tmp_path):
    g, now, a, p, t = setup(tmp_path)
    with open(g.path, 'rb') as f: old = f.read()
    approve(g, a, p)
    with open(g.path, 'wb') as f: f.write(old)
    with pytest.raises(Denied): g.reconcile_checkpoint(ADMIN)

def test_reconciliation_rejects_tampering(tmp_path):
    g, now, a, p, t = setup(tmp_path)
    break_checkpoint(g, lambda: g.approve(a, '0', p['0']))
    with sqlite3.connect(g.path) as c: c.execute('UPDATE plans SET expiry=expiry+100')
    with pytest.raises(Denied): g.reconcile_checkpoint(ADMIN)

def test_backup_closes_objection_raised_by_lead(tmp_path):
    g, now, a, p, t = setup(tmp_path); oid = g.object(a, 'lead', t['lead'])
    with pytest.raises(Denied): g.close_with_evidence(oid, 'lead', t['lead'], 'evidence_resolved', 'x' * 20)
    g.close_with_evidence(oid, 'backup', t['backup'], 'evidence_resolved', 'x' * 20)
    approve(g, a, p); assert g.execute(a, 'r', t['r']) == a.digest()

def test_backup_waits_for_deadline_otherwise(tmp_path):
    g, now, a, p, t = setup(tmp_path); oid = g.object(a, 'r', t['r'], 10)
    args = (oid, 'backup', t['backup'], 'evidence_resolved', 'x' * 20)
    with pytest.raises(Denied): g.close_with_evidence(*args)
    now[0] += 11; g.maintenance(YEAR)
    assert g.alerts('backup', t['backup']) == [oid]
    g.close_with_evidence(*args)

@pytest.mark.parametrize('backup', [None, 'lead', 'r', 'nobody'])
def test_distinct_backup_lead_required(tmp_path, backup):
    g, now, a, p, t = setup(tmp_path)
    with pytest.raises(Denied):
        g.register(ADMIN, Action('sim.edit', 'x', 'y', '2'), ['0'], 'r', 'lead', 60, backup=backup)

def test_core_roles_not_just_headcount(tmp_path):
    g, now, a, p, t = setup(tmp_path)
    generic = [str(i+5) for i in range(4)]
    for name in generic: g.add_actor(ADMIN,name,'reviewer')
    with pytest.raises(Denied,match='core reviewer roles'):
        g.register(ADMIN,Action('sim.high_risk','x','y','2'),generic,'r','lead',backup='backup')
    with pytest.raises(Denied,match='core reviewer roles'):
        g.register(ADMIN,Action('sim.high_risk','x','y','3'),['0','1','2',generic[0]],'r','lead',backup='backup')
    extra=g.add_actor(ADMIN,'extra','reviewer','additional')
    other=Action('sim.high_risk','x','y','4'); g.register(ADMIN,other,list(p)+['extra'],'r','lead',backup='backup')
    approve(g,other,p)
    with pytest.raises(Denied): g.execute(other,'r',t['r'])
    g.approve(other,'extra',extra); assert g.execute(other,'r',t['r'])==other.digest()

def test_inherited_close_cannot_bypass_evidence(tmp_path):
    g, now, a, p, t = setup(tmp_path); oid = g.object(a,'r',t['r'])
    with pytest.raises(Denied): g.close(oid,'lead',t['lead'],'evidence_resolved')
    assert rows(g,'SELECT closed FROM objections')==[(0,)]

def test_audit_records_actor(tmp_path):
    g, now, a, p, t = setup(tmp_path); g.approve(a, '2', p['2'])
    assert rows(g, "SELECT actor,outcome FROM audit WHERE event='approved'") == [('2', 'ok')]

def test_denial_is_recorded_without_secrets(tmp_path):
    g, now, a, p, t = setup(tmp_path)
    request = {'op': 'execute', 'args': {'a': vars(a).copy(), 'actor': 'r', 'token': 'bad-secret'}}
    with pytest.raises(Denied): g.dispatch('request', request)
    assert rows(g, "SELECT event,actor,subject,plan FROM audit WHERE outcome='denied'") == [('execute','unauthenticated','r',a.digest())]
    request['args']['token']=t['r']
    with pytest.raises(Denied): g.dispatch('request',request)
    assert ('r',None) in rows(g,"SELECT actor,subject FROM audit WHERE outcome='denied'")
    request['args']['actor'] = 'pasted-secret'
    with pytest.raises(Denied): g.dispatch('request', request)
    assert 'secret' not in repr(rows(g, 'SELECT * FROM audit'))

def test_denial_log_is_bounded(tmp_path):
    g, *_ = setup(tmp_path); g.denial_limit = 3
    for _ in range(8):
        with pytest.raises(Denied): g.dispatch('request', {'op': 'execute','args':{'actor':'r','token':'bad','a':{'kind':'sim.edit','resource':'x','value':'y','nonce':'bad'}}})
    assert rows(g, "SELECT count(*) FROM audit WHERE outcome='denied'") == [(3,)]

def test_maintenance_failure_closes_execution(tmp_path, capsys, monkeypatch):
    g, now, a, p, t = setup(tmp_path); approve(g,a,p)
    original=g.maintenance
    def fail(_): raise RuntimeError('simulated maintenance fault')
    monkeypatch.setattr(g,'maintenance',fail)
    assert maintenance_step(g, YEAR) is False
    assert 'maintenance refused' in capsys.readouterr().err
    with pytest.raises(Denied,match='maintenance unavailable'): g.execute(a,'r',t['r'])
    monkeypatch.setattr(g,'maintenance',original)
    assert maintenance_step(g, YEAR) is True
    assert g.execute(a,'r',t['r'])==a.digest()

@pytest.mark.parametrize('fault', ['clock', 'checkpoint'])
def test_recovery_works_after_restart(tmp_path, fault):
    now = [1000.0]; path, key = str(tmp_path / 'gate.db'), os.urandom(32)
    g = ProtectedGate(path, key, ADMIN, lambda: now[0])
    if fault == 'clock':
        now[0] += YEAR; g.maintenance(YEAR); now[0] -= YEAR
    else: break_checkpoint(g, lambda: g.add_actor(ADMIN, 'x', 'reviewer'))
    with pytest.raises(Denied): ProtectedGate(path, key, clock=lambda: now[0])
    stopped = ProtectedGate(path, key, clock=lambda: now[0], verify=False)
    getattr(stopped, 'recover_clock' if fault == 'clock' else 'reconcile_checkpoint')(ADMIN)
    ProtectedGate(path, key, clock=lambda: now[0])

def test_combined_recovery(tmp_path):
    g, now, a, p, t = setup(tmp_path); approve(g,a,p)
    pending=Action('sim.edit','x','y','pending'); g.register(ADMIN,pending,['0'],'r','lead',backup='backup'); g.object(pending,'r',t['r'])
    now[0]+=10; break_checkpoint(g,lambda:g.execute(a,'r',t['r'])); now[0]-=20
    with pytest.raises(Denied): g.recover_clock(ADMIN)
    with pytest.raises(Denied): g.reconcile_checkpoint(ADMIN)
    with pytest.raises(Denied): g.recover_combined('wrong')
    assert g.recover_combined(ADMIN)==1
    with pytest.raises(Denied): g.execute(a,'r',t['r'])
    with pytest.raises(Denied): g.approve(pending,'0',p['0'])
    assert rows(g,'SELECT count(*) FROM objections WHERE closed=0')==[(1,)]
    assert rows(g,'SELECT count(*) FROM effects')==[(1,)]
    ProtectedGate(g.path,g.key,clock=lambda:now[0])

def test_junk_cannot_displace_control_refusals(tmp_path):
    g,*_=setup(tmp_path); g.denial_limit=3
    with pytest.raises(Denied): g.dispatch('control',{'op':'add_actor','args':{'admin':'wrong','actor':'x','role':'reviewer'}})
    for _ in range(8):
        with pytest.raises(Denied): g.dispatch('request',{'op':'nonsense'})
    assert rows(g,"SELECT count(*) FROM audit WHERE event='add_actor' AND outcome='denied'")==[(1,)]


def test_junk_counters_are_separate_and_rate_limited(tmp_path):
    g,*_=setup(tmp_path)
    for _ in range(8):
        g.count_junk('wrong_peer')
        g.count_junk('malformed_request')
    g.flush_junk()
    assert rows(g,'SELECT kind,count FROM junk_counts ORDER BY kind')==[('malformed_request',8),('wrong_peer',8)]
    g.count_junk('wrong_peer'); g.flush_junk()
    assert rows(g,"SELECT count FROM junk_counts WHERE kind='wrong_peer'")==[(8,)]
    g.junk_last_flush-=2; g.flush_junk()
    assert rows(g,"SELECT count FROM junk_counts WHERE kind='wrong_peer'")==[(9,)]
