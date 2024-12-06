from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import RedirectResponse
import random
import string
import httpx
import base64
from urllib.parse import urlencode

import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI()

def generate_random_string(length: int) -> str:
    """Generates a random string of the specified length."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
def main():
    return "hello"

@app.get("/login")
async def Login():
    state = generate_random_string(16)
    scope = "user-read-private user-read-email"

    client_id=os.environ["CLIENT_ID"]
    query_params = {
        "response_type": "code",
        "client_id": client_id,
        "scope": scope,
        "redirect_uri": "http://localhost:8000/login/callback",
        "state": state
    }

    spotify_auth_url = f"https://accounts.spotify.com/authorize?{urlencode(query_params)}"
    return RedirectResponse(url=spotify_auth_url)

@app.get("/login/callback")
async def LoginCallback(request: Request):
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    
    if state is None:
        # state가 없을 경우 에러 리디렉션
        error_params = urlencode({"error": "state_mismatch"})
        return RedirectResponse(f"/#?{error_params}")

    # Spotify 인증 토큰 요청 설정
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    auth_url = "https://accounts.spotify.com/api/token"
    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + (base64.b64encode(f"{client_id}:{client_secret}".encode())).decode()
    }
    auth_data = {
        "code": code,
        "redirect_uri": "http://localhost:8000/login/callback",
        "grant_type": "authorization_code"
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(auth_url, headers=auth_headers, data=auth_data)
        if response.status_code != 200:
            print(f"Response: {response.status_code}, Body: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch token")

        token_data = response.json()
        return token_data