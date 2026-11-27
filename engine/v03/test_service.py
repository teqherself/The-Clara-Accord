# SPDX-License-Identifier: MIT
import json
import os
from pathlib import Path
import secrets
import socket
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import time
import pytest
from service import ProtectedGate, Action, Denied, OutcomeUncertain, CORE_ROLES

ADMIN='a'*64
KEY=b'k'*32

def fixture_gate(tmp_path,clock=time.time):
    g=ProtectedGate(str(tmp_path/'gate.db'),KEY,ADMIN,clock)
    a=Action('sim.high_risk','dummy','value','unique')
    p={str(i):g.add_actor(ADMIN,str(i),'reviewer',role) for i,role in enumerate(CORE_ROLES)}
    r=g.add_actor(ADMIN,'r','requester'); lead=g.add_actor(ADMIN,'lead','lead')
    g.add_actor(ADMIN,'backup','lead'); g.register(ADMIN,a,p,'r','lead',backup='backup')
    return g,a,p,r,lead

def approve(g,a,p):
    for actor,token in p.items(): g.approve(a,actor,token)

def test_state_tampering(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path); approve(g,a,p)
    with sqlite3.connect(g.path) as c: c.execute('UPDATE plans SET used=1')
    with pytest.raises(Denied,match='integrity'): g.execute(a,'r',r)

def test_schema_tampering(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path)
    with sqlite3.connect(g.path) as c: c.execute('CREATE TRIGGER unexpected AFTER INSERT ON effects BEGIN DELETE FROM approvals; END')
    with pytest.raises(Denied,match='integrity'): g.execute(a,'r',r)

def test_database_only_rollback(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path); approve(g,a,p)
    backup=tmp_path/'old.db'; shutil.copyfile(g.path,backup)
    assert g.execute(a,'r',r)==a.digest()
    shutil.copyfile(backup,g.path)
    with pytest.raises(Denied,match='checkpoint mismatch'): g.execute(a,'r',r)

def test_checkpoint_loss(tmp_path):
    g,*_=fixture_gate(tmp_path); g.anchor.unlink()
    with pytest.raises(Denied): ProtectedGate(g.path,KEY)

def test_checkpoint_write_failure(tmp_path,monkeypatch):
    g,a,p,r,_=fixture_gate(tmp_path); approve(g,a,p)
    def fail(_): raise OSError('injected checkpoint failure')
    monkeypatch.setattr(g,'checkpoint',fail)
    with pytest.raises(OutcomeUncertain): g.execute(a,'r',r)
    with sqlite3.connect(g.path) as c: assert c.execute('SELECT count(*) FROM effects').fetchone()==(1,)
    with pytest.raises(Denied,match='checkpoint mismatch'): ProtectedGate(g.path,KEY)

def test_wrong_key(tmp_path):
    g,*_=fixture_gate(tmp_path)
    with pytest.raises(Denied,match='integrity'): ProtectedGate(g.path,b'x'*32)

def test_no_rebootstrap(tmp_path):
    g,*_=fixture_gate(tmp_path)
    with sqlite3.connect(g.path) as c: c.execute('DROP TABLE integrity')
    with pytest.raises(Denied): ProtectedGate(g.path,KEY,ADMIN)

def test_credential_rotation_revokes_approval(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path); approve(g,a,p)
    token=g.credential(ADMIN,'0')
    with pytest.raises(Denied): g.approve(a,'0',p['0'])
    with pytest.raises(Denied): g.execute(a,'r',r)
    g.approve(a,'0',token); assert g.execute(a,'r',r)==a.digest()

def test_disabled_requester(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path); approve(g,a,p); g.credential(ADMIN,'r',True)
    with pytest.raises(Denied): g.execute(a,'r',r)

def test_unrelated_objection(tmp_path):
    g,a,p,r,_=fixture_gate(tmp_path); other=g.add_actor(ADMIN,'other','requester')
    with pytest.raises(Denied): g.object(a,'other',other)

def test_resolution_requires_evidence(tmp_path):
    g,a,p,r,lead=fixture_gate(tmp_path); approve(g,a,p); oid=g.object(a,'r',r)
    with pytest.raises(Denied): g.close_with_evidence(oid,'lead',lead,'evidence_resolved','')
    g.close_with_evidence(oid,'lead',lead,'evidence_resolved','Synthetic rationale verified')
    with pytest.raises(Denied): g.execute(a,'r',r)
    approve(g,a,p); assert g.execute(a,'r',r)==a.digest()

