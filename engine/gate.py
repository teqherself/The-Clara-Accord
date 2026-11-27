# SPDX-License-Identifier: MIT
"""In-memory simulated policy gate. No external effects or identity authentication."""
from dataclasses import dataclass
from hashlib import sha256
import json
from threading import RLock
from time import monotonic
from types import MappingProxyType

LEVELS = MappingProxyType({'sim.read': 1, 'sim.edit': 2, 'sim.private_disclosure': 3, 'sim.high_risk': 4})
MINIMUM = {1: 0, 2: 1, 3: 2, 4: 4}
@dataclass(frozen=True)
class Action:
    kind: str
    resource: str
    value: str
    nonce: str
    def digest(self):
        return sha256(json.dumps(['1.8', self.kind, self.resource, self.value, self.nonce], separators=(',', ':')).encode()).hexdigest()

class Denied(Exception): pass

class Gate:
    """Trusted harness owns all admin methods; caller identities are synthetic.
    The model would only receive a restricted request interface, not this object.
    """
    def __init__(self, clock=monotonic):
        self.clock = clock
        self.lock = RLock()
        self.available = True
        self.plans = {}
        self.approvals = {}
        self.objections = set()
        self.used = set()
        self.effects = []
    def register(self, action, reviewers, ttl=60):
        with self.lock:
            level = LEVELS.get(action.kind)
            reviewers = frozenset(reviewers)
            if level is None or len(reviewers) < MINIMUM[level] or not 0 < ttl <= 3600:
                raise Denied('invalid plan')
            key = action.digest()
            if key in self.plans: raise Denied('plan already registered')
            self.plans[key] = (reviewers, self.clock()+ttl)
            self.approvals[key] = set()
    def approve(self, action, reviewer):
        with self.lock:
            key = action.digest()
            plan = self.plans.get(key)
            if not plan or reviewer not in plan[0] or self.clock() >= plan[1] or key in self.used:
                raise Denied('invalid approval')
            self.approvals[key].add(reviewer)
    def revoke(self, action, reviewer):
        with self.lock:
            self.approvals.get(action.digest(), set()).discard(reviewer)
    def object(self, action):
        with self.lock: self.objections.add(action.digest())
    def execute(self, action):
        with self.lock:
            key = action.digest()
            if not self.available or action.kind not in LEVELS: raise Denied('default deny')
            plan = self.plans.get(key)
            if not plan or self.clock() >= plan[1] or key in self.used or key in self.objections:
                raise Denied('missing, expired, consumed or disputed plan')
            if self.approvals[key] != plan[0]: raise Denied('missing approvals')
            self.used.add(key)
            self.effects.append(key)  # simulated side effect only
            return key
