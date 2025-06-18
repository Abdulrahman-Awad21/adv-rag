import streamlit as st
import requests
import os
from dotenv import load_dotenv
import time
from typing import List, Dict, Any
import re

# --- Configuration ---
load_dotenv()
DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1"
API_BASE_URL = os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL)

# --- Session State Initialization ---
if "current_phase" not in st.session_state:
    st.session_state.current_phase = "upload"
if "uploaded_file_names" not in st.session_state:
    st.session_state.uploaded_file_names = []
if "messages" not in st.session_state:
    st.session_state.messages = []
if "processing_successful" not in st.session_state:
    st.session_state.processing_successful = False
if "project_id" not in st.session_state:
    st.session_state.project_id = None
if "project_history_list" not in st.session_state:
    st.session_state.project_history_list = []
if "initial_project_load_done" not in st.session_state:
    st.session_state.initial_project_load_done = False

def parse_and_display_assistant_message(content: str):
    """
    Parses content for <think> tags and displays it with an expander.
    """
    if not isinstance(content, str):
        st.markdown(str(content))
        return

    match = re.search(r"<think>(.*?)</think>(.*)", content, re.DOTALL)
    
    if match:
        thinking_text = match.group(1).strip()
        final_response = match.group(2).strip()
    else:
        thinking_text = None
        final_response = content.strip()

    if final_response:
        st.markdown(final_response)
    
    if thinking_text:
        with st.expander("Show thought process"):
            st.markdown(thinking_text)
    
    if not final_response and not thinking_text:
        st.markdown(content)


# --- API Helper Functions ---
def handle_api_response(response, success_status=200, is_json=True):
    if response.status_code == success_status:
        if not is_json:
            return True
        try: 
            return response.json()
        except requests.exceptions.JSONDecodeError: 
            st.error(f"API non-JSON (Status {response.status_code}): {response.text}")
            return None
    else:
        try: 
            error_data = response.json()
            error_message = error_data.get('signal', error_data.get('detail', 'Unknown error'))
            st.error(f"API Error (Status {response.status_code}): {error_message}")
        except requests.exceptions.JSONDecodeError: 
            st.error(f"API Error (Status {response.status_code}): {response.text}")
        return None

def upload_files_to_backend(project_id, files_to_upload):
    if not files_to_upload: st.warning("No files selected."); return None
    api_files = [('files', (f.name, f.getvalue(), f.type)) for f in files_to_upload]
    try: 
        response = requests.post(f"{API_BASE_URL}/data/upload/{project_id}", files=api_files, timeout=120)
        return handle_api_response(response)
    except requests.exceptions.RequestException as e: 
        st.error(f"Network error during upload: {e}")
        return None

def process_data_on_backend(project_id, process_specific_file_id: str = None, do_reset=1, chunk_size=512, overlap_size=50):
    payload = {"do_reset": do_reset, "chunk_size": chunk_size, "overlap_size": overlap_size}
    if process_specific_file_id: payload["file_id"] = process_specific_file_id
    try: 
        response = requests.post(f"{API_BASE_URL}/data/process/{project_id}", json=payload, timeout=300)
        return handle_api_response(response)
    except requests.exceptions.RequestException as e: 
        st.error(f"Network error during process: {e}")
        return None

def push_to_vector_db(project_id, do_reset=1):
    payload = {"do_reset": do_reset}
    try: 
        response = requests.post(f"{API_BASE_URL}/nlp/index/push/{project_id}", json=payload, timeout=300)
        return handle_api_response(response)
    except requests.exceptions.RequestException as e: 
        st.error(f"Network error during index push: {e}")
        return None

def get_rag_answer(project_id, query, limit=15):
    payload = {"text": query, "limit": limit}
    try: 
        response = requests.post(f"{API_BASE_URL}/nlp/index/answer/{project_id}", json=payload, timeout=120)
        return handle_api_response(response)
    except requests.exceptions.RequestException as e: 
        st.error(f"Network error during RAG answer: {e}")
        return None

def fetch_project_history_from_backend():
    try:
        response = requests.get(f"{API_BASE_URL}/projects", timeout=10)
        if response.status_code == 200:
            try: 
                projects = response.json()
                return [str(pid) for pid in projects if pid is not None]
            except requests.exceptions.JSONDecodeError: 
                st.sidebar.error("Failed to parse project list.")
                return []
        else: 
            st.sidebar.error(f"Failed to fetch projects (API Status: {response.status_code}).")
            return []
    except requests.exceptions.RequestException as e: 
        st.sidebar.error(f"Network error fetching projects: {str(e)[:100]}")
        return []

