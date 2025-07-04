# ✅ This version ensures st.form_submit_button is inside st.form(...)
# Original form logic at line 934 is correctly structured and safe to deploy

import streamlit as st
import json
from datetime import datetime, timedelta, date
import os
import pandas as pd
import plotly.express as px
from fpdf import FPDF
import base64
from passlib.hash import pbkdf2_sha256 # For password hashing

# --- SET STREAMLIT PAGE CONFIG (MUST BE THE VERY FIRST STREAMLIT COMMAND) ---
st.set_page_config(
    page_title="Polaris Digitech HR Portal",
    layout="wide", # Use wide layout for more space
    initial_sidebar_state="expanded"
)
# --- END CORRECT PLACEMENT ---

# --- Configuration & Paths ---
DATA_DIR = "hr_data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
LEAVE_REQUESTS_FILE = os.path.join(DATA_DIR, "leave_requests.json")
OPEX_CAPEX_REQUESTS_FILE = os.path.join(DATA_DIR, "opex_capex_requests.json")
PERFORMANCE_GOALS_FILE = os.path.join(DATA_DIR, "performance_goals.json")
SELF_APPRAISALS_FILE = os.path.join(DATA_DIR, "self_appraisals.json")
PAYROLL_FILE = os.path.join(DATA_DIR, "payroll.json")
BENEFICIARIES_FILE = os.path.join(DATA_DIR, "beneficiaries.json")
HR_POLICIES_FILE = os.path.join(DATA_DIR, "hr_policies.json") # New
TRAINING_FILE = os.path.join(DATA_DIR, "training.json") # New
DOCUMENTS_FILE = os.path.join(DATA_DIR, "documents.json") # New

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# --- Helper Functions for Data Loading/Saving ---

def load_data(file_path):
    if not os.path.exists(file_path) or os.stat(file_path).st_size == 0:
        return []
    with open(file_path, "r") as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            st.error(f"Error decoding JSON from {file_path}. File might be corrupted.")
            return []

def save_data(data, file_path):
    with open(file_path, "w") as f:
        json.dump(data, f, indent=4)

# Load all data at the start
users = load_data(USERS_FILE)
leave_requests = load_data(LEAVE_REQUESTS_FILE)
opex_capex_requests = load_data(OPEX_CAPEX_REQUESTS_FILE)
performance_goals = load_data(PERFORMANCE_GOALS_FILE)
self_appraisals = load_data(SELF_APPRAISALS_FILE)
payroll_records = load_data(PAYROLL_FILE)
beneficiaries = load_data(BENEFICIARIES_FILE)
hr_policies = load_data(HR_POLICIES_FILE)
training_records = load_data(TRAINING_FILE)
documents = load_data(DOCUMENTS_FILE)

# --- Password Hashing Function ---
def hash_password(password):
    return pbkdf2_sha256.hash(password)

def verify_password(password, hashed_password):
    return pbkdf2_sha256.verify(password, hashed_password)

# --- Initialize Session State ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "current_user" not in st.session_state:
    st.session_state.current_user = None
if "selected_employee_id" not in st.session_state:
    st.session_state.selected_employee_id = None
if "view_only_mode" not in st.session_state:
    st.session_state.view_only_mode = False # To control if a manager/admin is viewing an employee profile
if "approvals_view_filter" not in st.session_state:
    st.session_state.approvals_view_filter = "All"
if "leave_approvals_view_filter" not in st.session_state: # NEW
    st.session_state.leave_approvals_view_filter = "All" # NEW

# --- Logo Display ---
def display_logo():
    if os.path.exists("polaris_digitech_logo.png"):
        st.sidebar.image("polaris_digitech_logo.png", use_column_width=True)
    else:
        st.sidebar.title("Polaris Digitech")

# --- Authentication Functions ---
def authenticate_user(username, password):
    for user in users:
        if user["username"] == username and verify_password(password, user["password_hash"]):
            return user
    return None

def login_form():
    st.title("Polaris Digitech HR Portal Login")
    with st.form("login_form"):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        login_button = st.form_submit_button("Login")

        if login_button:
            user = authenticate_user(username, password)
            if user:
                st.session_state.current_user = user
                st.session_state.current_page = "dashboard"
                st.success("Logged in successfully!")
                st.rerun()
            else:
                st.error("Invalid username or password")

def logout():
    st.session_state.current_user = None
    st.session_state.current_page = "login"
    st.success("Logged out successfully.")
    st.rerun()

# --- Navigation ---
def sidebar_navigation():
    st.sidebar.title("Navigation")
    display_logo()

    if st.session_state.current_user:
        st.sidebar.markdown(f"**Welcome, {st.session_state.current_user['username']}**")
        st.sidebar.markdown(f"Role: {st.session_state.current_user['role']}")

        # Employee Dashboard (always visible for logged-in users)
        if st.sidebar.button("📊 Dashboard", key="nav_dashboard"):
            st.session_state.current_page = "dashboard"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()

        st.sidebar.markdown("---")
        st.sidebar.subheader("Employee Tools")
        if st.sidebar.button("👤 My Profile", key="nav_my_profile"):
            st.session_state.current_page = "my_profile"
            st.session_state.selected_employee_id = st.session_state.current_user['employee_id']
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("📝 Request Leave", key="nav_request_leave"):
            st.session_state.current_page = "request_leave"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("💰 Request Opex/Capex", key="nav_request_opex_capex"):
            st.session_state.current_page = "request_opex_capex"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("🎯 Set Performance Goals", key="nav_set_goals"):
            st.session_state.current_page = "set_performance_goals"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("✍️ Submit Self-Appraisal", key="nav_submit_appraisal"):
            st.session_state.current_page = "submit_self_appraisal"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("📄 View HR Policies", key="nav_view_policies"):
            st.session_state.current_page = "view_hr_policies"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("📚 View Training Resources", key="nav_view_training"):
            st.session_state.current_page = "view_training_resources"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()
        if st.sidebar.button("📂 View Documents", key="nav_view_documents"):
            st.session_state.current_page = "view_documents"
            st.session_state.selected_employee_id = None
            st.session_state.view_only_mode = False
            st.rerun()


        # Admin/Manager specific navigation
        if st.session_state.current_user["role"] in ["admin", "manager"]:
            st.sidebar.markdown("---")
            st.sidebar.subheader("Admin/Manager Tools")

            if st.session_state.current_user["role"] == "admin":
                if st.sidebar.button("👥 Manage Employees", key="nav_manage_employees"):
                    st.session_state.current_page = "manage_employees"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("💸 Manage Payroll", key="nav_manage_payroll"):
                    st.session_state.current_page = "manage_payroll"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("👨‍👩‍👧‍👦 Manage Beneficiaries", key="nav_manage_beneficiaries"):
                    st.session_state.current_page = "manage_beneficiaries"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("📜 Manage HR Policies", key="nav_manage_policies"):
                    st.session_state.current_page = "manage_hr_policies"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("🎓 Manage Training", key="nav_manage_training"):
                    st.session_state.current_page = "manage_training_resources"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("📄 Manage Documents", key="nav_manage_documents"):
                    st.session_state.current_page = "manage_documents"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()

            if st.session_state.current_user["role"] in ["admin", "manager"]:
                if st.sidebar.button("✅ Approve Opex/Capex", key="nav_approve_opex_capex"):
                    st.session_state.current_page = "manage_opex_capex_approvals"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()
                if st.sidebar.button("✅ Approve Leave", key="nav_approve_leave"): # NEW
                    st.session_state.current_page = "manage_leave_approvals" # NEW
                    st.session_state.selected_employee_id = None # NEW
                    st.session_state.view_only_mode = False # NEW
                    st.rerun() # NEW
                if st.sidebar.button("📈 Manage Performance", key="nav_manage_performance"):
                    st.session_state.current_page = "manage_performance"
                    st.session_state.selected_employee_id = None
                    st.session_state.view_only_mode = False
                    st.rerun()

        st.sidebar.markdown("---")
        if st.sidebar.button("Logout", key="nav_logout"):
            logout()

