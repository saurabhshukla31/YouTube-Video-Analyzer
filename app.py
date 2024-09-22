import streamlit as st
import re
from youtube_transcript_api import YouTubeTranscriptApi
import google.generativeai as genai
import logging
from fpdf import FPDF
import tempfile
import os

# Configure logging
logging.basicConfig(level=logging.INFO)

# Configure Gemini API
genai.configure(api_key='AIzaSyBhTddjulxSSHo7e7-1orUESyi6hDrJevI')  # Replace with your actual API key

# Set page config to wide mode
st.set_page_config(layout="wide")

# Custom CSS for Dark Mode styling
st.markdown("""
<style>
    .stApp {
        background-color: #1e1e1e;
        color: #f0f2f6;
    }
    .main {
        background-color: #2e2e2e;
        padding: 2rem;
        border-radius: 10px;
    }
    .stButton>button {
        width: 100%;
        border-radius: 5px;
        background-color: #444;
        color: #f0f2f6;
    }
    .stButton>button:hover {
        background-color: #666;
    }
    .quiz-option {
        margin: 10px 0;
        padding: 15px;
        border: 1px solid #444;
        border-radius: 5px;
        cursor: pointer;
        transition: all 0.3s ease;
    }
    .quiz-option:hover {
        background-color: #3e3e3e;
        transform: translateY(-2px);
        box-shadow: 0 4px 6px rgba(255,255,255,0.1);
    }
    .quiz-option.selected {
        background-color: #0068c9;
        color: white;
    }
    .summary-text {
        background-color: #3e3e3e;
        padding: 20px;
        border-radius: 10px;
        border-left: 5px solid #0068c9;
        box-shadow: 0 4px 6px rgba(255,255,255,0.1);
        margin-bottom: 20px;
        color: #f0f2f6;
    }
    h1, h2, h3, h4, p, label {
        color: #f0f2f6;
    }
    input, textarea {
        background-color: #2e2e2e;
        color: #f0f2f6;
        border: 1px solid #666;
    }
</style>
""", unsafe_allow_html=True)

def extract_video_id(url):
    pattern = r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com|youtu\.be)\/(?:watch\?v=)?(?:embed\/)?(?:v\/)?(?:shorts\/)?(\S{11})'
    match = re.search(pattern, url)
    return match.group(1) if match else None

def get_transcript(video_id):
    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)
        return ' '.join([entry['text'] for entry in transcript])
    except Exception as e:
        logging.error(f"Error getting transcript: {str(e)}")
        return f"An error occurred: {str(e)}"

def generate_summary(transcript):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            f"Provide a comprehensive, well-structured summary of the following transcript in 5-7 paragraphs. "
            f"Include an introduction, main points with supporting details, and a conclusion. "
            f"Ensure the summary is grammatically correct, free of typos, and captures the key points effectively:\n\n{transcript}"
        )
        return response.text
    except Exception as e:
        logging.error(f"Error generating summary: {str(e)}")
        return f"An error occurred while generating the summary: {str(e)}"

def generate_quiz(transcript):
    try:
        model = genai.GenerativeModel('gemini-pro')
        response = model.generate_content(
            f"Generate a 10-question multiple-choice quiz based on this transcript. "
            f"Format each question exactly as follows:\n"
            f"Q1: [Question]\n"
            f"a) [Option A]\n"
            f"b) [Option B]\n"
            f"c) [Option C]\n"
            f"d) [Option D]\n"
            f"Correct: [Correct option letter]\n\n"
            f"Ensure questions are clear, concise, and directly related to the main points of the transcript:\n\n{transcript}"
        )

        logging.info(f"Quiz response: {response.text}")

        if not response.text.strip():
            logging.warning("Quiz generation returned empty response.")
            return []

        return response.text
    except Exception as e:
        logging.error(f"Error generating quiz: {str(e)}")
        return f"An error occurred while generating the quiz: {str(e)}"

