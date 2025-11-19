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

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

ICON_BASE_DIR = "Project_Resources" # Assuming you create this folder and put images inside
if not os.path.exists(ICON_BASE_DIR):
    os.makedirs(ICON_BASE_DIR)

# Ensure 'leave_documents' and 'opex_capex_documents' directories exist for file uploads
os.makedirs("leave_documents", exist_ok=True)
os.makedirs("opex_capex_documents", exist_ok=True)


LOGO_FILE_NAME = "polaris_digitech_logo.png"
LOGO_PATH = os.path.join(ICON_BASE_DIR, LOGO_FILE_NAME)

ABDULAHI_IMAGE_FILE_NAME = "abdulahi_image.png"
ABDULAHI_IMAGE_PATH = os.path.join(ICON_BASE_DIR, ABDULAHI_IMAGE_FILE_NAME)

# --- Define Approval Route Roles and simulate emails (Updated to fetch from users) ---
# These are the *stages* in the approval chain, mapped to department/grade levels
# The order here defines the sequence of approval for OPEX/CAPEX
APPROVAL_CHAIN = [
    {"role_name": "Admin Manager", "department": "Administration", "grade_level": "Manager"},
    {"role_name": "HR Manager", "department": "HR", "grade_level": "Manager"},
    {"role_name": "Finance Manager", "department": "Finance", "grade_level": "Manager"},
    {"role_name": "MD", "department": "Executive", "grade_level": "MD"} # MD is assumed to be in Executive department
]

# Helper function to get an approver's full name based on department and grade level
def get_approver_name_by_criteria(users, department, grade_level):
    for user in users:
        profile = user.get('profile', {})
        if profile.get('department') == department and profile.get('grade_level') == grade_level:
            return profile.get('name')
    return None # Or raise an error if an approver is strictly required

# --- Data Loading/Saving Functions ---
class DateEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (date, datetime)):
            return obj.isoformat()
        return super().default(obj)

def load_data(filename, default_value=None):
    if default_value is None:
        default_value = []
    try:
        if os.path.exists(filename) and os.path.getsize(filename) > 0:
            with open(filename, "r") as file:
                return json.load(file)
        return default_value
    except json.JSONDecodeError:
        st.warning(f"Error decoding JSON from {filename}. File might be corrupted or empty. Resetting data.")
        return default_value
    except FileNotFoundError:
        return default_value

def save_data(data, filename):
    with open(filename, "w") as file:
        json.dump(data, file, indent=4, cls=DateEncoder)

def save_uploaded_file(uploaded_file, destination_folder="uploaded_documents"):
    if uploaded_file is not None:
        if not os.path.exists(destination_folder):
            os.makedirs(destination_folder)
            
        file_path = os.path.join(destination_folder, uploaded_file.name)
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    return None

# --- Initial Data Setup (Users, Policies, Beneficiaries) ---
def setup_initial_data():
    # Initial Users (Admin + 6 Staff Members)
    initial_users = [
        # Admin User (can act as MD and Admin Manager for initial setup if no other specific user)
        {
            "username": "abdul_bolaji@yahoo.com",
            "password": pbkdf2_sha256.hash("admin123"), # Hashed password
            "role": "admin", # This role grants access to admin functions
            "staff_id": "ADM/2024/000",
            "profile": {
                "name": "Abdul Bolaji (Admin)",
                "date_of_birth": "1980-01-01",
                "gender": "Male",
                "grade_level": "MD", # This user can act as MD approver
                "department": "Executive", # This user can act as MD approver, also Admin manager for the purpose of this demo
                "education_background": "MBA, Computer Science",
                "professional_experience": "15+ years in IT Management",
                "address": "123 Admin Lane, Lagos",
                "phone_number": "+2348011112222",
                "email_address": "abdul_bolaji@yahoo.com",
                "training_attended": [],
                "work_anniversary": "2010-09-01"
            }
        },
        # Staff Members (with generic password 123456)
        {
            "username": "ada_ama",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/001",
            "profile": {
                "name": "Ada Ama",
                "date_of_birth": "1995-01-01",
                "gender": "Female", # Corrected from Male in table
                "grade_level": "Officer", 
                "department": "Marketing", 
                "education_background": "BSc. Marketing",
                "professional_experience": "5 years in digital marketing",
                "address": "456 Market St, Abuja",
                "phone_number": "+2348023456789",
                "email_address": "ada.ama@example.com",
                "training_attended": [],
                "work_anniversary": "2024-01-15"
            }
        },
        {
            "username": "udu_aka",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/002",
            "profile": {
                "name": "Udu Aka",
                "date_of_birth": "2000-02-01",
                "gender": "Male",
                "grade_level": "Manager", # This user can act as Finance Manager approver
                "department": "Finance",
                "education_background": "ACA, B.Acc",
                "professional_experience": "8 years in financial management",
                "address": "789 Bank Rd, Lagos",
                "phone_number": "+2348034567890",
                "email_address": "udu.aka@example.com",
                "training_attended": [],
                "work_anniversary": "2024-03-01"
            }
        },
        {
            "username": "abdulahi_ibrahim",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/003",
            "profile": {
                "name": "Abdulahi Ibrahim",
                "date_of_birth": "1998-03-03",
                "gender": "Male", # Corrected from Female
                "grade_level": "Manager", # This user can act as Admin Manager approver
                "department": "Administration",
                "education_background": "B.A. Public Admin",
                "professional_experience": "6 years in office administration",
                "address": "101 Admin Way, Port Harcourt",
                "phone_number": "+2348045678901",
                "email_address": "abdulahi.ibrahim@example.com",
                "training_attended": [],
                "work_anniversary": "2024-02-10"
            }
        },
        {
            "username": "addidas_puma",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/004", 
            "profile": {
                "name": "Addidas Puma",
                "date_of_birth": "1999-09-04",
                "gender": "Female", # Corrected from Male
                "grade_level": "Manager", # This user can act as HR Manager approver
                "department": "HR",
                "education_background": "MSc. Human Resources",
                "professional_experience": "7 years in HR operations",
                "address": "202 HR Lane, Kano",
                "phone_number": "+2348056789012",
                "email_address": "addidas.puma@example.com",
                "training_attended": [],
                "work_anniversary": "2023-07-20"
            }
        },
        {
            "username": "big_kola",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/005", 
            "profile": {
                "name": "Big Kola",
                "date_of_birth": "2001-06-13",
                "gender": "Female",
                "grade_level": "Officer",
                "department": "Operations", # Assuming 'CV' was a typo for a department, changed to Operations
                "education_background": "BEng. Civil Engineering",
                "professional_experience": "3 years in project management",
                "address": "303 Ops Drive, Ibadan",
                "phone_number": "+2348067890123",
                "email_address": "big.kola@example.com",
                "training_attended": [],
                "work_anniversary": "2022-04-05"
            }
        },
        {
            "username": "king_queen",
            "password": pbkdf2_sha256.hash("123456"),
            "role": "staff",
            "staff_id": "POL/2024/006", 
            "profile": {
                "name": "King Queen",
                "date_of_birth": "2002-06-16",
                "gender": "Female",
                "grade_level": "Officer",
                "department": "IT", # Changed from Administration to IT for variety
                "education_background": "B.Sc. Computer Science",
                "professional_experience": "2 years in IT support",
                "address": "404 Tech Road, Enugu",
                "phone_number": "+2348078901234",
                "email_address": "king.queen@example.com",
                "training_attended": [],
                "work_anniversary": "2023-11-01"
            }
        }
    ]
    
    # Only create initial users if the file doesn't exist or is empty
    if not os.path.exists(USERS_FILE) or os.path.getsize(USERS_FILE) == 0:
        save_data(initial_users, USERS_FILE)
        st.success("Initial user data created.")

    # Initial HR Policies
    initial_policies = {
        "Staff Handbook": "This handbook outlines the policies, procedures, and expectations for all employees of Polaris Digitech. It covers topics such as conduct, benefits, and company culture...",
        "HSE Policy": "Polaris Digitech is committed to providing a safe and healthy working environment for all employees, contractors, and visitors. This policy details our approach to Health, Safety, and Environment management...",
        "Data Privacy Security Policy": "This policy establishes guidelines for the collection, use, storage, and disclosure of personal data to ensure compliance with data protection laws and safeguard sensitive information...",
        "Procurement Policy": "This policy governs all procurement activities at Polaris Digitech, ensuring transparency, fairness, and cost-effectiveness in acquiring goods and services...",
        "Password Secrecy Policy": "This policy sets forth the requirements for creating, using, and protecting passwords within Polaris Digitech to safeguard company information systems and data from unauthorized access."
    }
    if not os.path.exists(HR_POLICIES_FILE) or os.path.getsize(HR_POLICIES_FILE) == 0:
        save_data(initial_policies, HR_POLICIES_FILE)
        st.success("Initial HR policies created.")

    # Initial Beneficiaries Data (from prompt)
    initial_beneficiaries = {
        "Bestway Engineering Services Ltd": {"Account Name": "Benjamin", "Account No": "1234567890", "Bank": "GTB"},
        "Alpha Link Technical Services": {"Account Name": "Oladele", "Account No": "2345678900", "Bank": "Access Bank"},
        "AFLAC COM SPECs": {"Account Name": "Fasco", "Account No": "1234567890", "Bank": "Opay"},
        "Emmafem Resources Nig. Ent.": {"Account Name": "Radius", "Account No": "2345678901", "Bank": "UBA"},
        "Neptune Global Services": {"Account Name": "Folashade", "Account No": "12345678911", "Bank": "Union Bank"},
        "Other (Manually Enter Details)": {"Account Name": "", "Account No": "", "Bank": ""} # Option for manual entry
    }
    if not os.path.exists(BENEFICIARIES_FILE) or os.path.getsize(BENEFICIARIES_FILE) == 0:
        save_data(initial_beneficiaries, BENEFICIARIES_FILE)
        st.success("Initial Beneficiaries data created.")

