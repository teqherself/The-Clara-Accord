# SPDX-License-Identifier: MIT
"""Linux-only simulated governance service. No external effects."""
import argparse
import fcntl
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
from gate import Gate, Action, Denied, LEVELS

TABLES = ('actors', 'plans', 'approvals', 'objections', 'effects', 'audit', 'disabled', 'escalations', 'resolutions')
LIMIT = 16384

class OutcomeUncertain(Denied):
    """Commit completed but checkpoint confirmation failed; do not retry."""

class ProtectedGate(Gate):
    """Trusted service only. HMAC state seal and a separately stored checkpoint."""
    def __init__(self, path, key, admin_token=None, clock=time.time):
        self.key = key
        self.anchor = Path(str(path)+'.checkpoint')
        self.bootstrap = not Path(path).exists() and not self.anchor.exists() and admin_token is not None
        if len(key) != 32 or (not Path(path).exists() and not self.bootstrap):
            raise Denied('missing state or key')
        super().__init__(path, admin_token, clock)
        self.bootstrap = False

    def seal(self, c, timestamp):
        state = []
        for table in TABLES:
            cols = len(c.execute(f'PRAGMA table_info({table})').fetchall())
            order = ','.join(str(i+1) for i in range(cols))
            state.append((table, c.execute(f'SELECT * FROM {table} ORDER BY {order}').fetchall()))
        schema = c.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        data = json.dumps([timestamp, schema, state], separators=(',', ':'), allow_nan=False).encode()
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
    def tx(self):
        lock=os.open(str(self.anchor)+'.lock',os.O_CREAT|os.O_RDWR|os.O_NOFOLLOW,0o600)
        c=None
        try:
            fcntl.flock(lock,fcntl.LOCK_EX)
            c = sqlite3.connect(self.path, timeout=5, isolation_level=None)
            c.execute('PRAGMA trusted_schema=OFF')
            c.execute('PRAGMA secure_delete=ON')
            c.execute('PRAGMA synchronous=FULL')
            c.execute('BEGIN IMMEDIATE')
            now = float(self.clock())
            if not math.isfinite(now): raise Denied('invalid clock')
            if self.bootstrap:
                c.execute('CREATE TABLE disabled(actor TEXT PRIMARY KEY)')
                c.execute('CREATE TABLE escalations(oid TEXT PRIMARY KEY, at REAL)')
                c.execute('CREATE TABLE resolutions(oid TEXT PRIMARY KEY, evidence TEXT NOT NULL)')
                c.execute('CREATE TABLE integrity(id INTEGER PRIMARY KEY CHECK(id=1), at REAL, mac TEXT)')
            else:
                row = c.execute('SELECT at,mac FROM integrity WHERE id=1').fetchone()
                if not row or not hmac.compare_digest(row[1], self.seal(c, row[0])):
                    raise Denied('integrity failure')
                if not hmac.compare_digest(row[1],read_secret(self.anchor).decode()): raise Denied('checkpoint mismatch')
                if now < row[0]: raise Denied('clock rollback')
            yield c
            mac=self.seal(c,now)
            c.execute('INSERT OR REPLACE INTO integrity VALUES (1,?,?)', (now,mac))
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
            os.close(lock)

    def auth(self, c, actor, token, role=None):
        if c.execute('SELECT 1 FROM disabled WHERE actor=?',(actor,)).fetchone():
            raise Denied('account disabled')
        return super().auth(c, actor, token, role)

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
            self.log(c,'credential_disabled' if disable else 'credential_rotated','')
        return None if disable else token

    def object(self,a,actor,token,ttl=60,requester_only=False):
        if not 0 < ttl <= 3600: raise Denied('invalid deadline')
        key=a.digest(); oid=secrets.token_hex(16)
        with self.tx() as c:
            self.auth(c,actor,token,'requester' if requester_only else None)
            required=self.plan(c,key)
            requester,lead=c.execute('SELECT requester,lead FROM plans WHERE id=?',(key,)).fetchone()
            if actor not in required | {requester,lead}: raise Denied('unrelated actor')
            c.execute('INSERT INTO objections(id,plan,actor,deadline) VALUES (?,?,?,?)',(oid,key,actor,self.clock()+ttl))
            self.log(c,'objected',key)
        return oid

    def close_with_evidence(self,oid,actor,token,reason,evidence):
        if reason not in ('evidence_resolved','mitigation_verified') or not isinstance(evidence,str) or not 16<=len(evidence)<=1024:
            raise Denied('documented rationale required')
        with self.tx() as c:
            self.auth(c,actor,token,'lead')
            row=c.execute('SELECT plan,actor,closed FROM objections WHERE id=?',(oid,)).fetchone()
            if not row or row[1]==actor or row[2]: raise Denied('invalid closure')
            if c.execute('SELECT lead FROM plans WHERE id=?',(row[0],)).fetchone()!=(actor,): raise Denied('not assigned lead')
            c.execute('INSERT INTO resolutions VALUES (?,?)',(oid,hashlib.sha256(evidence.encode()).hexdigest()))
            c.execute('UPDATE objections SET closed=1 WHERE id=?',(oid,))
            c.execute('DELETE FROM approvals WHERE plan=?',(row[0],))
            self.log(c,'closed_'+reason,row[0])

    def maintenance(self, retention):
        """Record overdue escalations once. Remove aged audit events only; keep replay tombstones."""
        if not 60 <= retention <= 31536000: raise Denied('invalid retention')
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
            return [r[0] for r in c.execute('SELECT e.oid FROM escalations e JOIN objections o ON e.oid=o.id JOIN plans p ON o.plan=p.id WHERE p.lead=? AND o.closed=0',(actor,))]

    def dispatch(self, plane, request):
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
        try:
            _,uid,_=struct.unpack('3i',self.request.getsockopt(socket.SOL_SOCKET,socket.SO_PEERCRED,12))
            if uid!=self.server.peer_uid: raise Denied('peer uid denied')
            raw=self.rfile.readline(LIMIT+1)
            if len(raw)>LIMIT or not raw.endswith(b'\n'): raise Denied('invalid request')
            request=json.loads(raw)
            if not isinstance(request,dict): raise Denied('invalid request')
            result=self.server.gate.dispatch(self.server.plane,request)
            reply={'ok':True,'result':result}
        except OutcomeUncertain:
            reply={'ok':False,'error':'outcome_uncertain','retry':False}
        except (Denied,ValueError,TypeError,KeyError,OSError,AttributeError):
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

def serve(args):
    os.umask(0o077)
    private=Path(args.private); public=Path(args.sockets)
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
    for srv in servers: threading.Thread(target=srv.serve_forever,daemon=True).start()
    while True:
        gate.maintenance(args.retention)
        time.sleep(1)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--private',required=True); p.add_argument('--sockets',required=True); p.add_argument('--requester-uid',required=True,type=int); p.add_argument('--retention',type=int,default=86400); p.add_argument('--bootstrap',action='store_true')
    serve(p.parse_args())

if __name__=='__main__': main()
