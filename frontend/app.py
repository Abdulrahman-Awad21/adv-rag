import streamlit as st
import requests
import os
from dotenv import load_dotenv
import time
import pandas as pd
from typing import List, Dict, Any, Optional
import jwt

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
        "current_view": "login",
        "selected_project_id": None,
        "messages": [],
        "project_list": []
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

# --- API Helper Functions ---

def get_auth_header() -> Optional[Dict[str, str]]:
    if st.session_state.auth_token:
        return {"Authorization": f"Bearer {st.session_state.auth_token}"}
    return None

def handle_api_error(response, context="API"):
    try:
        error_data = response.json()
        detail = error_data.get('detail', 'Unknown error')
        st.error(f"{context} Error (Status {response.status_code}): {detail}")
    except requests.exceptions.JSONDecodeError:
        st.error(f"{context} Error (Status {response.status_code}): {response.text}")

def login_user(email, password):
    try:
        response = requests.post(f"{API_BASE_URL}/token", data={"username": email, "password": password})
        if response.status_code == 200:
            return response.json()
        handle_api_error(response, "Login")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during login: {e}")
        return None

def set_initial_password(token, new_password):
    payload = {"token": token, "new_password": new_password}
    try:
        response = requests.post(f"{API_BASE_URL}/set-initial-password", json=payload)
        if response.status_code == 200:
            st.success("Password set successfully! You can now log in.")
            return True
        handle_api_error(response, "Set Password")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return False

def request_password_reset(email):
    try:
        response = requests.post(f"{API_BASE_URL}/forgot-password", json={"email": email})
        if response.status_code == 202:
            st.info("If an account with that email exists, a password reset link has been sent.")
            return True
        handle_api_error(response, "Password Reset Request")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return False
        
def reset_password_with_token(token, new_password):
    payload = {"token": token, "new_password": new_password}
    try:
        response = requests.post(f"{API_BASE_URL}/reset-password", json=payload)
        if response.status_code == 200:
            st.success("Password has been reset successfully! You can now log in.")
            return True
        handle_api_error(response, "Password Reset")
        return False
    except requests.exceptions.RequestException as e:
        st.error(f"Network error: {e}")
        return False

def fetch_projects():
    headers = get_auth_header()
    if not headers: return []
    try:
        response = requests.get(f"{API_BASE_URL}/projects/", headers=headers)
        if response.status_code == 200:
            return [item['project_id'] for item in response.json()]
        handle_api_error(response, "Fetch Projects")
        return []
    except requests.exceptions.RequestException as e:
        st.error(f"Network error fetching projects: {e}")
        return []

def create_project_on_backend():
    headers = get_auth_header()
    if not headers: return None
    try:
        response = requests.post(f"{API_BASE_URL}/projects/", headers=headers, json={})
        if response.status_code == 201: return response.json()
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

def create_user_on_backend(email, role):
    headers = get_auth_header()
    if not headers: return None
    payload = {"email": email, "role": role}
    try:
        response = requests.post(f"{API_BASE_URL}/users/", json=payload, headers=headers)
        if response.status_code == 201:
            st.success(f"Successfully created user {email}. They will receive an email with instructions to set their password.")
            return response.json()
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
        handle_api_error(response, "System Wipe")
        return None
    except requests.exceptions.RequestException as e:
        st.error(f"Network error during system wipe: {e}")
        return None

# --- UI Rendering Functions ---

def render_login_page():
    st.set_page_config(page_title="Login - Mini RAG", layout="centered")
    st.title("Welcome to Adv-RAG")
    
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")

        if submitted:
            if not email or not password:
                st.error("Please enter both email and password.")
            else:
                with st.spinner("Authenticating..."):
                    token_info = login_user(email, password)
                if token_info and "access_token" in token_info:
                    st.session_state.logged_in = True
                    st.session_state.auth_token = token_info["access_token"]
                    try:
                        decoded_token = jwt.decode(token_info["access_token"], options={"verify_signature": False})
                        st.session_state.username = decoded_token.get("sub")
                        st.session_state.role = decoded_token.get("role")
                    except jwt.PyJWTError as e:
                        st.error(f"Could not decode authentication token: {e}")
                        handle_logout(rerun=False)
                        return
                    st.success("Login successful!")
                    time.sleep(1)
                    st.rerun()
    
    if st.button("Forgot your password?", type="secondary"):
        st.query_params["view"] = "forgot_password"