# --- Session State Initialization ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'current_user' not in st.session_state: # Stores full user object if logged in
    st.session_state.current_user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = "login"

# Load all persistent data into session state
st.session_state.users = load_data(USERS_FILE)
st.session_state.leave_requests = load_data(LEAVE_REQUESTS_FILE, [])
st.session_state.opex_capex_requests = load_data(OPEX_CAPEX_REQUESTS_FILE, [])
st.session_state.performance_goals = load_data(PERFORMANCE_GOALS_FILE, [])
st.session_state.self_appraisals = load_data(SELF_APPRAISALS_FILE, [])
st.session_state.payroll_data = load_data(PAYROLL_FILE, []) # New payroll data
st.session_state.beneficiaries = load_data(BENEFICIARIES_FILE, {}) # New beneficiaries data
st.session_state.hr_policies = load_data(HR_POLICIES_FILE, {}) # New policies data

# Ensure payroll data has necessary columns for DataFrame creation
# This handles cases where payroll.json might be empty or malformed initially
if not st.session_state.payroll_data:
    st.session_state.payroll_data = [] # Ensure it's an empty list if data is missing

# --- Common UI Elements ---
def display_logo():
    if os.path.exists(LOGO_PATH):
        st.image(LOGO_PATH, width=150)
    else:
        st.error(f"Company logo not found at: {LOGO_PATH}")
        st.warning(f"Please ensure '{LOGO_FILE_NAME}' is in '{ICON_BASE_DIR}'.")

def display_sidebar():
    st.sidebar.image(LOGO_PATH, width=200)
    st.sidebar.title("Navigation")
    st.sidebar.markdown("---")

    # Dynamic sidebar based on user role
    if st.session_state.logged_in:
        st.sidebar.button("📊 Dashboard", key="nav_dashboard", on_click=lambda: st.session_state.update(current_page="dashboard"))
        st.sidebar.button("📝 My Profile", key="nav_my_profile", on_click=lambda: st.session_state.update(current_page="my_profile"))
        st.sidebar.button("🏖️ Apply for Leave", key="nav_apply_leave", on_click=lambda: st.session_state.update(current_page="leave_request"))
        st.sidebar.button("📈 Performance Goal Setting", key="nav_performance_goals", on_click=lambda: st.session_state.update(current_page="performance_goal_setting"))
        st.sidebar.button("✍️ Self-Appraisal", key="nav_self_appraisal", on_click=lambda: st.session_state.update(current_page="self_appraisal"))
        st.sidebar.button("📄 HR Policies", key="nav_hr_policies", on_click=lambda: st.session_state.update(current_page="hr_policies"))
        st.sidebar.button("💰 My Payslips", key="nav_my_payslips", on_click=lambda: st.session_state.update(current_page="my_payslips")) # New
        st.sidebar.button("💲 OPEX/CAPEX Requisition", key="nav_submit_opex_capex", on_click=lambda: st.session_state.update(current_page="opex_capex_form"))

        if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
            st.sidebar.markdown("---")
            st.sidebar.subheader("Admin Functions")
            st.sidebar.button("👥 Manage Users", key="admin_manage_users", on_click=lambda: st.session_state.update(current_page="manage_users")) # New
            st.sidebar.button("📤 Upload Payroll", key="admin_upload_payroll", on_click=lambda: st.session_state.update(current_page="upload_payroll")) # New
            st.sidebar.button("✅ Manage OPEX/CAPEX Approvals", key="admin_manage_approvals", on_click=lambda: st.session_state.update(current_page="manage_opex_capex_approvals")) # New
            st.sidebar.button("🏦 Manage Beneficiaries", key="admin_manage_beneficiaries", on_click=lambda: st.session_state.update(current_page="manage_beneficiaries")) # New
            st.sidebar.button("📜 Manage HR Policies", key="admin_manage_policies", on_click=lambda: st.session_state.update(current_page="manage_hr_policies")) # New

        st.sidebar.markdown("---")
        st.sidebar.button("Logout", key="nav_logout", on_click=logout)
    else:
        st.sidebar.info("Please log in to access the portal.")

