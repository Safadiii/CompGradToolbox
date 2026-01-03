import os
import tempfile
from fastapi import APIRouter, UploadFile, File, HTTPException

from app.services.signaturechecker import run_signature_checker
from app.services.internship_report_checker import run_internship_checker

router = APIRouter()

def _save_upload_to_temp_pdf(upload: UploadFile) -> str:
    # UploadFile.content_type is sometimes missing; don't be too strict
    filename = upload.filename or "upload.pdf"
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Please upload a PDF file.")

    tmpdir = tempfile.mkdtemp(prefix="pdf_")
    pdf_path = os.path.join(tmpdir, filename)

    with open(pdf_path, "wb") as f:
        f.write(upload.file.read())

    return pdf_path


@router.post("/comp590")
async def check_comp590(file: UploadFile = File(...)):
    pdf_path = _save_upload_to_temp_pdf(file)
    return run_signature_checker(pdf_path, debug=False)


@router.post("/comp291-391")
async def check_comp291_391(file: UploadFile = File(...)):
    pdf_path = _save_upload_to_temp_pdf(file)
    return run_internship_checker(pdf_path, debug=False)