def parse_quiz(quiz_text):
    questions = []
    current_question = None
    for line in quiz_text.split('\n'):
        line = line.strip()
        if line.startswith('Q'):
            if current_question:
                questions.append(current_question)
            current_question = {'question': line, 'options': [], 'correct': ''}
        elif line.startswith(('a)', 'b)', 'c)', 'd)')) and current_question:
            current_question['options'].append(line)
        elif line.startswith('Correct:') and current_question:
            current_question['correct'] = line.split(':')[1].strip().rstrip(')')
    if current_question:
        questions.append(current_question)

    if not questions:
        logging.warning("No questions were parsed from the quiz text.")

    logging.info(f"Parsed questions: {questions}")
    return questions

def save_summary_to_pdf(summary):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.multi_cell(0, 10, summary)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
        pdf_file_path = temp_pdf.name
        pdf.output(pdf_file_path)

    with open(pdf_file_path, 'rb') as f:
        pdf_bytes = f.read()

    os.remove(pdf_file_path)

    return pdf_bytes

st.title('📺 YouTube Video Analyzer')

st.markdown("""
    <div style="padding: 20px; background-color: #3e3e3e; border-radius: 10px; margin-bottom: 20px;">
        <h5>This tool helps you analyze YouTube videos by providing transcripts, summaries, and interactive quizzes</h5>
    </div>
""", unsafe_allow_html=True)

url = st.text_input('🔗 Enter YouTube Video URL:')

if url:
    video_id = extract_video_id(url)
    if video_id:
        transcript = get_transcript(video_id)

        with st.expander("📽️ Watch Video", expanded=True):
            st.video(url)

        with st.expander("📝 View Transcript", expanded=False):
            st.text_area("Full Transcript", transcript, height=300)

        col1, col2 = st.columns(2)

        with col1:
            if st.button("📊 Generate Summary", use_container_width=True):
                with st.spinner('Generating summary...'):
                    summary = generate_summary(transcript)
                    st.session_state.summary = summary

        with col2:
            if st.button("🧠 Generate Quiz", use_container_width=True):
                with st.spinner('Preparing quiz...'):
                    quiz_text = generate_quiz(transcript)
                    quiz = parse_quiz(quiz_text)
                    st.session_state.quiz = quiz
                    st.session_state.user_answers = [''] * len(quiz)
                    logging.info(f"Quiz stored in session state: {st.session_state.quiz}")

        if 'summary' in st.session_state:
            st.subheader("📌 Video Summary")
            st.markdown(f'<div class="summary-text">{st.session_state.summary}</div>', unsafe_allow_html=True)
            if st.button("💾 Save Summary as PDF", use_container_width=True):
                pdf_bytes = save_summary_to_pdf(st.session_state.summary)
                st.download_button("Download PDF", pdf_bytes, file_name="video_summary.pdf")

        if 'quiz' in st.session_state:
            st.subheader("🎓 Video Quiz")
            quiz = st.session_state.quiz
            if not quiz:
                st.warning("No quiz questions were generated. Please try again or check the transcript.")
            else:
                for i, q in enumerate(quiz):
                    st.write(q['question'])
                    if q['options']:
                        options = [opt.split(') ', 1)[1] for opt in q['options']]
                        selected_option = st.radio("Select your answer:", options, key=f"q{i}", index=None)
                        if selected_option:
                            st.session_state.user_answers[i] = chr(97 + options.index(selected_option))
                    else:
                        st.warning(f"No options available for question {i + 1}")
                    st.markdown("---")

                if st.button("📝 Submit Quiz", use_container_width=True):
                    score = sum([1 for u, q in zip(st.session_state.user_answers, quiz) if u == q['correct']])
                    st.balloons()
                    st.success(f"🎉 You scored {score} out of {len(quiz)}!")
                    for u, q in zip(st.session_state.user_answers, quiz):
                        if u == q['correct']:
                            st.info(f"✅ Correct: {q['question']} - Answer: {q['correct']}")
                        else:
                            st.error(f"❌ Incorrect: {q['question']} - Your answer: {u} - Correct answer: {q['correct']}")
