"""Shared operator credential for this prototype; no claims of individual identity."""
import hmac
import os
from fastapi import HTTPException, Request


def access_mode():
    if os.environ.get('SIH26170_OPERATOR_KEY') or os.environ.get('SIH26170_PUBLIC_DEMO_KEY'):
        return 'protected'
    return 'local_demo' if os.environ.get('SIH26170_ENABLE_DEMO_WRITES') == '1' else 'read_only'


def has_access(request: Request):
    supplied = request.headers.get('Authorization', '').removeprefix('Bearer ')
    for name in ('SIH26170_OPERATOR_KEY', 'SIH26170_PUBLIC_DEMO_KEY'):
        key = os.environ.get(name, '')
        if key and hmac.compare_digest(key.encode(), supplied.encode()):
            return True
    return access_mode() == 'local_demo'


def read_access(request: Request):
    if access_mode() == 'protected' and not has_access(request):
        raise HTTPException(401, 'Unlock the operator workspace to view operational records')


def write_access(request: Request):
    if not has_access(request):
        raise HTTPException(401 if access_mode() == 'protected' else 403,
                            'Operator access is required; this public demo is read-only')
