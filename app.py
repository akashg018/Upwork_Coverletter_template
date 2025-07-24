import streamlit as st
from utils import extract_text, load_prompt, prepare_prompt, generate_with_gemini
from dotenv import load_dotenv

load_dotenv()

st.set_page_config(page_title="Upwork Cover Letter Generator", layout="centered")

st.title("📄 Smart Upwork Cover Letter Generator")

uploaded_file = st.file_uploader("Upload your project or resume document", type=["pdf", "docx", "txt"])

user_type = st.selectbox("Are you applying as an organization or individual?", ["Organization", "Freelancer"])

if uploaded_file:
    st.info("Extracting content from uploaded file...")
    doc_content = extract_text(uploaded_file)
    st.success("✅ Document processed!")

    if st.button("✍️ Generate Cover Letter"):
        with st.spinner("Calling Gemini..."):
            base_prompt = load_prompt()
            full_prompt = prepare_prompt(base_prompt, user_type, doc_content)
            try:
                cover_letter = generate_with_gemini(full_prompt)
                st.subheader("📬 Generated Cover Letter")
                st.code(cover_letter, language="markdown")
                st.download_button("⬇️ Download Cover Letter", cover_letter, file_name="cover_letter.md")
            except Exception as e:
                st.error(f"❌ Failed to generate cover letter: {e}")
