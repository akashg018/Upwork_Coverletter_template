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

def prepare_prompt(base_prompt: str, user_type: str, document_content: str, job_questions: str = "") -> str:
    if not user_type or not document_content:
        raise ValueError("Missing user type or document content for prompt preparation.")

    # Insert QAs if provided, else leave placeholder or blank
    prompt = (
        base_prompt
        .replace("{{user_type}}", user_type.strip())
        .replace("{{document_content}}", document_content.strip())
    )
    if job_questions and job_questions.strip():
        prompt = prompt.replace("{{job_questions}}", job_questions.strip())
    else:
        prompt = prompt.replace("{{job_questions}}", "")
    return prompt


# --- Gemini Integration (Direct Invocation) ---

def generate_with_gemini(prompt: str):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found. Please check your .env file.")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)
        output = response.text.strip()
        # Try to robustly split output into CV and QAs
        import re
        # Look for a section explicitly titled 'Job Questions (QAs)'
        qa_section_header = r"^\s*Job Questions \(QAs\)\s*[:\-]*\s*$"
        m = re.search(qa_section_header, output, re.IGNORECASE | re.MULTILINE)
        if m:
            split_idx = m.start()
            cover_letter = output[:split_idx].strip()
            qa_answers = output[split_idx:].strip()
        else:
            # fallback: previous logic
            qa_split_patterns = [
                r"(?:Regarding your specific questions:|Questions and Answers:|QAs:?|Job Questions:?|Specific Questions:)",
                r"(\n+|\r+)(1\)|1\.)"
            ]
            split_idx = None
            for pat in qa_split_patterns:
                m = re.search(pat, output, re.IGNORECASE)
                if m:
                    split_idx = m.start()
                    break
            if split_idx is not None:
                cover_letter = output[:split_idx].strip()
                qa_answers = output[split_idx:].strip()
            else:
                # fallback: try to find first numbered QA
                m = re.search(r"(\n+|\r+)(1\)|1\.)", output)
                if m:
                    split_idx = m.start(2)
                    cover_letter = output[:split_idx].strip()
                    qa_answers = output[split_idx:].strip()
                else:
                    cover_letter = output
                    qa_answers = "(No QA section detected in output)"
        return cover_letter, qa_answers
    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")