def render_forgot_password_page():
    st.set_page_config(page_title="Forgot Password", layout="centered")
    st.title("Forgot Password")
    with st.form("forgot_password_form"):
        email = st.text_input("Enter your account email")
        submitted = st.form_submit_button("Send Reset Link")
        if submitted:
            if request_password_reset(email):
                st.session_state.view = "login" # Go back to login after request
                time.sleep(3)
                st.query_params.clear()

def render_set_password_page(token):
    st.set_page_config(page_title="Set Your Password", layout="centered")
    st.title("Set Your Password")
    with st.form("set_password_form"):
        password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Set Password")
        if submitted:
            if not password or password != confirm_password:
                st.error("Passwords do not match or are empty.")
            else:
                if set_initial_password(token, password):
                    st.session_state.view = "login"
                    time.sleep(2)
                    st.query_params.clear()

def render_reset_password_page(token):
    st.set_page_config(page_title="Reset Your Password", layout="centered")
    st.title("Reset Your Password")
    with st.form("reset_password_form"):
        password = st.text_input("New Password", type="password")
        confirm_password = st.text_input("Confirm New Password", type="password")
        submitted = st.form_submit_button("Reset Password")
        if submitted:
            if not password or password != confirm_password:
                st.error("Passwords do not match or are empty.")
            else:
                if reset_password_with_token(token, password):
                    st.session_state.view = "login"
                    time.sleep(2)
                    st.query_params.clear()

def render_admin_view():
    st.title("Admin Dashboard")
    st.markdown("Manage users and system settings.")
    tab1, tab2 = st.tabs(["User Management", "System Actions"])
    with tab1:
        st.subheader("Manage Users")
        users_data = get_users_from_backend()
        if users_data:
            df = pd.DataFrame(users_data)
            st.dataframe(df[['id', 'email', 'role', 'is_active', 'created_at']], use_container_width=True)
            selected_user_id = st.selectbox("Select User to Edit", options=df['id'], format_func=lambda x: f"{df[df['id']==x]['email'].iloc[0]} (ID: {x})")
            if selected_user_id:
                selected_user = df[df['id'] == selected_user_id].iloc[0]
                with st.form(f"edit_user_{selected_user_id}"):
                    st.write(f"Editing User: **{selected_user['email']}**")
                    new_role = st.selectbox("Role", options=["admin", "uploader", "chatter"], index=["admin", "uploader", "chatter"].index(selected_user['role']))
                    new_is_active = st.checkbox("Is Active", value=selected_user['is_active'])
                    if st.form_submit_button("Update User"):
                        update_user_on_backend(selected_user_id, new_role, new_is_active)
                        st.rerun()

        with st.expander("Create New User", expanded=False):
            with st.form("create_user_form"):
                new_email = st.text_input("New User Email")
                new_user_role = st.selectbox("Assign Role", options=["uploader", "chatter"], index=1)
                if st.form_submit_button("Create User"):
                    if new_email:
                        create_user_on_backend(new_email, new_user_role)
                        st.rerun()
                    else:
                        st.warning("Please enter an email.")
    
    with tab2:
        st.subheader("System Actions")
        st.warning("This will permanently delete ALL data, files, and tables across all projects.")
        if st.button("🔴 Initiate System Wipe", type="primary"):
            st.session_state.confirm_wipe = True
        if st.session_state.get("confirm_wipe"):
            st.error("ARE YOU SURE? This cannot be undone.")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("✅ Yes, Wipe Everything"):
                    with st.spinner("Nuking the entire system... Please wait."):
                        nuke_system_on_backend()
                    st.session_state.confirm_wipe = False
                    handle_logout()
            with col2:
                if st.button("Cancel"):
                    st.session_state.confirm_wipe = False
                    st.rerun()

