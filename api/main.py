from fastapi import FastAPI
from .routes import moderation
from . import models
from .database import engine

# Create DB tables if not exists
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="Moderation API")

# Register Routers
app.include_router(moderation.router)

@app.get("/")
def root():
    return {"message": "Moderation API is running"}
