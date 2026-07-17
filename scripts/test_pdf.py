from app.services.pdf_service import extract_text_from_pdf

text = extract_text_from_pdf("Anuj_M_Resume_18.pdf")

print(text)