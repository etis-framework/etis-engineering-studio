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


class GitHubOwnerResolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class GitHubRepositoryOwner:
    login: str
    account_id: str
    owner_type: str


def repository_owner_identity(repo_full_name: str) -> GitHubRepositoryOwner:
    """Resolve the GitHub account that owns a nominated repository namespace.

    This uses public GitHub account metadata only. It does not use a PAT,
    OAuth access token, or GitHub App installation token, and it does not
    establish repository access or verification.
    """
    try:
        owner_login, _ = repo_full_name.split("/", 1)
    except ValueError as exc:
        raise GitHubOwnerResolutionError(
            "Repository name must be in owner/repository form"
        ) from exc

    owner_login = owner_login.strip()
    if not owner_login:
        raise GitHubOwnerResolutionError("Repository owner is missing")

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        with httpx.Client(
            base_url="https://api.github.com",
            headers=headers,
            timeout=12.0,
            follow_redirects=True,
        ) as client:
            response = client.get(f"/users/{owner_login}")

        if response.status_code == 404:
            raise GitHubOwnerResolutionError(
                "Repository owner account was not found on GitHub"
            )

        response.raise_for_status()
        data = response.json()

    except GitHubOwnerResolutionError:
        raise

    except (httpx.HTTPError, ValueError, TypeError) as exc:
        raise GitHubOwnerResolutionError(
            "GitHub owner identity could not be resolved"
        ) from exc

    owner_type = str(data.get("type") or "")
    if owner_type not in {"User", "Organization"}:
        raise GitHubOwnerResolutionError(
            "Unsupported GitHub repository owner type"
        )

    canonical_login = str(data.get("login") or "").strip()
    account_id = str(data.get("id") or "").strip()

    if not canonical_login or not account_id:
        raise GitHubOwnerResolutionError(
            "GitHub owner identity response was incomplete"
        )

    return GitHubRepositoryOwner(
        login=canonical_login,
        account_id=account_id,
        owner_type=owner_type,
    )


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
        with httpx.Client(
            base_url="https://api.github.com",
            headers=self._app_headers(),
            timeout=15.0,
        ) as c:
            r=c.get(f"/repos/{repo_full_name}/installation")

            if r.status_code==404:
                raise RuntimeError(
                    "ETIS Engineering Studio GitHub App is not installed "
                    "for this repository"
                )

            r.raise_for_status()
            data=r.json()

        if (
            str(data.get("repository_selection") or "").casefold()
            != "selected"
        ):
            raise RuntimeError(
                "ETIS GitHub App access must use Only select repositories; "
                "All repositories is not accepted"
            )

        installation_id=str(data.get("id") or "").strip()

        if not installation_id:
            raise RuntimeError(
                "GitHub App installation response was incomplete"
            )

        return installation_id

    def token_for_repo(self,repo_full_name:str)->CachedInstallationToken:
        cached=self._cache.get(repo_full_name)

        if cached and cached.expires_at-time.time()>120:
            return cached

        try:
            _,repo_name=repo_full_name.split("/",1)
        except ValueError as exc:
            raise RuntimeError(
                "Repository name must be in owner/repository form"
            ) from exc

        repo_name=repo_name.strip()

        if not repo_name:
            raise RuntimeError("Repository name is missing")

        installation_id=self.installation_for_repo(repo_full_name)

        with httpx.Client(
            base_url="https://api.github.com",
            headers=self._app_headers(),
            timeout=15.0,
        ) as c:
            r=c.post(
                f"/app/installations/{installation_id}/access_tokens",
                json={"repositories":[repo_name]},
            )
            r.raise_for_status()
            data=r.json()

        if (
            str(data.get("repository_selection") or "").casefold()
            != "selected"
        ):
            raise RuntimeError(
                "GitHub did not issue a selected-repository "
                "installation token"
            )

        granted=data.get("repositories")

        granted_full_names={
            str(item.get("full_name") or "").casefold()
            for item in granted
            if isinstance(item,dict)
        } if isinstance(granted,list) else set()

        if granted_full_names != {repo_full_name.casefold()}:
            raise RuntimeError(
                "GitHub installation token scope did not match the "
                "exact team repository"
            )

        token=str(data.get("token") or "").strip()

        if not token:
            raise RuntimeError(
                "GitHub installation token response was incomplete"
            )

        # Cache only the exact-repository token. It cannot be reused to read
        # another repository covered by the underlying installation.
        cached=CachedInstallationToken(
            token=token,
            expires_at=time.time()+3300,
            installation_id=installation_id,
        )

        self._cache[repo_full_name]=cached
        return cached

manager=GitHubAppTokenManager()