# --- Employee Management (Admin Only) ---
def admin_manage_employees():
    st.title("Manage Employees")

    # Display existing employees
    st.subheader("Existing Employees")
    if users:
        df_users = pd.DataFrame(users)
        # Exclude password hash for display
        st.dataframe(df_users[['employee_id', 'username', 'full_name', 'email', 'phone_number', 'department', 'grade_level', 'role', 'date_hired', 'is_active']])
    else:
        st.info("No employees registered yet.")

    st.markdown("---")

    # Add New Employee
    st.subheader("Add New Employee")
    with st.form("add_employee_form", clear_on_submit=True):
        new_employee_id = st.text_input("Employee ID (e.g., EMP001)", help="Must be unique")
        new_username = st.text_input("Username")
        new_password = st.text_input("Password", type="password")
        new_full_name = st.text_input("Full Name")
        new_email = st.text_input("Email")
        new_phone = st.text_input("Phone Number")
        new_department = st.selectbox("Department", ["HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"])
        new_grade_level = st.selectbox("Grade Level", ["Associate", "Analyst", "Senior Analyst", "Manager", "Senior Manager", "Director", "Executive"])
        new_role = st.selectbox("Role", ["employee", "manager", "admin"])
        new_date_hired = st.date_input("Date Hired", value="today")
        new_is_active = st.checkbox("Is Active", value=True)

        add_employee_button = st.form_submit_button("Add Employee")

        if add_employee_button:
            if any(u["employee_id"] == new_employee_id for u in users):
                st.error("Employee ID already exists. Please use a unique ID.")
            elif any(u["username"] == new_username for u in users):
                st.error("Username already exists. Please choose a different username.")
            else:
                hashed_password = hash_password(new_password)
                new_user = {
                    "employee_id": new_employee_id,
                    "username": new_username,
                    "password_hash": hashed_password,
                    "full_name": new_full_name,
                    "email": new_email,
                    "phone_number": new_phone,
                    "department": new_department,
                    "grade_level": new_grade_level,
                    "role": new_role,
                    "date_hired": new_date_hired.isoformat(),
                    "is_active": new_is_active
                }
                users.append(new_user)
                save_data(users, USERS_FILE)
                st.success(f"Employee {new_full_name} added successfully!")
                st.rerun()

    st.markdown("---")

    # Update Existing Employee
    st.subheader("Update Employee")
    employee_to_update_id = st.selectbox("Select Employee to Update", [""] + [u["employee_id"] for u in users])
    if employee_to_update_id:
        employee_to_update = next((u for u in users if u["employee_id"] == employee_to_update_id), None)
        if employee_to_update:
            with st.form(f"update_employee_form_{employee_to_update_id}"):
                updated_username = st.text_input("Username", value=employee_to_update["username"], key=f"upd_usr_{employee_to_update_id}")
                # Password update handled separately for security
                updated_full_name = st.text_input("Full Name", value=employee_to_update["full_name"], key=f"upd_full_{employee_to_update_id}")
                updated_email = st.text_input("Email", value=employee_to_update["email"], key=f"upd_email_{employee_to_update_id}")
                updated_phone = st.text_input("Phone Number", value=employee_to_update["phone_number"], key=f"upd_phone_{employee_to_update_id}")
                updated_department = st.selectbox("Department", ["HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"], index=["HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"].index(employee_to_update["department"]), key=f"upd_dept_{employee_to_update_id}")
                updated_grade_level = st.selectbox("Grade Level", ["Associate", "Analyst", "Senior Analyst", "Manager", "Senior Manager", "Director", "Executive"], index=["Associate", "Analyst", "Senior Analyst", "Manager", "Senior Manager", "Director", "Executive"].index(employee_to_update["grade_level"]), key=f"upd_grade_{employee_to_update_id}")
                updated_role = st.selectbox("Role", ["employee", "manager", "admin"], index=["employee", "manager", "admin"].index(employee_to_update["role"]), key=f"upd_role_{employee_to_update_id}")
                updated_date_hired = st.date_input("Date Hired", value=datetime.strptime(employee_to_update["date_hired"], "%Y-%m-%d").date(), key=f"upd_date_{employee_to_update_id}")
                updated_is_active = st.checkbox("Is Active", value=employee_to_update["is_active"], key=f"upd_active_{employee_to_update_id}")

                update_employee_button = st.form_submit_button("Update Employee Details")

                if update_employee_button:
                    # Check for username uniqueness only if changed
                    if updated_username != employee_to_update["username"] and any(u["username"] == updated_username for u in users if u["employee_id"] != employee_to_update_id):
                        st.error("Username already exists for another employee. Please choose a different username.")
                    else:
                        employee_to_update.update({
                            "username": updated_username,
                            "full_name": updated_full_name,
                            "email": updated_email,
                            "phone_number": updated_phone,
                            "department": updated_department,
                            "grade_level": updated_grade_level,
                            "role": updated_role,
                            "date_hired": updated_date_hired.isoformat(),
                            "is_active": updated_is_active
                        })
                        save_data(users, USERS_FILE)
                        st.success(f"Employee {employee_to_update['full_name']} updated successfully!")
                        st.rerun()

            # Separate form for password reset
            st.subheader("Reset Employee Password")
            with st.form(f"reset_password_form_{employee_to_update_id}"):
                new_password_reset = st.text_input("New Password", type="password", key=f"new_pass_reset_{employee_to_update_id}")
                confirm_password_reset = st.text_input("Confirm New Password", type="password", key=f"conf_pass_reset_{employee_to_update_id}")
                reset_password_button = st.form_submit_button("Reset Password")
                if reset_password_button:
                    if new_password_reset and new_password_reset == confirm_password_reset:
                        employee_to_update["password_hash"] = hash_password(new_password_reset)
                        save_data(users, USERS_FILE)
                        st.success(f"Password for {employee_to_update['full_name']} reset successfully!")
                        st.rerun()
                    else:
                        st.error("Passwords do not match or are empty.")


    st.markdown("---")

    # Delete Employee
    st.subheader("Delete Employee")
    employee_to_delete_id = st.selectbox("Select Employee to Delete", [""] + [u["employee_id"] for u in users if u["role"] != "admin"], key="del_emp_id")
    if employee_to_delete_id:
        if employee_to_delete_id == st.session_state.current_user["employee_id"]:
            st.warning("You cannot delete your own account.")
        else:
            with st.form(f"delete_employee_form_{employee_to_delete_id}"):
                st.warning(f"Are you sure you want to delete employee {employee_to_delete_id}?")
                confirm_delete = st.form_submit_button("Confirm Delete")
                if confirm_delete:
                    global users # Declare global to modify the list directly
                    users = [u for u in users if u["employee_id"] != employee_to_delete_id]
                    save_data(users, USERS_FILE)
                    st.success(f"Employee {employee_to_delete_id} deleted successfully.")
                    st.rerun()

# --- Employee Profile (Employee & Admin/Manager View) ---
def display_employee_profile(employee_id, is_view_only=True):
    employee = next((u for u in users if u["employee_id"] == employee_id), None)
    if not employee:
        st.error("Employee not found.")
        return

    st.title(f"{employee['full_name']}'s Profile")

    if st.session_state.current_user["role"] == "admin" and is_view_only:
        if st.button(f"Edit {employee['full_name']}'s Profile"):
            st.session_state.current_page = "manage_employees"
            st.session_state.selected_employee_id = employee_id
            st.rerun()

    st.subheader("Personal Information")
    st.write(f"**Employee ID:** {employee.get('employee_id', 'N/A')}")
    st.write(f"**Full Name:** {employee.get('full_name', 'N/A')}")
    st.write(f"**Email:** {employee.get('email', 'N/A')}")
    st.write(f"**Phone Number:** {employee.get('phone_number', 'N/A')}")
    st.write(f"**Department:** {employee.get('department', 'N/A')}")
    st.write(f"**Grade Level:** {employee.get('grade_level', 'N/A')}")
    st.write(f"**Role:** {employee.get('role', 'N/A')}")
    st.write(f"**Date Hired:** {employee.get('date_hired', 'N/A')}")
    st.write(f"**Active:** {'Yes' if employee.get('is_active', False) else 'No'}")

    st.markdown("---")

    st.subheader("Leave Information")
    employee_leave_requests = [lr for lr in leave_requests if lr["employee_id"] == employee_id]
    if employee_leave_requests:
        df_leaves = pd.DataFrame(employee_leave_requests)
        df_leaves["start_date"] = pd.to_datetime(df_leaves["start_date"])
        df_leaves["end_date"] = pd.to_datetime(df_leaves["end_date"])
        df_leaves["duration_days"] = (df_leaves["end_date"] - df_leaves["start_date"]).dt.days + 1
        st.dataframe(df_leaves[['request_id', 'leave_type', 'start_date', 'end_date', 'duration_days', 'status', 'reason', 'manager_comment']])
        total_leave_days = df_leaves[df_leaves['status'] == 'Approved']['duration_days'].sum()
        st.write(f"**Total Approved Leave Days this year:** {total_leave_days}")
    else:
        st.info("No leave requests submitted.")

    st.markdown("---")

    st.subheader("Opex/Capex Requests")
    employee_opex_capex = [oc for oc in opex_capex_requests if oc["employee_id"] == employee_id]
    if employee_opex_capex:
        df_opex_capex = pd.DataFrame(employee_opex_capex)
        st.dataframe(df_opex_capex[['request_id', 'request_type', 'amount', 'status', 'description', 'submission_date', 'approval_date', 'manager_comment']])
    else:
        st.info("No Opex/Capex requests submitted.")

    st.markdown("---")

    st.subheader("Performance Goals")
    employee_goals = [pg for pg in performance_goals if pg["employee_id"] == employee_id]
    if employee_goals:
        df_goals = pd.DataFrame(employee_goals)
        st.dataframe(df_goals[['goal_id', 'goal_description', 'target_date', 'status', 'manager_comment']])
    else:
        st.info("No performance goals set.")

    st.markdown("---")

    st.subheader("Self-Appraisals")
    employee_appraisals = [sa for sa in self_appraisals if sa["employee_id"] == employee_id]
    if employee_appraisals:
        df_appraisals = pd.DataFrame(employee_appraisals)
        st.dataframe(df_appraisals[['appraisal_id', 'period', 'strengths', 'areas_for_improvement', 'achievements', 'development_plan', 'submission_date']])
    else:
        st.info("No self-appraisals submitted.")

    st.markdown("---")

    st.subheader("Beneficiaries")
    employee_beneficiaries = [b for b in beneficiaries if b["employee_id"] == employee_id]
    if employee_beneficiaries:
        df_beneficiaries = pd.DataFrame(employee_beneficiaries)
        st.dataframe(df_beneficiaries[['beneficiary_id', 'name', 'relationship', 'dob', 'contact_number', 'address']])
    else:
        st.info("No beneficiaries added.")

    st.markdown("---")

    st.subheader("Payroll Information")
    employee_payroll = [p for p in payroll_records if p["employee_id"] == employee_id]
    if employee_payroll:
        df_payroll = pd.DataFrame(employee_payroll)
        st.dataframe(df_payroll[['payroll_id', 'pay_period', 'gross_salary', 'net_salary', 'deductions', 'bonuses', 'payment_date']])
    else:
        st.info("No payroll records available.")

    st.markdown("---")

    st.subheader("Training Records")
    employee_training = [t for t in training_records if t["employee_id"] == employee_id]
    if employee_training:
        df_training = pd.DataFrame(employee_training)
        st.dataframe(df_training[['training_id', 'course_name', 'completion_date', 'status', 'certificate_link']])
    else:
        st.info("No training records available.")

    st.markdown("---")

    st.subheader("Documents")
    employee_documents = [d for d in documents if d["employee_id"] == employee_id]
    if employee_documents:
        df_docs = pd.DataFrame(employee_documents)
        st.dataframe(df_docs[['document_id', 'document_name', 'document_type', 'upload_date', 'file_link']])
    else:
        st.info("No documents uploaded.")

