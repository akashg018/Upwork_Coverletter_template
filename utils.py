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

# --- Gemini Integration (Simplified and Improved) ---

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
        
        # Look for the exact "Job Questions (QAs)" header
        qa_pattern = r'\n\s*Job Questions \(QAs\)\s*\n'
        match = re.search(qa_pattern, output, re.IGNORECASE)
        
        if match:
            # Split at the Job Questions header
            split_idx = match.start()
            cover_letter = output[:split_idx].strip()
            qa_answers = output[match.end():].strip()
            
            # Add header back to QA answers for display
            if qa_answers:
                qa_answers = f"Job Questions (QAs)\n\n{qa_answers}"
            
        else:
            # Fallback: Look for numbered answers starting with "1)"
            numbered_pattern = r'\n\s*1\)\s+'
            numbered_match = re.search(numbered_pattern, output)
            
            if numbered_match:
                split_idx = numbered_match.start()
                cover_letter = output[:split_idx].strip()
                qa_section = output[numbered_match.start():].strip()
                qa_answers = f"Job Questions (QAs)\n\n{qa_section}"
            else:
                # No QA section found
                cover_letter = output
                if job_questions and job_questions.strip():
                    qa_answers = f"Job Questions (QAs)\n\n(No answers generated for the provided questions.)"
                else:
                    qa_answers = ""
        
        return cover_letter, qa_answers
        
    except Exception as e:
        raise RuntimeError(f"Gemini generation failed: {e}")
