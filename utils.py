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
        return "âŒ Unsupported file format. Please upload PDF, DOCX, or TXT."


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

def generate_with_gemini(prompt: str, job_questions: str = ""):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise EnvironmentError("GEMINI_API_KEY not found. Please check your .env file.")

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)
        output = response.text.strip()
        import re
        # Try to split at 'Job Questions (QAs)' header or similar
        qa_section_headers = [
            r"^\s*Job Questions \(QAs\)\s*[:\-]*\s*$",
            r"^\s*Questions and Answers\s*[:\-]*\s*$",
            r"^\s*QAs\s*[:\-]*\s*$",
            r"^\s*Specific Questions\s*[:\-]*\s*$",
            r"^\s*Regarding your specific questions\s*[:\-]*\s*$",
            r"^\s*Answers to Job Questions\s*[:\-]*\s*$"
        ]
        m = None
        for header_pat in qa_section_headers:
            m = re.search(header_pat, output, re.IGNORECASE | re.MULTILINE)
            if m:
                break
        if m:
            split_idx = m.start()
            cover_letter = output[:split_idx].strip()
            qa_answers = output[split_idx:].strip()
        else:
            # fallback: extract all numbered QAs from output (e.g., 1., 2), 3)
            qa_matches = list(re.finditer(r"(^|\n)(\d+[\)|\.])", output))
            if qa_matches:
                first_qa_idx = qa_matches[0].start(2)
                cover_letter = output[:first_qa_idx].strip()
                qa_answers = output[first_qa_idx:].strip()
            else:
                # fallback: look for lines starting with Q: or A:
                qa_line_matches = list(re.finditer(r"(^|\n)(Q:|A:)\s*", output))
                if qa_line_matches:
                    first_qa_idx = qa_line_matches[0].start(2)
                    cover_letter = output[:first_qa_idx].strip()
                    qa_answers = output[first_qa_idx:].strip()
                else:
                    # fallback: previous logic
                    qa_split_patterns = [
                        r"(?:Regarding your specific questions:|Questions and Answers:|QAs:?|Job Questions:?|Specific Questions:)"
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
                        cover_letter = output
                        qa_answers = "(No answers generated for job questions.)"
        # Final fallback: if answers are missing but questions were provided, show the questions
        if (not qa_answers or qa_answers.strip() == "(No answers generated for job questions.)") and job_questions.strip():
            qa_answers = f"Questions provided:\n{job_questions.strip()}\n(No answers generated for job questions.)"
        return cover_letter, qa_answers
    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")