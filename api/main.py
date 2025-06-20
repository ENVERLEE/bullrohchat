from fastapi import FastAPI, HTTPException
import subprocess
import shlex

app = FastAPI()

@app.get("/ask")
async def ask_endpoint(query: str):
    try:
        command = f"python ../main.py ask {shlex.quote(query)}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

@app.post("/crawl")
async def crawl_endpoint(max_posts: int = 5):
    try:
        command = f"python ../main.py crawl --max-posts {max_posts}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

@app.post("/onboard")
async def onboard_endpoint(business_name: str, blog_url: str, chatbot_personality: str):
    try:
        command = f"python ../main.py onboard --business-name {shlex.quote(business_name)} --blog-url {shlex.quote(blog_url)} --chatbot-personality {shlex.quote(chatbot_personality)}"
        result = subprocess.run(command, shell=True, capture_output=True, text=True, check=True)
        return {"response": result.stdout}
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr}")

# Add similar endpoints for other commands (etc.)