def logout():
    st.session_state.logged_in = False
    st.session_state.current_user = None
    st.session_state.current_page = "login"
    st.rerun()

# --- Login Form ---
def login_form():
    st.title("Polaris Digitech Staff Portal - Login")
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        username_input = st.text_input("User ID", key="login_username_input")
        password_input = st.text_input("Password", type="password", key="login_password_input")

        if st.button("Login", key="login_button"):
            found_user = None
            for user in st.session_state.users:
                # Check for both username and email (for admin login)
                if user['username'] == username_input:
                    if pbkdf2_sha256.verify(password_input, user['password']):
                        found_user = user
                        break
            
            if found_user:
                st.session_state.logged_in = True
                st.session_state.current_user = found_user
                st.success("Logged in successfully!")
                st.session_state.current_page = "dashboard"
                st.rerun()
            else:
                st.error("Invalid credentials")

# --- Dashboard Display ---
def display_dashboard():
    st.title("📊 Polaris Digitech HR Portal - Dashboard")

    if st.session_state.current_user:
        current_user_profile = st.session_state.current_user.get('profile', {})
        st.markdown(f"## Welcome, {current_user_profile.get('name', st.session_state.current_user['username']).title()}!")
        st.write(f"Your Staff ID: **{current_user_profile.get('staff_id', 'N/A')}**")
        st.write(f"Department: **{current_user_profile.get('department', 'N/A')}**")

        st.markdown("---")
        st.subheader("Upcoming Birthdays")
        today = date.today()
        upcoming_birthdays = []
        for user in st.session_state.users:
            profile = user.get('profile', {})
            dob_str = profile.get('date_of_birth')
            name = profile.get('name')
            if dob_str and name:
                try:
                    dob = datetime.strptime(dob_str, '%Y-%m-%d').date()
                    # Calculate birthday for current year
                    birthday_this_year = dob.replace(year=today.year)
                    # If birthday already passed this year, check next year
                    if birthday_this_year < today:
                        birthday_this_year = dob.replace(year=today.year + 1)
                    
                    days_until_birthday = (birthday_this_year - today).days

                    if 0 <= days_until_birthday <= 30: # Within next 30 days
                        upcoming_birthdays.append({
                            "Name": name,
                            "Birthday": birthday_this_year.strftime('%B %d'),
                            "Days Until": days_until_birthday
                        })
                except ValueError:
                    continue # Skip if DOB is malformed

        if upcoming_birthdays:
            df_birthdays = pd.DataFrame(upcoming_birthdays).sort_values(by="Days Until")
            st.dataframe(df_birthdays, use_container_width=True, hide_index=True)
            if any(b['Days Until'] == 0 for b in upcoming_birthdays):
                st.balloons()
                st.success("🎉 Happy Birthday to our staff members today! 🎉")
        else:
            st.info("No upcoming birthdays in the next 30 days.")

        st.markdown("---")
        st.subheader("HR Analytics Overview")

        total_employees = len(st.session_state.users)
        st.metric("Total Employees", total_employees)

        # Staff Distribution by Department
        if st.session_state.users:
            departments = [user.get('profile', {}).get('department', 'Unassigned') for user in st.session_state.users]
            df_departments = pd.DataFrame(departments, columns=['Department'])
            dept_counts = df_departments['Department'].value_counts().reset_index()
            dept_counts.columns = ['Department', 'Count']
            fig_dept = px.pie(dept_counts, values='Count', names='Department', title='Staff Distribution by Department', hole=0.3)
            st.plotly_chart(fig_dept, use_container_width=True)

            # Staff Distribution by Gender
            genders = [user.get('profile', {}).get('gender', 'N/A') for user in st.session_state.users]
            df_genders = pd.DataFrame(genders, columns=['Gender'])
            gender_counts = df_genders['Gender'].value_counts().reset_index()
            gender_counts.columns = ['Gender', 'Count']
            fig_gender = px.pie(gender_counts, values='Count', names='Gender', title='Staff Distribution by Gender', hole=0.3)
            st.plotly_chart(fig_gender, use_container_width=True)
        else:
            st.info("No staff data to display distributions.")

        # Staff On Leave
        current_on_leave = 0
        today = date.today()
        for req in st.session_state.leave_requests:
            try:
                start_date = datetime.strptime(req.get('start_date', '1900-01-01'), '%Y-%m-%d').date()
                end_date = datetime.strptime(req.get('end_date', '1900-01-01'), '%Y-%m-%d').date()
                if start_date <= today <= end_date and req.get('status') == 'Approved':
                    current_on_leave += 1
            except ValueError:
                continue # Skip malformed date entries
        st.metric("Staff Currently On Leave (Approved)", current_on_leave)

        st.markdown("---")
        st.subheader("Your Pending Requests")
    # 🔔 Notify if current user is an approver on any pending requests
    current_user_profile = st.session_state.current_user.get('profile', {})
    current_user_department = current_user_profile.get('department')
    current_user_grade = current_user_profile.get('grade_level')
    
    pending_approver_tasks_count = 0
    
    for req in st.session_state.opex_capex_requests:
        # Determine the current approver role for this request
        current_stage_index = req.get('current_approval_stage', 0)
        if current_stage_index < len(APPROVAL_CHAIN):
            expected_approver_stage = APPROVAL_CHAIN[current_stage_index]
            
            # Check if the current user matches the expected approver for this stage
            is_current_approver = (
                current_user_department == expected_approver_stage['department'] and
                current_user_grade == expected_approver_stage['grade_level'] and
                req.get('final_status') == "Pending" # Ensure overall request is still pending
            )
            if is_current_approver:
                 # Additional check to see if this specific stage is pending
                stage_status_key = f"status_{expected_approver_stage['role_name'].lower().replace(' ', '_')}"
                if req.get(stage_status_key) == "Pending":
                    pending_approver_tasks_count += 1

    if pending_approver_tasks_count > 0:
        st.warning(f"🔔 You have {pending_approver_tasks_count} OPEX/CAPEX requisition(s) awaiting your approval.")

        
        user_pending_leave = [
            req for req in st.session_state.leave_requests 
            if req.get('staff_id') == current_user_profile.get('staff_id') and req.get('status') == 'Pending'
        ]
        user_pending_opex_capex = [
            req for req in st.session_state.opex_capex_requests 
            if req.get('requester_staff_id') == current_user_profile.get('staff_id') and req.get('final_status') == 'Pending'
        ]

        if user_pending_leave:
            st.info(f"You have {len(user_pending_leave)} pending leave requests.")
        if user_pending_opex_capex:
            st.info(f"You have {len(user_pending_opex_capex)} pending OPEX/CAPEX requests.")
        if not user_pending_leave and not user_pending_opex_capex and pending_approver_tasks_count == 0:
            st.info("You have no pending requests.")


    else:
        st.info("You have no pending requests.") # Changed from warning to info when no pending tasks
        # If no pending tasks for approver, still show user's own requests
        user_pending_leave = [
            req for req in st.session_state.leave_requests 
            if req.get('staff_id') == current_user_profile.get('staff_id') and req.get('status') == 'Pending'
        ]
        user_pending_opex_capex = [
            req for req in st.session_state.opex_capex_requests 
            if req.get('requester_staff_id') == current_user_profile.get('staff_id') and req.get('final_status') == 'Pending'
        ]

        if user_pending_leave:
            st.info(f"You have {len(user_pending_leave)} pending leave requests.")
        if user_pending_opex_capex:
            st.info(f"You have {len(user_pending_opex_capex)} pending OPEX/CAPEX requests.")
        if not user_pending_leave and not user_pending_opex_capex:
            st.info("You have no pending requests (either as requester or approver).")


