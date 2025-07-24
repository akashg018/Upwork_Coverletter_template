import fitz  # PyMuPDF
import docx
import os
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# --- Document Readers ---

def read_pdf(file):
    text = ""
    doc = fitz.open(stream=file.read(), filetype="pdf")
    for page in doc:
        text += page.get_text()
    return text.strip()

def read_docx(file):
    doc = docx.Document(file)
    return "\n".join([para.text for para in doc.paragraphs]).strip()

def read_txt(file):
    return file.read().decode('utf-8').strip()

def extract_text(file):
    filename = file.name.lower()
    if filename.endswith(".pdf"):
        return read_pdf(file)
    elif filename.endswith(".docx"):
        return read_docx(file)
    elif filename.endswith(".txt"):
        return read_txt(file)
    else:
        return "❌ Unsupported file format. Please upload PDF, DOCX, or TXT."


# --- Prompt Builder ---

def load_prompt():
    try:
        with open("prompts/base_prompt.md", "r", encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        raise FileNotFoundError("Prompt template not found at 'prompts/base_prompt.md'.")

def prepare_prompt(base_prompt: str, user_type: str, document_content: str) -> str:
    if not user_type or not document_content:
        raise ValueError("Missing user type or document content for prompt preparation.")

    return (
        base_prompt
        .replace("{{user_type}}", user_type.strip())
        .replace("{{document_content}}", document_content.strip())
    )


# --- Gemini Integration (Direct Invocation) ---

def generate_with_gemini(prompt: str) -> str:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found. Please check your .env file.")

    try:
        genai.configure(api_key=api_key)
        # Direct model invocation: hardcoded
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")
