from fastapi import FastAPI, HTTPException, UploadFile, File
import os
from app.services.gemini_service import summarize_text
from app.services.pdf_service import extract_text_from_pdf

app = FastAPI(
    title="AI Document Summarizer",
    description="Summarize documents using AI",
    version="1.0.0"
)


@app.get("/")
def home():
    return {
        "message": "Welcome to AI Document Summarizer 🚀",
        "status": "Running"
    }


@app.get("/test")
def test():
    try:
        summary = summarize_text(
            """
            Artificial Intelligence is transforming industries by automating repetitive tasks,
            assisting with decision-making, and improving customer experiences.
            Large Language Models are one of the most exciting advances in AI.
            """
        )

        return {"summary": summary}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@app.post("/summarize")
async def summarize_pdf(
    file: UploadFile = File(...),
    style: str = "bullet"
):
    try:
        # Validate file type
        if not file.filename.endswith(".pdf"):
            raise HTTPException(
                status_code=400,
                detail="Only PDF files are allowed."
            )

        # Save uploaded file
        file_path = os.path.join("app", "uploads", file.filename)

        with open(file_path, "wb") as buffer:
            buffer.write(await file.read())

        # Extract text
        text = extract_text_from_pdf(file_path)

        # Generate summary
        summary = summarize_text(text, style)

        # Delete uploaded file
        os.remove(file_path)

        return {
            "filename": file.filename,
            "summary": summary
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))