from fastapi import FastAPI
from sqlalchemy import text

from database import engine

app = FastAPI(title="Syphership API")

@app.get('/')
def root():
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        return {
            "message": "Syphership API is running",
            "database": result.scalar(),
        }