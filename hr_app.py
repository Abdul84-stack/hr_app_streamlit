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
os.makedirs("opex_capex_pdfs", exist_ok=True) # New directory for generated PDFs


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

# --- PDF Generation Function (New) ---
def generate_opex_capex_pdf(request_data):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(200, 10, "OPEX/CAPEX Requisition Summary", 0, 1, "C")
    pdf.ln(10)

    pdf.set_font("Arial", "", 10)
    
    for key, value in request_data.items():
        if key in ['request_id', 'requester_name', 'requester_staff_id', 'requester_department',
                            'request_type', 'item_description', 'quantity', 'unit_price', 'total_amount',
                            'justification', 'vendor_name', 'vendor_account_name', 'vendor_account_no',
                            'vendor_bank', 'submission_date', 'final_status']:
            pdf.set_font("Arial", "B", 10)
            pdf.cell(50, 7, f"{key.replace('_', ' ').title()}:", 0, 0)
            pdf.set_font("Arial", "", 10)
            pdf.multi_cell(0, 7, str(value))
    
    pdf.ln(5)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(200, 10, "Approval History:", 0, 1)
    pdf.set_font("Arial", "", 10)
    if request_data.get('approval_history'):
        for entry in request_data['approval_history']:
            pdf.multi_cell(0, 7, f"- {entry.get('approver_role')} by {entry.get('approver_name')} on {entry.get('date')}: {entry.get('status')}. Comment: {entry.get('comment', 'No comment.')}")
    else:
        pdf.multi_cell(0, 7, "No approval history recorded.")

    # Save the PDF
    pdf_filename = f"OPEX_CAPEX_Request_{request_data['request_id']}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    pdf_path = os.path.join("opex_capex_pdfs", pdf_filename)
    pdf.output(pdf_path)
    return pdf_path

