# SPDX-License-Identifier: MIT
"""Linux-only simulated governance service. No external effects."""
import argparse
import fcntl
import getpass
import hashlib
import hmac
import json
import math
import os
from pathlib import Path
import secrets
import socket
import socketserver
import sqlite3
import stat
import struct
import sys
import threading
import time
from contextlib import contextmanager

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'v02'))
from gate import Gate, Action as BaseAction, Denied, LEVELS

class Action(BaseAction):
    def digest(self):
        body=json.dumps(['1.8.1/0.3.1', self.kind, self.resource, self.value, self.nonce], separators=(',',':')).encode()
        return hashlib.sha256(body).hexdigest()

TABLES = ('actors', 'plans', 'approvals', 'objections', 'effects', 'audit', 'disabled', 'escalations', 'resolutions', 'backups', 'reviewer_roles', 'junk_counts')
LIMIT = 16384
CORE_ROLES = ('operational_authority', 'technical_safety', 'ethics_rights', 'independent_oversight')
OPERATIONS = ('execute','object','add_actor','register','approve','revoke','close','credential','alerts')

class OutcomeUncertain(Denied):
    """Commit completed but checkpoint confirmation failed; do not retry."""

class ProtectedGate(Gate):
    """Trusted service only. HMAC state seal and a separately stored checkpoint."""
    denial_limit = 1000
    JUNK_KINDS = ('wrong_peer', 'malformed_request', 'malformed_control')

    def __init__(self, path, key, admin_token=None, clock=time.time, verify=True):
        self.key = key
        self.anchor = Path(str(path)+'.checkpoint')
        self.bootstrap = not Path(path).exists() and not self.anchor.exists() and admin_token is not None
        if len(key) != 32 or (not Path(path).exists() and not self.bootstrap):
            raise Denied('missing state or key')
        self.local = threading.local()
        self.operation_lock = threading.RLock()
        self.junk_lock = threading.Lock()
        self.junk_pending = {kind: 0 for kind in self.JUNK_KINDS}
        self.junk_last_flush = None
        self.maintenance_ok = True
        self.raw_clock = clock
        def transaction_clock():
            now = getattr(self.local, 'now', None)
            return self.raw_clock() if now is None else now
        if self.bootstrap:
            super().__init__(path, admin_token, transaction_clock)
            self.bootstrap = False
        else:
            self.path, self.clock = path, transaction_clock
            if verify:
                with self.tx(): pass

    def seal(self, c, timestamp, previous):
        state = []
        for table in TABLES:
            cols = len(c.execute(f'PRAGMA table_info({table})').fetchall())
            order = ','.join(str(i+1) for i in range(cols))
            state.append((table, c.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall()))
        schema = c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        data = json.dumps([timestamp, previous, schema, state], separators=(',', ':'), allow_nan=False).encode()
        return hmac.new(self.key, data, hashlib.sha256).hexdigest()

    def checkpoint(self, mac):
        temp = self.anchor.with_name(self.anchor.name+'.'+secrets.token_hex(8))
        try:
            fd=os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY|os.O_NOFOLLOW,0o600)
            with os.fdopen(fd,'w') as f:
                f.write(mac); f.flush(); os.fsync(f.fileno())
            os.replace(temp,self.anchor)
            fd=os.open(self.anchor.parent,os.O_RDONLY|os.O_DIRECTORY)
            try: os.fsync(fd)
            finally: os.close(fd)
        finally:
            if temp.exists(): temp.unlink()

    @contextmanager
    def tx(self, recovery=None):
        self.local.actor = None
        self.local.now = None
        lock=None
        c=None
        try:
            lock=os.open(str(self.anchor)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
            fcntl.flock(lock,fcntl.LOCK_EX)
            c = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            c.execute('PRAGMA trusted_schema=OFF')
            c.execute('PRAGMA secure_delete=ON')
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            now = float(self.raw_clock())
            self.local.now = now
            if not math.isfinite(now): raise Denied('invalid clock')
            if self.bootstrap:
                c.execute('CREATE TABLE disabled(actor TEXT PRIMARY KEY)')
                c.execute('CREATE TABLE escalations(oid TEXT PRIMARY KEY, at REAL)')
                c.execute('CREATE TABLE resolutions(oid TEXT PRIMARY KEY, evidence TEXT NOT NULL)')
                c.execute('CREATE TABLE backups(plan TEXT PRIMARY KEY, actor TEXT NOT NULL)')
                c.execute('CREATE TABLE reviewer_roles(actor TEXT PRIMARY KEY, role TEXT NOT NULL)')
                c.execute('CREATE TABLE junk_counts(kind TEXT PRIMARY KEY, count INTEGER NOT NULL)')
                c.execute('CREATE TABLE integrity(id INTEGER PRIMARY KEY CHECK(id=1), at REAL, mac TEXT, previous TEXT)')
                previous = ''
            else:
                row = c.execute('SELECT at,mac,previous FROM integrity WHERE id=1').fetchone()
                if not row or not hmac.compare_digest(row[1], self.seal(c, row[0], row[2])):
                    raise Denied('integrity failure')
                anchor = read_secret(self.anchor).decode()
                if recovery in ('checkpoint','combined'):
                    if hmac.compare_digest(row[1], anchor) or not hmac.compare_digest(row[2], anchor):
                        raise Denied('not reconcilable')
                elif not hmac.compare_digest(row[1], anchor):
                    raise Denied('checkpoint mismatch')
                if recovery in ('clock','combined'):
                    if now >= row[0]: raise Denied('clock recovery not needed')
                elif now < row[0]: raise Denied('clock rollback')
                previous = anchor
            yield c
            if self.bootstrap:
                for column in ('actor', 'outcome', 'subject', 'plane'):
                    c.execute(f'ALTER TABLE audit ADD COLUMN {column} TEXT')
            mac=self.seal(c,now,previous)
            c.execute('INSERT OR REPLACE INTO integrity VALUES (1,?,?,?)', (now,mac,previous))
            c.commit()
            # A crash after commit but before checkpoint replacement fails closed on restart.
            try: self.checkpoint(mac)
            except OSError as exc: raise OutcomeUncertain('commit completed; checkpoint unconfirmed') from exc
        except (sqlite3.Error,OSError,UnicodeError) as exc:
            if c: c.rollback()
            raise Denied('storage or integrity failure') from exc
        except BaseException:
            if c: c.rollback()
            raise
        finally:
            if c: c.close()
            if lock is not None: os.close(lock)
            self.local.now = None

    def auth(self, c, actor, token, role=None):
        if c.execute('SELECT 1 FROM disabled WHERE actor=?',(actor,)).fetchone():
            raise Denied('account disabled')
        result = super().auth(c, actor, token, role)
        self.local.actor = actor
        return result

    def log(self, c, event, key, outcome='ok', actor=None, subject=None, plane=None):
        c.execute('INSERT INTO audit(event,plan,at,actor,outcome,subject,plane) VALUES (?,?,?,?,?,?,?)',
                  (event,key,self.clock(),actor or self.local.actor or 'system',outcome,subject,plane))

    def add_actor(self, admin, actor, role, reviewer_role=None):
        if role not in ('reviewer','lead','requester') or not isinstance(actor,str) or not 0<len(actor)<=80:
            raise Denied('invalid actor')
        if reviewer_role is not None and (role!='reviewer' or reviewer_role not in CORE_ROLES+('additional',)):
            raise Denied('invalid reviewer role')
        token=secrets.token_hex(32)
        with self.tx() as c:
            self.auth(c,'admin',admin,'admin')
            c.execute('INSERT INTO actors VALUES (?,?,?)',(actor,self.hash(token),role))
            if role=='reviewer':
                c.execute('INSERT INTO reviewer_roles VALUES (?,?)',(actor,reviewer_role or 'additional'))
            self.log(c,'actor_registered','',subject=actor)
        return token

    def register(self, admin, a, reviewers, requester, lead, ttl=60, backup=None):
        people=sorted(set(reviewers)); key=a.digest()
        if a.kind not in LEVELS or len(people)<LEVELS[a.kind] or not 0<ttl<=3600: raise Denied('invalid plan')
        if not backup or backup==lead: raise Denied('distinct backup lead required')
        with self.tx() as c:
            self.auth(c,'admin',admin,'admin')
            assigned=[(p,'reviewer') for p in people]+[(requester,'requester'),(lead,'lead'),(backup,'lead')]
            for actor,role in assigned:
                if c.execute('SELECT role FROM actors WHERE id=?',(actor,)).fetchone()!=(role,) or c.execute('SELECT 1 FROM disabled WHERE actor=?',(actor,)).fetchone():
                    raise Denied('invalid assigned role')
            roles={c.execute('SELECT role FROM reviewer_roles WHERE actor=?',(p,)).fetchone()[0] for p in people}
            if a.kind=='sim.high_risk' and not set(CORE_ROLES)<=roles:
                raise Denied('missing required core reviewer roles')
            c.execute('INSERT INTO plans(id,reviewers,requester,lead,expiry) VALUES (?,?,?,?,?)',(key,json.dumps(people),requester,lead,self.clock()+ttl))
            c.execute('INSERT INTO backups VALUES (?,?)',(key,backup))
            self.log(c,'registered',key)

    def recover_clock(self, admin):
        """Offline only. Invalidate pending plans rather than extend their expiry."""
        with self.tx(recovery='clock') as c:
            self.auth(c,'admin',admin,'admin')
            c.execute('DELETE FROM approvals')
            c.execute('UPDATE plans SET used=1 WHERE used=0')
            self.log(c,'clock_recovered','')

    def reconcile_checkpoint(self, admin):
        """Accept only one authentic commit ahead; invalidate pending plans, never replay."""
        with self.tx(recovery='checkpoint') as c:
            self.auth(c,'admin',admin,'admin')
            c.execute('DELETE FROM approvals')
            c.execute('UPDATE plans SET used=1 WHERE used=0')
            self.log(c,'checkpoint_reconciled','')
            return c.execute('SELECT count(*) FROM effects').fetchone()[0]

    def recover_combined(self, admin):
        """Offline only: authenticated one-commit successor and corrected backwards clock."""
        with self.tx(recovery='combined') as c:
            self.auth(c,'admin',admin,'admin')
            c.execute('DELETE FROM approvals')
            c.execute('UPDATE plans SET used=1 WHERE used=0')
            self.log(c,'combined_recovered','')
            return c.execute('SELECT count(*) FROM effects').fetchone()[0]

    def execute(self,a,actor,token):
        with self.operation_lock:
            if not self.maintenance_ok: raise Denied('maintenance unavailable')
            return super().execute(a,actor,token)

    def credential(self, admin, actor, disable=False):
        if actor == 'admin': raise Denied('offline admin recovery required')
        token = secrets.token_hex(32)
        with self.tx() as c:
            self.auth(c,'admin',admin,'admin')
            if not c.execute('SELECT 1 FROM actors WHERE id=?',(actor,)).fetchone(): raise Denied('unknown actor')
            c.execute('UPDATE actors SET secret=? WHERE id=?',(self.hash(token),actor))
            c.execute('DELETE FROM approvals WHERE actor=?',(actor,))
            if disable: c.execute('INSERT OR IGNORE INTO disabled VALUES (?)',(actor,))
            else: c.execute('DELETE FROM disabled WHERE actor=?',(actor,))
            self.log(c,'credential_disabled' if disable else 'credential_rotated','',subject=actor)
        return None if disable else token

    def object(self,a,actor,token,ttl=60,requester_only=False):
        if not 0 < ttl <= 3600: raise Denied('invalid deadline')
        key=a.digest(); oid=secrets.token_hex(16)
        with self.tx() as c:
            self.auth(c,actor,token,'requester' if requester_only else None)
            required=self.plan(c,key)
            requester,lead=c.execute('SELECT requester,lead FROM plans WHERE id=?',(key,)).fetchone()
            if actor not in required | {requester,lead,self.backup_for(c,key)}: raise Denied('unrelated actor')
            c.execute('INSERT INTO objections(id,plan,actor,deadline) VALUES (?,?,?,?)',(oid,key,actor,self.clock()+ttl))
            self.log(c,'objected',key)
        return oid

    def backup_for(self,c,key):
        row=c.execute('SELECT actor FROM backups WHERE plan=?',(key,)).fetchone()
        return row[0] if row else None

    def close(self,*args,**kwargs):
        raise Denied('documented rationale required; use close_with_evidence')

    def close_with_evidence(self,oid,actor,token,reason,evidence):
        if reason not in ('evidence_resolved','mitigation_verified') or not isinstance(evidence,str) or not 16<=len(evidence)<=1024:
            raise Denied('documented rationale required')
        with self.tx() as c:
            self.auth(c,actor,token,'lead')
            row=c.execute('SELECT plan,actor,closed,deadline FROM objections WHERE id=?',(oid,)).fetchone()
            if not row or row[1]==actor or row[2]: raise Denied('invalid closure')
            lead=c.execute('SELECT lead FROM plans WHERE id=?',(row[0],)).fetchone()[0]
            if actor!=lead:
                if actor!=self.backup_for(c,row[0]): raise Denied('not assigned lead')
                disabled=c.execute('SELECT 1 FROM disabled WHERE actor=?',(lead,)).fetchone()
                if not (row[1]==lead or disabled or row[3]<=self.clock()): raise Denied('assigned lead still responsible')
            c.execute('INSERT INTO resolutions VALUES (?,?)',(oid,hashlib.sha256(evidence.encode()).hexdigest()))
            c.execute('UPDATE objections SET closed=1 WHERE id=?',(oid,))
            c.execute('DELETE FROM approvals WHERE plan=?',(row[0],))
            self.log(c,'closed_'+reason,row[0])

    def count_junk(self, kind):
        """Constant-space aggregate; no disk write or individual audit entry per junk request."""
        if kind not in self.JUNK_KINDS: raise ValueError('unknown counter')
        with self.junk_lock:
            self.junk_pending[kind] = min(2**63-1, self.junk_pending[kind]+1)

    def flush_junk(self):
        """At most one counter transaction per monotonic second; never evicts audit evidence."""
        with self.junk_lock:
            now=time.monotonic()
            if self.junk_last_flush is not None and now-self.junk_last_flush<1: return
            pending=self.junk_pending.copy()
            if not any(pending.values()): return
            self.junk_pending={kind:0 for kind in self.JUNK_KINDS}
            self.junk_last_flush=now
        try:
            with self.tx() as c:
                for kind,count in pending.items():
                    if count:
                        c.execute('INSERT INTO junk_counts VALUES (?,?) ON CONFLICT(kind) DO UPDATE SET count=min(9223372036854775807,count+excluded.count)',(kind,count))
        except OutcomeUncertain:
            # Do not re-add possibly committed counts.
            raise
        except BaseException:
            with self.junk_lock:
                for kind,count in pending.items():
                    self.junk_pending[kind]=min(2**63-1,self.junk_pending[kind]+count)
            raise

    def maintenance(self, retention):
        """Record overdue escalations once. Remove aged audit events only; keep replay tombstones."""
        if not 60 <= retention <= 31536000: raise Denied('invalid retention')
        self.flush_junk()
        with self.tx() as c:
            now=self.clock()
            for oid,key in c.execute('SELECT id,plan FROM objections WHERE closed=0 AND deadline<=?',(now,)).fetchall():
                if c.execute('INSERT OR IGNORE INTO escalations VALUES (?,?)',(oid,now)).rowcount:
                    self.log(c,'escalation_required',key)
            removed=c.execute('DELETE FROM audit WHERE at<?',(now-retention,)).rowcount
            if removed: self.log(c,'audit_retention_purge','')
            return removed

    def alerts(self, actor, token):
        with self.tx() as c:
            self.auth(c,actor,token,'lead')
            return [r[0] for r in c.execute('SELECT e.oid FROM escalations e JOIN objections o ON e.oid=o.id JOIN plans p ON o.plan=p.id JOIN backups b ON b.plan=p.id WHERE (p.lead=? OR b.actor=?) AND o.closed=0',(actor,actor))]

    def record_denial(self, request, authenticated=None, plane="request"):
        op=request.get('op'); args=request.get('args')
        if not isinstance(args,dict): args={}
        if not isinstance(op,str) or op not in OPERATIONS or not isinstance(request.get('args'),dict):
            self.count_junk('malformed_control' if plane=='control' else 'malformed_request'); return
        if plane=='request' and op not in ('execute','object'):
            self.count_junk('malformed_request'); return
        claimed='admin' if 'admin' in args else args.get('actor')
        key=''
        obj=args.get('a')
        if isinstance(obj,dict) and set(obj)=={'kind','resource','value','nonce'} and all(isinstance(v,str) and 0<len(v)<=1024 for v in obj.values()):
            key=Action(**obj).digest()
        try:
            with self.tx() as c:
                known=isinstance(claimed,str) and c.execute('SELECT 1 FROM actors WHERE id=?',(claimed,)).fetchone()
                self.log(c,op,key,'denied',authenticated or 'unauthenticated',claimed if known and claimed!=authenticated else None,plane=plane)
                # Unauthenticated requester refusals have their own bounded partition.
                # Authenticated and control-plane evidence follows time retention only.
                c.execute("DELETE FROM audit WHERE outcome='denied' AND plane='request' AND actor='unauthenticated' AND seq NOT IN (SELECT seq FROM audit WHERE outcome='denied' AND plane='request' AND actor='unauthenticated' ORDER BY seq DESC LIMIT ?)",(self.denial_limit,))
        except Denied: pass

    def dispatch(self, plane, request):
        self.local.actor=None
        try: return self.route(plane,request)
        except OutcomeUncertain: raise
        except (Denied,ValueError,TypeError,KeyError,AttributeError):
            self.record_denial(request,getattr(self.local,'actor',None),plane)
            raise

    def route(self, plane, request):
        op=request.get('op'); args=request.get('args',{})
        if not isinstance(args,dict): raise Denied('invalid arguments')
        allowed={'request':{'execute':self.execute,'object':self.object},'control':{'add_actor':self.add_actor,'register':self.register,'approve':self.approve,'revoke':self.revoke,'object':self.object,'close':self.close_with_evidence,'credential':self.credential,'alerts':self.alerts}}
        method=allowed[plane].get(op)
        if not method or 'requester_only' in args: raise Denied('operation forbidden')
        if op=='object' and plane=='request': args=dict(args,requester_only=True)
        if 'a' in args:
            obj=args['a']
            if not isinstance(obj,dict) or set(obj)!={'kind','resource','value','nonce'} or not all(isinstance(v,str) and 0<len(v)<=1024 for v in obj.values()): raise Denied('invalid action')
            args=dict(args,a=Action(**obj))
        return method(**args)

class Handler(socketserver.StreamRequestHandler):
    def handle(self):
        self.request.settimeout(3)
        routed=False
        junk_kind='malformed_control' if self.server.plane=='control' else 'malformed_request'
        try:
            _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=self.server.peer_uid:
                junk_kind='wrong_peer'; raise Denied('peer uid denied')
            raw=self.rfile.readline(LIMIT+1)
            if len(raw)>LIMIT or not raw.endswith(b'\n'): raise Denied('invalid request')
            request=json.loads(raw)
            if not isinstance(request,dict): raise Denied('invalid request')
            routed=True
            result=self.server.gate.dispatch(self.server.plane,request)
            reply={'ok':True,'result':result}
        except OutcomeUncertain:
            reply={'ok':False,'error':'outcome_uncertain','retry':False}
        except (Denied,ValueError,TypeError,KeyError,OSError,AttributeError):
            if not routed:
                self.server.gate.count_junk(junk_kind)
            reply={'ok':False,'error':'denied'}
        try: self.wfile.write(json.dumps(reply).encode()+b'\n')
        except OSError: pass

class Server(socketserver.UnixStreamServer):
    def __init__(self,path,gate,plane,peer_uid):
        self.gate,self.plane,self.peer_uid=gate,plane,peer_uid
        super().__init__(str(path),Handler)
        os.chmod(path,0o666 if plane=='request' else 0o600)

def protected_directory(path, mode):
    path.mkdir(mode=mode,parents=True,exist_ok=True)
    s=path.lstat()
    if not stat.S_ISDIR(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=mode:
        raise Denied('unsafe directory')

def read_secret(path):
    fd=os.open(path,os.O_RDONLY|os.O_NOFOLLOW)
    with os.fdopen(fd,'rb') as f:
        s=os.fstat(f.fileno())
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600: raise Denied('unsafe secret file')
        return f.read(256)

def maintenance_step(gate, retention):
    with gate.operation_lock:
        try:
            gate.maintenance(retention)
        except Exception as exc:
            gate.maintenance_ok=False
            print(f'maintenance refused: {type(exc).__name__}',file=sys.stderr,flush=True)
            return False
        gate.maintenance_ok=True
        return True

def serve(args):
    os.umask(0o077)
    private=Path(args.private); public=Path(args.sockets)
    if not 60<=args.retention<=31536000: raise Denied('invalid retention')
    protected_directory(private,0o700); protected_directory(public,0o755)
    lock=os.open(private/'service.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    if args.requester_uid==os.getuid(): raise Denied('requester must use a separate uid')
    db=private/'gate.db'
    if db.exists() or db.is_symlink():
        if args.bootstrap: raise Denied('refusing bootstrap over existing database')
        s=db.lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_uid!=os.getuid() or stat.S_IMODE(s.st_mode)!=0o600: raise Denied('unsafe database')
    key=read_secret(private/'integrity.key')
    if args.recover:
        if args.bootstrap: raise Denied('recovery and bootstrap are mutually exclusive')
        gate=ProtectedGate(str(db),key,verify=False)
        token=getpass.getpass('Administrator token: ')
        if args.recover=='clock':
            gate.recover_clock(token); print('Clock recovered; pending plans voided')
        elif args.recover=='checkpoint':
            print('Checkpoint reconciled; recorded effects:',gate.reconcile_checkpoint(token))
        else:
            print('Clock and checkpoint recovered; recorded effects:',gate.recover_combined(token))
        return
    bootstrap=read_secret(private/'bootstrap.token').decode().strip() if args.bootstrap else None
    gate=ProtectedGate(str(private/'gate.db'),key,bootstrap)
    if args.bootstrap: (private/'bootstrap.token').unlink()
    for name in ('request.sock','control.sock'):
        path=public/name
        if path.exists() or path.is_symlink():
            s=path.lstat()
            if not stat.S_ISSOCK(s.st_mode) or s.st_uid!=os.getuid(): raise Denied('unsafe socket path')
            path.unlink()
    servers=[Server(public/'request.sock',gate,'request',args.requester_uid),Server(public/'control.sock',gate,'control',os.getuid())]
    gate.maintenance_ok=False
    for srv in servers: threading.Thread(target=srv.serve_forever,daemon=True).start()
    while True:
        maintenance_step(gate,args.retention)
        time.sleep(1)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--private',required=True); p.add_argument('--sockets',required=True); p.add_argument('--requester-uid',required=True,type=int); p.add_argument('--retention',type=int,default=86400); p.add_argument('--bootstrap',action='store_true'); p.add_argument('--recover',choices=('clock','checkpoint','combined'))
    serve(p.parse_args())

if __name__=='__main__': main()
