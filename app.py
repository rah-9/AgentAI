import os
import streamlit as st
import requests
import json
import traceback
from PIL import Image
from dotenv import load_dotenv
from config.settings import APP_CONFIG, COMPANY_INFO, THEME

# Load environment variables
load_dotenv()

# API endpoint configuration
FASTAPI_URL = os.getenv("BACKEND_URL", "http://localhost:8000/process_input/")

# Initialize session state variables
if 'debug_info' not in st.session_state:
    st.session_state.debug_info = {}
if 'last_result' not in st.session_state:
    st.session_state.last_result = None

def load_css():
    # Load the main CSS file with a version parameter to force refresh
    st.markdown(
        f"""
        <link rel="stylesheet" type="text/css" href="static/css/style.css?v=1.0.0" />
        <style>
            :root {{
                --primary-color: #a1c9f1; /* Soft light blue */
                --primary-hover-color: #c0e7f3; /* Lighter teal hover */
                --background-color: #fefefe; /* Nearly white */
                --card-bg-color: #ffffff; /* Pure white for cards */
                --border-color: #dce3eb; /* Light gray-blue */
                --text-color: #2b3a55; /* Dark blue-gray for readability */
                --text-secondary-color: #6c7a89; /* Muted navy gray */
                --text-muted-color: #9eafbc; /* Subtle gray-blue */
            }}

            body {{
                background-color: var(--background-color);
                color: var(--text-color);
                font-family: 'Segoe UI', sans-serif;
            }}

            .custom-header h1 {{
                color: var(--text-color);
            }}

            .custom-header p {{
                color: var(--text-secondary-color);
            }}

            .stButton>button {{
                background-color: var(--primary-color);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 0.6rem 1.2rem;
                font-weight: 600;
            }}

            .stButton>button:hover {{
                background-color: var(--primary-hover-color);
                color: #003b5c;
            }}

            .footer {{
                color: var(--text-muted-color);
                font-size: 0.85rem;
                margin-top: 2rem;
                padding: 1rem 0;
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )



def main():
    st.set_page_config(**APP_CONFIG)
    load_css()

    # Header
    st.markdown(f"""
        <div class='custom-header' style="background: linear-gradient(135deg, #e3f0ff 0%, #ffffff 100%);">
            <h1 style='text-align: center; font-size: 2.5rem; margin-bottom: 0.5rem; color: #1a237e;'>
                📄 INVOICE EXTRACTION USING AI
            </h1>
            <p style='text-align: center; color: #4f5b62; font-size: 1.1rem;'>
                Effortless Invoice Extraction and Analysis with AI
            </p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1], gap="large")

    # Initialize process_button
    process_button = False
    result = None
    error_msg = None
    
    with col1:
        st.markdown("### Upload Invoice or Document")
        uploaded_file = st.file_uploader("", type=['png', 'jpg', 'jpeg', 'pdf', 'json', 'eml'])
        preview_shown = False
        if uploaded_file:
            try:
                if uploaded_file.type.startswith('image/'):
                    image = Image.open(uploaded_file)
                    st.image(image, use_column_width=True)
                    preview_shown = True
                elif uploaded_file.type == 'application/pdf':
                    st.image("https://cdn-icons-png.flaticon.com/512/337/337946.png", width=100, caption=f"PDF File: {uploaded_file.name}")
                    preview_shown = True
                elif uploaded_file.type == 'application/json':
                    json_bytes = uploaded_file.read()
                    st.code(json_bytes.decode('utf-8')[:500], language='json')
                    preview_shown = True
                else:
                    st.warning("Unsupported file type.")
            except Exception as e:
                st.error(f"Error previewing file: {str(e)}")

            # Always reset file pointer before sending to backend
            uploaded_file.seek(0)
            process_button = st.button("Process Document 🔍", use_container_width=True)

    # Handle backend call and error handling
    if process_button and uploaded_file:
        try:
            # For JSON files, send as JSON body
            if uploaded_file.type == 'application/json':
                json_bytes = uploaded_file.read()
                try:
                    json_obj = json.loads(json_bytes.decode('utf-8'))
                except Exception as e:
                    st.error(f"Invalid JSON file: {e}")
                    st.stop()
                response = requests.post(FASTAPI_URL, json=json_obj)
            else:
                files = {'file': (uploaded_file.name, uploaded_file, uploaded_file.type)}
                response = requests.post(FASTAPI_URL, files=files)
            try:
                result = response.json()
            except Exception as e:
                st.error(f"Error parsing backend response: {e}")
                st.write(response.text)
                result = None
            st.session_state['last_result'] = result
        except Exception as e:
            st.error(f"Error communicating with backend: {e}")
            st.code(traceback.format_exc(), language='python')

    with col2:
        st.markdown("### Extraction Results")
        if 'last_result' in st.session_state:
            result = st.session_state['last_result']
            st.markdown('#### Raw Backend Response (Debug)')
            if isinstance(result, dict):
                st.json(result)
            else:
                st.error("Backend did not return a valid JSON object.")
                st.write(result)
            # Robust error handling for backend response
            if result is None:
                st.error("No response received from backend.")
            elif isinstance(result, dict) and 'error' in result:
                st.error(f"Backend Error: {result['error']}")
                if isinstance(result['error'], dict) and 'message' in result['error']:
                    st.write(result['error']['message'])
                if 'detail' in result:
                    st.write(result['detail'])
                if 'debug' in result:
                    st.write(result['debug'])
                if 'traceback' in result.get('debug', {}):
                    st.code(result['debug']['traceback'], language='python')
            elif isinstance(result, dict) and 'classification' in result:
                st.markdown(f"**Format:** `{result['classification'].get('format', 'N/A')}`")
                st.markdown(f"**Business Intent:** `{result['classification'].get('intent', 'N/A')}`")
                if 'routed_agent' in result['classification']:
                    st.markdown(f"**Routed Agent:** `{result['classification']['routed_agent']}`")
                # Show summary and extracted fields
                if 'result' in result and isinstance(result['result'], dict) and 'fields' in result['result'] and result['result']['fields']:
                    st.markdown("---")
                    st.markdown(f"**Summary:**\n\n{result['result']['fields'].get('text_excerpt', 'No summary available.')}")
                    st.markdown("**Extracted Fields:**")
                    for k, v in result['result']['fields'].items():
                        if k != 'text_excerpt':
                            st.write(f"- **{k}**: {v}")
            else:
                st.warning("Unexpected backend response structure.")
                st.write(result)
        else:
            st.info("👆 Upload and process a document to see extraction results here.")

    st.markdown(f"""
        <div class='footer' style='text-align: center;'>
            {COMPANY_INFO['copyright']}
        </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()