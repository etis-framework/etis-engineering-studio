from __future__ import annotations
import base64, hashlib, hmac, json, secrets, time
from urllib.parse import urlencode
import httpx
from fastapi import HTTPException
from ..config import get_settings


def _sign(payload: str) -> str:
    secret=get_settings().etis_session_secret.encode()
    return hmac.new(secret,payload.encode(),hashlib.sha256).hexdigest()


def create_session_token(user_id: int, github_login: str, role: str, ttl=86400) -> str:
    data={"uid":user_id,"login":github_login,"role":role,"exp":int(time.time())+ttl,"nonce":secrets.token_hex(6)}
    raw=base64.urlsafe_b64encode(json.dumps(data,separators=(",",":")).encode()).decode().rstrip("=")
    return f"{raw}.{_sign(raw)}"


def parse_session_token(token: str) -> dict:
    try:
        raw,sig=token.rsplit(".",1)
        if not hmac.compare_digest(_sign(raw),sig):
            raise ValueError("bad signature")
        padded=raw+"="*((4-len(raw)%4)%4)
        data=json.loads(base64.urlsafe_b64decode(padded).decode())
        if int(data["exp"])<int(time.time()):
            raise ValueError("expired")
        return data
    except Exception as e:
        raise HTTPException(status_code=401,detail="Invalid or expired session") from e


def github_authorize_url(state: str) -> str:
    s=get_settings()
    q=urlencode({"client_id":s.github_oauth_client_id,"redirect_uri":s.github_oauth_redirect_uri,"scope":"read:user user:email","state":state})
    return f"https://github.com/login/oauth/authorize?{q}"


def github_exchange(code: str) -> dict:
    s=get_settings()
    with httpx.Client(timeout=20) as c:
        t=c.post("https://github.com/login/oauth/access_token",headers={"Accept":"application/json"},data={"client_id":s.github_oauth_client_id,"client_secret":s.github_oauth_client_secret,"code":code,"redirect_uri":s.github_oauth_redirect_uri})
        t.raise_for_status(); token=t.json().get("access_token")
        if not token: raise HTTPException(401,"GitHub OAuth exchange failed")
        u=c.get("https://api.github.com/user",headers={"Authorization":f"Bearer {token}","Accept":"application/vnd.github+json"})
        u.raise_for_status(); return u.json()
