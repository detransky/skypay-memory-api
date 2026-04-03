import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from supabase import Client, create_client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
API_KEY = os.environ["API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

app = FastAPI(title="Skypay Memory API", version="1.0.0")
bearer_scheme = HTTPBearer()


def verify_token(credentials: HTTPAuthorizationCredentials = Security(bearer_scheme)):
    if credentials.credentials != API_KEY:
        raise HTTPException(status_code=401, detail="Invalid or missing API key.")
    return credentials.credentials


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/session_log")
def session_log(_: str = Depends(verify_token)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    result = (
        supabase.schema("skypay").table("session_log")
        .select("*").gte("created_at", cutoff)
        .order("created_at", desc=True).execute()
    )
    return {"data": result.data}


@app.get("/open_commitments")
def open_commitments(_: str = Depends(verify_token)):
    result = supabase.schema("skypay").table("open_commitments").select("*").execute()
    return {"data": result.data}


@app.get("/active_avoidance")
def active_avoidance(_: str = Depends(verify_token)):
    result = supabase.schema("skypay").table("active_avoidance").select("*").execute()
    return {"data": result.data}


@app.get("/recent_wins")
def recent_wins(_: str = Depends(verify_token)):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    result = (
        supabase.schema("skypay").table("recent_wins")
        .select("*").gte("created_at", cutoff)
        .order("created_at", desc=True).execute()
    )
    return {"data": result.data}


@app.get("/relationship_alerts")
def relationship_alerts(_: str = Depends(verify_token)):
    result = supabase.schema("skypay").table("relationship_alerts").select("*").execute()
    return {"data": result.data}
