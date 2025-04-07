from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
import os

app = FastAPI(title="Simple HTML Server")

# Check if the static directory exists, if not create it
if not os.path.exists("static"):
    os.makedirs("static")

# Mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    try:
        with open("index.html", "r") as file:
            content = file.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="index.html not found")

if __name__ == "__main__":
    print("Server starting at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)