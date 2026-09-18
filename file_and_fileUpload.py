# in this, section, I'm gonna learn about data ingestion, in FastAPI
# Objectives
# 1. Learn data validation logic
# 2. File Upload methods
# 3. In-memory file handling, and Disk-oriented processing
# 4. Differentiate between sync, and async
# 5. Take a practice quiz, and close

from typing import List
from fastapi import FastAPI, File, UploadFile
import shutil
from pathlib import Path

#  file uploads can be handled using options like byte, or UploadFile module.
#  UploadFile is particularly important because it rolls over larger files onto Disk, 
#  preventing RAM shortage.
#  byte option is predominantly used for smaller files, which are stored entirely in RAM

# # UploadFile methods:
# Async => allows safe file handling within the worker threadpool. it has four main methods.
# 1. await file.read(size)
# 2. await file.write(data)
# 3. await file.seek(offset)
# 4. await file.close()

# implemeting the async file upload

app = FastAPI()
file_dir = Path("upload_files")
file_dir.mkdir(exist_ok=True)

@app.post("/multiple-files/")
async def get_multiple_files(files: List[UploadFile] = File(...)):
    file_details = []
    for file in files:
        file_details.append(
            {
                "filename": file.filename,
                "content-type": file.content_type,
                "file_size": file.size
            }
        )
    return {"file count": len(files), "detail": file_details}

@app.post("/upload/")
async def initiate_file_upload(file: UploadFile = File(...)):
    print(f"Uploading: {file.filename} ({file.content_type})")

    #  to save the file, securely
    file_path = file_dir/file.filename
    with open(file_path, "wb") as buffer:
        content = await file.read()

        buffer.write(content)

    return {"filename": file.filename, "status": "saved successfully"}
