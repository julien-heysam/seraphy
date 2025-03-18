from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from constants import Envs
from utils.try_openai_agent import main

app = FastAPI(title="Seraphy API", description="AI-powered document processing API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import routers
from api.routes import router as api_router

# Include routers
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "Welcome to Seraphy API"}

if __name__ == "__main__":
    main()
