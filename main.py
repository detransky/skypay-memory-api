import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from typing import Optional

import psycopg2
import psycopg2.extras
from psycopg2.pool import ThreadedConnectionPool
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Query, Security
from fastapi.responses import JSONResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

load_dotenv()

DATABASE_URL = os.environ["DATABASE_URL"]
API_KEY      = os.environ["API_KEY"]

if "sslmode" not in DATABASE_URL:
    DATABASE_URL += "?sslmode=require"

pool = ThreadedConnectionPool(1, 10, dsn=DATABASE_URL)

app = FastAPI(title="Skypay Memory API", version="1.0.0")
bearer_scheme = HTTPBearer(auto_error=False)


@contextmanager
def get_conn():
    conn = pool.getconn()
    try:
        yield conn
    finally:
        pool.putconn(conn)


def query(sql: str, params=None) -> list:
    with get_conn() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


def verify_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(bearer_scheme),
    api_key: Optional[str] = Query(default=None, alias="api_key"),
):
    token = None
    if credentials is not None:
        token = credentials.credentials
    elif api_key is not None:
        token = api_key
    if token is None or token != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid or missing API key.")
    return token


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/session_log")
def session_log(_: str = Depends(verify_token)):
    try:
        cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
        rows = query(
            "SELECT * FROM skypay.session_log WHERE created_at >= %s ORDER BY created_at DESC",
            (cutoff,)
        )
        return {"data": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/open_commitments")
def open_commitments(_: str = Depends(verify_token)):
    try:
        rows = query("SELECT * FROM skypay.open_commitments ORDER BY due_date ASC NULLS LAST")
        return {"data": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/active_avoidance")
def active_avoidance(_: str = Depends(verify_token)):
    try:
        rows = query("SELECT * FROM skypay.active_avoidance ORDER BY times_skipped DESC")
        return {"data": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/recent_wins")
def recent_wins(_: str = Depends(verify_token)):
    try:
        rows = query(
            "SELECT * FROM skypay.wins_log WHERE date >= CURRENT_DATE - INTERVAL '30 days' ORDER BY date DESC"
        )
        return {"data": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/relationship_alerts")
def relationship_alerts(_: str = Depends(verify_token)):
    try:
        rows = query("SELECT * FROM skypay.relationship_alerts ORDER BY next_due ASC")
        return {"data": rows}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