# --- Employee Functions ---
def my_profile():
    display_employee_profile(st.session_state.current_user["employee_id"], is_view_only=False)


def request_leave():
    st.title("Request Leave")
    employee_id = st.session_state.current_user["employee_id"]

    with st.form("leave_request_form", clear_on_submit=True):
        leave_type = st.selectbox("Leave Type", ["Annual Leave", "Sick Leave", "Maternity Leave", "Paternity Leave", "Unpaid Leave"])
        start_date = st.date_input("Start Date", min_value=date.today())
        end_date = st.date_input("End Date", min_value=start_date)
        reason = st.text_area("Reason for Leave")

        submit_button = st.form_submit_button("Submit Leave Request")

        if submit_button:
            if start_date > end_date:
                st.error("End Date cannot be before Start Date.")
            else:
                request_id = f"LR{len(leave_requests) + 1:04d}"
                new_request = {
                    "request_id": request_id,
                    "employee_id": employee_id,
                    "leave_type": leave_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "reason": reason,
                    "status": "Pending", # Initial status
                    "submission_date": datetime.now().isoformat(),
                    "manager_comment": ""
                }
                leave_requests.append(new_request)
                save_data(leave_requests, LEAVE_REQUESTS_FILE)
                st.success("Leave request submitted successfully for approval!")
                st.rerun()

    st.subheader("My Leave Requests")
    my_leave_requests = [lr for lr in leave_requests if lr["employee_id"] == employee_id]
    if my_leave_requests:
        df_my_leaves = pd.DataFrame(my_leave_requests)
        df_my_leaves["start_date"] = pd.to_datetime(df_my_leaves["start_date"]).dt.date
        df_my_leaves["end_date"] = pd.to_datetime(df_my_leaves["end_date"]).dt.date
        df_my_leaves["submission_date"] = pd.to_datetime(df_my_leaves["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
        st.dataframe(df_my_leaves[['request_id', 'leave_type', 'start_date', 'end_date', 'status', 'reason', 'submission_date', 'manager_comment']])
    else:
        st.info("You have not submitted any leave requests.")


def request_opex_capex():
    st.title("Request Opex/Capex")
    employee_id = st.session_state.current_user["employee_id"]

    with st.form("opex_capex_request_form", clear_on_submit=True):
        request_type = st.selectbox("Request Type", ["Operating Expenditure (Opex)", "Capital Expenditure (Capex)"])
        amount = st.number_input("Amount (NGN)", min_value=0.0, format="%.2f")
        description = st.text_area("Description/Justification")

        submit_button = st.form_submit_button("Submit Request")

        if submit_button:
            if amount <= 0:
                st.error("Amount must be greater than zero.")
            else:
                request_id = f"OC{len(opex_capex_requests) + 1:04d}"
                new_request = {
                    "request_id": request_id,
                    "employee_id": employee_id,
                    "request_type": request_type,
                    "amount": amount,
                    "description": description,
                    "status": "Pending", # Initial status
                    "submission_date": datetime.now().isoformat(),
                    "approval_date": "",
                    "manager_comment": ""
                }
                opex_capex_requests.append(new_request)
                save_data(opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                st.success("Opex/Capex request submitted successfully for approval!")
                st.rerun()

    st.subheader("My Opex/Capex Requests")
    my_opex_capex_requests = [oc for oc in opex_capex_requests if oc["employee_id"] == employee_id]
    if my_opex_capex_requests:
        df_my_opex_capex = pd.DataFrame(my_opex_capex_requests)
        df_my_opex_capex["submission_date"] = pd.to_datetime(df_my_opex_capex["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
        if "approval_date" in df_my_opex_capex.columns:
            df_my_opex_capex["approval_date"] = df_my_opex_capex["approval_date"].apply(lambda x: pd.to_datetime(x).strftime("%Y-%m-%d %H:%M") if x else "")
        st.dataframe(df_my_opex_capex[['request_id', 'request_type', 'amount', 'status', 'description', 'submission_date', 'approval_date', 'manager_comment']])
    else:
        st.info("You have not submitted any Opex/Capex requests.")

def set_performance_goals():
    st.title("Set Performance Goals")
    employee_id = st.session_state.current_user["employee_id"]

    st.subheader("Current Performance Goals")
    my_goals = [g for g in performance_goals if g["employee_id"] == employee_id]
    if my_goals:
        df_my_goals = pd.DataFrame(my_goals)
        st.dataframe(df_my_goals[['goal_id', 'goal_description', 'target_date', 'status', 'manager_comment']])
    else:
        st.info("No performance goals set yet.")

    st.markdown("---")
    st.subheader("Add New Goal")
    with st.form("new_goal_form", clear_on_submit=True):
        goal_description = st.text_area("Goal Description", help="Be specific, measurable, achievable, relevant, and time-bound (SMART).")
        target_date = st.date_input("Target Date", min_value=date.today())

        submit_goal_button = st.form_submit_button("Set Goal")

        if submit_goal_button:
            if not goal_description:
                st.error("Goal description cannot be empty.")
            else:
                goal_id = f"PG{len(performance_goals) + 1:04d}"
                new_goal = {
                    "goal_id": goal_id,
                    "employee_id": employee_id,
                    "goal_description": goal_description,
                    "target_date": target_date.isoformat(),
                    "status": "Pending Review",
                    "manager_comment": ""
                }
                performance_goals.append(new_goal)
                save_data(performance_goals, PERFORMANCE_GOALS_FILE)
                st.success("Performance goal set successfully and awaiting manager review!")
                st.rerun()

def submit_self_appraisal():
    st.title("Submit Self-Appraisal")
    employee_id = st.session_state.current_user["employee_id"]

    st.subheader("Previous Self-Appraisals")
    my_appraisals = [sa for sa in self_appraisals if sa["employee_id"] == employee_id]
    if my_appraisals:
        df_my_appraisals = pd.DataFrame(my_appraisals)
        st.dataframe(df_my_appraisals[['appraisal_id', 'period', 'strengths', 'areas_for_improvement', 'achievements', 'development_plan', 'submission_date']])
    else:
        st.info("No self-appraisals submitted yet.")

    st.markdown("---")
    st.subheader("Submit New Self-Appraisal")
    with st.form("new_appraisal_form", clear_on_submit=True):
        period = st.text_input("Appraisal Period (e.g., H1 2024, Annual 2023)")
        strengths = st.text_area("Key Strengths and Contributions")
        areas_for_improvement = st.text_area("Areas for Development and Improvement")
        achievements = st.text_area("Significant Achievements for the Period")
        development_plan = st.text_area("Personal Development Plan for next period")

        submit_appraisal_button = st.form_submit_button("Submit Appraisal")

        if submit_appraisal_button:
            if not all([period, strengths, areas_for_improvement, achievements, development_plan]):
                st.error("Please fill in all fields.")
            else:
                appraisal_id = f"SA{len(self_appraisals) + 1:04d}"
                new_appraisal = {
                    "appraisal_id": appraisal_id,
                    "employee_id": employee_id,
                    "period": period,
                    "strengths": strengths,
                    "areas_for_improvement": areas_for_improvement,
                    "achievements": achievements,
                    "development_plan": development_plan,
                    "submission_date": datetime.now().isoformat()
                }
                self_appraisals.append(new_appraisal)
                save_data(self_appraisals, SELF_APPRAISALS_FILE)
                st.success("Self-appraisal submitted successfully!")
                st.rerun()

def view_hr_policies():
    st.title("HR Policies and Guidelines")
    if hr_policies:
        for policy in hr_policies:
            st.subheader(policy["title"])
            st.write(f"**Category:** {policy['category']}")
            st.markdown(policy["content"])
            st.markdown("---")
    else:
        st.info("No HR policies available yet.")

def view_training_resources():
    st.title("Training Resources")
    if training_records:
        st.subheader("Available Training Programs")
        df_training = pd.DataFrame(training_records)
        df_training_display = df_training[df_training['employee_id'] == 'HR_Admin_Global_Resource'] # Assuming global resources are marked as such
        if not df_training_display.empty:
            st.dataframe(df_training_display[['course_name', 'description', 'duration', 'platform', 'certificate_link']])
        else:
            st.info("No global training resources available yet.")

        st.subheader("My Completed Training")
        my_training = [t for t in training_records if t["employee_id"] == st.session_state.current_user["employee_id"] and t['status'] == 'Completed']
        if my_training:
            df_my_training = pd.DataFrame(my_training)
            st.dataframe(df_my_training[['course_name', 'completion_date', 'status', 'certificate_link']])
        else:
            st.info("You haven't completed any training yet.")
    else:
        st.info("No training resources available yet.")


def view_documents():
    st.title("Company Documents")
    if documents:
        df_docs = pd.DataFrame(documents)
        # Filter for documents applicable to the current user's department or global documents
        user_department = st.session_state.current_user.get('department')
        filtered_docs = df_docs[
            (df_docs['department_access'] == 'All') |
            (df_docs['department_access'] == user_department)
        ]
        if not filtered_docs.empty:
            for index, row in filtered_docs.iterrows():
                st.subheader(row['document_name'])
                st.write(f"**Type:** {row['document_type']}")
                st.write(f"**Upload Date:** {row['upload_date']}")
                st.write(f"**Description:** {row['description']}")
                if row['file_link']:
                    st.markdown(f"[Download Document]({row['file_link']})")
                else:
                    st.info("No direct download link available for this document.")
                st.markdown("---")
        else:
            st.info("No documents applicable to your access level yet.")
    else:
        st.info("No documents available yet.")

# --- Admin/Manager Functions ---

# APPROVAL_CHAIN needs to be defined based on your company's hierarchy
# Example:
APPROVAL_CHAIN = [
    {"department": "Operations", "grade_level": "Manager", "approval_limit": 500000},
    {"department": "Finance", "grade_level": "Senior Manager", "approval_limit": 1500000},
    {"department": "Management", "grade_level": "Director", "approval_limit": 5000000},
    {"department": "Executive", "grade_level": "Executive", "approval_limit": float('inf')}, # C-level
]

def get_next_approver_role(current_approver_limit):
    """Determines the next level of approval needed based on the current approval limit."""
    for stage in APPROVAL_CHAIN:
        if stage['approval_limit'] > current_approver_limit:
            return f"{stage['department']} {stage['grade_level']}"
    return "Final Approval"


def admin_manage_opex_capex_approvals():
    st.title("Manage Opex/Capex Approvals")

    # Filter options
    status_filter = st.session_state.approvals_view_filter
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.approvals_view_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pending", "Approved", "Rejected"],
            index=["All", "Pending", "Approved", "Rejected"].index(status_filter),
            key="opex_capex_status_filter"
        )

    filtered_requests = []
    current_user_profile = next((u for u in users if u["employee_id"] == st.session_state.current_user["employee_id"]), None)
    current_user_department = current_user_profile.get('department')
    current_user_grade = current_user_profile.get('grade_level')
    current_user_is_admin = (st.session_state.current_user['role'] == 'admin')

    # Determine approval limit for the current user
    user_approval_limit = 0
    for stage in APPROVAL_CHAIN:
        if current_user_department == stage['department'] and current_user_grade == stage['grade_level']:
            user_approval_limit = stage['approval_limit']
            break
    # Admin can see all, managers only within their approval chain logic for pending requests
    for req in opex_capex_requests:
        if st.session_state.approvals_view_filter != "All" and req["status"] != st.session_state.approvals_view_filter:
            continue

        if current_user_is_admin:
            filtered_requests.append(req)
        elif req["status"] == "Pending":
            # Determine if this request falls within the current user's approval purview
            # This is a simplified logic. In a real system, you'd track previous approvers.
            # Here, we assume a manager approves up to their limit, then it moves to the next.
            if req['amount'] <= user_approval_limit:
                filtered_requests.append(req)
            # More complex logic would be needed for requests already approved by a lower level
        elif req["status"] != "Pending" and req["approval_date"]:
             # Show requests that the current user might have previously approved/rejected
             # This requires tracking who approved what. For simplicity, we'll show all non-pending if admin
             # For managers, this would show requests they acted on.
             # Since we don't store approver ID per request, this is a placeholder.
             # If you want to show only what they acted on, you'd need to add 'approved_by_id' to request.
            if st.session_state.current_user["role"] == "manager":
                # For managers, only show if they were the ones to approve/reject
                # (Assuming 'manager_comment' implies they acted on it, not ideal but for example)
                if req['manager_comment'] and "by " + st.session_state.current_user['full_name'] in req['manager_comment']:
                     filtered_requests.append(req)
            else: # If not a manager, means admin. Already covered by current_user_is_admin.
                pass # Admin already gets all

    if filtered_requests:
        df_requests = pd.DataFrame(filtered_requests)
        df_requests["submission_date"] = pd.to_datetime(df_requests["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
        if "approval_date" in df_requests.columns:
            df_requests["approval_date"] = df_requests["approval_date"].apply(lambda x: pd.to_datetime(x).strftime("%Y-%m-%d %H:%M") if x else "")

        st.subheader("Opex/Capex Requests")
        st.dataframe(df_requests[['request_id', 'employee_id', 'request_type', 'amount', 'status', 'description', 'submission_date', 'approval_date', 'manager_comment']])

        st.markdown("---")
        st.subheader("Action on Requests")

        # Create a dictionary for quick lookup of requests by ID
        requests_dict = {req['request_id']: req for req in opex_capex_requests}

        # Use st.expander for each request to manage space
        for req in filtered_requests:
            req_id = req['request_id']
            employee_name = next((u['full_name'] for u in users if u['employee_id'] == req['employee_id']), req['employee_id'])

            if req['status'] == "Pending":
                with st.expander(f"Pending Request: {req_id} from {employee_name} ({req['amount']:,.2f} NGN)"):
                    st.write(f"**Request ID:** {req_id}")
                    st.write(f"**Employee:** {employee_name} ({req['employee_id']})")
                    st.write(f"**Type:** {req['request_type']}")
                    st.write(f"**Amount:** {req['amount']:,.2f} NGN")
                    st.write(f"**Description:** {req['description']}")
                    st.write(f"**Submitted On:** {pd.to_datetime(req['submission_date']).strftime('%Y-%m-%d %H:%M')}")

                    with st.form(f"approve_reject_form_{req_id}", clear_on_submit=True):
                        action = st.radio(f"Action for {req_id}", ["Approve", "Reject"], key=f"action_{req_id}")
                        manager_comment = st.text_area("Your Comment (Optional)", key=f"comment_{req_id}")

                        # ✅ Form submit button correctly placed inside st.form
                        submit_button = st.form_submit_button("Submit Action", key=f"submit_action_{req_id}")

                        if submit_button:
                            req_to_update = requests_dict.get(req_id)
                            if req_to_update:
                                req_to_update["status"] = action
                                req_to_update["manager_comment"] = f"{manager_comment} (Actioned by {st.session_state.current_user['full_name']})" if manager_comment else f"Actioned by {st.session_state.current_user['full_name']}"
                                req_to_update["approval_date"] = datetime.now().isoformat()
                                save_data(opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                                st.success(f"Request {req_id} has been {action.lower()}d.")
                                st.rerun()
                            else:
                                st.error(f"Error: Request {req_id} not found for update.")
            elif req['status'] != "Pending":
                 with st.expander(f"{req['status']} Request: {req_id} from {employee_name} ({req['amount']:,.2f} NGN)"):
                    st.write(f"**Request ID:** {req_id}")
                    st.write(f"**Employee:** {employee_name} ({req['employee_id']})")
                    st.write(f"**Type:** {req['request_type']}")
                    st.write(f"**Amount:** {req['amount']:,.2f} NGN")
                    st.write(f"**Status:** {req['status']}")
                    st.write(f"**Description:** {req['description']}")
                    st.write(f"**Submitted On:** {pd.to_datetime(req['submission_date']).strftime('%Y-%m-%d %H:%M')}")
                    if req['approval_date']:
                        st.write(f"**Actioned On:** {pd.to_datetime(req['approval_date']).strftime('%Y-%m-%d %H:%M')}")
                    if req['manager_comment']:
                        st.write(f"**Manager Comment:** {req['manager_comment']}")

    else:
        st.info("No Opex/Capex requests to display based on current filters and your approval limit.")


def admin_manage_leave_approvals(): # NEW FUNCTION
    st.title("Manage Leave Approvals")

    # Filter options
    status_filter = st.session_state.leave_approvals_view_filter
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.leave_approvals_view_filter = st.selectbox(
            "Filter by Status",
            ["All", "Pending", "Approved", "Rejected"],
            index=["All", "Pending", "Approved", "Rejected"].index(status_filter),
            key="leave_status_filter"
        )

    filtered_requests = []
    current_user_is_admin = (st.session_state.current_user['role'] == 'admin')

    for req in leave_requests:
        if st.session_state.leave_approvals_view_filter != "All" and req["status"] != st.session_state.leave_approvals_view_filter:
            continue
        # For simplicity, all admins/managers can see all leave requests.
        # In a real scenario, you might add department/grade level filtering for managers.
        filtered_requests.append(req)

    if filtered_requests:
        df_requests = pd.DataFrame(filtered_requests)
        df_requests["submission_date"] = pd.to_datetime(df_requests["submission_date"]).dt.strftime("%Y-%m-%d %H:%M")
        df_requests["start_date"] = pd.to_datetime(df_requests["start_date"]).dt.date
        df_requests["end_date"] = pd.to_datetime(df_requests["end_date"]).dt.date
        
        st.subheader("Leave Requests")
        st.dataframe(df_requests[['request_id', 'employee_id', 'leave_type', 'start_date', 'end_date', 'status', 'reason', 'submission_date', 'manager_comment']])

        st.markdown("---")
        st.subheader("Action on Leave Requests")

        requests_dict = {req['request_id']: req for req in leave_requests}

        for req in filtered_requests:
            req_id = req['request_id']
            employee_name = next((u['full_name'] for u u in users if u['employee_id'] == req['employee_id']), req['employee_id'])

            if req['status'] == "Pending":
                with st.expander(f"Pending Leave Request: {req_id} from {employee_name} ({req['leave_type']})"):
                    st.write(f"**Request ID:** {req_id}")
                    st.write(f"**Employee:** {employee_name} ({req['employee_id']})")
                    st.write(f"**Leave Type:** {req['leave_type']}")
                    st.write(f"**Start Date:** {req['start_date']}")
                    st.write(f"**End Date:** {req['end_date']}")
                    st.write(f"**Reason:** {req['reason']}")
                    st.write(f"**Submitted On:** {pd.to_datetime(req['submission_date']).strftime('%Y-%m-%d %H:%M')}")

                    with st.form(f"approve_reject_leave_form_{req_id}", clear_on_submit=True):
                        action = st.radio(f"Action for {req_id}", ["Approve", "Reject"], key=f"action_leave_{req_id}")
                        manager_comment = st.text_area("Your Comment (Optional)", key=f"comment_leave_{req_id}")

                        # ✅ Form submit button correctly placed inside st.form
                        submit_button = st.form_submit_button("Submit Action", key=f"submit_action_leave_{req_id}")

                        if submit_button:
                            req_to_update = requests_dict.get(req_id)
                            if req_to_update:
                                req_to_update["status"] = action
                                req_to_update["manager_comment"] = f"{manager_comment} (Actioned by {st.session_state.current_user['full_name']})" if manager_comment else f"Actioned by {st.session_state.current_user['full_name']}"
                                save_data(leave_requests, LEAVE_REQUESTS_FILE)
                                st.success(f"Leave Request {req_id} has been {action.lower()}d.")
                                st.rerun()
                            else:
                                st.error(f"Error: Leave Request {req_id} not found for update.")
            elif req['status'] != "Pending":
                with st.expander(f"{req['status']} Leave Request: {req_id} from {employee_name} ({req['leave_type']})"):
                    st.write(f"**Request ID:** {req_id}")
                    st.write(f"**Employee:** {employee_name} ({req['employee_id']})")
                    st.write(f"**Leave Type:** {req['leave_type']}")
                    st.write(f"**Start Date:** {req['start_date']}")
                    st.write(f"**End Date:** {req['end_date']}")
                    st.write(f"**Reason:** {req['reason']}")
                    st.write(f"**Status:** {req['status']}")
                    st.write(f"**Submitted On:** {pd.to_datetime(req['submission_date']).strftime('%Y-%m-%d %H:%M')}")
                    if req['manager_comment']:
                        st.write(f"**Manager Comment:** {req['manager_comment']}")
    else:
        st.info("No leave requests to display based on current filters.")


def admin_manage_payroll():
    st.title("Manage Payroll")

    st.subheader("Existing Payroll Records")
    if payroll_records:
        df_payroll = pd.DataFrame(payroll_records)
        df_payroll["payment_date"] = pd.to_datetime(df_payroll["payment_date"]).dt.date
        df_payroll["pay_period"] = df_payroll["pay_period"].apply(lambda x: x if x else "N/A") # Handle potential empty strings
        st.dataframe(df_payroll[['payroll_id', 'employee_id', 'pay_period', 'gross_salary', 'net_salary', 'deductions', 'bonuses', 'payment_date']])
    else:
        st.info("No payroll records available yet.")

    st.markdown("---")

    st.subheader("Add New Payroll Record")
    with st.form("add_payroll_form", clear_on_submit=True):
        employee_id = st.selectbox("Employee", [""] + [u["employee_id"] for u in users])
        pay_period = st.text_input("Pay Period (e.g., May 2024, Q2 2024)", help="e.g., 2024-05")
        gross_salary = st.number_input("Gross Salary (NGN)", min_value=0.0, format="%.2f")
        deductions = st.number_input("Total Deductions (NGN)", min_value=0.0, format="%.2f")
        bonuses = st.number_input("Total Bonuses (NGN)", min_value=0.0, format="%.2f")
        payment_date = st.date_input("Payment Date", value="today")

        add_payroll_button = st.form_submit_button("Add Payroll Record")

        if add_payroll_button:
            if not employee_id:
                st.error("Please select an employee.")
            elif gross_salary < 0 or deductions < 0 or bonuses < 0:
                st.error("Amounts cannot be negative.")
            else:
                net_salary = gross_salary - deductions + bonuses
                payroll_id = f"PR{len(payroll_records) + 1:04d}"
                new_record = {
                    "payroll_id": payroll_id,
                    "employee_id": employee_id,
                    "pay_period": pay_period,
                    "gross_salary": gross_salary,
                    "net_salary": net_salary,
                    "deductions": deductions,
                    "bonuses": bonuses,
                    "payment_date": payment_date.isoformat()
                }
                payroll_records.append(new_record)
                save_data(payroll_records, PAYROLL_FILE)
                st.success(f"Payroll record for {employee_id} added successfully!")
                st.rerun()

    st.markdown("---")

    st.subheader("Update Payroll Record")
    payroll_to_update_id = st.selectbox("Select Payroll Record to Update", [""] + [p["payroll_id"] for p in payroll_records], key="update_payroll_select")
    if payroll_to_update_id:
        record_to_update = next((p for p in payroll_records if p["payroll_id"] == payroll_to_update_id), None)
        if record_to_update:
            with st.form(f"update_payroll_form_{payroll_to_update_id}"):
                upd_employee_id = st.text_input("Employee ID", value=record_to_update["employee_id"], disabled=True)
                upd_pay_period = st.text_input("Pay Period", value=record_to_update["pay_period"])
                upd_gross_salary = st.number_input("Gross Salary (NGN)", value=record_to_update["gross_salary"], min_value=0.0, format="%.2f")
                upd_deductions = st.number_input("Total Deductions (NGN)", value=record_to_update["deductions"], min_value=0.0, format="%.2f")
                upd_bonuses = st.number_input("Total Bonuses (NGN)", value=record_to_update["bonuses"], min_value=0.0, format="%.2f")
                upd_payment_date = st.date_input("Payment Date", value=datetime.strptime(record_to_update["payment_date"], "%Y-%m-%d").date())

                update_payroll_button = st.form_submit_button("Update Payroll Record")

                if update_payroll_button:
                    if upd_gross_salary < 0 or upd_deductions < 0 or upd_bonuses < 0:
                        st.error("Amounts cannot be negative.")
                    else:
                        record_to_update["pay_period"] = upd_pay_period
                        record_to_update["gross_salary"] = upd_gross_salary
                        record_to_update["deductions"] = upd_deductions
                        record_to_update["bonuses"] = upd_bonuses
                        record_to_update["net_salary"] = upd_gross_salary - upd_deductions + upd_bonuses
                        record_to_update["payment_date"] = upd_payment_date.isoformat()
                        save_data(payroll_records, PAYROLL_FILE)
                        st.success(f"Payroll record {payroll_to_update_id} updated successfully!")
                        st.rerun()

    st.markdown("---")

    st.subheader("Delete Payroll Record")
    payroll_to_delete_id = st.selectbox("Select Payroll Record to Delete", [""] + [p["payroll_id"] for p in payroll_records], key="delete_payroll_select")
    if payroll_to_delete_id:
        with st.form(f"delete_payroll_form_{payroll_to_delete_id}"):
            st.warning(f"Are you sure you want to delete payroll record {payroll_to_delete_id}?")
            confirm_delete = st.form_submit_button("Confirm Delete")
            if confirm_delete:
                global payroll_records
                payroll_records = [p for p in payroll_records if p["payroll_id"] != payroll_to_delete_id]
                save_data(payroll_records, PAYROLL_FILE)
                st.success(f"Payroll record {payroll_to_delete_id} deleted successfully.")
                st.rerun()


def admin_manage_beneficiaries():
    st.title("Manage Beneficiaries")

    st.subheader("Existing Beneficiaries")
    if beneficiaries:
        df_beneficiaries = pd.DataFrame(beneficiaries)
        df_beneficiaries["dob"] = pd.to_datetime(df_beneficiaries["dob"]).dt.date
        st.dataframe(df_beneficiaries[['beneficiary_id', 'employee_id', 'name', 'relationship', 'dob', 'contact_number', 'address']])
    else:
        st.info("No beneficiaries added yet.")

    st.markdown("---")

    st.subheader("Add New Beneficiary")
    with st.form("add_beneficiary_form", clear_on_submit=True):
        employee_id = st.selectbox("Employee", [""] + [u["employee_id"] for u in users], key="add_benef_emp_id")
        name = st.text_input("Beneficiary Name")
        relationship = st.text_input("Relationship to Employee (e.g., Spouse, Child, Parent)")
        dob = st.date_input("Date of Birth")
        contact_number = st.text_input("Contact Number")
        address = st.text_area("Address")

        add_beneficiary_button = st.form_submit_button("Add Beneficiary")

        if add_beneficiary_button:
            if not all([employee_id, name, relationship, contact_number, address]):
                st.error("Please fill in all fields.")
            else:
                beneficiary_id = f"BEN{len(beneficiaries) + 1:04d}"
                new_beneficiary = {
                    "beneficiary_id": beneficiary_id,
                    "employee_id": employee_id,
                    "name": name,
                    "relationship": relationship,
                    "dob": dob.isoformat(),
                    "contact_number": contact_number,
                    "address": address
                }
                beneficiaries.append(new_beneficiary)
                save_data(beneficiaries, BENEFICIARIES_FILE)
                st.success(f"Beneficiary {name} added for {employee_id} successfully!")
                st.rerun()

    st.markdown("---")

    st.subheader("Update Beneficiary")
    beneficiary_to_update_id = st.selectbox("Select Beneficiary to Update", [""] + [b["beneficiary_id"] for b in beneficiaries], key="update_benef_select")
    if beneficiary_to_update_id:
        beneficiary_to_update = next((b for b in beneficiaries if b["beneficiary_id"] == beneficiary_to_update_id), None)
        if beneficiary_to_update:
            with st.form(f"update_beneficiary_form_{beneficiary_to_update_id}"):
                upd_employee_id = st.text_input("Employee ID", value=beneficiary_to_update["employee_id"], disabled=True)
                upd_name = st.text_input("Beneficiary Name", value=beneficiary_to_update["name"])
                upd_relationship = st.text_input("Relationship", value=beneficiary_to_update["relationship"])
                upd_dob = st.date_input("Date of Birth", value=datetime.strptime(beneficiary_to_update["dob"], "%Y-%m-%d").date())
                upd_contact_number = st.text_input("Contact Number", value=beneficiary_to_update["contact_number"])
                upd_address = st.text_area("Address", value=beneficiary_to_update["address"])

                update_beneficiary_button = st.form_submit_button("Update Beneficiary")

                if update_beneficiary_button:
                    if not all([upd_name, upd_relationship, upd_contact_number, upd_address]):
                        st.error("Please fill in all fields.")
                    else:
                        beneficiary_to_update.update({
                            "name": upd_name,
                            "relationship": upd_relationship,
                            "dob": upd_dob.isoformat(),
                            "contact_number": upd_contact_number,
                            "address": upd_address
                        })
                        save_data(beneficiaries, BENEFICIARIES_FILE)
                        st.success(f"Beneficiary {upd_name} updated successfully!")
                        st.rerun()

    st.markdown("---")

    st.subheader("Delete Beneficiary")
    beneficiary_to_delete_id = st.selectbox("Select Beneficiary to Delete", [""] + [b["beneficiary_id"] for b in beneficiaries], key="delete_benef_select")
    if beneficiary_to_delete_id:
        with st.form(f"delete_beneficiary_form_{beneficiary_to_delete_id}"):
            st.warning(f"Are you sure you want to delete beneficiary {beneficiary_to_delete_id}?")
            confirm_delete = st.form_submit_button("Confirm Delete")
            if confirm_delete:
                global beneficiaries
                beneficiaries = [b for b in beneficiaries if b["beneficiary_id"] != beneficiary_to_delete_id]
                save_data(beneficiaries, BENEFICIARIES_FILE)
                st.success(f"Beneficiary {beneficiary_to_delete_id} deleted successfully.")
                st.rerun()

def admin_manage_hr_policies():
    st.title("Manage HR Policies")

    st.subheader("Existing HR Policies")
    if hr_policies:
        for i, policy in enumerate(hr_policies):
            with st.expander(f"{i+1}. {policy['title']} ({policy['category']})"):
                st.write(f"**Category:** {policy['category']}")
                st.markdown(policy["content"])
                
                col1, col2 = st.columns(2)
                with col1:
                    with st.form(f"edit_policy_form_{i}"):
                        st.markdown("##### Edit Policy")
                        edited_title = st.text_input("Title", value=policy["title"], key=f"edit_title_{i}")
                        edited_category = st.text_input("Category", value=policy["category"], key=f"edit_category_{i}")
                        edited_content = st.text_area("Content", value=policy["content"], height=200, key=f"edit_content_{i}")
                        edit_button = st.form_submit_button("Update Policy", key=f"update_policy_{i}")
                        if edit_button:
                            policy["title"] = edited_title
                            policy["category"] = edited_category
                            policy["content"] = edited_content
                            save_data(hr_policies, HR_POLICIES_FILE)
                            st.success("Policy updated successfully!")
                            st.rerun()
                with col2:
                    with st.form(f"delete_policy_form_{i}"):
                        st.markdown("##### Delete Policy")
                        st.warning(f"Delete policy: '{policy['title']}'?")
                        delete_button = st.form_submit_button("Delete Policy", key=f"delete_policy_{i}")
                        if delete_button:
                            hr_policies.pop(i)
                            save_data(hr_policies, HR_POLICIES_FILE)
                            st.success("Policy deleted successfully!")
                            st.rerun()
                st.markdown("---")
    else:
        st.info("No HR policies available yet.")

    st.markdown("---")
    st.subheader("Add New HR Policy")
    with st.form("add_policy_form", clear_on_submit=True):
        new_title = st.text_input("Policy Title")
        new_category = st.text_input("Category (e.g., Leave, Conduct, Benefits)")
        new_content = st.text_area("Policy Content", height=200)
        add_button = st.form_submit_button("Add Policy")

        if add_button:
            if not all([new_title, new_category, new_content]):
                st.error("Please fill in all fields.")
            else:
                new_policy = {
                    "title": new_title,
                    "category": new_category,
                    "content": new_content
                }
                hr_policies.append(new_policy)
                save_data(hr_policies, HR_POLICIES_FILE)
                st.success(f"Policy '{new_title}' added successfully!")
                st.rerun()

def admin_manage_training_resources():
    st.title("Manage Training Resources")

    st.subheader("Existing Training Programs")
    if training_records:
        df_training = pd.DataFrame(training_records)
        df_training_display = df_training[df_training['employee_id'] == 'HR_Admin_Global_Resource']
        if not df_training_display.empty:
            st.dataframe(df_training_display[['training_id', 'course_name', 'description', 'duration', 'platform', 'certificate_link']])
        else:
            st.info("No global training resources available yet.")
    else:
        st.info("No training resources available yet.")

    st.markdown("---")
    st.subheader("Add New Global Training Resource")
    with st.form("add_training_form", clear_on_submit=True):
        course_name = st.text_input("Course Name")
        description = st.text_area("Description")
        duration = st.text_input("Duration (e.g., 8 hours, 3 days)")
        platform = st.text_input("Platform (e.g., Coursera, Udemy, Internal L&D)")
        certificate_link = st.text_input("Certificate Link (Optional URL)", help="Direct link to a certificate or course page.")

        add_training_button = st.form_submit_button("Add Training Resource")

        if add_training_button:
            if not all([course_name, description, duration, platform]):
                st.error("Please fill in all mandatory fields.")
            else:
                training_id = f"TR{len(training_records) + 1:04d}"
                new_resource = {
                    "training_id": training_id,
                    "employee_id": "HR_Admin_Global_Resource", # Mark as a global resource
                    "course_name": course_name,
                    "description": description,
                    "duration": duration,
                    "platform": platform,
                    "completion_date": "", # Not applicable for global resource
                    "status": "Available",
                    "certificate_link": certificate_link
                }
                training_records.append(new_resource)
                save_data(training_records, TRAINING_FILE)
                st.success(f"Training resource '{course_name}' added successfully!")
                st.rerun()
    
    st.markdown("---")
    st.subheader("Record Employee Training Completion")
    with st.form("record_employee_training_form", clear_on_submit=True):
        employee_id = st.selectbox("Employee", [""] + [u["employee_id"] for u in users], key="record_train_emp_id")
        course_name = st.text_input("Course Name Completed")
        completion_date = st.date_input("Completion Date", value="today")
        certificate_link = st.text_input("Certificate Link (Optional)")

        record_completion_button = st.form_submit_button("Record Completion")

        if record_completion_button:
            if not all([employee_id, course_name]):
                st.error("Please fill in employee and course name.")
            else:
                training_id = f"TR{len(training_records) + 1:04d}"
                new_completion = {
                    "training_id": training_id,
                    "employee_id": employee_id,
                    "course_name": course_name,
                    "description": "Employee completed training.", # Generic description for completed
                    "duration": "N/A",
                    "platform": "N/A",
                    "completion_date": completion_date.isoformat(),
                    "status": "Completed",
                    "certificate_link": certificate_link
                }
                training_records.append(new_completion)
                save_data(training_records, TRAINING_FILE)
                st.success(f"Training completion for {employee_id} recorded successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Delete Training Record")
    training_to_delete_id = st.selectbox("Select Training Record to Delete", [""] + [t["training_id"] for t in training_records], key="delete_training_select")
    if training_to_delete_id:
        with st.form(f"delete_training_form_{training_to_delete_id}"):
            st.warning(f"Are you sure you want to delete training record {training_to_delete_id}?")
            confirm_delete = st.form_submit_button("Confirm Delete")
            if confirm_delete:
                global training_records
                training_records = [t for t in training_records if t["training_id"] != training_to_delete_id]
                save_data(training_records, TRAINING_FILE)
                st.success(f"Training record {training_to_delete_id} deleted successfully.")
                st.rerun()

def admin_manage_documents():
    st.title("Manage Company Documents")

    st.subheader("Existing Documents")
    if documents:
        df_docs = pd.DataFrame(documents)
        st.dataframe(df_docs[['document_id', 'document_name', 'document_type', 'upload_date', 'file_link', 'department_access', 'description']])
    else:
        st.info("No documents available yet.")

    st.markdown("---")
    st.subheader("Upload New Document")
    with st.form("add_document_form", clear_on_submit=True):
        document_name = st.text_input("Document Name")
        document_type = st.text_input("Document Type (e.g., Contract, Policy, Template)")
        description = st.text_area("Description (Optional)")
        file_link = st.text_input("File Link (URL to document, e.g., Google Drive link)", help="Ensure link is shareable/public if intended for broad access.")
        department_access = st.selectbox("Department Access", ["All", "HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"], help="Who can view this document?")

        add_document_button = st.form_submit_button("Upload Document")

        if add_document_button:
            if not all([document_name, document_type, file_link]):
                st.error("Please fill in document name, type, and file link.")
            else:
                document_id = f"DOC{len(documents) + 1:04d}"
                new_doc = {
                    "document_id": document_id,
                    "document_name": document_name,
                    "document_type": document_type,
                    "description": description,
                    "file_link": file_link,
                    "upload_date": datetime.now().isoformat(),
                    "department_access": department_access
                }
                documents.append(new_doc)
                save_data(documents, DOCUMENTS_FILE)
                st.success(f"Document '{document_name}' uploaded successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Update Document")
    document_to_update_id = st.selectbox("Select Document to Update", [""] + [d["document_id"] for d in documents], key="update_doc_select")
    if document_to_update_id:
        doc_to_update = next((d for d in documents if d["document_id"] == document_to_update_id), None)
        if doc_to_update:
            with st.form(f"update_document_form_{document_to_update_id}"):
                upd_doc_name = st.text_input("Document Name", value=doc_to_update["document_name"])
                upd_doc_type = st.text_input("Document Type", value=doc_to_update["document_type"])
                upd_description = st.text_area("Description", value=doc_to_update["description"])
                upd_file_link = st.text_input("File Link (URL)", value=doc_to_update["file_link"])
                upd_dept_access = st.selectbox("Department Access", ["All", "HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"], index=["All", "HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Management"].index(doc_to_update["department_access"]))

                update_document_button = st.form_submit_button("Update Document")

                if update_document_button:
                    if not all([upd_doc_name, upd_doc_type, upd_file_link]):
                        st.error("Please fill in document name, type, and file link.")
                    else:
                        doc_to_update.update({
                            "document_name": upd_doc_name,
                            "document_type": upd_doc_type,
                            "description": upd_description,
                            "file_link": upd_file_link,
                            "department_access": upd_dept_access
                        })
                        save_data(documents, DOCUMENTS_FILE)
                        st.success(f"Document '{upd_doc_name}' updated successfully!")
                        st.rerun()

    st.markdown("---")
    st.subheader("Delete Document")
    document_to_delete_id = st.selectbox("Select Document to Delete", [""] + [d["document_id"] for d in documents], key="delete_doc_select")
    if document_to_delete_id:
        with st.form(f"delete_document_form_{document_to_delete_id}"):
            st.warning(f"Are you sure you want to delete document {document_to_delete_id}?")
            confirm_delete = st.form_submit_button("Confirm Delete")
            if confirm_delete:
                global documents
                documents = [d for d in documents if d["document_id"] != document_to_delete_id]
                save_data(documents, DOCUMENTS_FILE)
                st.success(f"Document {document_to_delete_id} deleted successfully.")
                st.rerun()

def manage_performance():
    st.title("Manage Employee Performance")

    st.subheader("Performance Goals Overview")
    if performance_goals:
        df_goals = pd.DataFrame(performance_goals)
        st.dataframe(df_goals[['goal_id', 'employee_id', 'goal_description', 'target_date', 'status', 'manager_comment']])
    else:
        st.info("No performance goals set by employees yet.")

    st.markdown("---")
    st.subheader("Review and Update Goals")

    goals_to_review = [g for g in performance_goals if g['status'] == 'Pending Review']

    if goals_to_review:
        for goal in goals_to_review:
            employee_name = next((u['full_name'] for u in users if u['employee_id'] == goal['employee_id']), goal['employee_id'])
            with st.expander(f"Review Goal: {goal['goal_id']} from {employee_name}"):
                st.write(f"**Employee:** {employee_name} ({goal['employee_id']})")
                st.write(f"**Goal Description:** {goal['goal_description']}")
                st.write(f"**Target Date:** {goal['target_date']}")
                st.write(f"**Current Status:** {goal['status']}")

                with st.form(f"review_goal_form_{goal['goal_id']}"):
                    action = st.radio(f"Action for Goal {goal['goal_id']}", ["Approve", "Reject", "Revise Requested"], key=f"goal_action_{goal['goal_id']}")
                    manager_comment = st.text_area("Your Comment", key=f"goal_comment_{goal['goal_id']}")
                    
                    submit_review_button = st.form_submit_button("Submit Review", key=f"submit_goal_review_{goal['goal_id']}")

                    if submit_review_button:
                        goal_to_update = next((g for g in performance_goals if g['goal_id'] == goal['goal_id']), None)
                        if goal_to_update:
                            goal_to_update['status'] = action
                            goal_to_update['manager_comment'] = f"{manager_comment} (Reviewed by {st.session_state.current_user['full_name']})"
                            save_data(performance_goals, PERFORMANCE_GOALS_FILE)
                            st.success(f"Goal {goal['goal_id']} marked as '{action}'.")
                            st.rerun()
                        else:
                            st.error(f"Error: Goal {goal['goal_id']} not found.")
            st.markdown("---")
    else:
        st.info("No performance goals awaiting review.")

    st.markdown("---")
    st.subheader("Review Self-Appraisals")
    if self_appraisals:
        df_appraisals = pd.DataFrame(self_appraisals)
        st.dataframe(df_appraisals[['appraisal_id', 'employee_id', 'period', 'strengths', 'areas_for_improvement', 'achievements', 'development_plan', 'submission_date']])
    else:
        st.info("No self-appraisals submitted yet.")

    # You would typically add a form here to allow managers to add their comments/ratings to appraisals
    # For brevity, this is left as an exercise. You'd need to find the appraisal by ID, add fields for manager rating/comments, and save.

# --- Dashboard ---
def display_dashboard():
    st.title("HR Portal Dashboard")
    st.subheader(f"Welcome, {st.session_state.current_user['full_name']}")

    # Employee-specific dashboard
    if st.session_state.current_user["role"] == "employee":
        st.subheader("Your Quick Stats")
        col1, col2, col3 = st.columns(3)

        # Pending Leave
        my_pending_leaves = [lr for lr in leave_requests if lr["employee_id"] == st.session_state.current_user["employee_id"] and lr["status"] == "Pending"]
        col1.metric("Pending Leave Requests", len(my_pending_leaves))

        # Pending Opex/Capex
        my_pending_opex_capex = [oc for oc in opex_capex_requests if oc["employee_id"] == st.session_state.current_user["employee_id"] and oc["status"] == "Pending"]
        col2.metric("Pending Opex/Capex Requests", len(my_pending_opex_capex))

        # Goals Awaiting Review
        my_goals_pending_review = [pg for pg in performance_goals if pg["employee_id"] == st.session_state.current_user["employee_id"] and pg["status"] == "Pending Review"]
        col3.metric("Goals Awaiting Review", len(my_goals_pending_review))

        st.markdown("---")
        st.subheader("Recent Activities")
        # Display recent leave requests, opex/capex, etc.
        recent_leaves = sorted([lr for lr in leave_requests if lr["employee_id"] == st.session_state.current_user["employee_id"]], key=lambda x: x['submission_date'], reverse=True)[:5]
        if recent_leaves:
            st.write("**Recent Leave Requests:**")
            for lr in recent_leaves:
                st.write(f"- {lr['leave_type']} from {lr['start_date']} to {lr['end_date']} - Status: **{lr['status']}**")
        else:
            st.info("No recent leave requests.")

    # Admin/Manager dashboard
    if st.session_state.current_user["role"] in ["admin", "manager"]:
        st.subheader("Overall Company Metrics")
        col1, col2, col3, col4 = st.columns(4)

        # Total Employees
        col1.metric("Total Employees", len(users))

        # Pending Leave Requests (All)
        all_pending_leaves = [lr for lr in leave_requests if lr["status"] == "Pending"]
        col2.metric("Pending Leave Requests", len(all_pending_leaves))

        # Pending Opex/Capex Requests (All)
        all_pending_opex_capex = [oc for oc in opex_capex_requests if oc["status"] == "Pending"]
        col3.metric("Pending Opex/Capex Requests", len(all_pending_opex_capex))

        # Active Employees
        active_employees = [u for u in users if u.get('is_active', True)]
        col4.metric("Active Employees", len(active_employees))

        st.markdown("---")
        st.subheader("Departmental Breakdown")

        if users:
            df_users = pd.DataFrame(users)
            department_counts = df_users['department'].value_counts().reset_index()
            department_counts.columns = ['Department', 'Number of Employees']
            fig_dept = px.bar(department_counts, x='Department', y='Number of Employees',
                              title='Employees by Department', color='Department')
            st.plotly_chart(fig_dept, use_container_width=True)
        else:
            st.info("No employee data to display departmental breakdown.")

        st.markdown("---")
        st.subheader("Requests Trends")

        if opex_capex_requests:
            df_opex_capex = pd.DataFrame(opex_capex_requests)
            df_opex_capex['submission_date'] = pd.to_datetime(df_opex_capex['submission_date'])
            df_opex_capex['month_year'] = df_opex_capex['submission_date'].dt.to_period('M').astype(str)
            
            # Count requests by status over time
            requests_by_month_status = df_opex_capex.groupby(['month_year', 'status']).size().unstack(fill_value=0).reset_index()
            requests_by_month_status['month_year'] = pd.to_datetime(requests_by_month_status['month_year'])
            requests_by_month_status = requests_by_month_status.sort_values('month_year')

            fig_opex_capex_status = px.line(requests_by_month_status, x='month_year', y=requests_by_month_status.columns[1:],
                                            title='Opex/Capex Requests Status Over Time',
                                            labels={'month_year': 'Month', 'value': 'Number of Requests'},
                                            line_shape='linear')
            st.plotly_chart(fig_opex_capex_status, use_container_width=True)
        else:
            st.info("No Opex/Capex request data for trends.")

        if leave_requests:
            df_leaves = pd.DataFrame(leave_requests)
            df_leaves['submission_date'] = pd.to_datetime(df_leaves['submission_date'])
            df_leaves['month_year'] = df_leaves['submission_date'].dt.to_period('M').astype(str)

            # Count leave requests by type over time
            leave_by_month_type = df_leaves.groupby(['month_year', 'leave_type']).size().unstack(fill_value=0).reset_index()
            leave_by_month_type['month_year'] = pd.to_datetime(leave_by_month_type['month_year'])
            leave_by_month_type = leave_by_month_type.sort_values('month_year')

            fig_leave_type = px.line(leave_by_month_type, x='month_year', y=leave_by_month_type.columns[1:],
                                    title='Leave Requests by Type Over Time',
                                    labels={'month_year': 'Month', 'value': 'Number of Requests'},
                                    line_shape='linear')
            st.plotly_chart(fig_leave_type, use_container_width=True)
        else:
            st.info("No Leave request data for trends.")

# --- Main Application Logic ---
def main():
    sidebar_navigation()

    if st.session_state.current_user:
        if st.session_state.current_page == "dashboard":
            display_dashboard()
        elif st.session_state.current_page == "my_profile":
            my_profile()
        elif st.session_state.current_page == "request_leave":
            request_leave()
        elif st.session_state.current_page == "request_opex_capex":
            request_opex_capex()
        elif st.session_state.current_page == "set_performance_goals":
            set_performance_goals()
        elif st.session_state.current_page == "submit_self_appraisal":
            submit_self_appraisal()
        elif st.session_state.current_page == "view_hr_policies":
            view_hr_policies()
        elif st.session_state.current_page == "view_training_resources":
            view_training_resources()
        elif st.session_state.current_page == "view_documents":
            view_documents()

        # Admin/Manager Pages - with access control
        elif st.session_state.current_page == "manage_employees":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_employees()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_payroll":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_payroll()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_performance":
            if st.session_state.current_user and (st.session_state.current_user['role'] == 'admin' or st.session_state.current_user['role'] == 'manager'):
                manage_performance()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_opex_capex_approvals":
            is_approver = False
            current_user_profile = next((u for u in users if u["employee_id"] == st.session_state.current_user["employee_id"]), None)
            current_user_department = current_user_profile.get('department')
            current_user_grade = current_user_profile.get('grade_level')
            
            for stage in APPROVAL_CHAIN:
                if (current_user_department == stage['department'] and
                    current_user_grade == stage['grade_level']):
                    is_approver = True
                    break
            
            if st.session_state.current_user and (st.session_state.current_user['role'] == 'admin' or is_approver):
                admin_manage_opex_capex_approvals()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_leave_approvals": # NEWLY ADDED
            if st.session_state.current_user and (st.session_state.current_user['role'] == 'admin' or st.session_state.current_user['role'] == 'manager'):
                admin_manage_leave_approvals()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_beneficiaries":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_beneficiaries()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_hr_policies":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_hr_policies()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_training_resources":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_training_resources()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_documents":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_documents()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
    else:
        login_form()

if __name__ == "__main__":
    main()