def test_overdue_escalation_and_retention(tmp_path):
    t=[100.0]; g,a,p,r,lead=fixture_gate(tmp_path,lambda:t[0]); approve(g,a,p)
    oid=g.object(a,'r',r,1); t[0]=102
    g.maintenance(60); g.maintenance(60)
    assert g.alerts('lead',lead)==[oid]
    with sqlite3.connect(g.path) as c: assert c.execute('SELECT count(*) FROM escalations').fetchone()==(1,)
    with pytest.raises(Denied): g.execute(a,'r',r)
    t[0]=170; assert g.maintenance(60)>0
    assert g.alerts('lead',lead)==[oid]
    with sqlite3.connect(g.path) as c: assert c.execute('SELECT count(*) FROM audit WHERE at<110').fetchone()==(0,)

def test_retention_preserves_consumption(tmp_path):
    t=[100.0]; g,a,p,r,_=fixture_gate(tmp_path,lambda:t[0]); approve(g,a,p); g.execute(a,'r',r)
    t[0]=170; g.maintenance(60)
    with pytest.raises(Denied): g.execute(a,'r',r)
    with sqlite3.connect(g.path) as c: assert c.execute('SELECT count(*) FROM effects').fetchone()==(1,)

def test_clock_rollback(tmp_path):
    t=[100.0]; g,a,p,r,_=fixture_gate(tmp_path,lambda:t[0]); approve(g,a,p); t[0]=99
    with pytest.raises(Denied,match='clock rollback'): g.execute(a,'r',r)

def test_request_plane_disallows_admin(tmp_path):
    g,*_=fixture_gate(tmp_path)
    with pytest.raises(Denied): g.dispatch('request',{'op':'add_actor','args':{'admin':ADMIN,'actor':'new','role':'reviewer'}})

def rpc(path,op,**args):
    with socket.socket(socket.AF_UNIX) as s:
        s.settimeout(5); s.connect(str(path)); s.sendall(json.dumps({'op':op,'args':args}).encode()+b'\n')
        return json.loads(s.makefile('rb').readline())

