
from fastapi import FastAPI, Query, Request
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.background import BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import os
import yt_dlp
import subprocess
import zipfile
import math
import uuid



app = FastAPI()
DOWNLOAD_FOLDER = "downloads"
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security headers middleware
@app.middleware("http")
async def add_security_headers(request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
    return response


def cleanup_file(path: str):
    if os.path.exists(path):
        os.remove(path)


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/split")
def split_video(
    url: str = Query(..., description="YouTube video URL"),
    interval: float = Query(..., description="Interval in seconds"),
    base_name: str = Query("clip", description="Base name for split clips"),
    background_tasks: BackgroundTasks = None
):
    try:
        # Step 1: Download full video
        full_filename = os.path.join(DOWNLOAD_FOLDER, "%(title)s.%(ext)s")
        ydl_opts = {
            "outtmpl": full_filename,
            "format": "mp4",
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            full_filepath = ydl.prepare_filename(info)

        # Get video duration in seconds
        duration = info.get("duration")
        if not duration:
            return JSONResponse(content={"error": "Cannot get video duration"}, status_code=500)

        clip_files = []

        # Step 2: Split video into interval clips
        num_clips = math.ceil(duration / interval)
        for i in range(num_clips):
            start = i * interval
            end = min((i + 1) * interval, duration)
            clip_filename = os.path.join(DOWNLOAD_FOLDER, f"{base_name}{i}.mp4")  # numbered clips

            cmd = [
                "ffmpeg",
                "-i", full_filepath,
                "-ss", str(start),
                "-to", str(end),
                "-c", "copy",
                clip_filename,
                "-y"
            ]
            subprocess.run(cmd, check=True)
            clip_files.append(clip_filename)

        # Step 3: Create ZIP of all clips
        zip_filename = os.path.join(DOWNLOAD_FOLDER, f"{base_name}_{uuid.uuid4().hex}.zip")
        with zipfile.ZipFile(zip_filename, "w") as zipf:
            for clip in clip_files:
                zipf.write(clip, os.path.basename(clip))

        # Step 4: Cleanup clips + full video in background
        background_tasks.add_task(cleanup_file, full_filepath)
        for clip in clip_files:
            background_tasks.add_task(cleanup_file, clip)
        background_tasks.add_task(cleanup_file, zip_filename)  # delete zip after sending

        # Step 5: Send ZIP to client
        return FileResponse(
            zip_filename,
            media_type="application/zip",
            filename=os.path.basename(zip_filename),
            background=background_tasks
        )

    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