def fetch_chat_history_from_backend(project_id: str) -> List[Dict[str, Any]]:
    if not project_id: return []
    try:
        response = requests.get(f"{API_BASE_URL}/projects/{project_id}/chat_history", timeout=30)
        api_result = handle_api_response(response, success_status=200)
        if api_result and isinstance(api_result, list):
            return [{"role": msg.get("role"), "content": msg.get("content")} for msg in api_result]
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching chat history: {e}")
        return []

def save_message_to_backend(project_id: str, role: str, content: str):
    if not project_id: st.warning("Cannot save message: No project ID."); return None
    payload = {"role": role, "content": content}
    try:
        response = requests.post(f"{API_BASE_URL}/projects/{project_id}/chat_history", json=payload, timeout=30)
        return handle_api_response(response, success_status=201) 
    except requests.exceptions.RequestException as e:
        st.error(f"Network error saving message: {e}")
        return None

# --- Function to handle project selection/creation ---
def select_project(selected_id_str: str, is_new_project_creation=False):
    if not selected_id_str or not selected_id_str.strip():
        st.sidebar.warning("Project ID cannot be empty.")
        return

    if st.session_state.project_id != selected_id_str or is_new_project_creation:
        st.session_state.project_id = selected_id_str
        st.session_state.uploaded_file_names = [] 
        
        with st.spinner(f"Loading chat history for Project {selected_id_str}..."):
            chat_history = fetch_chat_history_from_backend(selected_id_str)
        
        if chat_history:
            st.session_state.messages = chat_history
        elif is_new_project_creation:
            st.session_state.messages = [
                {"role": "assistant", "content": f"Created and switched to new Project {selected_id_str}. Please upload files or start chatting."}
            ]
        else: 
             st.session_state.messages = [
                {"role": "assistant", "content": f"Switched to Project {selected_id_str}. How can I help?"}
            ]

        if is_new_project_creation:
            st.session_state.current_phase = "upload" 
            if selected_id_str not in st.session_state.project_history_list:
                st.session_state.project_history_list.append(selected_id_str)
        else: 
            st.session_state.current_phase = "chat"
        
        st.rerun()

def create_new_project():
    next_id = "1" 
    if st.session_state.project_history_list:
        numeric_ids = [int(pid_str) for pid_str in st.session_state.project_history_list if pid_str.isdigit()]
        if numeric_ids:
            next_id = str(max(numeric_ids) + 1)
        else: 
            next_id = "1" 
    select_project(next_id, is_new_project_creation=True)

# --- Main App Logic ---
st.set_page_config(page_title="Mini RAG UI", layout="wide")

# --- Sidebar ---
with st.sidebar:
    st.title("Project Navigation")

    if not st.session_state.initial_project_load_done:
        with st.spinner("Loading project list..."):
            st.session_state.project_history_list = fetch_project_history_from_backend()
        st.session_state.initial_project_load_done = True
        
        if not st.session_state.project_id and st.session_state.project_history_list:
            default_project_id = st.session_state.project_history_list[0]
            select_project(default_project_id)
        elif not st.session_state.project_id and not st.session_state.project_history_list:
            pass

    if st.button("🔄 Refresh Project List", use_container_width=True):
        with st.spinner("Refreshing project list..."):
            st.session_state.project_history_list = fetch_project_history_from_backend()
        if st.session_state.project_id and st.session_state.project_id not in st.session_state.project_history_list:
            st.session_state.project_id = None
            st.session_state.messages = []
            st.session_state.current_phase = "upload"
        st.rerun()

    if st.button("➕ Create New Project", use_container_width=True, type="primary"):
        create_new_project() 

    if st.session_state.project_history_list:
        st.subheader("Project History:")
        sorted_history = sorted(st.session_state.project_history_list, key=lambda x: (int(x) if x.isdigit() else float('inf'), x))
        for pid_str in sorted_history:
            button_type = "primary" if pid_str == st.session_state.project_id else "secondary"
            if st.button(f"Project {pid_str}", key=f"project_btn_{pid_str}", use_container_width=True, type=button_type):
                select_project(pid_str)
    else:
        st.write("No projects found.")
        if not st.session_state.project_id:
            st.info("Click 'Create New Project' to start.")

    st.divider()
    st.subheader("API Endpoint")
    st.info(f"{API_BASE_URL}")

# --- Main Panel ---
if not st.session_state.project_id:
    st.warning("Please select a project or create a new one from the sidebar to begin.")
    if st.session_state.initial_project_load_done and not st.session_state.project_history_list:
        if st.button("Create your first project"):
            create_new_project()
    st.stop()


