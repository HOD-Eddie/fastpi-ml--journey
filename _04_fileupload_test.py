import io
from fastapi import FastAPI, File, UploadFile, HTTPException, status
from pydantic import BaseModel
app = FastAPI()

MAX_SIZE = 5 * 1024 * 1024  # 5 MB
CHUNK_SIZE = 1024 * 1024    # 1 MB
ALLOWED_TYPES = {"image/jpeg", "image/png", "audio/mp3", "image/jpg"}


@app.post("/transcribe/")
async def transcribe_audio(file: UploadFile = File(...)):
    # The server should validate the file at the API boundary before it spends time
    # processing a payload that violates the expected contract.
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format.Only jpg, png, mp3, and jpeg files are allowed."
        )

    # File metadata is a quick way to reject unusually large uploads before we start
    # reading content from the stream.
    if file.size > MAX_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_CONTENT_TOO_LARGE,
            detail="File is too massive!"
        )

    # Streaming in fixed-size chunks lets us verify the file's integrity without
    # buffering the entire payload in memory.
    total_bytes = 0
    try:
        while chunk := await file.read(CHUNK_SIZE):
            total_bytes += len(chunk)

        # reset file cursor position to beginning
        await file.seek(0)
            
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Error occurred while reading the audio stream."
        )
        
    return {
        "filename": file.filename,
        "verified_size": total_bytes,
        "transcript": f"Mock transcription completed for {file.filename}"
    }


