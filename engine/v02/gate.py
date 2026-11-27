# SPDX-License-Identifier: MIT
"""Sandbox only: SQLite authorisation and synthetic effects; no external executor."""
import hashlib, hmac, json, secrets, sqlite3, time
from contextlib import contextmanager
from dataclasses import dataclass
from types import MappingProxyType

LEVELS = MappingProxyType({'sim.read': 0, 'sim.edit': 1, 'sim.private_disclosure': 2, 'sim.high_risk': 4})
class Denied(Exception): pass
@dataclass(frozen=True)
class Action:
    kind: str
    resource: str
    value: str
    nonce: str
    def digest(self):
        return hashlib.sha256(json.dumps(['1.8/0.2', self.kind, self.resource, self.value, self.nonce], separators=(',', ':')).encode()).hexdigest()

class Gate:
    def __init__(self, path, admin_token=None, clock=time.time):
        self.path, self.clock = path, clock
        with self.tx() as c:
            for sql in (
                'CREATE TABLE IF NOT EXISTS actors(id TEXT PRIMARY KEY, secret TEXT NOT NULL, role TEXT NOT NULL)',
                'CREATE TABLE IF NOT EXISTS plans(id TEXT PRIMARY KEY, reviewers TEXT, requester TEXT, lead TEXT, expiry REAL, used INTEGER DEFAULT 0)',
                'CREATE TABLE IF NOT EXISTS approvals(plan TEXT, actor TEXT, PRIMARY KEY(plan,actor))',
                'CREATE TABLE IF NOT EXISTS objections(id TEXT PRIMARY KEY, plan TEXT, actor TEXT, deadline REAL, closed INTEGER DEFAULT 0)',
                'CREATE TABLE IF NOT EXISTS effects(plan TEXT PRIMARY KEY)',
                'CREATE TABLE IF NOT EXISTS audit(seq INTEGER PRIMARY KEY, event TEXT, plan TEXT, at REAL)'):
                c.execute(sql)
            if not c.execute('SELECT 1 FROM actors').fetchone():
                if not admin_token or len(admin_token)<32: raise Denied('bootstrap token required')
                c.execute('INSERT INTO actors VALUES (?,?,?)', ('admin',self.hash(admin_token),'admin'))
    @staticmethod
    def hash(token): return hashlib.sha256(token.encode()).hexdigest()
    @contextmanager
    def tx(self):
        c=sqlite3.connect(self.path, timeout=10, isolation_level=None)
        try:
            c.execute('BEGIN IMMEDIATE'); yield c; c.commit()
        except sqlite3.Error as e:
            c.rollback(); raise Denied('storage unavailable') from e
        except BaseException:
            c.rollback(); raise
        finally: c.close()
    def auth(self,c,actor,token,role=None):
        row=c.execute('SELECT secret,role FROM actors WHERE id=?',(actor,)).fetchone()
        if not row or not hmac.compare_digest(row[0],self.hash(token)) or (role and row[1]!=role): raise Denied('authentication failed')
        return row[1]
    def log(self,c,event,key): c.execute('INSERT INTO audit(event,plan,at) VALUES (?,?,?)',(event,key,self.clock()))
    def add_actor(self,admin,actor,role):
        if role not in ('reviewer','lead','requester') or not actor: raise Denied('invalid role')
        token=secrets.token_hex(32)
        with self.tx() as c:
            self.auth(c,'admin',admin,'admin'); c.execute('INSERT INTO actors VALUES (?,?,?)',(actor,self.hash(token),role))
        return token
    def register(self,admin,a,reviewers,requester,lead,ttl=60):
        people=sorted(set(reviewers)); key=a.digest()
        if a.kind not in LEVELS or len(people)<LEVELS[a.kind] or not 0<ttl<=3600: raise Denied('invalid plan')
        with self.tx() as c:
            self.auth(c,'admin',admin,'admin')
            for p in people:
                if c.execute('SELECT role FROM actors WHERE id=?',(p,)).fetchone()!=('reviewer',): raise Denied('invalid reviewer')
            for actor,role in ((requester,'requester'),(lead,'lead')):
                if c.execute('SELECT role FROM actors WHERE id=?',(actor,)).fetchone()!=(role,): raise Denied('invalid assigned role')
            c.execute('INSERT INTO plans(id,reviewers,requester,lead,expiry) VALUES (?,?,?,?,?)',(key,json.dumps(people),requester,lead,self.clock()+ttl)); self.log(c,'registered',key)
    def plan(self,c,key):
        row=c.execute('SELECT reviewers,expiry,used FROM plans WHERE id=?',(key,)).fetchone()
        if not row or row[1]<=self.clock() or row[2]: raise Denied('missing, expired or consumed plan')
        return set(json.loads(row[0]))
    def approve(self,a,actor,token):
        key=a.digest()
        with self.tx() as c:
            self.auth(c,actor,token,'reviewer')
            if actor not in self.plan(c,key): raise Denied('not required')
            c.execute('INSERT OR IGNORE INTO approvals VALUES (?,?)',(key,actor)); self.log(c,'approved',key)
    def revoke(self,a,actor,token):
        key=a.digest()
        with self.tx() as c:
            self.auth(c,actor,token,'reviewer'); c.execute('DELETE FROM approvals WHERE plan=? AND actor=?',(key,actor)); self.log(c,'revoked',key)
    def object(self,a,actor,token,ttl=60):
        key=a.digest(); oid=secrets.token_hex(16)
        if not 0<ttl<=3600: raise Denied('invalid deadline')
        with self.tx() as c:
            self.auth(c,actor,token); self.plan(c,key)
            c.execute('INSERT INTO objections(id,plan,actor,deadline) VALUES (?,?,?,?)',(oid,key,actor,self.clock()+ttl)); self.log(c,'objected',key)
        return oid
    def close(self,oid,actor,token,reason):
        if reason not in ('evidence_resolved','mitigation_verified'): raise Denied('resolution required')
        with self.tx() as c:
            self.auth(c,actor,token,'lead'); row=c.execute('SELECT plan,actor,closed FROM objections WHERE id=?',(oid,)).fetchone()
            if not row or row[1]==actor or row[2]: raise Denied('invalid closure')
            if c.execute('SELECT lead FROM plans WHERE id=?',(row[0],)).fetchone()!=(actor,): raise Denied('not assigned lead')
            c.execute('UPDATE objections SET closed=1 WHERE id=?',(oid,)); c.execute('DELETE FROM approvals WHERE plan=?',(row[0],)); self.log(c,'closed_'+reason,row[0])
    def overdue(self,actor,token):
        with self.tx() as c:
            self.auth(c,actor,token,'lead'); return [r[0] for r in c.execute('SELECT id FROM objections WHERE closed=0 AND deadline<=?',(self.clock(),))]
    def execute(self,a,actor,token):
        key=a.digest()
        with self.tx() as c:
            self.auth(c,actor,token,'requester')
            if a.kind not in LEVELS: raise Denied('default deny')
            required=self.plan(c,key)
            if c.execute('SELECT requester FROM plans WHERE id=?',(key,)).fetchone()!=(actor,): raise Denied('not assigned requester')
            if c.execute('SELECT 1 FROM objections WHERE plan=? AND closed=0',(key,)).fetchone(): raise Denied('unresolved objection')
            if {r[0] for r in c.execute('SELECT actor FROM approvals WHERE plan=?',(key,))}!=required: raise Denied('missing approvals')
            c.execute('INSERT INTO effects VALUES (?)',(key,)); c.execute('UPDATE plans SET used=1 WHERE id=?',(key,)); self.log(c,'executed',key)
        return key
