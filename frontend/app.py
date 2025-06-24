# frontend/app.py

import streamlit as st
import requests
import os
from dotenv import load_dotenv
import time
import pandas as pd
from typing import List, Dict, Any, Optional
import re

# --- Configuration ---
load_dotenv()
DEFAULT_API_BASE_URL = "http://localhost:8000/api/v1"
API_BASE_URL = os.getenv("API_BASE_URL", DEFAULT_API_BASE_URL)

# --- Session State Initialization ---
def init_session_state():
    defaults = {
        "logged_in": False,
        "auth_token": None,
        "username": None,
        "role": None,
        "current_view": "login", # login, uploader, admin, chatter
        "selected_project_id": None,
        "messages": [],
        "shareable_link": None,
        "project_list": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- API Helper Functions ---
# All helpers now include the auth token in headers.

def get_auth_header() -> Optional[Dict[str, str]]:
    """Constructs the authorization header if a token exists."""
    if st.session_state.auth_token:
        return {"Authorization": f"Bearer {st.session_state.auth_token}"}
    return None

def handle_api_error(response, context="API"):
    """Unified error handler for API responses."""
    try:
        error_data = response.json()
        detail = error_data.get('detail', 'Unknown error')
        st.error(f"{context} Error (Status {response.status_code}): {detail}")
    except requests.exceptions.JSONDecodeError:
        st.error(f"{context} Error (Status {response.status_code}): {response.text}")

def login_user(username, password):
    """Authenticates the user and returns the token."""
    try:
        response = requests.post(f"{API_BASE_URL}/token", data={"username": username, "password": password})
        if response.status_code == 200:
            return response.json()
        else:
            handle_api_error(response, "Login")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during login: {e}")
        return None

def fetch_projects():
    """Fetches projects for the current user."""
    headers = get_auth_header()
    if not headers: return []
    try:
        response = requests.get(f"{API_BASE_URL}/projects/", headers=headers)
        if response.status_code == 200:
            # The backend now returns a list of dicts, e.g., [{"project_id": "1"}]
            return [item['project_id'] for item in response.json()]
        else:
            handle_api_error(response, "Fetch Projects")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching projects: {e}")
        return []

def create_project_on_backend():
    headers = get_auth_header()
    if not headers: return None
    try:
        # Assuming the create endpoint doesn't need a body for now
        response = requests.post(f"{API_BASE_URL}/projects/", headers=headers, json={})
        if response.status_code == 201:
            return response.json()
        else:
            handle_api_error(response, "Create Project")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error creating project: {e}")
        return None

def upload_files_to_backend(project_id, files_to_upload):
    headers = get_auth_header()
    if not headers: return None
    api_files = [('files', (f.name, f.getvalue(), f.type)) for f in files_to_upload]
    try:
        response = requests.post(f"{API_BASE_URL}/data/upload/{project_id}", files=api_files, headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "File Upload")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during upload: {e}")
        return None

def process_data_on_backend(project_id, chunk_size=512, overlap_size=50):
    headers = get_auth_header()
    if not headers: return None
    payload = {"do_reset": 1, "chunk_size": chunk_size, "overlap_size": overlap_size}
    try:
        response = requests.post(f"{API_BASE_URL}/data/process/{project_id}", json=payload, headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "Process Data")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during processing: {e}")
        return None

def push_to_vector_db(project_id):
    headers = get_auth_header()
    if not headers: return None
    payload = {"do_reset": 1}
    try:
        response = requests.post(f"{API_BASE_URL}/nlp/index/push/{project_id}", json=payload, headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "Index Push")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during index push: {e}")
        return None

def get_rag_answer(project_id, query):
    headers = get_auth_header()
    if not headers: return None
    payload = {"text": query, "limit": 15}
    try:
        response = requests.post(f"{API_BASE_URL}/nlp/index/answer/{project_id}", json=payload, headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "RAG Answer")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error getting answer: {e}")
        return None

def fetch_chat_history_from_backend(project_id):
    headers = get_auth_header()
    if not headers or not project_id: return []
    try:
        response = requests.get(f"{API_BASE_URL}/projects/{project_id}/chat_history", headers=headers)
        if response.status_code == 200:
            return [{"role": msg.get("role"), "content": msg.get("content")} for msg in response.json()]
        else:
            # Don't show error if it's just a new project with no history (404)
            if response.status_code != 404:
                handle_api_error(response, "Fetch Chat History")
            return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching chat history: {e}")
        return []

def save_message_to_backend(project_id, role, content):
    headers = get_auth_header()
    if not headers or not project_id: return None
    payload = {"role": role, "content": content}
    try:
        response = requests.post(f"{API_BASE_URL}/projects/{project_id}/chat_history", json=payload, headers=headers)
        if response.status_code == 201: return response.json()
        handle_api_error(response, "Save Message")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error saving message: {e}")
        return None

# --- Admin API Helpers ---
def get_users_from_backend():
    headers = get_auth_header()
    if not headers: return []
    try:
        response = requests.get(f"{API_BASE_URL}/users/", headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "Get Users")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error getting users: {e}")
        return []

def create_user_on_backend(username, password, role):
    headers = get_auth_header()
    if not headers: return None
    payload = {"username": username, "password": password, "role": role}
    try:
        response = requests.post(f"{API_BASE_URL}/users/", json=payload, headers=headers)
        if response.status_code == 201: return response.json()
        handle_api_error(response, "Create User")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error creating user: {e}")
        return None

def update_user_on_backend(user_id, role, is_active):
    headers = get_auth_header()
    if not headers: return None
    payload = {"role": role, "is_active": is_active}
    try:
        response = requests.put(f"{API_BASE_URL}/users/{user_id}", json=payload, headers=headers)
        if response.status_code == 200: return response.json()
        handle_api_error(response, "Update User")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error updating user: {e}")
        return None

def nuke_system_on_backend():
    headers = get_auth_header()
    if not headers:
        st.error("Authentication token not found.")
        return None
    try:
        response = requests.delete(f"{API_BASE_URL}/admin/nuke-and-rebuild-db", headers=headers)
        if response.status_code == 200:
            st.success("System wipe successful!")
            return response.json()
        else:
            handle_api_error(response, "System Wipe")
            return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during system wipe: {e}")
        return None


# --- UI Rendering Functions ---

def render_login_page():
    """Displays the login form."""
    st.set_page_config(page_title="Login - Mini RAG", layout="centered")
    st.title("Welcome to Adv-RAG")
    
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not username or not password:
                st.error("Please enter both username and password.")
            else:
                with st.spinner("Authenticating..."):
                    token_info = login_user(username, password)
                if token_info and "access_token" in token_info:
                    st.session_state.logged_in = True
                    st.session_state.auth_token = token_info["access_token"]
                    # For simplicity, we decode the role from the token on the frontend
                    # In a real high-security app, you'd fetch user profile from a /users/me endpoint
                    import jwt
                    try:
                        decoded_token = jwt.decode(token_info["access_token"], options={"verify_signature": False})
                        st.session_state.username = decoded_token.get("sub")
                        st.session_state.role = decoded_token.get("role")
                    except Exception:
                        st.session_state.username = "User"
                        st.session_state.role = "chatter"

                    st.success("Login successful!")
                    time.sleep(1)
                    st.rerun()
                # Error is already shown by login_user function

def render_admin_view():
    st.title(f"Admin Dashboard")
    st.markdown("Manage users and system settings.")

    tab1, tab2 = st.tabs(["User Management", "System Actions"])

    with tab1:
        st.subheader("Manage Users")
        
        users_data = get_users_from_backend()
        if users_data:
            df = pd.DataFrame(users_data)
            st.dataframe(df[['id', 'username', 'role', 'is_active', 'created_at']], use_container_width=True)

            selected_user_id = st.selectbox("Select User to Edit", options=df['id'], format_func=lambda x: f"{df[df['id']==x]['username'].iloc[0]} (ID: {x})")
            if selected_user_id:
                selected_user = df[df['id'] == selected_user_id].iloc[0]
                with st.form(f"edit_user_{selected_user_id}"):
                    st.write(f"Editing User: **{selected_user['username']}**")
                    new_role = st.selectbox("Role", options=["admin", "uploader", "chatter"], index=["admin", "uploader", "chatter"].index(selected_user['role']))
                    new_is_active = st.checkbox("Is Active", value=selected_user['is_active'])
                    if st.form_submit_button("Update User"):
                        update_user_on_backend(selected_user_id, new_role, new_is_active)
                        st.rerun()

        with st.expander("Create New User", expanded=False):
            with st.form("create_user_form"):
                new_username = st.text_input("New Username")
                new_password = st.text_input("New Password", type="password")
                new_user_role = st.selectbox("Assign Role", options=["admin", "uploader", "chatter"])
                if st.form_submit_button("Create User"):
                    if new_username and new_password:
                        create_user_on_backend(new_username, new_password, new_user_role)
                        st.rerun()
                    else:
                        st.warning("Please fill all fields.")
    
    with tab2:
        st.subheader("System Actions")
        st.warning("This will permanently delete ALL data, files, and tables across all projects.")
        if st.button("🔴 Initiate System Wipe", type="primary"):
            if "confirm_wipe" not in st.session_state:
                st.session_state.confirm_wipe = True
            
        if st.session_state.get("confirm_wipe"):
            st.error("ARE YOU SURE? This cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Wipe Everything"):
                    with st.spinner("Nuking the entire system... Please wait."):
                        nuke_system_on_backend()
                    st.session_state.confirm_wipe = False
                    # On success, log out user to force a fresh start
                    handle_logout()
            with col2:
                if st.button("Cancel"):
                    st.session_state.confirm_wipe = False
                    st.rerun()


def render_uploader_view():
    st.title("Project Management")
    st.markdown("Create new projects, upload files, and get chat links.")

    # Fetch projects on each run
    st.session_state.project_list = fetch_projects()

    col1, col2 = st.columns([1, 2])
    with col1:
        st.subheader("Your Projects")
        if st.button("➕ Create New Project", use_container_width=True, type="primary"):
            with st.spinner("Creating project..."):
                new_project_info = create_project_on_backend()
                if new_project_info:
                    st.session_state.selected_project_id = new_project_info.get("project_id")
                    st.rerun()

        if not st.session_state.project_list:
            st.info("You haven't created any projects yet.")
        else:
            sorted_projects = sorted(st.session_state.project_list, key=lambda x: int(x))
            # Use a selectbox for project selection
            st.session_state.selected_project_id = st.radio(
                "Select a project:",
                sorted_projects,
                index=sorted_projects.index(st.session_state.selected_project_id) if st.session_state.selected_project_id in sorted_projects else 0,
                format_func=lambda x: f"Project {x}"
            )

    with col2:
        if st.session_state.selected_project_id:
            project_id = st.session_state.selected_project_id
            st.header(f"Project {project_id}")

            base_url = st.get_option("server.baseUrlPath")
            full_url = f"{base_url}?project_id={project_id}"
            st.success("Shareable Chat Link:")
            st.code(full_url, language=None)
            
            st.subheader("Upload & Process Files")
            uploaded_files = st.file_uploader(
                "Choose files (PDF, TXT, CSV, XLSX, PNG, JPG)",
                accept_multiple_files=True,
                type=["pdf", "txt", "png", "jpg", "jpeg", "csv", "xlsx"],
                key=f"uploader_{project_id}"
            )
            if uploaded_files:
                if st.button("Upload and Process", type="primary"):
                    with st.status("Processing Pipeline...", expanded=True) as status:
                        status.write("1. Uploading files...")
                        upload_res = upload_files_to_backend(project_id, uploaded_files)
                        if not upload_res:
                            status.update(label="Upload Failed", state="error"); st.stop()
                        
                        status.write("2. Processing data...")
                        process_res = process_data_on_backend(project_id)
                        if not process_res:
                            status.update(label="Processing Failed", state="error"); st.stop()
                        
                        status.write("3. Indexing data...")
                        index_res = push_to_vector_db(project_id)
                        if not index_res:
                            status.update(label="Indexing Failed", state="error"); st.stop()
                            
                        status.update(label="Pipeline Complete!", state="complete")
                    st.success("Files processed successfully!")
                    st.balloons()

def render_chatter_view(project_id):
    """Displays the chat interface for a specific project."""
    st.title(f"Chat with Project {project_id}")

    # Load chat history
    if "messages" not in st.session_state or st.session_state.get("chatter_project_id") != project_id:
        st.session_state.messages = fetch_chat_history_from_backend(project_id)
        st.session_state.chatter_project_id = project_id

    # Display messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            # Simple markdown display for now
            st.markdown(message["content"])

    # Chat input
    if prompt := st.chat_input(f"Ask about Project {project_id}..."):
        # Add user message to UI and save
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        save_message_to_backend(project_id, "user", prompt)

        # Get assistant response
        with st.spinner("Thinking..."), st.chat_message("assistant"):
            response = get_rag_answer(project_id, prompt)
            if response and response.get("signal") == "rag_answer_success":
                answer = response.get("answer", "I couldn't find an answer.")
                st.markdown(answer)
                st.session_state.messages.append({"role": "assistant", "content": answer})
                save_message_to_backend(project_id, "assistant", answer)
            else:
                error_msg = "Sorry, I ran into an issue. Please try again."
                st.markdown(error_msg)
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                save_message_to_backend(project_id, "assistant", error_msg)

def handle_logout():
    """Clears session state and reruns the app to show the login page."""
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    init_session_state() # Re-initialize with defaults
    st.rerun()

# --- Main App Logic ---

def main():
    """Main function to control the app flow."""
    init_session_state()

    if not st.session_state.logged_in:
        render_login_page()
        return

    # --- Logged-in User Experience ---
    st.set_page_config(page_title="Mini RAG", layout="wide")
    with st.sidebar:
        st.title("Mini RAG")
        st.write(f"Welcome, **{st.session_state.username}**!")
        st.caption(f"Role: `{st.session_state.role}`")
        st.divider()

        # Navigation based on role
        if st.session_state.role == "admin":
            st.session_state.current_view = st.radio("Navigation", ["Admin Dashboard", "Project Management"], key="nav_admin")
        elif st.session_state.role == "uploader":
            st.session_state.current_view = "Project Management"
        else: # chatter
            st.session_state.current_view = "Chat"

        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    # --- Main Panel Rendering ---
    
    # Check for project_id in URL for direct chat view access
    query_params = st.query_params
    url_project_id = query_params.get("project_id")
    
    if url_project_id:
        # For any user trying to access a direct link
        render_chatter_view(url_project_id)
    elif st.session_state.current_view == "Admin Dashboard":
        render_admin_view()
    elif st.session_state.current_view == "Project Management":
        render_uploader_view()
    elif st.session_state.current_view == "Chat":
        st.info("Please select a project from the 'Project Management' view or use a direct chat link.")
    else:
        st.info("Select a view from the sidebar.")


if __name__ == "__main__":
    main()