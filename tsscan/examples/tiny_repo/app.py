from fastapi import FastAPI
app = FastAPI()

@app.get("/health")
def health():
    return {"ok": True}

# pretend db import
import sqlite3
def save(x): pass
