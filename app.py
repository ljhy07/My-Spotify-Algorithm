from fastapi import FastAPI, Response, Request, HTTPException, Cookie
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
import random
import string
import json
import jwt
import httpx
import base64
from urllib.parse import urlencode

import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
env = load_dotenv(os.path.join(BASE_DIR, ".env"))

app = FastAPI()

origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET"],
    allow_headers=["*"],
)

def generate_random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@app.get("/")
def main():
    

    return 

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
async def LoginCallback(response: Response, request: Request):
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
        result = await client.post(auth_url, headers=auth_headers, data=auth_data)
        if result.status_code != 200:
            print(f"Response: {response.status_code}, Body: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch token")

        token_data = json.loads(result.json())

        response.set_cookie(
            key="access_token",
            value=token_data["access_token"],
            httponly=True,    # JavaScript에서 접근 불가
            secure=True,      # HTTPS에서만 사용
            samesite="Strict", # CSRF 방지
            max_age=token_data["expires_in"],     # 1시간
        )

        response.set_cookie(
            key="refresh_token",
            value=token_data["refresh_token"],
            httponly=True,    # JavaScript에서 접근 불가
            secure=True,      # HTTPS에서만 사용
            samesite="Strict", # CSRF 방지
            max_age=604800, # 7일
        )

@app.post("/refresh")
async def Refresh(response: Response, refresh_token: str = Cookie(None)):
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    auth_url = "https://accounts.spotify.com/api/token"
    auth_headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic " + (base64.b64encode(f"{client_id}:{client_secret}".encode())).decode()
    }
    auth_data = {
        "grant_type": "refresh_token",
        "refresh_token": refresh_token
    }

    async with httpx.AsyncClient() as client:
        result = await client.post(auth_url, headers=auth_headers, data=auth_data)
        if result.status_code != 200:
            print(f"Response: {response.status_code}, Body: {response.text}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch token")

        token_data = json.loads(result.json())

        response.set_cookie(
            key="access_token",
            value=token_data["access_token"],
            httponly=True,    # JavaScript에서 접근 불가
            secure=True,      # HTTPS에서만 사용
            samesite="Strict", # CSRF 방지
            max_age=token_data["expires_in"],     # 1시간
        )

        response.set_cookie(
            key="refresh_token",
            value=token_data["refresh_token"],
            httponly=True,    # JavaScript에서 접근 불가
            secure=True,      # HTTPS에서만 사용
            samesite="Strict", # CSRF 방지
            max_age=604800, # 7일
        )