def render_uploader_view():
    st.title("Project Management")
    st.markdown("Create new projects, upload files, and get chat links.")
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
            st.session_state.selected_project_id = st.radio("Select a project:", sorted_projects, index=sorted_projects.index(st.session_state.selected_project_id) if st.session_state.selected_project_id in sorted_projects else 0, format_func=lambda x: f"Project {x}")
    with col2:
        if st.session_state.selected_project_id:
            project_id = st.session_state.selected_project_id
            st.header(f"Project {project_id}")
            st.success(f"Shareable Chat Link: `?project_id={project_id}`")
            st.subheader("Upload & Process Files")
            uploaded_files = st.file_uploader("Choose files", accept_multiple_files=True, type=["pdf", "txt", "png", "jpg", "jpeg", "csv", "xlsx"], key=f"uploader_{project_id}")
            if uploaded_files:
                if st.button("Upload and Process", type="primary"):
                    with st.status("Processing Pipeline...", expanded=True) as status:
                        status.write("1. Uploading files...")
                        if not upload_files_to_backend(project_id, uploaded_files):
                            status.update(label="Upload Failed", state="error"); return
                        status.write("2. Processing data...")
                        if not process_data_on_backend(project_id):
                            status.update(label="Processing Failed", state="error"); return
                        status.write("3. Indexing data...")
                        if not push_to_vector_db(project_id):
                            status.update(label="Indexing Failed", state="error"); return
                        status.update(label="Pipeline Complete!", state="complete")
                    st.success("Files processed successfully!")
                    st.balloons()

def render_chatter_view(project_id):
    st.title(f"Chat with Project {project_id}")
    if "messages" not in st.session_state or st.session_state.get("chatter_project_id") != project_id:
        st.session_state.messages = fetch_chat_history_from_backend(project_id)
        st.session_state.chatter_project_id = project_id
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    if prompt := st.chat_input(f"Ask about Project {project_id}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"): st.markdown(prompt)
        save_message_to_backend(project_id, "user", prompt)
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

def handle_logout(rerun=True):
    for key in list(st.session_state.keys()): del st.session_state[key]
    init_session_state()
    st.query_params.clear()
    if rerun: st.rerun()

# --- Main App Logic ---
def main():
    init_session_state()
    
    # Simple Router based on query params
    query_params = st.query_params
    view = query_params.get("view")
    token = query_params.get("token")
    project_id = query_params.get("project_id")
    
    if view == "set_password" and token:
        render_set_password_page(token)
        return
    elif view == "forgot_password":
        render_forgot_password_page()
        return
    elif view == "reset_password" and token:
        render_reset_password_page(token)
        return

    if not st.session_state.logged_in:
        render_login_page()
        return

    # Logged-in experience
    st.set_page_config(page_title="Mini RAG", layout="wide")
    with st.sidebar:
        st.title("Mini RAG")
        st.write(f"Welcome, **{st.session_state.username}**!")
        st.caption(f"Role: `{st.session_state.role}`")
        st.divider()

        # Navigation based on role
        nav_options = []
        if st.session_state.role == "admin":
            nav_options = ["Admin Dashboard", "Project Management"]
        elif st.session_state.role == "uploader":
            nav_options = ["Project Management"]

        if nav_options:
            st.session_state.current_view = st.radio("Navigation", nav_options, key="nav_main")
        else: # Chatter
            st.session_state.current_view = "Chat"

        if st.button("Logout", use_container_width=True):
            handle_logout()
    
    # Main Panel Rendering
    if project_id:
        render_chatter_view(project_id)
    elif st.session_state.current_view == "Admin Dashboard":
        render_admin_view()
    elif st.session_state.current_view == "Project Management":
        render_uploader_view()
    elif st.session_state.current_view == "Chat":
        st.info("Please select a project from the 'Project Management' view or use a direct chat link.")
    else:
        render_login_page()

if __name__ == "__main__":
    main()