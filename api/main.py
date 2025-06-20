from fastapi import FastAPI, HTTPException
from fastapi.openapi.utils import get_openapi
import subprocess
import shlex

app = FastAPI(
    title="Bullroh Chat API",
    description="REST API for automotive Q&A chatbot",
    version="1.0.0",
    openapi_url="/openapi.json",
    docs_url="/docs",
    redoc_url="/redoc"
)

@app.get("/ask", summary="Ask a question", response_description="AI-generated response")
async def ask_endpoint(query: str):
    """
    Get an AI-generated answer to a question about automotive topics.
    
    - **query**: Natural language question about automotive topics
    - **returns**: JSON with AI-generated response
    """
    try:
        command = f"python ../main.py ask {shlex.quote(query)}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

@app.post("/crawl", summary="Trigger blog crawling", response_description="Crawling status")
async def crawl_endpoint(max_posts: int = 5):
    """
    Initiate blog crawling process to gather automotive content.
    
    - **max_posts**: Maximum number of posts to crawl (default: 5)
    - **returns**: JSON with crawling status
    """
    try:
        command = f"python ../main.py crawl --max-posts {max_posts}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

@app.post("/onboard", summary="Set up business information", response_description="Onboarding status")
async def onboard_endpoint(business_name: str, blog_url: str, chatbot_personality: str):
    """
    Configure business details for the chatbot.
    
    - **business_name**: Name of the business
    - **blog_url**: URL of the automotive blog
    - **chatbot_personality**: Personality description for the chatbot
    - **returns**: JSON with onboarding status
    """
    try:
        command = f"python ../main.py onboard --business-name {shlex.quote(business_name)} --blog-url {shlex.quote(blog_url)} --chatbot-personality {shlex.quote(chatbot_personality)}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

# Add similar endpoints for other commands (etc.)
