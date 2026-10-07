import os
from urllib.parse import urlencode

import httpx


def get_github_auth_url():
    params = {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "redirect_uri": os.getenv("GITHUB_REDIRECT_URI"),
        "scope": "repo read:user user:email",
    }

    return "https://github.com/login/oauth/authorize?" + urlencode(params)


async def exchange_code_for_token(code: str):
    data = {
        "client_id": os.getenv("GITHUB_CLIENT_ID"),
        "client_secret": os.getenv("GITHUB_CLIENT_SECRET"),
        "code": code,
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://github.com/login/oauth/access_token",
            data=data,
            headers={
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        return response.json()


async def get_github_user(access_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        return response.json()


async def get_github_emails(access_token: str):
    async with httpx.AsyncClient() as client:
        response = await client.get(
            "https://api.github.com/user/emails",
            headers={
                "Authorization": f"Bearer {access_token}",
                "Accept": "application/json",
            },
        )

        response.raise_for_status()

        return response.json()