# --- My Profile Page ---
def display_my_profile():
    st.title("📝 My Profile")

    user_index = -1
    for i, user in enumerate(st.session_state.users):
        if user['username'] == st.session_state.current_user['username']:
            user_index = i
            break

    if user_index == -1:
        st.error("Could not find your profile. Please log out and log in again.")
        return

    current_user_profile = st.session_state.users[user_index]['profile']

    with st.form("profile_edit_form"):
        st.subheader("Personal Details")
        current_user_profile['name'] = st.text_input("Full Name", value=current_user_profile.get("name", ""), key="profile_name_edit")
        
        # New fields: Staff ID, Date of Birth, Gender, Grade Level, Department
        st.text_input("Staff ID", value=current_user_profile.get("staff_id", ""), disabled=True, help="Staff ID cannot be changed.")
        
        dob_value = None
        if current_user_profile.get("date_of_birth"):
            try:
                dob_value = datetime.strptime(current_user_profile["date_of_birth"], '%Y-%m-%d').date()
            except ValueError:
                st.warning("Invalid date of birth format in existing profile. Please update.")
                dob_value = date.today()
        else:
            dob_value = date.today() # Default if no DOB exists
            
        current_user_profile['date_of_birth'] = st.date_input("Date of Birth", value=dob_value, key="profile_dob")
        current_user_profile['gender'] = st.selectbox("Gender", ["Male", "Female", "Other"], index=["Male", "Female", "Other"].index(current_user_profile.get("gender", "Male")), key="profile_gender")
        current_user_profile['grade_level'] = st.text_input("Grade Level", value=current_user_profile.get("grade_level", ""), key="profile_grade")
        
        department_options = ["Admin", "HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Executive", "Administration", "CV", "Other", "Unassigned"]
        current_dept = current_user_profile.get("department", "Unassigned")
        current_dept_index = department_options.index(current_dept) if current_dept in department_options else 0
        current_user_profile['department'] = st.selectbox("Department", options=department_options, index=current_dept_index, key="profile_department_edit")

        current_user_profile['address'] = st.text_area("Address", value=current_user_profile.get("address", ""), key="profile_address_edit")
        current_user_profile['phone_number'] = st.text_input("Phone Number", value=current_user_profile.get("phone_number", ""), key="profile_phone_edit")
        st.text_input("Email Address (Login ID)", value=st.session_state.current_user['username'], disabled=True, help="Your login email cannot be changed here.", key="profile_email_edit")
        
        st.subheader("Professional Background")
        current_user_profile['education_background'] = st.text_area("Education Background", value=current_user_profile.get("education_background", ""), height=100, key="profile_education_edit")
        current_user_profile['professional_experience'] = st.text_area("Professional Experience", value=current_user_profile.get("professional_experience", ""), height=150, key="profile_experience_edit")

        st.subheader("Change Password")
        new_password = st.text_input("New Password", type="password", key="new_password_input")
        confirm_password = st.text_input("Confirm New Password", type="password", key="confirm_password_input")

        save_profile_button = st.form_submit_button("Save Profile and Change Password (if entered)")

        if save_profile_button:
            # Update profile details
            st.session_state.users[user_index]['profile'] = current_user_profile
            
            # Handle password change
            if new_password:
                if new_password == confirm_password:
                    st.session_state.users[user_index]['password'] = pbkdf2_sha256.hash(new_password)
                    st.success("Password changed successfully!")
                else:
                    st.error("New password and confirm password do not match.")
                    st.rerun() # Stop execution to show error
            
            save_data(st.session_state.users, USERS_FILE)
            st.success("Profile details saved successfully!")
            st.rerun()

    st.markdown("---")
    st.subheader("Training Attended")
    with st.form("new_training_form"):
        new_training_name = st.text_input("New Training Name")
        new_training_date = st.date_input("Training Date", value=datetime.now())
        
        add_training_button = st.form_submit_button("Add Training Record")

        if add_training_button:
            if new_training_name:
                training_record = {"name": new_training_name, "date": str(new_training_date)}
                # Ensure 'training_attended' key exists in profile
                if "training_attended" not in current_user_profile:
                    current_user_profile["training_attended"] = []
                current_user_profile["training_attended"].append(training_record)
                save_data(st.session_state.users, USERS_FILE)
                st.success(f"Added training: {new_training_name}")
                st.rerun()
            else:
                st.error("Training name cannot be empty.")

    current_trainings = current_user_profile.get("training_attended", [])
    if current_trainings:
        st.write("---")
        st.markdown("#### Existing Training Records:")
        training_container = st.container()
        with training_container:
            for i, training in enumerate(current_trainings):
                col_tr1, col_tr2, col_tr3 = st.columns([0.6, 0.3, 0.1])
                with col_tr1:
                    st.write(f"- **{training.get('name', 'N/A')}**")
                with col_tr2:
                    st.write(f"({training.get('date', 'N/A')})")
                with col_tr3:
                    # Use a unique key for the button
                    if st.button("x", key=f"delete_training_{i}_btn_{training.get('name', '')}"):
                        current_user_profile["training_attended"].pop(i)
                        save_data(st.session_state.users, USERS_FILE)
                        st.info("Training record deleted.")
                        st.rerun()
    else:
        st.info("No training records added yet.")


