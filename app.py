
import streamlit as st
from utils import extract_text, load_prompt, prepare_prompt, generate_with_gemini
from dotenv import load_dotenv

# --- Custom CSS for wider code output boxes (must be at the very top before any UI code) ---
st.markdown(
    """
    <style>
    .big-codebox .stCodeBlock, .big-codebox pre {
        max-width: 100vw !important;
        min-width: 800px !important;
        white-space: pre-wrap !important;
        word-break: break-word !important;
    }
    </style>
    """,
    unsafe_allow_html=True
)

load_dotenv()

st.set_page_config(page_title="Upwork Cover Letter Generator", layout="centered")

st.title("📄 Upwork Cover Letter Generator")


uploaded_file = st.file_uploader("Upload your project or resume document", type=["pdf", "docx", "txt"])

user_type = st.selectbox("Are you applying as an organization or individual?", ["Organization", "Freelancer"])

# New: Text area for job questions (QAs)
job_questions = st.text_area(
    "Paste any job-specific questions (QAs) from the Upwork post here (one per line):",
    placeholder="1) ...\n2) ...\n3) ...",
    height=150
)

if uploaded_file:
    st.info("Extracting content from uploaded file...")
    doc_content = extract_text(uploaded_file)
    st.success("✅ Document processed!")

    if st.button("✍️ Generate Cover Letter"):
        with st.spinner("Calling Gemini..."):
            base_prompt = load_prompt()
            # Pass job_questions to prepare_prompt
            full_prompt = prepare_prompt(base_prompt, user_type, doc_content, job_questions)
            try:
                # Split the output into CV and QAs
                cover_letter, qa_answers = generate_with_gemini(full_prompt, job_questions)
                import re
                def clean_text(text):
                    # Remove all leading whitespace from the first line only
                    # Remove QA header if present
                    lines = text.splitlines()
                    cleaned = []
                    for line in lines:
                        # Remove any line that is a QA header
                        if re.match(r'^\s*\*?\*?Job Questions \(QAs\)\*?\*?\s*$', line, re.IGNORECASE):
                            continue
                        cleaned.append(re.sub(r'^[ \t\*-]+', '', line))
                    result = '\n'.join(cleaned).strip()
                    result = re.sub(r'</div>\s*$', '', result)
                    return result

                def format_qa_answers(qa_text):
                    # Remove extra characters and ensure proper numbering
                    lines = qa_text.splitlines()
                    formatted = []
                    q_num = 1
                    for line in lines:
                        # Remove leading *, -, whitespace
                        l = re.sub(r'^[\s\*-]+', '', line).rstrip()
                        # If line starts with a number and a parenthesis or dot, keep as is
                        if re.match(r'^(\d+)[\).]', l):
                            formatted.append(l)
                            q_num = int(re.match(r'^(\d+)', l).group(1)) + 1
                        # If line looks like an answer, indent it
                        elif l:
                            formatted.append(f"&nbsp;&nbsp;{l}")
                    return '<br>'.join(formatted)

                st.subheader("📄 Cover Letter (CV)")
                st.markdown(
                    f"""
                    <div style='background: #f4f8fc; padding: 1.5em 2em; border-radius: 10px; font-size: 1.08em; line-height: 1.7; color: #222; margin-bottom: 2em; white-space: pre-wrap; text-align: left; box-shadow: 0 2px 8px #e3eaf2;'>
                    {clean_text(cover_letter)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.subheader("📝 Job Questions (QAs)")
                st.markdown(
                    f"""
                    <div style='background: #f4f8fc; padding: 1.5em 2em; border-radius: 10px; font-size: 1.08em; line-height: 1.7; color: #222; margin-bottom: 2em; white-space: pre-wrap; word-break: break-word; text-align: left; box-shadow: 0 2px 8px #ece6da;'>
                    {format_qa_answers(qa_answers)}
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                st.download_button("⬇️ Download Cover Letter", cover_letter, file_name="cover_letter.md")
                st.download_button("⬇️ Download QAs", qa_answers, file_name="qa_answers.md")
            except Exception as e:
                st.error(f"❌ Failed to generate cover letter: {e}")