@pytest.mark.skipif(os.geteuid()!=0 or not sys.platform.startswith('linux'),reason='requires Linux root for real UID separation test')
def test_kernel_boundary_and_restart():
    # Root is only the harness. Service and requester run as distinct unprivileged UIDs.
    with tempfile.TemporaryDirectory(prefix='cae-test-',dir='/tmp') as td:
        base=Path(td); base.chmod(0o755); private=base/'private'; private.mkdir(mode=0o700); public=base/'public'; public.mkdir(mode=0o755)
        for name,data in [('integrity.key',KEY),('bootstrap.token',ADMIN.encode())]:
            f=private/name; f.write_bytes(data); f.chmod(0o600); os.chown(f,65533,65533)
        os.chown(private,65533,65533); os.chown(public,65533,65533)
        # Use only the two required source files in a traversable, root-owned fixture.
        source=Path(__file__).resolve().parent
        code_root=base/'code'; code_root.mkdir(mode=0o755)
        for version,filename in (('v03','service.py'),('v02','gate.py')):
            folder=code_root/version; folder.mkdir(mode=0o755)
            origin=source/filename if version=='v03' else source.parent/version/filename
            target=folder/filename; shutil.copyfile(origin,target); target.chmod(0o644)
        command=[sys.executable,str(code_root/'v03'/'service.py'),'--private',str(private),'--sockets',str(public),'--requester-uid','65534']
        def start(first=False):
            proc=subprocess.Popen(command+(['--bootstrap'] if first else []),stdout=subprocess.PIPE,stderr=subprocess.PIPE,user=65533,group=65533,extra_groups=[],cwd='/tmp')
            for _ in range(100):
                if proc.poll() is not None: raise AssertionError(proc.communicate())
                try:
                    # Wrong operation is harmless, but proves the socket accepts calls.
                    if control('invalid')=={'ok':False,'error':'denied'}: return proc
                except (OSError,AssertionError): time.sleep(0.05)
            proc.kill(); proc.wait(); raise AssertionError('service not ready')
        def child(code,uid=65534):
            return subprocess.run([sys.executable,'-c',code],user=uid,group=uid,extra_groups=[],cwd='/tmp',capture_output=True,text=True,timeout=10)
        def call_as(plane,op,args,uid):
            code=f"import socket,json;s=socket.socket(socket.AF_UNIX);s.connect({str(public/(plane+'.sock'))!r});s.sendall({(json.dumps({'op':op,'args':args})+chr(10)).encode()!r});print(s.makefile('rb').readline().decode())"
            result=child(code,uid)
            if uid==65532 and result.returncode and any(e in result.stderr for e in ('BrokenPipeError','ConnectionResetError')):
                return {'ok':False,'error':'peer_closed'}
            assert result.returncode==0,result.stderr
            return json.loads(result.stdout)
        def as_request(op,args,uid=65534): return call_as('request',op,args,uid)
        def control(op,**args): return call_as('control',op,args,65533)
        proc=start(True)
        try:
            assert not (private/'bootstrap.token').exists()
            assert child(f"open({str(private/'gate.db')!r},'rb')").returncode!=0
            assert child(f"open({str(private/'integrity.key')!r},'rb')").returncode!=0
            assert child(f"import socket;s=socket.socket(socket.AF_UNIX);s.connect({str(public/'control.sock')!r})").returncode!=0
            req=control('add_actor',admin=ADMIN,actor='r',role='requester')['result']
            lead=control('add_actor',admin=ADMIN,actor='l',role='lead')['result']
            reviewer=control('add_actor',admin=ADMIN,actor='h',role='reviewer')['result']
            assert control('add_actor',admin=ADMIN,actor='b',role='lead')['ok']
            a=dict(kind='sim.edit',resource='dummy',value='v',nonce=secrets.token_hex(8))
            assert control('register',admin=ADMIN,a=a,reviewers=['h'],requester='r',lead='l',backup='b')['ok']
            assert control('approve',a=a,actor='h',token=reviewer)['ok']
            assert not as_request('add_actor',dict(admin=ADMIN,actor='x',role='reviewer'))['ok']
            assert not as_request('execute',dict(a=a,actor='r',token=req),65532)['ok']
            assert not as_request('object',dict(a=a,actor='h',token=reviewer))['ok']
            oid=as_request('object',dict(a=a,actor='r',token=req,ttl=1))['result']
            for _ in range(20):
                if oid in control('alerts',actor='l',token=lead)['result']: break
                time.sleep(0.2)
            else: raise AssertionError('automatic escalation not recorded')
            assert not as_request('execute',dict(a=a,actor='r',token=req))['ok']
            assert control('close',oid=oid,actor='l',token=lead,reason='evidence_resolved',evidence='Synthetic evidence reviewed')['ok']
            assert control('approve',a=a,actor='h',token=reviewer)['ok']
            assert as_request('execute',dict(a=a,actor='r',token=req))['ok']
        finally: proc.terminate(); proc.wait(timeout=5)
        proc=start()
        try:
            assert not as_request('execute',dict(a=a,actor='r',token=req))['ok']
            attempts = 120
            traffic = child(f"""
import json
import socket
import time

started = time.monotonic()
for index in range({attempts}):
    time.sleep(max(0, started + index / 40 - time.monotonic()))
    with socket.socket(socket.AF_UNIX) as sock:
        sock.settimeout(3)
        sock.connect({str(public/'request.sock')!r})
        sock.sendall(b'{{"op":"inspect","args":{{}}}}\\n')
        with sock.makefile('rb') as reply:
            assert json.load(reply) == {{'ok': False, 'error': 'denied'}}
print(f'{{time.monotonic() - started:.2f}}')
""")
            assert traffic.returncode == 0, traffic.stderr
            for _ in range(15):
                snapshot = control('inspect', admin=ADMIN)['result']
                groups = {(e['kind'], e['operation'], e['actor']): e['count'] for e in snapshot['events']}
                if groups.get(('privileged_attempt', 'inspect', None)) == attempts:
                    break
                time.sleep(0.2)
            else:
                pytest.fail(f'Expected {attempts} persisted requester attempts, got {groups}')
            print(f'Processed {attempts} requester socket calls in {traffic.stdout.strip()} s')
        finally: proc.terminate(); proc.wait(timeout=5)
