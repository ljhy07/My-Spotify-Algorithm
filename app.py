from fastapi import FastAPI, Response, Request, HTTPException, Cookie, Body, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import random
import string
import json
import httpx
import base64
from urllib.parse import urlencode

import os
from dotenv import load_dotenv
from models import SearchData
from db import *

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
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def generate_random_string(length: int) -> str:
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

templates = Jinja2Templates(directory="templates")

@app.get("/")
def Main(request: Request):
    init_db()
    return templates.TemplateResponse("index.html", {"request":request})

@app.get("/data")
def Data(request: Request):
    return templates.TemplateResponse("data.html", {"request":request})

@app.post("/search")
async def search(request: Request, search: str = Body(...), session=Depends(get_session)):
    SPOTIFY_API_URL = "https://api.spotify.com/v1/search"

    search = json.loads(search)
    print(search["search"])
    params = {
        "q": search,
        "type": "album,artist,playlist",
        "market": "KO",
        "limit": 10,
        "offset": 5
    }

    search_data = SearchData(searchValue=search["search"])
    session.add(search_data)
    session.commit()
    session.refresh(search_data)
    
    token = request.cookies.get("access_token")
    print(token)
    headers = {
        "Authorization": f"Bearer {token}"
    }

    # Spotify API 요청
    async with httpx.AsyncClient() as client:
        response = await client.get(SPOTIFY_API_URL, params=params, headers=headers)
        
        if response.status_code == 200:
            return recommend(response.json())
        else:
            raise HTTPException(status_code=response.status_code, detail=response.text)


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
    
    if not state:
        error_params = urlencode({"error": "state_mismatch"})
        return RedirectResponse(f"/#?{error_params}")

    client_id = os.getenv("CLIENT_ID")
    client_secret = os.getenv("CLIENT_SECRET")

    if not client_id or not client_secret:
        raise HTTPException(status_code=500, detail="Missing CLIENT_ID or CLIENT_SECRET in environment variables")

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
            print(f"Error fetching token: {result.status_code}, Body: {result.text}")
            raise HTTPException(status_code=result.status_code, detail=result.text)

        token_data = result.json()

        response.set_cookie(
            key="access_token",
            value=token_data["access_token"],
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=token_data.get("expires_in", 3600),
        )

        refresh_token = token_data.get("refresh_token")
        if refresh_token:
            response.set_cookie(
                key="refresh_token",
                value=refresh_token,
                httponly=True,
                secure=True,
                samesite="Strict",
                max_age=604800,  # 7일
            )

@app.post("/refresh")
async def Refresh(response: Response, request: Request, refresh_token: str = Cookie(None)):
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
            print(f"Response: {response.status_code}, Body: {response.body}")
            raise HTTPException(status_code=response.status_code, detail="Failed to fetch token")

        token_data = result.json()

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

def artist(request):
    dataList = []

    for item in request["items"]:
        print(item)
        dataList.append({
            "id": item["id"],
            "name": item["name"],
            "spotifyUrl": item["external_urls"]["spotify"],
            "followers": item["followers"]["total"],
            "genres": item["genres"],
            "popularity": item["popularity"],
            "imgUrl": item["images"][1]["url"]
        })

    return dataList

def playlist(request):
    dataList = []

    for item in request["items"]:
        print(item)
        dataList.append({
            "id": item["id"],
            "name": item["name"],
            "spotifyUrl": item["external_urls"]["spotify"],
            "tracks": item["tracks"]["total"],
            "owner": item["owner"],
            "isPublic": item["public"],
            "imgUrl": item["images"][0]["url"]
        })

    return dataList

def album(request):
    dataList = []

    for item in request["items"]:
        print(item)
        dataList.append({
            "id": item["id"],
            "name": item["name"],
            "spotifyUrl": item["external_urls"]["spotify"],
            "tracks": item["total_tracks"],
            "releaseDate": item["release_date"],
            "artist": item["artists"],
            "isPlayAble": item["is_playable"],
            "imgUrl": item["images"][1]["url"]
        })

    return dataList

def recommend(request):
    artists = None
    playlists = None
    albums = None

    if request["artists"]["total"] > 0:
        # print(request["artists"])
        artists = artist(request["artists"])
    
    if request["playlists"]["total"] > 0:
        # print(request["playlists"])
        playlists = playlist(request["playlists"])
    
    if request["albums"]["total"] > 0:
        # print(request["albums"])
        albums = album(request["albums"])
    
    return {"artists": artists, "albums":albums, "playlists": playlists}