# --- Leave Request Form (Existing) ---
def leave_request_form():
    st.title("🏖️ Apply for Leave")
    st.write("Fill out the form below to submit a leave request.")

    current_user_profile = st.session_state.current_user.get('profile', {})
    
    with st.form("leave_application_form"):
        st.subheader(f"Leave Application for {current_user_profile.get('name', 'N/A')}")
        
        leave_type = st.selectbox("Leave Type", ["Annual Leave", "Sick Leave", "Maternity Leave", "Paternity Leave", "Compassionate Leave", "Study Leave", "Other"])
        start_date = st.date_input("Start Date", value=datetime.now().date())
        end_date = st.date_input("End Date", value=datetime.now().date() + timedelta(days=7))
        reason = st.text_area("Reason for Leave", height=100)
        
        # Calculate number of days
        num_days = (end_date - start_date).days + 1
        st.info(f"Number of days requested: {num_days} days")

        supporting_document = st.file_uploader("Upload Supporting Document (Optional)", type=["pdf", "jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Submit Leave Request")

        if submitted:
            if start_date > end_date:
                st.error("End Date cannot be before Start Date.")
            elif num_days <= 0:
                st.error("Number of days requested must be at least 1.")
            else:
                doc_path = save_uploaded_file(supporting_document, "leave_documents")
                
                new_request = {
                    "request_id": len(st.session_state.leave_requests) + 1,
                    "staff_id": current_user_profile.get('staff_id', 'N/A'),
                    "staff_name": current_user_profile.get('name', 'N/A'),
                    "leave_type": leave_type,
                    "start_date": str(start_date),
                    "end_date": str(end_date),
                    "num_days": num_days,
                    "reason": reason,
                    "document_path": doc_path,
                    "submission_date": str(datetime.now().date()),
                    "status": "Pending" # Initial status for leave
                }
                st.session_state.leave_requests.append(new_request)
                save_data(st.session_state.leave_requests, LEAVE_REQUESTS_FILE)
                st.success("Leave request submitted successfully!") # Completed this line
                st.rerun()
    
    st.markdown("---")
    st.subheader("Your Leave History")
    user_leave_history = [
        req for req in st.session_state.leave_requests
        if req.get('staff_id') == current_user_profile.get('staff_id')
    ]
    if user_leave_history:
        df_leave = pd.DataFrame(user_leave_history)
        df_leave_display = df_leave[['submission_date', 'leave_type', 'start_date', 'end_date', 'num_days', 'status', 'reason']]
        st.dataframe(df_leave_display, use_container_width=True, hide_index=True)
    else:
        st.info("You have not submitted any leave requests yet.")


# --- Performance Goal Setting (Placeholder) ---
def performance_goal_setting():
    st.title("📈 Performance Goal Setting")
    st.write("This section will allow staff to set and track their performance goals.")
    st.info("Feature under development.")

# --- Self-Appraisal (Placeholder) ---
def self_appraisal():
    st.title("✍️ Self-Appraisal")
    st.write("This section will enable staff to submit their self-appraisals.")
    st.info("Feature under development.")

# --- HR Policies (Placeholder) ---
def hr_policies():
    st.title("📄 HR Policies")
    st.write("Browse company HR policies.")
    
    policies = st.session_state.hr_policies
    
    if policies:
        selected_policy_title = st.selectbox("Select a Policy", options=list(policies.keys()))
        
        if selected_policy_title:
            st.subheader(selected_policy_title)
            st.write(policies[selected_policy_title])
    else:
        st.info("No HR policies available yet.")

# --- My Payslips (Placeholder) ---
def my_payslips():
    st.title("💰 My Payslips")
    st.write("View and download your payslips here.")
    st.info("Feature under development.")
    
    current_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id')
    
    # Filter payroll data for the current user
    user_payslips = [
        payslip for payslip in st.session_state.payroll_data
        if payslip.get('Staff ID') == current_staff_id # Assuming 'Staff ID' is the column name
    ]

    if user_payslips:
        df_payslips = pd.DataFrame(user_payslips)
        st.dataframe(df_payslips, use_container_width=True, hide_index=True)
        # TODO: Add PDF generation/download for individual payslips later
    else:
        st.info("No payslips available for your Staff ID yet.")


# --- OPEX/CAPEX Requisition Form (Requester Side) ---
def opex_capex_form():
    st.title("💲 OPEX/CAPEX Requisition")
    st.write("Submit your operational or capital expenditure requisition.")

    current_user_profile = st.session_state.current_user.get('profile', {})
    
    with st.form("opex_capex_requisition_form"):
        st.subheader(f"Requisition by {current_user_profile.get('name', 'N/A')}")
        
        request_type = st.selectbox("Request Type", ["OPEX (Operational Expenditure)", "CAPEX (Capital Expenditure)"])
        item_description = st.text_area("Item/Service Description", height=100)
        quantity = st.number_input("Quantity", min_value=1, value=1)
        unit_price = st.number_input("Unit Price (NGN)", min_value=0.01, value=1000.00, format="%.2f")
        total_amount = quantity * unit_price
        st.info(f"Calculated Total Amount: NGN {total_amount:,.2f}")
        
        justification = st.text_area("Justification/Purpose", height=150)
        
        # New: Vendor Details
        st.subheader("Vendor Details")
        beneficiary_options = list(st.session_state.beneficiaries.keys())
        selected_beneficiary_name = st.selectbox("Select Existing Beneficiary or Manually Enter", beneficiary_options)

        vendor_name = ""
        vendor_account_name = ""
        vendor_account_no = ""
        vendor_bank = ""

        if selected_beneficiary_name == "Other (Manually Enter Details)":
            vendor_name = st.text_input("New Vendor Name")
            vendor_account_name = st.text_input("Vendor Account Name")
            vendor_account_no = st.text_input("Vendor Account Number")
            vendor_bank = st.text_input("Vendor Bank Name")
        else:
            selected_details = st.session_state.beneficiaries.get(selected_beneficiary_name, {})
            vendor_name = selected_beneficiary_name
            vendor_account_name = st.text_input("Vendor Account Name", value=selected_details.get("Account Name", ""), disabled=True)
            vendor_account_no = st.text_input("Vendor Account Number", value=selected_details.get("Account No", ""), disabled=True)
            vendor_bank = st.text_input("Vendor Bank Name", value=selected_details.get("Bank", ""), disabled=True)

        supporting_document = st.file_uploader("Upload Supporting Document (e.g., Invoice, Quote)", type=["pdf", "jpg", "jpeg", "png"])
        
        submitted = st.form_submit_button("Submit Requisition")

        if submitted:
            if not item_description or not justification:
                st.error("Item description and justification are required.")
            elif selected_beneficiary_name == "Other (Manually Enter Details)" and (not vendor_name or not vendor_account_name or not vendor_account_no or not vendor_bank):
                st.error("Please enter all manual vendor details, or select an existing beneficiary.")
            else:
                doc_path = save_uploaded_file(supporting_document, "opex_capex_documents")
                
                # Initialize approval statuses for each stage
                approval_stages_data = {}
                for stage in APPROVAL_CHAIN:
                    key_prefix = stage['role_name'].lower().replace(' ', '_')
                    approval_stages_data[f"status_{key_prefix}"] = "Pending"
                    approval_stages_data[f"{key_prefix}_approved_by"] = None
                    approval_stages_data[f"{key_prefix}_approval_date"] = None
                    approval_stages_data[f"{key_prefix}_comments"] = None

                new_request = {
                    "request_id": len(st.session_state.opex_capex_requests) + 1,
                    "requester_staff_id": current_user_profile.get('staff_id', 'N/A'),
                    "requester_name": current_user_profile.get('name', 'N/A'),
                    "requester_department": current_user_profile.get('department', 'N/A'),
                    "request_type": request_type,
                    "item_description": item_description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_amount": total_amount,
                    "justification": justification,
                    "vendor_name": vendor_name,
                    "vendor_account_name": vendor_account_name,
                    "vendor_account_no": vendor_account_no,
                    "vendor_bank": vendor_bank,
                    "document_path": doc_path,
                    "submission_date": str(datetime.now().date()),
                    "final_status": "Pending", # Overall status
                    "current_approval_stage": 0, # Index of the current approver in APPROVAL_CHAIN
                    "approval_history": [], # To store comments/decisions from each stage
                    **approval_stages_data # Unpack the dynamically created approval status fields
                }
                st.session_state.opex_capex_requests.append(new_request)
                save_data(st.session_state.opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                st.success("OPEX/CAPEX requisition submitted successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Your OPEX/CAPEX Requisition History")
    user_opex_capex_history = [
        req for req in st.session_state.opex_capex_requests
        if req.get('requester_staff_id') == current_user_profile.get('staff_id')
    ]
    if user_opex_capex_history:
        df_opex_capex = pd.DataFrame(user_opex_capex_history)
        # Select relevant columns for display
        display_cols = [
            'submission_date', 'request_type', 'item_description', 'total_amount', 
            'final_status', 'current_approval_stage'
        ]
        # Add individual stage statuses if they exist and are relevant
        for stage in APPROVAL_CHAIN:
            display_cols.append(f"status_{stage['role_name'].lower().replace(' ', '_')}")
            
        st.dataframe(df_opex_capex[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("You have not submitted any OPEX/CAPEX requisitions yet.")


# --- Admin Functions (New/Modified) ---

# Admin: Manage Users (Placeholder)
def admin_manage_users():
    st.title("👥 Admin: Manage Users")
    st.write("This section allows administrators to view, add, edit, and deactivate user accounts.")
    
    # Display current users
    st.subheader("Current Users")
    if st.session_state.users:
        df_users = pd.DataFrame([
            {
                "Username": user['username'],
                "Name": user['profile']['name'],
                "Staff ID": user['staff_id'],
                "Role": user['role'],
                "Department": user['profile']['department'],
                "Grade Level": user['profile']['grade_level'],
                "Email": user['profile']['email_address']
            } for user in st.session_state.users
        ])
        st.dataframe(df_users, use_container_width=True, hide_index=True)
    else:
        st.info("No users found.")
    
    st.markdown("---")
    st.subheader("Add New User")
    with st.form("add_user_form"):
        new_username = st.text_input("New User ID (e.g., email or unique identifier)", key="new_user_username")
        new_password = st.text_input("Password", type="password", key="new_user_password")
        new_name = st.text_input("Full Name", key="new_user_name")
        new_staff_id = st.text_input("Staff ID", key="new_user_staff_id")
        new_role = st.selectbox("Role", ["staff", "admin"], key="new_user_role")
        new_department_options = ["Admin", "HR", "Finance", "IT", "Marketing", "Operations", "Sales", "Executive", "Administration", "CV", "Other", "Unassigned"]
        new_department = st.selectbox("Department", options=new_department_options, key="new_user_department")
        new_grade_level = st.text_input("Grade Level", key="new_user_grade_level")
        new_email = st.text_input("Email Address", key="new_user_email")

        add_user_button = st.form_submit_button("Add User")

        if add_user_button:
            if not new_username or not new_password or not new_staff_id:
                st.error("User ID, Password, and Staff ID are required.")
            elif any(user['username'] == new_username for user in st.session_state.users):
                st.error("User ID already exists. Please choose a different one.")
            elif any(user['staff_id'] == new_staff_id for user in st.session_state.users):
                st.error("Staff ID already exists. Please use a unique Staff ID.")
            else:
                new_user_obj = {
                    "username": new_username,
                    "password": pbkdf2_sha256.hash(new_password),
                    "role": new_role,
                    "staff_id": new_staff_id,
                    "profile": {
                        "name": new_name,
                        "date_of_birth": "", # Can be updated by user later
                        "gender": "Other", # Can be updated by user later
                        "grade_level": new_grade_level,
                        "department": new_department,
                        "education_background": "",
                        "professional_experience": "",
                        "address": "",
                        "phone_number": "",
                        "email_address": new_email,
                        "training_attended": [],
                        "work_anniversary": str(date.today())
                    }
                }
                st.session_state.users.append(new_user_obj)
                save_data(st.session_state.users, USERS_FILE)
                st.success(f"User '{new_username}' added successfully!")
                st.rerun()

    st.info("Additional features like editing and deactivating users can be added here.")


# Admin: Upload Payroll (Placeholder)
def admin_upload_payroll():
    st.title("📤 Admin: Upload Payroll")
    st.write("This section allows administrators to upload payroll data, typically from a CSV or Excel file.")
    
    uploaded_file = st.file_uploader("Upload Payroll File (CSV, Excel)", type=["csv", "xlsx"])
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.csv'):
                df_payroll = pd.read_csv(uploaded_file)
            else: # Assume xlsx
                df_payroll = pd.read_excel(uploaded_file)
            
            st.subheader("Preview of Uploaded Data")
            st.dataframe(df_payroll)
            
            if st.button("Confirm and Save Payroll Data"):
                # Convert DataFrame to list of dictionaries for JSON storage
                st.session_state.payroll_data = df_payroll.to_dict(orient='records')
                save_data(st.session_state.payroll_data, PAYROLL_FILE)
                st.success("Payroll data uploaded and saved successfully!")
                st.rerun()

        except Exception as e:
            st.error(f"Error processing file: {e}")
            st.info("Please ensure the file is a valid CSV or Excel format.")
    
    st.subheader("Current Payroll Data Summary")
    if st.session_state.payroll_data:
        df_current_payroll = pd.DataFrame(st.session_state.payroll_data)
        st.dataframe(df_current_payroll.head()) # Show first few rows
        st.write(f"Total records: {len(df_current_payroll)}")
    else:
        st.info("No payroll data currently loaded.")


# Admin: Manage OPEX/CAPEX Approvals (Crucial for Requirement 1)
def admin_manage_opex_capex_approvals():
    st.title("✅ Admin: Manage OPEX/CAPEX Approvals")
    st.write("Review and approve/reject pending OPEX/CAPEX requisitions.")

    current_user_profile = st.session_state.current_user.get('profile', {})
    current_user_department = current_user_profile.get('department')
    current_user_grade = current_user_profile.get('grade_level')

    st.subheader("Requisitions Awaiting Your Approval")
    pending_for_current_approver = []

    for req in st.session_state.opex_capex_requests:
        current_stage_index = req.get('current_approval_stage', 0)
        if req.get('final_status') == "Pending" and current_stage_index < len(APPROVAL_CHAIN):
            expected_approver_stage = APPROVAL_CHAIN[current_stage_index]
            
            # Check if the current logged-in user is the approver for the current stage
            is_current_approver = (
                current_user_department == expected_approver_stage['department'] and
                current_user_grade == expected_approver_stage['grade_level']
            )
            
            # Check the specific status for this stage
            stage_status_key = f"status_{expected_approver_stage['role_name'].lower().replace(' ', '_')}"
            if is_current_approver and req.get(stage_status_key) == "Pending":
                pending_for_current_approver.append(req)

    if not pending_for_current_approver:
        st.info("No OPEX/CAPEX requisitions awaiting your approval at this time.")
    else:
        st.warning(f"You have {len(pending_for_current_approver)} requisition(s) to review.")
        for i, req in enumerate(pending_for_current_approver):
            st.markdown(f"---")
            st.subheader(f"Request ID: {req.get('request_id')} - {req.get('request_type')} by {req.get('requester_name')}")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Requester Staff ID:** {req.get('requester_staff_id')}")
                st.write(f"**Department:** {req.get('requester_department')}")
                st.write(f"**Item:** {req.get('item_description')}")
                st.write(f"**Quantity:** {req.get('quantity')}")
                st.write(f"**Unit Price:** NGN {req.get('unit_price'):,.2f}")
                st.write(f"**Total Amount:** NGN {req.get('total_amount'):,.2f}")
                st.write(f"**Submission Date:** {req.get('submission_date')}")
            with col2:
                st.write(f"**Justification:** {req.get('justification')}")
                st.write(f"**Vendor:** {req.get('vendor_name')} (Account: {req.get('vendor_account_name')}/{req.get('vendor_account_no')} - {req.get('vendor_bank')})")
                if req.get('document_path'):
                    st.download_button(
                        label="Download Supporting Document",
                        data=open(req['document_path'], "rb").read(),
                        file_name=os.path.basename(req['document_path']),
                        mime="application/octet-stream",
                        key=f"download_doc_{req['request_id']}"
                    )
                else:
                    st.info("No supporting document uploaded.")
            
            st.markdown("---")
            st.write(f"**Current Approval Stage:** {APPROVAL_CHAIN[req['current_approval_stage']]['role_name']}")
            
            # Display approval history
            if req.get('approval_history'):
                st.markdown("#### Approval History:")
                for entry in req['approval_history']:
                    status_text = "Approved" if entry['status'] == "Approved" else "Rejected"
                    st.markdown(f"- **{entry['approver_role']}** by **{entry['approver_name']}** on *{entry['date']}*: {status_text}. Comment: *{entry['comment'] if entry['comment'] else 'No comment.'}*")
            else:
                st.info("No approval history yet.")

            with st.form(f"approval_form_{req['request_id']}"):
                approval_comment = st.text_area("Your Comment (Optional)", key=f"comment_{req['request_id']}")
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    approve_button = st.form_submit_button("Approve", help="Approve this requisition")
                with col_btn2:
                    reject_button = st.form_submit_button("Reject", help="Reject this requisition")

                if approve_button or reject_button:
                    # Update the specific stage status for the current approver
                    current_approver_stage_name = APPROVAL_CHAIN[current_stage_index]['role_name']
                    stage_status_key = f"status_{current_approver_stage_name.lower().replace(' ', '_')}"
                    approver_name_key = f"{current_approver_stage_name.lower().replace(' ', '_')}_approved_by"
                    approval_date_key = f"{current_approver_stage_name.lower().replace(' ', '_')}_approval_date"
                    comments_key = f"{current_approver_stage_name.lower().replace(' ', '_')}_comments"

                    req[approver_name_key] = current_user_profile.get('name')
                    req[approval_date_key] = str(date.today())
                    req[comments_key] = approval_comment

                    history_entry = {
                        "approver_role": current_approver_stage_name,
                        "approver_name": current_user_profile.get('name'),
                        "date": str(date.today()),
                        "comment": approval_comment
                    }

                    if approve_button:
                        req[stage_status_key] = "Approved"
                        history_entry["status"] = "Approved"
                        
                        # Move to next stage or finalize
                        if current_stage_index + 1 < len(APPROVAL_CHAIN):
                            req['current_approval_stage'] += 1
                            st.success(f"Requisition {req['request_id']} approved by {current_approver_stage_name}. Moving to next approval stage.")
                        else:
                            req['final_status'] = "Approved"
                            req['current_approval_stage'] = -1 # Indicate final state
                            st.success(f"Requisition {req['request_id']} fully approved!")
                    elif reject_button:
                        req[stage_status_key] = "Rejected"
                        req['final_status'] = "Rejected"
                        req['current_approval_stage'] = -1 # Indicate final state
                        history_entry["status"] = "Rejected"
                        st.error(f"Requisition {req['request_id']} rejected by {current_approver_stage_name}.")
                    
                    req['approval_history'].append(history_entry)
                    save_data(st.session_state.opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                    st.rerun() # Refresh the page to show updated status

    st.markdown("---")
    st.subheader("All OPEX/CAPEX Requisitions (for Admin/Overview)")
    if st.session_state.opex_capex_requests:
        df_all_opex_capex = pd.DataFrame(st.session_state.opex_capex_requests)
        display_cols = [
            'request_id', 'requester_name', 'submission_date', 'request_type', 
            'total_amount', 'final_status', 
            'current_approval_stage'
        ]
        # Add all individual stage statuses for full overview
        for stage in APPROVAL_CHAIN:
            display_cols.append(f"status_{stage['role_name'].lower().replace(' ', '_')}")

        st.dataframe(df_all_opex_capex[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("No OPEX/CAPEX requisitions submitted yet.")


# Admin: Manage Beneficiaries (New)
def admin_manage_beneficiaries():
    st.title("🏦 Admin: Manage Beneficiaries")
    st.write("Add, edit, or delete beneficiary bank details for payments.")

    st.subheader("Current Beneficiaries")
    if st.session_state.beneficiaries:
        # Exclude the "Other" option for display purposes if it's just a placeholder
        display_beneficiaries = {k: v for k, v in st.session_state.beneficiaries.items() if k != "Other (Manually Enter Details)"}
        
        if display_beneficiaries:
            df_beneficiaries = pd.DataFrame.from_dict(display_beneficiaries, orient='index')
            df_beneficiaries.index.name = "Beneficiary Name"
            st.dataframe(df_beneficiaries, use_container_width=True)

            # Option to delete beneficiaries
            st.markdown("---")
            st.subheader("Delete Beneficiary")
            beneficiary_to_delete = st.selectbox("Select beneficiary to delete", list(display_beneficiaries.keys()), key="delete_beneficiary_select")
            if st.button("Delete Selected Beneficiary", key="delete_beneficiary_button"):
                if beneficiary_to_delete:
                    del st.session_state.beneficiaries[beneficiary_to_delete]
                    save_data(st.session_state.beneficiaries, BENEFICIARIES_FILE)
                    st.success(f"Beneficiary '{beneficiary_to_delete}' deleted.")
                    st.rerun()
                else:
                    st.warning("Please select a beneficiary to delete.")
        else:
            st.info("No beneficiaries added yet (excluding manual entry option).")
    else:
        st.info("No beneficiaries data loaded.")

    st.markdown("---")
    st.subheader("Add New Beneficiary")
    with st.form("add_beneficiary_form"):
        new_beneficiary_name = st.text_input("Beneficiary Name (e.g., Company Name)", key="new_beneficiary_name")
        new_account_name = st.text_input("Account Name", key="new_account_name")
        new_account_no = st.text_input("Account Number", key="new_account_no")
        new_bank = st.text_input("Bank Name", key="new_bank")
        
        add_beneficiary_button = st.form_submit_button("Add Beneficiary")

        if add_beneficiary_button:
            if new_beneficiary_name and new_account_name and new_account_no and new_bank:
                if new_beneficiary_name in st.session_state.beneficiaries:
                    st.error("Beneficiary name already exists. Please choose a unique name or edit the existing one.")
                else:
                    st.session_state.beneficiaries[new_beneficiary_name] = {
                        "Account Name": new_account_name,
                        "Account No": new_account_no,
                        "Bank": new_bank
                    }
                    save_data(st.session_state.beneficiaries, BENEFICIARIES_FILE)
                    st.success(f"Beneficiary '{new_beneficiary_name}' added successfully!")
                    st.rerun()
            else:
                st.error("All fields are required to add a new beneficiary.")


# Admin: Manage HR Policies (New)
def admin_manage_hr_policies():
    st.title("📜 Admin: Manage HR Policies")
    st.write("Add, edit, or delete company HR policies.")

    st.subheader("Existing HR Policies")
    policies = st.session_state.hr_policies
    
    if policies:
        policy_titles = list(policies.keys())
        
        # Display existing policies in a read-only manner first
        st.markdown("---")
        st.markdown("#### View/Edit Policies")
        selected_policy_to_edit = st.selectbox("Select a policy to view/edit", options=policy_titles, key="edit_policy_select")
        
        if selected_policy_to_edit:
            current_content = policies.get(selected_policy_to_edit, "")
            edited_policy_title = st.text_input("Policy Title", value=selected_policy_to_edit, key="edited_policy_title")
            edited_policy_content = st.text_area("Policy Content", value=current_content, height=300, key="edited_policy_content")
            
            col_edit1, col_edit2 = st.columns(2)
            with col_edit1:
                if st.button("Save Edited Policy", key="save_edited_policy_btn"):
                    if edited_policy_title and edited_policy_content:
                        # If title changed, delete old entry and add new one
                        if edited_policy_title != selected_policy_to_edit:
                            del st.session_state.hr_policies[selected_policy_to_edit]
                        st.session_state.hr_policies[edited_policy_title] = edited_policy_content
                        save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                        st.success(f"Policy '{edited_policy_title}' updated successfully!")
                        st.rerun()
                    else:
                        st.error("Policy title and content cannot be empty.")
            with col_edit2:
                if st.button("Delete Policy", key="delete_policy_btn"):
                    if selected_policy_to_edit in st.session_state.hr_policies:
                        del st.session_state.hr_policies[selected_policy_to_edit]
                        save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                        st.success(f"Policy '{selected_policy_to_edit}' deleted.")
                        st.rerun()
        else:
            st.info("No policies to display for editing.")
    else:
        st.info("No HR policies available yet. Add one below!")

    st.markdown("---")
    st.subheader("Add New HR Policy")
    with st.form("add_policy_form"):
        new_policy_title = st.text_input("New Policy Title", key="new_policy_title_input")
        new_policy_content = st.text_area("New Policy Content", height=200, key="new_policy_content_input")
        
        add_policy_button = st.form_submit_button("Add Policy")
        
        if add_policy_button:
            if new_policy_title and new_policy_content:
                if new_policy_title in st.session_state.hr_policies:
                    st.error("A policy with this title already exists. Please choose a different title or edit the existing policy.")
                else:
                    st.session_state.hr_policies[new_policy_title] = new_policy_content
                    save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                    st.success(f"Policy '{new_policy_title}' added successfully!")
                    st.rerun()
            else:
                st.error("Policy title and content cannot be empty.")


# --- Main App Logic ---
if __name__ == "__main__":
    setup_initial_data() # Ensure initial data exists on first run

    display_sidebar()

    if st.session_state.logged_in:
        if st.session_state.current_page == "dashboard":
            display_dashboard()
        elif st.session_state.current_page == "my_profile":
            display_my_profile()
        elif st.session_state.current_page == "leave_request":
            leave_request_form()
        elif st.session_state.current_page == "performance_goal_setting":
            performance_goal_setting()
        elif st.session_state.current_page == "self_appraisal":
            self_appraisal()
        elif st.session_state.current_page == "hr_policies":
            hr_policies()
        elif st.session_state.current_page == "my_payslips":
            my_payslips()
        elif st.session_state.current_page == "opex_capex_form":
            opex_capex_form()
        # Admin Pages
        elif st.session_state.current_page == "manage_users":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_users()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "upload_payroll":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_upload_payroll()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_opex_capex_approvals":
            # This page is for anyone in the approval chain, not just 'admin' role
            # It relies on checking department/grade_level against APPROVAL_CHAIN
            is_approver = False
            current_user_profile = st.session_state.current_user.get('profile', {})
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
    else:
        login_form()

