"""FastAPI: POST /extract and POST /process."""

from __future__ import annotations

import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from extract.process import process_file, process_folder

app = FastAPI(title="clinic-doc-extractor")


class ProcessRequest(BaseModel):
    folder: str = "./inbox"


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/extract")
async def extract(file: UploadFile = File(...)):
    suffix = Path(file.filename or "upload.bin").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = Path(tmp.name)

    try:
        result = process_file(
            tmp_path,
            source_filename=file.filename or tmp_path.name,
        )
        return result.model_dump(mode="json")
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/process")
def process(req: ProcessRequest):
    results = process_folder(req.folder)
    return {
        "ok": True,
        "processed": len(results),
        "needs_review": sum(1 for r in results if r.needs_review),
        "results": [r.model_dump(mode="json") for r in results],
    }
