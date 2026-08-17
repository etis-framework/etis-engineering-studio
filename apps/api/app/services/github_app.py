from __future__ import annotations
import time
from dataclasses import dataclass
import httpx, jwt
from ..config import get_settings

@dataclass
class CachedInstallationToken:
    token:str
    expires_at:float
    installation_id:str

class GitHubAppTokenManager:
    """Short-lived GitHub App installation tokens for bounded private-repository access."""
    def __init__(self):
        self.s=get_settings(); self._cache:dict[str,CachedInstallationToken]={}

    def configured(self)->bool:
        return bool(self.s.github_app_id and self.s.github_app_private_key)

    def _app_jwt(self)->str:
        if not self.configured(): raise RuntimeError("GitHub App credentials are not configured")
        now=int(time.time()); key=self.s.github_app_private_key.replace('\\n','\n')
        return jwt.encode({"iat":now-30,"exp":now+540,"iss":str(self.s.github_app_id)},key,algorithm="RS256")

    def _app_headers(self):
        return {"Authorization":f"Bearer {self._app_jwt()}","Accept":"application/vnd.github+json","X-GitHub-Api-Version":"2022-11-28"}

    def installation_for_repo(self,repo_full_name:str)->str:
        with httpx.Client(base_url="https://api.github.com",headers=self._app_headers(),timeout=15.0) as c:
            r=c.get(f"/repos/{repo_full_name}/installation")
            if r.status_code==404: raise RuntimeError("ETIS Engineering Studio GitHub App is not installed for this repository")
            r.raise_for_status(); return str(r.json()["id"])

    def token_for_repo(self,repo_full_name:str)->CachedInstallationToken:
        cached=self._cache.get(repo_full_name)
        if cached and cached.expires_at-time.time()>120: return cached
        installation_id=self.installation_for_repo(repo_full_name)
        with httpx.Client(base_url="https://api.github.com",headers=self._app_headers(),timeout=15.0) as c:
            r=c.post(f"/app/installations/{installation_id}/access_tokens")
            r.raise_for_status(); data=r.json(); token=data["token"]
        # GitHub installation tokens normally live for one hour. Keep a conservative local expiry.
        cached=CachedInstallationToken(token=token,expires_at=time.time()+3300,installation_id=installation_id)
        self._cache[repo_full_name]=cached; return cached

manager=GitHubAppTokenManager()