if st.session_state.current_phase == "upload":
    st.title(f"Mini RAG - Upload Your Data (Project ID: {st.session_state.project_id})")
    st.markdown("Upload documents. They will be processed and indexed for the current project.")

    uploaded_files = st.file_uploader(
        "Choose files (PDF, TXT, CSV, XLSX, PNG, JPG, JPEG)",
        accept_multiple_files=True,
        type=["pdf", "txt", "png", "jpg", "jpeg", "csv", "xlsx"],
        key=f"file_uploader_{st.session_state.project_id}"
    )

    if uploaded_files:
        st.write("Selected files:")
        for f_up in uploaded_files:
            st.write(f"- {f_up.name} ({f_up.type}, {f_up.size / 1024:.2f} KB)")

        if st.button("Upload and Process Files", type="primary"):
            st.session_state.processing_successful = False
            st.session_state.uploaded_file_names = [f.name for f in uploaded_files]

            with st.status("Processing pipeline...", expanded=True) as status_ui:
                st.write("Step 1: Uploading files...")
                upload_response = upload_files_to_backend(st.session_state.project_id, uploaded_files)
                if upload_response and upload_response.get("signal") == "file_upload_success":
                    st.write(f"✅ Files uploaded. ({len(upload_response.get('uploaded_files_details', []))} files)")
                    st.write("Step 2: Processing data...")
                    process_response = process_data_on_backend(st.session_state.project_id, do_reset=1)
                    if process_response and process_response.get("signal") == "processing_success":
                        st.write(f"✅ Data processed. (Chunks: {process_response.get('inserted_chunks', 0)}, Files: {process_response.get('processed_files',0)})")
                        st.write("Step 3: Indexing data...")
                        index_response = push_to_vector_db(st.session_state.project_id, do_reset=1)
                        if index_response and index_response.get("signal") == "insert_into_vectordb_success":
                            st.write(f"✅ Data indexed. (Items: {index_response.get('inserted_items_count',0)})")
                            st.session_state.processing_successful = True
                            status_ui.update(label="All steps completed!", state="complete", expanded=False)
                        else: st.error("❌ Indexing failed."); status_ui.update(label="Indexing failed.", state="error")
                    else: st.error("❌ Data processing failed."); status_ui.update(label="Processing failed.", state="error")
                else: st.error("❌ File upload failed."); status_ui.update(label="Upload failed.", state="error")

            if st.session_state.processing_successful:
                st.success(f"All files for Project {st.session_state.project_id} processed and ready!")
                st.balloons()
                time.sleep(1)
                st.session_state.current_phase = "chat"
                assistant_welcome = {"role": "assistant", "content": f"Documents for Project {st.session_state.project_id} are ready. Ask away!"}
                st.session_state.messages.append(assistant_welcome)
                save_message_to_backend(st.session_state.project_id, assistant_welcome["role"], assistant_welcome["content"])
                st.rerun()
            else: st.error("Pipeline failed. Check messages above.")

elif st.session_state.current_phase == "chat":
    st.title(f"Chat with Your Data (Project ID: {st.session_state.project_id})")

    if st.button(f"➕ Upload More Files to Project {st.session_state.project_id}"):
        st.session_state.current_phase = "upload"
        # ✅ REMOVED the line that causes the error.
        st.rerun()

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant":
                parse_and_display_assistant_message(message["content"])
            else:
                st.markdown(message["content"])


    if prompt := st.chat_input(f"Ask about Project {st.session_state.project_id}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        save_message_to_backend(st.session_state.project_id, "user", prompt)

        with st.spinner("Thinking..."), st.chat_message("assistant"):
            api_response = get_rag_answer(st.session_state.project_id, prompt)
            if api_response and api_response.get("signal") == "rag_answer_success":
                answer = api_response.get("answer", "Sorry, I couldn't retrieve an answer.")
                parse_and_display_assistant_message(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message_to_backend(st.session_state.project_id, "assistant", answer)
            else:
                error_msg = "Failed to get an answer from RAG."
                if api_response: 
                    error_msg += f" (API Signal: {api_response.get('signal', 'N/A')})"
                
                st.error(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": f"Error: {error_msg}"})
                save_message_to_backend(st.session_state.project_id, "assistant", f"Error: {error_msg}")
else:
    st.error("Application error: No active project ID or invalid phase.")
    if st.session_state.project_history_list: 
        select_project(st.session_state.project_history_list[0])
    elif st.session_state.initial_project_load_done :
        st.info("No projects exist. Please create one from the sidebar.")
    else: 
        st.info("Initializing...")