# --- Initial Data Setup (Users, Policies, Beneficiaries) ---
def setup_initial_data():
    # Initial Users (Admin + 6 Staff Members)
    initial_users = [
        # Admin User (can act as MD and Admin Manager for initial setup if no other specific user)
        {
            "username": "abdul_bolaji@yahoo.com",
            "password": pbkdf2_sha256.hash("admin123"), # Hashed password
            "role": "admin", # This role grants access to admin functions
            "profile": { # Ensure staff_id is within profile
                "name": "Abdul Bolaji (Admin)",
                "staff_id": "ADM/2024/000", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "Ada Ama",
                "staff_id": "POL/2024/001", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "Udu Aka",
                "staff_id": "POL/2024/002", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "Abdulahi Ibrahim",
                "staff_id": "POL/2024/003", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "Addidas Puma",
                "staff_id": "POL/2024/004", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "Big Kola",
                "staff_id": "POL/2024/005", # Moved staff_id here
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
            "profile": { # Ensure staff_id is within profile
                "name": "King Queen",
                "staff_id": "POL/2024/006", # Moved staff_id here
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
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("My Applications")
        st.sidebar.button("🏖️ Apply for Leave", key="nav_apply_leave", on_click=lambda: st.session_state.update(current_page="leave_request"))
        st.sidebar.button("👀 View My Leave", key="nav_view_my_leave", on_click=lambda: st.session_state.update(current_page="view_my_leave")) # New
        st.sidebar.button("💲 OPEX/CAPEX Requisition", key="nav_submit_opex_capex", on_click=lambda: st.session_state.update(current_page="opex_capex_form"))
        st.sidebar.button("👀 View My OPEX/CAPEX", key="nav_view_my_opex_capex", on_click=lambda: st.session_state.update(current_page="view_my_opex_capex")) # New
        st.sidebar.button("📈 Performance Goal Setting", key="nav_performance_goals", on_click=lambda: st.session_state.update(current_page="performance_goal_setting"))
        st.sidebar.button("👀 View My Goals", key="nav_view_my_goals", on_click=lambda: st.session_state.update(current_page="view_my_goals")) # New
        st.sidebar.button("✍️ Self-Appraisal", key="nav_self_appraisal", on_click=lambda: st.session_state.update(current_page="self_appraisal"))
        st.sidebar.button("👀 View My Appraisals", key="nav_view_my_appraisals", on_click=lambda: st.session_state.update(current_page="view_my_appraisals")) # New
        
        st.sidebar.markdown("---")
        st.sidebar.subheader("Company Resources")
        st.sidebar.button("📄 HR Policies", key="nav_hr_policies", on_click=lambda: st.session_state.update(current_page="hr_policies"))
        st.sidebar.button("💰 My Payslips", key="nav_my_payslips", on_click=lambda: st.session_state.update(current_page="my_payslips")) # New

        if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
            st.sidebar.markdown("---")
            st.sidebar.subheader("Admin Functions")
            st.sidebar.button("👥 Manage Users", key="admin_manage_users", on_click=lambda: st.session_state.update(current_page="manage_users")) # New
            st.sidebar.button("📤 Upload Payroll", key="admin_upload_payroll", on_click=lambda: st.session_state.update(current_page="upload_payroll")) # New
            st.sidebar.button("✅ Manage OPEX/CAPEX Approvals", key="admin_manage_approvals", on_click=lambda: st.session_state.update(current_page="manage_opex_capex_approvals")) # New
            st.sidebar.button("✅ Manage Leave Approvals", key="admin_manage_leave_approvals", on_click=lambda: st.session_state.update(current_page="manage_leave_approvals")) # NEWLY ADDED
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
        
        # Ensure staff_id is displayed from profile
        staff_id_display = current_user_profile.get('staff_id', 'N/A')
        st.write(f"Your Staff ID: **{staff_id_display}**")
        
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

    # Check for pending leave requests for admin
    pending_leave_approvals_count = len([req for req in st.session_state.leave_requests if req.get('status') == 'Pending' and st.session_state.current_user['role'] == 'admin'])
    if pending_leave_approvals_count > 0:
        st.warning(f"🔔 You have {pending_leave_approvals_count} leave request(s) awaiting your approval.")
        pending_approver_tasks_count += pending_leave_approvals_count # Sum up all pending approvals


    if pending_approver_tasks_count > 0:
        st.warning(f"🔔 You have {pending_approver_tasks_count} pending approval task(s) in total.")

        
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

    st.markdown("---")
    st.subheader("Quick Access: Your Applications")
    current_user_staff_id = current_user_profile.get('staff_id', 'N/A')

    # Display Your Leave History on Dashboard
    st.markdown("#### Your Leave Applications")
    user_leave_history = [
        req for req in st.session_state.leave_requests
        if req.get('staff_id') == current_user_staff_id # Use the corrected staff ID
    ]
    if user_leave_history:
        df_leave = pd.DataFrame(user_leave_history)
        df_leave_display = df_leave[['submission_date', 'leave_type', 'start_date', 'end_date', 'num_days', 'status']]
        st.dataframe(df_leave_display, use_container_width=True, hide_index=True)
    else:
        st.info("You have not submitted any leave requests yet.")
    st.button("View All My Leave Applications", key="dashboard_view_all_leave", on_click=lambda: st.session_state.update(current_page="view_my_leave"))

    st.markdown("#### Your OPEX/CAPEX Requisitions")
    user_opex_capex_history = [
        req for req in st.session_state.opex_capex_requests
        if req.get('requester_staff_id') == current_user_staff_id # Use the corrected staff ID
    ]
    if user_opex_capex_history:
        df_opex_capex = pd.DataFrame(user_opex_capex_history)
        display_cols = [
            'submission_date', 'request_type', 'item_description', 'total_amount', 
            'final_status'
        ]
        # Add individual stage statuses if they exist and are relevant
        for stage in APPROVAL_CHAIN:
            display_cols.append(f"status_{stage['role_name'].lower().replace(' ', '_')}")
            
        st.dataframe(df_opex_capex[display_cols], use_container_width=True, hide_index=True)
    else:
        st.info("You have not submitted any OPEX/CAPEX requisitions yet.")
    st.button("View All My OPEX/CAPEX Requisitions", key="dashboard_view_all_opex_capex", on_click=lambda: st.session_state.update(current_page="view_my_opex_capex"))


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

    st.subheader("Personal Information")
    st.write(f"**Name:** {current_user_profile.get('name', 'N/A')}")
    st.write(f"**Staff ID:** {current_user_profile.get('staff_id', 'N/A')}") # Display Staff ID
    st.write(f"**Email:** {current_user_profile.get('email_address', 'N/A')}")
    st.write(f"**Phone Number:** {current_user_profile.get('phone_number', 'N/A')}")
    st.write(f"**Date of Birth:** {current_user_profile.get('date_of_birth', 'N/A')}")
    st.write(f"**Gender:** {current_user_profile.get('gender', 'N/A')}")
    st.write(f"**Address:** {current_user_profile.get('address', 'N/A')}")

    st.subheader("Company Information")
    st.write(f"**Department:** {current_user_profile.get('department', 'N/A')}")
    st.write(f"**Grade Level:** {current_user_profile.get('grade_level', 'N/A')}")
    st.write(f"**Work Anniversary:** {current_user_profile.get('work_anniversary', 'N/A')}")

    st.subheader("Professional Background")
    st.write(f"**Education Background:** {current_user_profile.get('education_background', 'N/A')}")
    st.write(f"**Professional Experience:** {current_user_profile.get('professional_experience', 'N/A')}")
    
    st.markdown("---")
    st.subheader("Update Profile")
    with st.form("profile_edit_form"):
        # Include staff_id for potential update
        new_staff_id = st.text_input("Staff ID", value=current_user_profile.get('staff_id', ''), help="Your unique employee identification number.")
        new_name = st.text_input("Full Name", value=current_user_profile.get('name', ''))
        new_email = st.text_input("Email Address", value=current_user_profile.get('email_address', ''))
        new_phone = st.text_input("Phone Number", value=current_user_profile.get('phone_number', ''))
        new_address = st.text_area("Residential Address", value=current_user_profile.get('address', ''))

        # Date inputs for DOB and Work Anniversary
        current_dob_str = current_user_profile.get('date_of_birth')
        current_dob_date = datetime.strptime(current_dob_str, '%Y-%m-%d').date() if current_dob_str else None
        new_dob = st.date_input("Date of Birth", value=current_dob_date, max_value=date.today())

        current_wa_str = current_user_profile.get('work_anniversary')
        current_wa_date = datetime.strptime(current_wa_str, '%Y-%m-%d').date() if current_wa_str else None
        new_work_anniversary = st.date_input("Work Anniversary", value=current_wa_date, max_value=date.today())

        new_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], index=["", "Male", "Female", "Other"].index(current_user_profile.get('gender', '')))
        new_department = st.selectbox("Department", ["", "Administration", "HR", "Finance", "Executive", "Marketing", "Operations", "IT"], index=["", "Administration", "HR", "Finance", "Executive", "Marketing", "Operations", "IT"].index(current_user_profile.get('department', '')))
        new_grade_level = st.selectbox("Grade Level", ["", "Intern", "Officer", "Senior Officer", "Manager", "Senior Manager", "MD"], index=["", "Intern", "Officer", "Senior Officer", "Manager", "Senior Manager", "MD"].index(current_user_profile.get('grade_level', '')))
        
        new_education_background = st.text_area("Education Background", value=current_user_profile.get('education_background', ''))
        new_professional_experience = st.text_area("Professional Experience", value=current_user_profile.get('professional_experience', ''))
        
        # Training Attended (assuming a comma-separated string or list for simplicity in text input)
        current_training = ", ".join(current_user_profile.get('training_attended', []))
        new_training_attended = st.text_area("Training Attended (comma-separated)", value=current_training)

        if st.form_submit_button("Update Profile"):
            # Update the profile dictionary
            st.session_state.users[user_index]['profile']['staff_id'] = new_staff_id
            st.session_state.users[user_index]['profile']['name'] = new_name
            st.session_state.users[user_index]['profile']['email_address'] = new_email
            st.session_state.users[user_index]['profile']['phone_number'] = new_phone
            st.session_state.users[user_index]['profile']['address'] = new_address
            st.session_state.users[user_index]['profile']['date_of_birth'] = new_dob.isoformat() if new_dob else ''
            st.session_state.users[user_index]['profile']['work_anniversary'] = new_work_anniversary.isoformat() if new_work_anniversary else ''
            st.session_state.users[user_index]['profile']['gender'] = new_gender
            st.session_state.users[user_index]['profile']['department'] = new_department
            st.session_state.users[user_index]['profile']['grade_level'] = new_grade_level
            st.session_state.users[user_index]['profile']['education_background'] = new_education_background
            st.session_state.users[user_index]['profile']['professional_experience'] = new_professional_experience
            st.session_state.users[user_index]['profile']['training_attended'] = [t.strip() for t in new_training_attended.split(',') if t.strip()]

            # Update the current_user in session state to reflect changes immediately
            st.session_state.current_user['profile'] = st.session_state.users[user_index]['profile']

            save_data(st.session_state.users, USERS_FILE)
            st.success("Profile updated successfully!")
            st.rerun()

# --- Apply for Leave Form ---
def leave_request_form():
    st.title("🏖️ Apply for Leave")
    current_user_profile = st.session_state.current_user.get('profile', {})
    
    st.write(f"**Applicant Name:** {current_user_profile.get('name', 'N/A')}")
    st.write(f"**Staff ID:** {current_user_profile.get('staff_id', 'N/A')}") # Display Staff ID
    st.write(f"**Department:** {current_user_profile.get('department', 'N/A')}")

    with st.form("leave_request_form", clear_on_submit=True):
        leave_type = st.selectbox("Type of Leave", ["Annual Leave", "Sick Leave", "Maternity Leave", "Paternity Leave", "Compassionate Leave", "Study Leave", "Other"])
        start_date = st.date_input("Start Date", min_value=date.today())
        end_date = st.date_input("End Date", min_value=start_date)
        reason = st.text_area("Reason for Leave", max_chars=500)
        
        # Only allow document upload for Sick Leave or Study Leave
        uploaded_file = None
        if leave_type in ["Sick Leave", "Study Leave"]:
            uploaded_file = st.file_uploader(f"Upload Supporting Document for {leave_type} (e.g., Doctor's note, Admission Letter)", type=['pdf', 'jpg', 'jpeg', 'png'])

        submitted = st.form_submit_button("Submit Leave Request")

        if submitted:
            if start_date > end_date:
                st.error("End Date cannot be before Start Date.")
            elif not reason:
                st.error("Please provide a reason for your leave.")
            elif leave_type in ["Sick Leave", "Study Leave"] and uploaded_file is None:
                st.error(f"Please upload a supporting document for {leave_type}.")
            else:
                num_days = (end_date - start_date).days + 1
                
                file_path = None
                if uploaded_file:
                    file_path = save_uploaded_file(uploaded_file, "leave_documents")

                leave_id = f"LR-{len(st.session_state.leave_requests) + 1:04d}"
                new_leave_request = {
                    "leave_id": leave_id,
                    "staff_id": current_user_profile.get('staff_id'), # Capture staff_id from profile
                    "requester_name": current_user_profile.get('name', 'N/A'),
                    "department": current_user_profile.get('department', 'N/A'),
                    "leave_type": leave_type,
                    "start_date": start_date.isoformat(),
                    "end_date": end_date.isoformat(),
                    "num_days": num_days,
                    "reason": reason,
                    "document_path": file_path, # Store path to uploaded document
                    "submission_date": datetime.now().isoformat(),
                    "status": "Pending", # Initial status
                    "approval_history": []
                }
                st.session_state.leave_requests.append(new_leave_request)
                save_data(st.session_state.leave_requests, LEAVE_REQUESTS_FILE)
                st.success(f"Leave request ({leave_id}) submitted successfully for {num_days} days!")
                st.rerun()

# --- View My Leave Requests ---
def view_my_leave():
    st.title("👀 My Leave Applications")
    current_user_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id', 'N/A')

    user_leave_requests = [
        req for req in st.session_state.leave_requests
        if req.get('staff_id') == current_user_staff_id
    ]

    if not user_leave_requests:
        st.info("You have not submitted any leave requests yet.")
        return

    df_leave = pd.DataFrame(user_leave_requests)
    
    # Format dates for better display
    df_leave['submission_date'] = pd.to_datetime(df_leave['submission_date']).dt.strftime('%Y-%m-%d %H:%M')
    df_leave['start_date'] = pd.to_datetime(df_leave['start_date']).dt.strftime('%Y-%m-%d')
    df_leave['end_date'] = pd.to_datetime(df_leave['end_date']).dt.strftime('%Y-%m-%d')

    # Display a simplified view first
    display_cols = ['submission_date', 'leave_id', 'leave_type', 'start_date', 'end_date', 'num_days', 'status']
    st.dataframe(df_leave[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Details and History")
    for i, request in enumerate(user_leave_requests):
        expander_title = f"Leave Request ID: {request['leave_id']} - Type: {request['leave_type']} - Status: {request['status']}"
        with st.expander(expander_title):
            st.json(request) # Display full JSON for debugging/details
            if request.get('document_path') and os.path.exists(request['document_path']):
                st.write("### Supporting Document:")
                with open(request['document_path'], "rb") as f:
                    bytes_data = f.read()
                    b64_pdf = base64.b64encode(bytes_data).decode('utf-8')
                    # This creates a direct download link, not an embed. Streamlit doesn't natively embed PDFs easily without external libraries/workarounds.
                    # For simple display, one might use an iframe or st.markdown with HTML, but it's often blocked by browsers for security.
                    st.markdown(f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(request["document_path"])}">Download Document</a>', unsafe_allow_html=True)
            else:
                st.info("No supporting document attached or file not found.")

# --- OPEX/CAPEX Requisition Form ---
def opex_capex_form():
    st.title("💲 OPEX/CAPEX Requisition")
    current_user_profile = st.session_state.current_user.get('profile', {})

    st.write(f"**Requester Name:** {current_user_profile.get('name', 'N/A')}")
    st.write(f"**Requester Staff ID:** {current_user_profile.get('staff_id', 'N/A')}") # Display Staff ID
    st.write(f"**Requester Department:** {current_user_profile.get('department', 'N/A')}")

    beneficiaries_options = list(st.session_state.beneficiaries.keys())
    
    with st.form("opex_capex_form", clear_on_submit=True):
        request_type = st.selectbox("Request Type", ["OPEX (Operational Expenditure)", "CAPEX (Capital Expenditure)"])
        item_description = st.text_area("Item Description", help="Detailed description of the item or service requested.", max_chars=1000)
        quantity = st.number_input("Quantity", min_value=1, value=1)
        unit_price = st.number_input("Unit Price (NGN)", min_value=0.01, format="%.2f", value=0.01)
        total_amount = quantity * unit_price
        st.info(f"Calculated Total Amount: NGN {total_amount:,.2f}")

        justification = st.text_area("Justification/Purpose of Request", max_chars=1000)
        
        vendor_choice = st.selectbox("Select Vendor", beneficiaries_options, index=len(beneficiaries_options) - 1) # Default to 'Other'

        vendor_name_display = ""
        vendor_account_name_display = ""
        vendor_account_no_display = ""
        vendor_bank_display = ""

        if vendor_choice == "Other (Manually Enter Details)":
            vendor_name_manual = st.text_input("Vendor Name (Manual Entry)")
            vendor_account_name_manual = st.text_input("Vendor Account Name (Manual Entry)")
            vendor_account_no_manual = st.text_input("Vendor Account Number (Manual Entry)")
            vendor_bank_manual = st.text_input("Vendor Bank (Manual Entry)")
            
            # Use manual inputs
            vendor_name_display = vendor_name_manual
            vendor_account_name_display = vendor_account_name_manual
            vendor_account_no_display = vendor_account_no_manual
            vendor_bank_display = vendor_bank_manual
        else:
            selected_beneficiary = st.session_state.beneficiaries.get(vendor_choice, {})
            vendor_name_display = vendor_choice
            vendor_account_name_display = selected_beneficiary.get("Account Name", "N/A")
            vendor_account_no_display = selected_beneficiary.get("Account No", "N/A")
            vendor_bank_display = selected_beneficiary.get("Bank", "N/A")

            st.markdown(f"**Selected Vendor Details:**")
            st.write(f"Account Name: {vendor_account_name_display}")
            st.write(f"Account Number: {vendor_account_no_display}")
            st.write(f"Bank: {vendor_bank_display}")

        # Document upload for supporting files
        uploaded_doc = st.file_uploader("Upload Supporting Documents (e.g., Invoice, Quote)", type=['pdf', 'jpg', 'jpeg', 'png'], accept_multiple_files=True)

        submitted = st.form_submit_button("Submit Requisition")

        if submitted:
            if not item_description or not justification:
                st.error("Please fill in all required fields (Item Description, Quantity, Unit Price, Justification).")
            elif vendor_choice == "Other (Manually Enter Details)" and (not vendor_name_manual or not vendor_account_name_manual or not vendor_account_no_manual or not vendor_bank_manual):
                 st.error("Please provide all manual vendor details if 'Other' is selected.")
            else:
                request_id = f"OC-{len(st.session_state.opex_capex_requests) + 1:04d}"
                
                doc_paths = []
                if uploaded_doc:
                    for doc in uploaded_doc:
                        path = save_uploaded_file(doc, "opex_capex_documents")
                        if path:
                            doc_paths.append(path)

                new_request = {
                    "request_id": request_id,
                    "requester_name": current_user_profile.get('name', 'N/A'),
                    "requester_staff_id": current_user_profile.get('staff_id', 'N/A'), # Capture staff_id from profile
                    "requester_department": current_user_profile.get('department', 'N/A'),
                    "request_type": request_type,
                    "item_description": item_description,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_amount": total_amount,
                    "justification": justification,
                    "vendor_name": vendor_name_display,
                    "vendor_account_name": vendor_account_name_display,
                    "vendor_account_no": vendor_account_no_display,
                    "vendor_bank": vendor_bank_display,
                    "document_paths": doc_paths, # List of paths
                    "submission_date": datetime.now().isoformat(),
                    "current_approval_stage": 0, # Index into APPROVAL_CHAIN
                    "final_status": "Pending",
                    "approval_history": []
                }

                # Initialize status for each stage
                for stage in APPROVAL_CHAIN:
                    key = f"status_{stage['role_name'].lower().replace(' ', '_')}"
                    new_request[key] = "Pending"
                
                st.session_state.opex_capex_requests.append(new_request)
                save_data(st.session_state.opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                st.success(f"OPEX/CAPEX requisition ({request_id}) submitted successfully!")
                st.rerun()

# --- View My OPEX/CAPEX Requisitions ---
def view_my_opex_capex():
    st.title("👀 My OPEX/CAPEX Requisitions")
    current_user_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id', 'N/A')

    if current_user_staff_id == 'N/A':
        st.warning("Your Staff ID is not available. Please update your profile to view your requisitions.")
        st.button("Update My Profile Now", on_click=lambda: st.session_state.update(current_page="my_profile"))
        return

    user_opex_capex_requests = [
        req for req in st.session_state.opex_capex_requests
        if req.get('requester_staff_id') == current_user_staff_id
    ]

    if not user_opex_capex_requests:
        st.info("You have not submitted any OPEX/CAPEX requisitions yet.")
        return

    df_opex_capex = pd.DataFrame(user_opex_capex_requests)
    
    # Format dates for better display
    df_opex_capex['submission_date'] = pd.to_datetime(df_opex_capex['submission_date']).dt.strftime('%Y-%m-%d %H:%M')

    # Prepare display columns
    display_cols = ['submission_date', 'request_id', 'request_type', 'item_description', 'total_amount', 'final_status']
    for stage in APPROVAL_CHAIN:
        status_key = f"status_{stage['role_name'].lower().replace(' ', '_')}"
        if status_key in df_opex_capex.columns:
            display_cols.append(status_key)
        else:
            df_opex_capex[status_key] = "N/A" # Ensure column exists even if no data for it

    st.dataframe(df_opex_capex[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Details and Approval History")
    for i, request in enumerate(user_opex_capex_requests):
        expander_title = f"Request ID: {request['request_id']} - {request['item_description']} - Status: {request['final_status']}"
        with st.expander(expander_title):
            st.write(f"**Request Type:** {request.get('request_type')}")
            st.write(f"**Item Description:** {request.get('item_description')}")
            st.write(f"**Quantity:** {request.get('quantity')}")
            st.write(f"**Unit Price:** NGN {request.get('unit_price'):,.2f}")
            st.write(f"**Total Amount:** NGN {request.get('total_amount'):,.2f}")
            st.write(f"**Justification:** {request.get('justification')}")
            st.write(f"**Vendor Name:** {request.get('vendor_name')}")
            st.write(f"**Vendor Account Name:** {request.get('vendor_account_name')}")
            st.write(f"**Vendor Account No:** {request.get('vendor_account_no')}")
            st.write(f"**Vendor Bank:** {request.get('vendor_bank')}")
            st.write(f"**Submission Date:** {request.get('submission_date')}")
            st.write(f"**Final Status:** {request.get('final_status')}")

            st.markdown("##### Current Approval Statuses:")
            for stage in APPROVAL_CHAIN:
                status_key = f"status_{stage['role_name'].lower().replace(' ', '_')}"
                st.write(f"- **{stage['role_name']}:** {request.get(status_key, 'N/A')}")
            
            st.markdown("##### Approval History:")
            if request.get('approval_history'):
                for history_entry in request['approval_history']:
                    st.markdown(f"**{history_entry.get('approver_role')}** by {history_entry.get('approver_name')} on {history_entry.get('date')}: **{history_entry.get('status')}**")
                    st.markdown(f"  *Comment:* {history_entry.get('comment', 'No comment.')}")
            else:
                st.info("No approval history yet.")
            
            if request.get('document_paths'):
                st.markdown("##### Supporting Documents:")
                for doc_path in request['document_paths']:
                    if os.path.exists(doc_path):
                        with open(doc_path, "rb") as f:
                            bytes_data = f.read()
                            b64_pdf = base64.b64encode(bytes_data).decode('utf-8')
                            st.markdown(f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(doc_path)}">Download: {os.path.basename(doc_path)}</a>', unsafe_allow_html=True)
                    else:
                        st.warning(f"Document not found: {os.path.basename(doc_path)}")
            else:
                st.info("No supporting documents attached.")

            # If the request is pending and the user is the current requester, allow withdrawal
            if request.get('final_status') == 'Pending' and request.get('requester_staff_id') == current_user_staff_id:
                if st.button(f"Withdraw Request {request['request_id']}", key=f"withdraw_{request['request_id']}"):
                    for idx, req in enumerate(st.session_state.opex_capex_requests):
                        if req['request_id'] == request['request_id']:
                            st.session_state.opex_capex_requests[idx]['final_status'] = 'Withdrawn'
                            # Record withdrawal in history
                            st.session_state.opex_capex_requests[idx]['approval_history'].append({
                                "approver_name": current_user_profile.get('name', 'N/A'),
                                "approver_role": "Requester",
                                "date": datetime.now().isoformat(),
                                "status": "Withdrawn",
                                "comment": "Request withdrawn by requester."
                            })
                            save_data(st.session_state.opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                            st.success(f"Request {request['request_id']} has been withdrawn.")
                            st.rerun()


# --- Manage OPEX/CAPEX Approvals (Admin Function) ---
def admin_manage_opex_capex_approvals():
    st.title("✅ Manage OPEX/CAPEX Approvals")
    current_user_profile = st.session_state.current_user.get('profile', {})
    current_user_department = current_user_profile.get('department')
    current_user_grade = current_user_profile.get('grade_level')
    current_approver_name = current_user_profile.get('name', 'Admin User')

    st.markdown("---")
    st.subheader("Pending OPEX/CAPEX Requisitions Awaiting Your Approval")

    pending_for_current_approver = []

    for req in st.session_state.opex_capex_requests:
        if req.get('final_status') == "Pending":
            current_stage_index = req.get('current_approval_stage', 0)
            if current_stage_index < len(APPROVAL_CHAIN):
                expected_approver_stage = APPROVAL_CHAIN[current_stage_index]
                
                # Check if current user is the correct approver for this stage
                is_correct_approver = (
                    current_user_department == expected_approver_stage['department'] and
                    current_user_grade == expected_approver_stage['grade_level']
                )

                # Ensure this specific stage is still pending
                stage_status_key = f"status_{expected_approver_stage['role_name'].lower().replace(' ', '_')}"
                if is_correct_approver and req.get(stage_status_key) == "Pending":
                    pending_for_current_approver.append((req, current_stage_index, expected_approver_stage))

    if not pending_for_current_approver:
        st.info("No OPEX/CAPEX requisitions currently require your approval.")
        return

    for i, (request, current_stage_index, expected_approver_stage) in enumerate(pending_for_current_approver):
        st.markdown(f"### Requisition ID: {request['request_id']}")
        st.write(f"**Requester:** {request.get('requester_name')} (Staff ID: {request.get('requester_staff_id')})")
        st.write(f"**Department:** {request.get('requester_department')}")
        st.write(f"**Request Type:** {request.get('request_type')}")
        st.write(f"**Item:** {request.get('item_description')}")
        st.write(f"**Total Amount:** NGN {request.get('total_amount'):,.2f}")
        st.write(f"**Justification:** {request.get('justification')}")
        st.write(f"**Vendor:** {request.get('vendor_name')} (Acc: {request.get('vendor_account_no')}, Bank: {request.get('vendor_bank')})")
        st.write(f"**Submission Date:** {datetime.fromisoformat(request.get('submission_date')).strftime('%Y-%m-%d %H:%M')}")
        st.write(f"**Current Approval Stage:** {expected_approver_stage['role_name']}")

        # Display supporting documents
        if request.get('document_paths'):
            st.markdown("##### Supporting Documents:")
            for doc_path in request['document_paths']:
                if os.path.exists(doc_path):
                    with open(doc_path, "rb") as f:
                        bytes_data = f.read()
                        b64_pdf = base64.b64encode(bytes_data).decode('utf-8')
                        st.markdown(f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(doc_path)}">Download: {os.path.basename(doc_path)}</a>', unsafe_allow_html=True)
                else:
                    st.warning(f"Document not found: {os.path.basename(doc_path)}")
        else:
            st.info("No supporting documents attached.")

        # Display Approval History
        st.markdown("##### Approval History:")
        if request.get('approval_history'):
            for entry in request['approval_history']:
                st.markdown(f"- **{entry.get('approver_role')}** by {entry.get('approver_name')} on {entry.get('date')}: **{entry.get('status')}**. Comment: {entry.get('comment', 'No comment.')}")
        else:
            st.info("No history yet.")

        # Approval Form
        with st.form(key=f"opex_capex_approval_form_{request['request_id']}"):
            comment = st.text_area("Comments (Optional)", key=f"comment_{request['request_id']}")
            col_approve, col_reject = st.columns(2)
            
            approved = col_approve.form_submit_button("Approve", help="Approve this requisition")
            rejected = col_reject.form_submit_button("Reject", help="Reject this requisition")

            if approved or rejected:
                # Find the request in the main session state list to update it
                for req_idx, r in enumerate(st.session_state.opex_capex_requests):
                    if r['request_id'] == request['request_id']:
                        updated_request = st.session_state.opex_capex_requests[req_idx]
                        
                        action_status = "Approved" if approved else "Rejected"
                        
                        # Update the specific stage status
                        stage_status_key = f"status_{expected_approver_stage['role_name'].lower().replace(' ', '_')}"
                        updated_request[stage_status_key] = action_status
                        
                        # Add to approval history
                        updated_request['approval_history'].append({
                            "approver_name": current_approver_name,
                            "approver_role": expected_approver_stage['role_name'],
                            "date": datetime.now().isoformat(),
                            "status": action_status,
                            "comment": comment
                        })

                        if action_status == "Approved":
                            updated_request['current_approval_stage'] += 1
                            if updated_request['current_approval_stage'] >= len(APPROVAL_CHAIN):
                                updated_request['final_status'] = "Approved"
                                st.success(f"Requisition {request['request_id']} has been fully APPROVED!")
                                # Generate PDF on final approval
                                pdf_path = generate_opex_capex_pdf(updated_request)
                                st.success(f"Summary PDF generated: {pdf_path}")
                                with open(pdf_path, "rb") as f:
                                    st.download_button(
                                        label="Download Approval Summary PDF",
                                        data=f.read(),
                                        file_name=os.path.basename(pdf_path),
                                        mime="application/pdf"
                                    )
                            else:
                                next_stage = APPROVAL_CHAIN[updated_request['current_approval_stage']]
                                st.success(f"Requisition {request['request_id']} APPROVED by {expected_approver_stage['role_name']}. Moving to {next_stage['role_name']} stage.")
                        elif action_status == "Rejected":
                            updated_request['final_status'] = "Rejected"
                            st.error(f"Requisition {request['request_id']} REJECTED by {expected_approver_stage['role_name']}.")
                            # Generate PDF on rejection as well
                            pdf_path = generate_opex_capex_pdf(updated_request)
                            st.info(f"Summary PDF generated: {pdf_path}")
                            with open(pdf_path, "rb") as f:
                                st.download_button(
                                    label="Download Rejection Summary PDF",
                                    data=f.read(),
                                    file_name=os.path.basename(pdf_path),
                                    mime="application/pdf"
                                )

                        save_data(st.session_state.opex_capex_requests, OPEX_CAPEX_REQUESTS_FILE)
                        st.rerun()
            st.markdown("---") # Separator between requests

# --- Manage Leave Approvals (Admin Function) ---
def admin_manage_leave_approvals():
    st.title("✅ Manage Leave Approvals")
    current_user_profile = st.session_state.current_user.get('profile', {})
    current_approver_name = current_user_profile.get('name', 'Admin User')

    st.markdown("---")
    st.subheader("Pending Leave Requests Awaiting Your Approval")

    pending_leave_requests = [req for req in st.session_state.leave_requests if req.get('status') == 'Pending']

    if not pending_leave_requests:
        st.info("No leave requests currently require your approval.")
        return

    for i, request in enumerate(pending_leave_requests):
        st.markdown(f"### Leave Request ID: {request['leave_id']}")
        st.write(f"**Requester:** {request.get('requester_name')} (Staff ID: {request.get('staff_id')})")
        st.write(f"**Department:** {request.get('department')}")
        st.write(f"**Leave Type:** {request.get('leave_type')}")
        st.write(f"**Period:** {request.get('start_date')} to {request.get('end_date')} ({request.get('num_days')} days)")
        st.write(f"**Reason:** {request.get('reason')}")
        st.write(f"**Submission Date:** {datetime.fromisoformat(request.get('submission_date')).strftime('%Y-%m-%d %H:%M')}")

        # Display supporting document if available
        if request.get('document_path') and os.path.exists(request['document_path']):
            st.write("##### Supporting Document:")
            with open(request['document_path'], "rb") as f:
                bytes_data = f.read()
                b64_pdf = base64.b64encode(bytes_data).decode('utf-8')
                st.markdown(f'<a href="data:application/octet-stream;base64,{b64_pdf}" download="{os.path.basename(request["document_path"])}">Download Document</a>', unsafe_allow_html=True)
        else:
            st.info("No supporting document attached.")

        # Display Approval History
        st.markdown("##### Approval History:")
        if request.get('approval_history'):
            for entry in request['approval_history']:
                st.markdown(f"- **{entry.get('approver_name')}** on {entry.get('date')}: **{entry.get('status')}**. Comment: {entry.get('comment', 'No comment.')}")
        else:
            st.info("No history yet.")

        # Approval Form for leave
        with st.form(key=f"leave_approval_form_{request['leave_id']}"):
            comment = st.text_area("Comments (Optional)", key=f"leave_comment_{request['leave_id']}")
            col_approve, col_reject = st.columns(2)
            
            approved = col_approve.form_submit_button("Approve Leave", help="Approve this leave request")
            rejected = col_reject.form_submit_button("Reject Leave", help="Reject this leave request")

            if approved or rejected:
                for req_idx, r in enumerate(st.session_state.leave_requests):
                    if r['leave_id'] == request['leave_id']:
                        updated_request = st.session_state.leave_requests[req_idx]
                        
                        action_status = "Approved" if approved else "Rejected"
                        updated_request['status'] = action_status
                        
                        # Add to approval history
                        updated_request['approval_history'].append({
                            "approver_name": current_approver_name,
                            "approver_role": "Admin/HR Approver", # Generic role for leave approval
                            "date": datetime.now().isoformat(),
                            "status": action_status,
                            "comment": comment
                        })
                        
                        save_data(st.session_state.leave_requests, LEAVE_REQUESTS_FILE)
                        if action_status == "Approved":
                            st.success(f"Leave request {request['leave_id']} has been APPROVED!")
                        else:
                            st.error(f"Leave request {request['leave_id']} has been REJECTED!")
                        st.rerun()
        st.markdown("---") # Separator between requests

# --- Performance Goal Setting ---
def performance_goal_setting():
    st.title("📈 Performance Goal Setting")
    current_user_profile = st.session_state.current_user.get('profile', {})
    current_staff_id = current_user_profile.get('staff_id')
    current_user_name = current_user_profile.get('name', 'N/A')

    st.write(f"**Employee:** {current_user_name}")
    st.write(f"**Staff ID:** {current_staff_id}")

    with st.form("performance_goal_form", clear_on_submit=True):
        goal_title = st.text_input("Goal Title", help="e.g., Improve Customer Satisfaction")
        goal_description = st.text_area("Goal Description", help="Provide a detailed description of the goal and what it entails.")
        due_date = st.date_input("Due Date", min_value=date.today() + timedelta(days=1))
        # Assuming goals are initially set by the employee for their review/approval by a manager
        submitted = st.form_submit_button("Set Goal")

        if submitted:
            if not goal_title or not goal_description:
                st.error("Please fill in all required fields (Goal Title, Goal Description, Due Date).")
            else:
                goal_id = f"PG-{len(st.session_state.performance_goals) + 1:04d}"
                new_goal = {
                    "goal_id": goal_id,
                    "staff_id": current_staff_id,
                    "employee_name": current_user_name,
                    "goal_title": goal_title,
                    "goal_description": goal_description,
                    "due_date": due_date.isoformat(),
                    "set_date": datetime.now().isoformat(),
                    "status": "Pending Review", # e.g., Pending Review, Approved, Completed, Overdue
                    "manager_comment": "",
                    "employee_updates": [],
                    "final_score": None
                }
                st.session_state.performance_goals.append(new_goal)
                save_data(st.session_state.performance_goals, PERFORMANCE_GOALS_FILE)
                st.success(f"Performance goal '{goal_title}' set successfully with ID: {goal_id}!")
                st.rerun()

def view_my_goals():
    st.title("👀 My Performance Goals")
    current_user_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id', 'N/A')

    user_goals = [
        goal for goal in st.session_state.performance_goals
        if goal.get('staff_id') == current_user_staff_id
    ]

    if not user_goals:
        st.info("You have not set any performance goals yet.")
        return

    df_goals = pd.DataFrame(user_goals)
    df_goals['set_date'] = pd.to_datetime(df_goals['set_date']).dt.strftime('%Y-%m-%d %H:%M')
    df_goals['due_date'] = pd.to_datetime(df_goals['due_date']).dt.strftime('%Y-%m-%d')

    display_cols = ['goal_id', 'goal_title', 'due_date', 'status', 'manager_comment']
    st.dataframe(df_goals[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Goal Details and Updates")
    for i, goal in enumerate(user_goals):
        expander_title = f"Goal: {goal['goal_title']} (Status: {goal['status']})"
        with st.expander(expander_title):
            st.write(f"**Goal ID:** {goal.get('goal_id')}")
            st.write(f"**Description:** {goal.get('goal_description')}")
            st.write(f"**Set Date:** {goal.get('set_date')}")
            st.write(f"**Due Date:** {goal.get('due_date')}")
            st.write(f"**Status:** {goal.get('status')}")
            st.write(f"**Manager Comment:** {goal.get('manager_comment', 'N/A')}")
            st.write(f"**Final Score:** {goal.get('final_score', 'N/A')}")

            st.markdown("##### Employee Updates:")
            if goal.get('employee_updates'):
                for update in goal['employee_updates']:
                    st.markdown(f"- On {update.get('date')}: {update.get('comment')}")
            else:
                st.info("No updates recorded yet.")
            
            # Allow employee to add updates if goal is not completed/overdue
            if goal.get('status') not in ['Completed', 'Overdue', 'Rejected']:
                with st.form(key=f"goal_update_form_{goal['goal_id']}"):
                    new_update_comment = st.text_area("Add an Update to this Goal", key=f"update_comment_{goal['goal_id']}")
                    if st.form_submit_button("Submit Update", key=f"submit_update_{goal['goal_id']}"):
                        if new_update_comment:
                            for idx, g in enumerate(st.session_state.performance_goals):
                                if g['goal_id'] == goal['goal_id']:
                                    st.session_state.performance_goals[idx]['employee_updates'].append({
                                        "date": datetime.now().isoformat(),
                                        "comment": new_update_comment
                                    })
                                    save_data(st.session_state.performance_goals, PERFORMANCE_GOALS_FILE)
                                    st.success("Goal update submitted!")
                                    st.rerun()
                        else:
                            st.warning("Please enter a comment for your update.")
            st.markdown("---")

# --- Self-Appraisal ---
def self_appraisal():
    st.title("✍️ Self-Appraisal")
    current_user_profile = st.session_state.current_user.get('profile', {})
    current_staff_id = current_user_profile.get('staff_id')
    current_user_name = current_user_profile.get('name', 'N/A')

    st.write(f"**Employee:** {current_user_name}")
    st.write(f"**Staff ID:** {current_staff_id}")

    st.markdown("---")
    st.subheader("New Self-Appraisal Submission")

    # Check for existing pending appraisal for the current year (simple check)
    current_year = datetime.now().year
    existing_appraisal_this_year = next((
        app for app in st.session_state.self_appraisals
        if app.get('staff_id') == current_staff_id and 
           datetime.fromisoformat(app.get('submission_date')).year == current_year and
           app.get('status') == 'Pending'
    ), None)

    if existing_appraisal_this_year:
        st.warning(f"You already have a pending self-appraisal for {current_year}. Please await review or view your existing appraisal.")
        if st.button("View My Pending Appraisal"):
            st.session_state.current_page = "view_my_appraisals"
            st.rerun()
        return

    with st.form("self_appraisal_form", clear_on_submit=True):
        st.markdown("Please evaluate your performance based on the following criteria:")

        # Example appraisal questions
        q1 = st.slider("1. How would you rate your overall performance in achieving your goals?", 1, 5, 3)
        c1 = st.text_area("   *Comments on Goal Achievement:*")
        
        q2 = st.slider("2. To what extent did you demonstrate teamwork and collaboration?", 1, 5, 3)
        c2 = st.text_area("   *Comments on Teamwork:*")

        q3 = st.slider("3. How well did you adapt to changes and new challenges?", 1, 5, 3)
        c3 = st.text_area("   *Comments on Adaptability:*")
        
        achievements = st.text_area("4. List your key achievements and contributions during this period:")
        improvements = st.text_area("5. What areas do you believe you need to improve, and how do you plan to do so?")
        support_needed = st.text_area("6. What support or training do you need from the company to enhance your performance?")
        
        submitted = st.form_submit_button("Submit Self-Appraisal")

        if submitted:
            if not achievements or not improvements or not support_needed:
                st.error("Please fill in all text areas (Achievements, Improvements, Support Needed).")
            else:
                appraisal_id = f"SA-{len(st.session_state.self_appraisals) + 1:04d}"
                new_appraisal = {
                    "appraisal_id": appraisal_id,
                    "staff_id": current_staff_id,
                    "employee_name": current_user_name,
                    "appraisal_period": current_year, # Simple: current year
                    "q1_rating": q1,
                    "q1_comment": c1,
                    "q2_rating": q2,
                    "q2_comment": c2,
                    "q3_rating": q3,
                    "q3_comment": c3,
                    "achievements": achievements,
                    "improvements": improvements,
                    "support_needed": support_needed,
                    "submission_date": datetime.now().isoformat(),
                    "status": "Pending", # Pending, Reviewed, Approved
                    "manager_feedback": "",
                    "final_score": None
                }
                st.session_state.self_appraisals.append(new_appraisal)
                save_data(st.session_state.self_appraisals, SELF_APPRAISALS_FILE)
                st.success(f"Self-appraisal for {current_year} submitted successfully!")
                st.rerun()

def view_my_appraisals():
    st.title("👀 My Self-Appraisals")
    current_user_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id', 'N/A')

    user_appraisals = [
        app for app in st.session_state.self_appraisals
        if app.get('staff_id') == current_user_staff_id
    ]

    if not user_appraisals:
        st.info("You have not submitted any self-appraisals yet.")
        return

    df_appraisals = pd.DataFrame(user_appraisals)
    df_appraisals['submission_date'] = pd.to_datetime(df_appraisals['submission_date']).dt.strftime('%Y-%m-%d %H:%M')

    display_cols = ['appraisal_id', 'appraisal_period', 'submission_date', 'status', 'final_score']
    st.dataframe(df_appraisals[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Appraisal Details and Manager Feedback")
    for i, appraisal in enumerate(user_appraisals):
        expander_title = f"Appraisal ID: {appraisal['appraisal_id']} for {appraisal['appraisal_period']} - Status: {appraisal['status']}"
        with st.expander(expander_title):
            st.write(f"**Employee:** {appraisal.get('employee_name')}")
            st.write(f"**Appraisal Period:** {appraisal.get('appraisal_period')}")
            st.write(f"**Submission Date:** {appraisal.get('submission_date')}")
            st.write(f"**Status:** {appraisal.get('status')}")
            st.write(f"**Final Score (Manager):** {appraisal.get('final_score', 'N/A')}")
            
            st.markdown("##### Your Self-Evaluation:")
            st.write(f"- **Overall performance on goals (1-5):** {appraisal.get('q1_rating')}")
            st.write(f"  *Comments:* {appraisal.get('q1_comment', 'N/A')}")
            st.write(f"- **Teamwork and collaboration (1-5):** {appraisal.get('q2_rating')}")
            st.write(f"  *Comments:* {appraisal.get('q2_comment', 'N/A')}")
            st.write(f"- **Adaptability to changes (1-5):** {appraisal.get('q3_rating')}")
            st.write(f"  *Comments:* {appraisal.get('q3_comment', 'N/A')}")
            st.write(f"**Key Achievements:** {appraisal.get('achievements')}")
            st.write(f"**Areas for Improvement:** {appraisal.get('improvements')}")
            st.write(f"**Support/Training Needed:** {appraisal.get('support_needed')}")

            st.markdown("##### Manager's Feedback:")
            if appraisal.get('manager_feedback'):
                st.write(appraisal.get('manager_feedback'))
            else:
                st.info("No manager feedback yet.")
            st.markdown("---")


# --- My Payslips ---
def my_payslips():
    st.title("💰 My Payslips")
    current_user_staff_id = st.session_state.current_user.get('profile', {}).get('staff_id', 'N/A')

    if not st.session_state.payroll_data:
        st.info("No payroll data available yet. Please contact HR.")
        return

    # Filter payroll data for the current user
    user_payslips = [
        payslip for payslip in st.session_state.payroll_data
        if payslip.get('staff_id') == current_user_staff_id
    ]

    if not user_payslips:
        st.info("No payslips found for your Staff ID.")
        return

    # Create a DataFrame for display
    df_payslips = pd.DataFrame(user_payslips)
    
    # Ensure 'payment_date' is a datetime object for sorting
    if 'payment_date' in df_payslips.columns:
        df_payslips['payment_date'] = pd.to_datetime(df_payslips['payment_date'], errors='coerce')
        df_payslips = df_payslips.sort_values(by='payment_date', ascending=False)
        df_payslips['payment_date'] = df_payslips['payment_date'].dt.strftime('%Y-%m-%d') # Format back for display

    # Select columns to display
    display_cols = ['payment_date', 'pay_period', 'gross_pay', 'net_pay', 'status']
    st.dataframe(df_payslips[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Payslip Details")
    for payslip in user_payslips:
        expander_title = f"Payslip for {payslip.get('pay_period')} (Paid: {payslip.get('payment_date', 'N/A')})"
        with st.expander(expander_title):
            st.json(payslip) # Display full JSON for details
            # You might generate a PDF payslip here or provide a download link if physical files exist.

# --- HR Policies ---
def hr_policies():
    st.title("📄 HR Policies")

    if not st.session_state.hr_policies:
        st.info("No HR policies available yet.")
        return

    policy_names = list(st.session_state.hr_policies.keys())
    selected_policy = st.selectbox("Select a Policy", policy_names)

    if selected_policy:
        st.markdown(f"### {selected_policy}")
        st.write(st.session_state.hr_policies.get(selected_policy, "Policy content not found."))

# --- Admin Functions ---
def admin_manage_users():
    st.title("👥 Manage Users")
    st.subheader("All System Users")

    if not st.session_state.users:
        st.info("No users found in the system.")
        return

    df_users = pd.DataFrame(st.session_state.users)
    
    # Flatten profile data for better display in DataFrame
    df_users_display = df_users.copy()
    profile_data = df_users_display['profile'].apply(pd.Series)
    df_users_display = pd.concat([df_users_display.drop('profile', axis=1), profile_data], axis=1)

    # Select relevant columns for display
    display_cols = ['username', 'role', 'name', 'staff_id', 'department', 'grade_level', 'email_address', 'phone_number']
    st.dataframe(df_users_display[display_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.subheader("Add New User")

    with st.form("add_user_form", clear_on_submit=True):
        new_username = st.text_input("New User ID (e.g., john.doe)", key="new_username")
        new_password = st.text_input("Temporary Password", type="password", key="new_password")
        new_user_role = st.selectbox("Role", ["staff", "admin"], key="new_user_role")
        
        st.markdown("##### New User Profile Details")
        new_user_staff_id = st.text_input("Staff ID", key="new_user_staff_id")
        new_user_name = st.text_input("Full Name", key="new_user_name")
        new_user_email = st.text_input("Email Address", key="new_user_email")
        new_user_phone = st.text_input("Phone Number", key="new_user_phone")
        new_user_dob = st.date_input("Date of Birth", max_value=date.today(), key="new_user_dob")
        new_user_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], key="new_user_gender_new")
        new_user_department = st.selectbox("Department", ["", "Administration", "HR", "Finance", "Executive", "Marketing", "Operations", "IT"], key="new_user_dept_new")
        new_user_grade_level = st.selectbox("Grade Level", ["", "Intern", "Officer", "Senior Officer", "Manager", "Senior Manager", "MD"], key="new_user_grade_new")
        new_user_education = st.text_area("Education Background", key="new_user_edu")
        new_user_experience = st.text_area("Professional Experience", key="new_user_exp")
        new_user_work_anniversary = st.date_input("Work Anniversary", max_value=date.today(), key="new_user_wa")

        add_user_submitted = st.form_submit_button("Add User")

        if add_user_submitted:
            if not new_username or not new_password or not new_user_staff_id or not new_user_name:
                st.error("User ID, Password, Staff ID, and Full Name are required.")
            elif any(u['username'] == new_username for u in st.session_state.users):
                st.error("Username already exists.")
            else:
                hashed_password = pbkdf2_sha256.hash(new_password)
                new_user_obj = {
                    "username": new_username,
                    "password": hashed_password,
                    "role": new_user_role,
                    "profile": {
                        "staff_id": new_user_staff_id,
                        "name": new_user_name,
                        "date_of_birth": new_user_dob.isoformat() if new_user_dob else '',
                        "gender": new_user_gender,
                        "grade_level": new_user_grade_level,
                        "department": new_user_department,
                        "education_background": new_user_education,
                        "professional_experience": new_user_experience,
                        "address": "", # Placeholder, can be added later
                        "phone_number": new_user_phone,
                        "email_address": new_user_email,
                        "training_attended": [], # Can be managed via profile edit
                        "work_anniversary": new_user_work_anniversary.isoformat() if new_user_work_anniversary else ''
                    }
                }
                st.session_state.users.append(new_user_obj)
                save_data(st.session_state.users, USERS_FILE)
                st.success(f"User '{new_username}' added successfully!")
                st.rerun()
    
    st.markdown("---")
    st.subheader("Edit/Delete User (Admin Only)")
    # Admin can edit/delete users
    user_to_manage_username = st.selectbox("Select User to Edit/Delete", [""] + [u['username'] for u in st.session_state.users if u['username'] != st.session_state.current_user['username']])

    if user_to_manage_username:
        user_to_manage_idx = next((i for i, u in enumerate(st.session_state.users) if u['username'] == user_to_manage_username), -1)
        if user_to_manage_idx != -1:
            selected_user = st.session_state.users[user_to_manage_idx]
            selected_user_profile = selected_user.get('profile', {})

            st.write(f"**Managing: {selected_user_profile.get('name', selected_user_username)}**")

            with st.form(f"edit_user_form_{user_to_manage_username}"):
                # Editable fields
                edited_role = st.selectbox("Role", ["staff", "admin"], index=["staff", "admin"].index(selected_user['role']), key=f"edit_role_{user_to_manage_username}")
                # Profile fields
                edited_staff_id = st.text_input("Staff ID", value=selected_user_profile.get('staff_id', ''), key=f"edit_staff_id_{user_to_manage_username}")
                edited_name = st.text_input("Full Name", value=selected_user_profile.get('name', ''), key=f"edit_name_{user_to_manage_username}")
                edited_email = st.text_input("Email Address", value=selected_user_profile.get('email_address', ''), key=f"edit_email_{user_to_manage_username}")
                edited_phone = st.text_input("Phone Number", value=selected_user_profile.get('phone_number', ''), key=f"edit_phone_{user_to_manage_username}")

                current_dob_str = selected_user_profile.get('date_of_birth')
                current_dob_date = datetime.strptime(current_dob_str, '%Y-%m-%d').date() if current_dob_str else None
                edited_dob = st.date_input("Date of Birth", value=current_dob_date, max_value=date.today(), key=f"edit_dob_{user_to_manage_username}")

                edited_gender = st.selectbox("Gender", ["", "Male", "Female", "Other"], index=["", "Male", "Female", "Other"].index(selected_user_profile.get('gender', '')), key=f"edit_gender_{user_to_manage_username}")
                edited_department = st.selectbox("Department", ["", "Administration", "HR", "Finance", "Executive", "Marketing", "Operations", "IT"], index=["", "Administration", "HR", "Finance", "Executive", "Marketing", "Operations", "IT"].index(selected_user_profile.get('department', '')), key=f"edit_dept_{user_to_manage_username}")
                edited_grade_level = st.selectbox("Grade Level", ["", "Intern", "Officer", "Senior Officer", "Manager", "Senior Manager", "MD"], index=["", "Intern", "Officer", "Senior Officer", "Manager", "Senior Manager", "MD"].index(selected_user_profile.get('grade_level', '')), key=f"edit_grade_{user_to_manage_username}")
                edited_education = st.text_area("Education Background", value=selected_user_profile.get('education_background', ''), key=f"edit_edu_{user_to_manage_username}")
                edited_experience = st.text_area("Professional Experience", value=selected_user_profile.get('professional_experience', ''), key=f"edit_exp_{user_to_manage_username}")
                
                current_wa_str = selected_user_profile.get('work_anniversary')
                current_wa_date = datetime.strptime(current_wa_str, '%Y-%m-%d').date() if current_wa_str else None
                edited_work_anniversary = st.date_input("Work Anniversary", value=current_wa_date, max_value=date.today(), key=f"edit_wa_{user_to_manage_username}")


                col_edit, col_delete = st.columns(2)
                edit_submitted = col_edit.form_submit_button("Update User")
                delete_submitted = col_delete.form_submit_button("Delete User", type="secondary") # Use type secondary for delete

                if edit_submitted:
                    st.session_state.users[user_to_manage_idx]['role'] = edited_role
                    st.session_state.users[user_to_manage_idx]['profile']['staff_id'] = edited_staff_id
                    st.session_state.users[user_to_manage_idx]['profile']['name'] = edited_name
                    st.session_state.users[user_to_manage_idx]['profile']['email_address'] = edited_email
                    st.session_state.users[user_to_manage_idx]['profile']['phone_number'] = edited_phone
                    st.session_state.users[user_to_manage_idx]['profile']['date_of_birth'] = edited_dob.isoformat() if edited_dob else ''
                    st.session_state.users[user_to_manage_idx]['profile']['gender'] = edited_gender
                    st.session_state.users[user_to_manage_idx]['profile']['department'] = edited_department
                    st.session_state.users[user_to_manage_idx]['profile']['grade_level'] = edited_grade_level
                    st.session_state.users[user_to_manage_idx]['profile']['education_background'] = edited_education
                    st.session_state.users[user_to_manage_idx]['profile']['professional_experience'] = edited_experience
                    st.session_state.users[user_to_manage_idx]['profile']['work_anniversary'] = edited_work_anniversary.isoformat() if edited_work_anniversary else ''


                    save_data(st.session_state.users, USERS_FILE)
                    st.success(f"User '{user_to_manage_username}' updated successfully!")
                    st.rerun()

                if delete_submitted:
                    # Add a confirmation step for deletion
                    if st.warning(f"Are you sure you want to delete user '{user_to_manage_username}'? This action cannot be undone."):
                        if st.button("Confirm Delete", key=f"confirm_delete_{user_to_manage_username}"):
                            del st.session_state.users[user_to_manage_idx]
                            save_data(st.session_state.users, USERS_FILE)
                            st.success(f"User '{user_to_manage_username}' deleted successfully.")
                            st.rerun()
            st.markdown("---") # Separator between forms

# --- Upload Payroll (Admin Function) ---
def upload_payroll():
    st.title("📤 Upload Payroll Data")
    st.write("Upload a CSV file containing payroll information.")
    st.info("Expected CSV columns: `staff_id`, `pay_period`, `gross_pay`, `deductions`, `net_pay`, `payment_date`, `status` (e.g., Paid)")

    uploaded_file = st.file_uploader("Choose a CSV file", type="csv")

    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            st.write("Preview of uploaded data:")
            st.dataframe(df)

            required_cols = ['staff_id', 'pay_period', 'gross_pay', 'deductions', 'net_pay', 'payment_date', 'status']
            if not all(col in df.columns for col in required_cols):
                st.error(f"Missing one or more required columns. Please ensure your CSV has: {', '.join(required_cols)}")
                return

            if st.button("Process and Save Payroll Data"):
                # Convert DataFrame to list of dictionaries for JSON storage
                new_payroll_records = df.to_dict(orient='records')
                
                # Append new records to existing ones, avoiding duplicates if necessary (e.g., by staff_id + pay_period)
                # For simplicity, this example just appends. A more robust system would handle updates/duplicates.
                st.session_state.payroll_data.extend(new_payroll_records)
                save_data(st.session_state.payroll_data, PAYROLL_FILE)
                st.success(f"Successfully uploaded and saved {len(new_payroll_records)} payroll records.")
                st.rerun()

        except Exception as e:
            st.error(f"Error processing file: {e}")

# --- Manage Beneficiaries (Admin Function) ---
def admin_manage_beneficiaries():
    st.title("🏦 Manage Beneficiaries")
    st.subheader("Current Beneficiaries")

    if not st.session_state.beneficiaries:
        st.info("No beneficiaries configured yet.")
        return

    # Convert beneficiaries dictionary to a list for DataFrame display
    beneficiary_list = []
    for name, details in st.session_state.beneficiaries.items():
        if name != "Other (Manually Enter Details)": # Don't list this as a managed beneficiary
            beneficiary_list.append({
                "Vendor Name": name,
                "Account Name": details.get("Account Name"),
                "Account No": details.get("Account No"),
                "Bank": details.get("Bank")
            })
    
    if beneficiary_list:
        df_beneficiaries = pd.DataFrame(beneficiary_list)
        st.dataframe(df_beneficiaries, use_container_width=True, hide_index=True)
    else:
        st.info("No defined beneficiaries (excluding manual entry option).")


    st.markdown("---")
    st.subheader("Add New Beneficiary")
    with st.form("add_beneficiary_form", clear_on_submit=True):
        new_vendor_name = st.text_input("Vendor Name (e.g., ABC Solutions Ltd)")
        new_account_name = st.text_input("Account Name")
        new_account_no = st.text_input("Account Number")
        new_bank = st.text_input("Bank Name")
        
        add_submitted = st.form_submit_button("Add Beneficiary")

        if add_submitted:
            if not new_vendor_name or not new_account_name or not new_account_no or not new_bank:
                st.error("All fields are required to add a beneficiary.")
            elif new_vendor_name in st.session_state.beneficiaries:
                st.error("Beneficiary with this name already exists.")
            else:
                st.session_state.beneficiaries[new_vendor_name] = {
                    "Account Name": new_account_name,
                    "Account No": new_account_no,
                    "Bank": new_bank
                }
                save_data(st.session_state.beneficiaries, BENEFICIARIES_FILE)
                st.success(f"Beneficiary '{new_vendor_name}' added successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Edit/Delete Beneficiary")
    # Exclude the "Other" option from direct editing/deletion
    editable_beneficiaries = [name for name in st.session_state.beneficiaries.keys() if name != "Other (Manually Enter Details)"]
    selected_beneficiary_name = st.selectbox("Select Beneficiary to Edit/Delete", [""] + editable_beneficiaries)

    if selected_beneficiary_name:
        current_b_details = st.session_state.beneficiaries[selected_beneficiary_name]
        with st.form(f"edit_beneficiary_form_{selected_beneficiary_name}"):
            edited_vendor_name = st.text_input("Vendor Name", value=selected_beneficiary_name, key=f"edit_vendor_name_{selected_beneficiary_name}", disabled=True) # Name usually not editable
            edited_account_name = st.text_input("Account Name", value=current_b_details.get("Account Name", ""), key=f"edit_account_name_{selected_beneficiary_name}")
            edited_account_no = st.text_input("Account Number", value=current_b_details.get("Account No", ""), key=f"edit_account_no_{selected_beneficiary_name}")
            edited_bank = st.text_input("Bank Name", value=current_b_details.get("Bank", ""), key=f"edit_bank_{selected_beneficiary_name}")

            col_edit, col_delete = st.columns(2)
            edit_submitted = col_edit.form_submit_button("Update Beneficiary")
            delete_submitted = col_delete.form_submit_button("Delete Beneficiary", type="secondary")

            if edit_submitted:
                if not edited_account_name or not edited_account_no or not edited_bank:
                    st.error("All fields are required for update.")
                else:
                    st.session_state.beneficiaries[selected_beneficiary_name] = {
                        "Account Name": edited_account_name,
                        "Account No": edited_account_no,
                        "Bank": edited_bank
                    }
                    save_data(st.session_state.beneficiaries, BENEFICIARIES_FILE)
                    st.success(f"Beneficiary '{selected_beneficiary_name}' updated successfully!")
                    st.rerun()

            if delete_submitted:
                if st.warning(f"Are you sure you want to delete beneficiary '{selected_beneficiary_name}'?"):
                    if st.button("Confirm Delete", key=f"confirm_delete_b_{selected_beneficiary_name}"):
                        del st.session_state.beneficiaries[selected_beneficiary_name]
                        save_data(st.session_state.beneficiaries, BENEFICIARIES_FILE)
                        st.success(f"Beneficiary '{selected_beneficiary_name}' deleted successfully.")
                        st.rerun()
            st.markdown("---")

# --- Manage HR Policies (Admin Function) ---
def admin_manage_hr_policies():
    st.title("📜 Manage HR Policies")
    st.subheader("Current HR Policies")

    if not st.session_state.hr_policies:
        st.info("No HR policies defined yet.")
        st.session_state.hr_policies = {} # Initialize if empty to prevent errors

    # Display policies in a read-only table or list for overview
    policy_data = [{"Policy Name": name, "Content Snippet": content[:100] + "..." if len(content) > 100 else content} 
                    for name, content in st.session_state.hr_policies.items()]
    if policy_data:
        st.dataframe(pd.DataFrame(policy_data), use_container_width=True, hide_index=True)
    else:
        st.info("No policies to display.")

    st.markdown("---")
    st.subheader("Add New Policy")
    with st.form("add_policy_form", clear_on_submit=True):
        new_policy_name = st.text_input("Policy Name")
        new_policy_content = st.text_area("Policy Content", height=200)
        
        add_submitted = st.form_submit_button("Add Policy")
        
        if add_submitted:
            if not new_policy_name or not new_policy_content:
                st.error("Both Policy Name and Policy Content are required.")
            elif new_policy_name in st.session_state.hr_policies:
                st.error("A policy with this name already exists. Please use a unique name or edit the existing one.")
            else:
                st.session_state.hr_policies[new_policy_name] = new_policy_content
                save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                st.success(f"Policy '{new_policy_name}' added successfully!")
                st.rerun()

    st.markdown("---")
    st.subheader("Edit/Delete Policy")
    # Create a list of policy names for the selectbox
    policy_options = [""] + list(st.session_state.hr_policies.keys())
    selected_policy_to_manage = st.selectbox("Select Policy to Edit/Delete", policy_options)

    if selected_policy_to_manage and selected_policy_to_manage != "":
        current_policy_content = st.session_state.hr_policies.get(selected_policy_to_manage, "")

        with st.form(f"edit_delete_policy_form_{selected_policy_to_manage}"):
            edited_policy_name_display = st.text_input("Policy Name (Not editable directly)", value=selected_policy_to_manage, disabled=True)
            edited_policy_content = st.text_area("Policy Content", value=current_policy_content, height=300, key=f"edit_content_{selected_policy_to_manage}")
            
            col_edit, col_delete = st.columns(2)
            edit_submitted = col_edit.form_submit_button("Update Policy")
            delete_submitted = col_delete.form_submit_button("Delete Policy", type="secondary")

            if edit_submitted:
                if not edited_policy_content:
                    st.error("Policy content cannot be empty.")
                else:
                    st.session_state.hr_policies[selected_policy_to_manage] = edited_policy_content
                    save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                    st.success(f"Policy '{selected_policy_to_manage}' updated successfully!")
                    st.rerun()

            if delete_submitted:
                if st.warning(f"Are you sure you want to delete policy '{selected_policy_to_manage}'? This action cannot be undone."):
                    if st.button("Confirm Delete", key=f"confirm_delete_policy_{selected_policy_to_manage}"):
                        del st.session_state.hr_policies[selected_policy_to_manage]
                        save_data(st.session_state.hr_policies, HR_POLICIES_FILE)
                        st.success(f"Policy '{selected_policy_to_manage}' deleted successfully.")
                        st.rerun()
            st.markdown("---")


# --- Main Application Logic ---
def main():
    setup_initial_data() # Ensure initial data exists on first run

    if st.session_state.logged_in:
        display_sidebar()
        if st.session_state.current_page == "dashboard":
            display_dashboard()
        elif st.session_state.current_page == "my_profile":
            display_my_profile()
        elif st.session_state.current_page == "leave_request":
            leave_request_form()
        elif st.session_state.current_page == "view_my_leave":
            view_my_leave()
        elif st.session_state.current_page == "opex_capex_form":
            opex_capex_form()
        elif st.session_state.current_page == "view_my_opex_capex":
            view_my_opex_capex()
        elif st.session_state.current_page == "performance_goal_setting":
            performance_goal_setting()
        elif st.session_state.current_page == "view_my_goals":
            view_my_goals()
        elif st.session_state.current_page == "self_appraisal":
            self_appraisal()
        elif st.session_state.current_page == "view_my_appraisals":
            view_my_appraisals()
        elif st.session_state.current_page == "hr_policies":
            hr_policies()
        elif st.session_state.current_page == "my_payslips":
            my_payslips()
        # Admin functions
        elif st.session_state.current_page == "manage_users":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_users()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "upload_payroll":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                upload_payroll()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_opex_capex_approvals":
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
                admin_manage_opex_capex_approvals()
            else:
                st.error("Access Denied: You do not have permission to view this page.")
                st.session_state.current_page = "dashboard"
                st.rerun()
        elif st.session_state.current_page == "manage_leave_approvals": # NEWLY ADDED
            if st.session_state.current_user and st.session_state.current_user['role'] == 'admin':
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
    else:
        login_form()

if __name__ == "__main__":
    main()
