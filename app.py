import streamlit as st
import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore, exceptions
import random, string
import time
import subprocess, sys


# Initialize Firebase only if not already initialized
def initialize_firebase():
    try:
        # Check if Firebase has already been initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        
    except Exception as e:
        st.write(f"Error initializing Firebase: {e}")

# Initialize Firebase (only once)
initialize_firebase()

# Initialize Firestore client
db = firestore.client()

# Collection references
employees_ref = db.collection('employees')
job_sites_ref = db.collection('job_sites')
assignments_ref = db.collection('assignments')

# Streamlit UI for adding an employee
def add_employee_form():
    st.header("Add Employee")

    # Generate a random worker ID
    worker_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

    first_name = st.text_input("First Name")
    middle_name = st.text_input("Middle Name")
    sur_name = st.text_input("Surname")
    phone_number = st.text_input("Phone Number")  # Changed from number_input to text_input for better validation
    home_address = st.text_input("Home Location (e.g., 43.7,-79.3 for Toronto)")
    have_car = st.selectbox("Do you have a car?", ["Yes", "No"])
    
    role = st.multiselect("Role", ["Cleaner", "Labour", "Painter"])

    availability = st.multiselect("Availability", ["7:00-15:30", "14:00-22:00", "22:00-06:00"])
    
    certificates = st.multiselect("Certifications", ["Working at Heights", "4 Steps", "WHMIS"])
    
    skills = st.multiselect("Skills", ["Boomlift", "Scissors Lift", "Forklift"])
    
    rating = st.slider("Employee Rating", min_value=0.0, max_value=5.0, value=3.0, step=0.1)  # Allows float rating selection
    
    if st.button("Add Employee"):
        employee_data = {
            "worker_id": worker_id,
            "first_name": first_name,
            "middle_name": middle_name,
            "sur_name": sur_name,
            "phone_number": phone_number,
            "home_address": home_address,
            "have_car": have_car,
            "role": role,
            "availability": availability,
            "certificates": certificates,
            "skills": skills,
            "rating": rating
        }

        # Add document to Firestore
        doc_ref = employees_ref.add(employee_data)

        # Check the result of the add() operation
        if isinstance(doc_ref, tuple):
            # Handle the case where add() returns a tuple
            employee_id = doc_ref[0]  # Extract the ID from the tuple
        else:
            # Normally, doc_ref should be a DocumentReference
            employee_id = doc_ref.id

        st.success(f"Employee {first_name} {sur_name} added with ID: {employee_id}")



# Streamlit UI for viewing all employees
from datetime import datetime, timezone

# ✅ Streamlit UI for Viewing Employees
def view_employees():
    st.header("View Employees")

    # Fetch employee data
    docs = employees_ref.stream()
    employee_data = []

    for doc in docs:
        data = doc.to_dict()
        data['worker_id'] = data.get('worker_id', "N/A")
        
        # Ensure role, skills, certificates, and availability are always lists
        data['role'] = data.get('role', []) if isinstance(data.get('role'), list) else [data.get('role', "")]
        data['skills'] = data.get('skills', []) if isinstance(data.get('skills'), list) else [data.get('skills', "")]
        data['certificates'] = data.get('certificates', []) if isinstance(data.get('certificates'), list) else [data.get('certificates', "")]
        data['availability'] = data.get('availability', []) if isinstance(data.get('availability'), list) else [data.get('availability', "")]
        
        employee_data.append(data)

    # Define the desired column order
    column_order = [
        'worker_id', 'first_name', 'middle_name', 'sur_name', 'phone_number', 'home_address','have_car', 
        'role', 'skills', 'certificates', 'availability', 'rating'
    ]

    # Convert to DataFrame and display in the specified order
    if employee_data:
        df = pd.DataFrame(employee_data)

        # Ensure the columns are displayed in the desired order
        df = df[column_order]

        st.dataframe(df)
    else:
        st.write("No employees found.")


#--------------------------------------------


# ✅ Streamlit UI for Adding a Job Site
def add_job_site_form():
    st.header("Add Job Site")

    site_id = f"SITE{random.randint(1000, 9999)}"  # Auto-generated site ID
    st.write(f"Generated Site ID: {site_id}")  # Debugging output
    
    site_name = st.text_input("Site Name")
    site_company = st.text_input("Site Company")
    site_superintendent = st.text_input("Site Superintendent")
    site_contact_number = st.text_input("Site Contact Number")
    address = st.text_input("Site Address (Use Google Maps for accuracy)")
    
    # ✅ Job Site Status Selection
    job_status = st.selectbox("Job Site Status", ["Active", "Inactive", "Completed"])
    
    # ✅ Date Selection with Calendar Widget
    work_start_date = st.date_input("Work Start Date")
    work_end_date = st.date_input("Work End Date")
    
    # ✅ Required roles selection with toggle
    st.subheader("Required Roles")
    required_roles = {}
    roles = ["Cleaner", "Labour", "Painter"]
    
    for role in roles:
        toggle = st.toggle(f"Enable {role}", key=f"toggle_{role}")
        if toggle:
            st.write(f"### {role}")
            work_schedule = st.multiselect(
                f"Work Schedule for {role}",
                ["7:00-15:30", "14:00-22:00", "22:00-06:00"],
                key=f"schedule_{role}"
            )
            num_workers = st.number_input(f"Number of {role}s Required", min_value=0, step=1, key=f"workers_{role}")
            
            required_roles[role] = {"work_schedule": work_schedule, "num_workers": num_workers}
    
    if st.button("Add Job Site"):
        try:
            job_site_data = {
                "site_id": site_id,
                "site_name": site_name,
                "site_company": site_company,
                "site_superintendent": site_superintendent,
                "site_contact_number": site_contact_number,
                "address": address,
                "job_status": job_status,
                "work_start_date": work_start_date.strftime('%Y-%m-%d'),
                "work_end_date": work_end_date.strftime('%Y-%m-%d'),
                "required_roles": required_roles
            }
            
            doc_ref = job_sites_ref.document(site_id)  # Manually create document reference
            doc_ref.set(job_site_data)  # Store data explicitly

            # Verify if the document exists after writing
            if doc_ref.get().exists:
                st.success(f"Job Site {site_name} added with ID: {site_id}")
            else:
                st.error("Firestore write operation completed, but document not found.")
        except Exception as e:
            st.error(f"Error adding job site: {str(e)}")


#-----------------------------------------------------------------


# ✅ Streamlit UI for Running Assignments
def do_assignments():
    st.header("Run Assignments")
    st.write("Click the button below to run the assignment process and match employees to job sites. This will also remove old assignments to prevent duplicates.")
    
    if st.button("Run Assignments"):
        with st.spinner("Fetching new Employees and Job Sites..."):
            time.sleep(5)  # Simulate loading effect
        with st.spinner("Updating assignments..."):
            time.sleep(2)  # Simulate loading effect
            
            # ✅ Step 1: Delete Old Assignments
            try:
                old_assignments = assignments_ref.stream()
                for doc in old_assignments:
                    doc.reference.delete()
                print("🗑️ Old assignments deleted successfully.")
            except Exception as e:
                st.error(f"❌ Error deleting old assignments: {e}")
                return
            
            # ✅ Step 2: Run assign.py in the same Python environment
            python_executable = sys.executable  # Ensures it runs in the same environment as Streamlit
            process = subprocess.run([python_executable, "assign.py"], capture_output=True, text=True)
            
            if process.returncode == 0:
                st.success("✅ Successfully executed assign.py, updated assignments, and removed duplicates!")
            else:
                st.error(f"❌ Error running assign.py: {process.stderr}")
    
        with st.spinner("Loading the new assigments, please wait..."):
            time.sleep(2)  # Simulate loading effect

        view_assignments() 
    


# ✅ Streamlit UI for Viewing Job Sites
def view_job_sites():
    st.header("View Job Sites")

    # Fetch job sites from Firestore
    docs = job_sites_ref.stream()

    # Prepare data for the table
    job_sites_data = []
    for doc in docs:
        job_site = doc.to_dict()

        # Ensure essential fields exist, otherwise assign a default value
        job_site_data = {
            "Site ID": job_site.get("site_id", "N/A"),
            "Job Status": job_site.get("job_status", "N/A"),
            "Work Start Date": job_site.get("work_start_date", "N/A"),
            "Work End Date": job_site.get("work_end_date", "N/A"),
            "Site Name": job_site.get("site_name", "N/A"),
            "Company": job_site.get("site_company", "N/A"),
            "Superintendent": job_site.get("site_superintendent", "N/A"),
            "Contact Number": job_site.get("site_contact_number", "N/A"),
            "Address": job_site.get("address", "N/A"),
        }

        # ✅ Calculate total number of required workers
        required_roles = job_site.get("required_roles", {})
        total_workers = 0
        formatted_roles = []

        for role, details in required_roles.items():
            num_workers = details.get("num_workers", 0)
            schedule = ", ".join(details.get("work_schedule", [])) if "work_schedule" in details else "N/A"
            formatted_roles.append(f"{role} ({num_workers} workers, {schedule})")

            # Accumulate total workers
            total_workers += num_workers

        job_site_data["# Required Workers"] = total_workers  # Add computed num_workers
        job_site_data["Required Roles"] = ", ".join(formatted_roles) if formatted_roles else "N/A"

        job_sites_data.append(job_site_data)

    # Convert data to a DataFrame
    job_sites_df = pd.DataFrame(job_sites_data)

    # Define the correct column order
    column_order = ["Site ID", "Job Status", "Work Start Date", "Work End Date", "Site Name", "Company", "Superintendent", 
                    "Contact Number", "Address", "# Required Workers", "Required Roles"]

    # Ensure only existing columns are displayed
    job_sites_df = job_sites_df[column_order]

    # Display the data in a table format
    st.dataframe(job_sites_df)


#--------------------------------------------


def view_assignments():
    st.header("View Assignments")

    # Fetch assignments from Firestore
    docs = assignments_ref.stream()

    # Fetch all employees as a dictionary {worker_id: employee_data}
    employees_dict = {doc.to_dict().get("worker_id"): doc.to_dict() for doc in employees_ref.stream()}

    # Prepare data for the table
    assignments_data = []
    
    for doc in docs:
        assignment = doc.to_dict()

        # 🔹 Fetch job site details using job_site_id
        site_id = assignment.get("job_site_id", "N/A")
        site_doc = job_sites_ref.document(site_id).get()
        site_data = site_doc.to_dict() if site_doc.exists else {}

        # 🔹 Fetch employee details using employee_id
        employee_id = assignment.get("employee_id", "N/A")
        employee_data = employees_dict.get(employee_id, {})

        if not employee_data:
            print(f"⚠️ Employee {employee_id} not found in Firestore!")  # Debugging

        # 🔹 Retrieve distance from assignment document
        distance = assignment.get("distance", "N/A")  # ✅ Fetch Distance from Assignments Collection

        # 🔹 Construct a single row for the table with safe default values
        assignment_data = {
            "Site Name": site_data.get("site_name", "N/A"),
            "Company": site_data.get("site_company", "N/A"),
            "Address": site_data.get("address", "N/A"),
            "Num Workers": sum([details.get("num_workers", 0) for details in site_data.get("required_roles", {}).values()]) if site_data.get("required_roles") else 0,
            "Full Name": f"{employee_data.get('first_name', 'N/A')} {employee_data.get('middle_name', '')} {employee_data.get('sur_name', 'N/A')}".strip(),
            "Phone Number": employee_data.get("phone_number", "N/A"),
            "Home Address": employee_data.get("home_address", "N/A"),
            "Has Car": employee_data.get("have_car", "N/A"),
            "Role": assignment.get("role", "N/A"),
            "Skills": ", ".join(employee_data.get("skills", [])) if isinstance(employee_data.get("skills"), list) else "N/A",
            "Certificates": ", ".join(employee_data.get("certificates", [])) if isinstance(employee_data.get("certificates"), list) else "N/A",
            "Availability": ", ".join(employee_data.get("availability", [])) if isinstance(employee_data.get("availability"), list) else "N/A",
            "Rating": employee_data.get("rating", "N/A"),
            "Distance (km)": f"{distance:.2f} km" if isinstance(distance, (int, float)) else "N/A",  # ✅ Formatted Distance
        }

        assignments_data.append(assignment_data)

    # Convert data to a DataFrame
    assignments_df = pd.DataFrame(assignments_data)

    # Define expected column order with formatted names
    formatted_columns = ["Site Name", "Company", "Address", "Num Workers", "Full Name", "Phone Number", 
                         "Home Address", "Has Car", "Role", "Skills", "Certificates", "Availability", "Rating", "Distance (km)"]

    # ✅ Ensure only valid columns are selected
    existing_columns = [col for col in formatted_columns if col in assignments_df.columns]
    assignments_df = assignments_df[existing_columns] if existing_columns else pd.DataFrame(columns=formatted_columns)

    # ✅ Sort the DataFrame alphabetically by "Site Name"
    assignments_df = assignments_df.sort_values(by="Site Name", ascending=True)

    # ✅ Display the final table with formatted column names
    st.dataframe(assignments_df)




#--------------------------------------------

# ✅ Streamlit UI for Finding and Updating an Employee
def find_and_update_employee():
    st.header("Find and Update Employee")
    
    if st.button("New Search"):
        st.session_state.pop("selected_employee", None)
        st.session_state.pop("search_term", None)
        st.rerun()
    
    search_term = st.text_input("Search by Worker ID, Phone Number, First Name, or Last Name", value=st.session_state.get("search_term", "")).strip().lower()
    search_results = []

    if st.button("Search"):
        st.session_state["search_term"] = search_term
        query_ref = employees_ref.stream()
        
        for doc in query_ref:
            employee = doc.to_dict()
            
            if search_term in [
                str(employee.get("worker_id", "")).lower(),
                str(employee.get("phone_number", "")).lower(),
                str(employee.get("first_name", "")).lower(),
                str(employee.get("sur_name", "")).lower(),
            ]:
                employee["doc_id"] = doc.id  # Store Firestore document ID for updates
                search_results.append(employee)

        if search_results:
            selected_employee = st.selectbox(
                "Select Employee to Edit", 
                search_results, 
                format_func=lambda x: f"{x['first_name']} {x['sur_name']} ({x['worker_id']})"
            )
            if selected_employee:
                st.session_state["selected_employee"] = selected_employee
    
    if "selected_employee" in st.session_state:
        update_employee_form(st.session_state["selected_employee"]) 

# ✅ Streamlit UI for Updating Employee Details
def update_employee_form(employee):
    st.subheader("Update Employee Details")
    
    first_name = st.text_input("First Name", employee["first_name"])
    middle_name = st.text_input("Middle Name", employee["middle_name"])
    sur_name = st.text_input("Surname", employee["sur_name"])
    phone_number = st.text_input("Phone Number", employee["phone_number"])
    home_address = st.text_input("Home Address", employee["home_address"])
    have_car = st.selectbox("Do you have a car?", ["Yes", "No"], index=["Yes", "No"].index(employee["have_car"]))
    role = st.multiselect("Role", ["Cleaner", "Labour", "Painter"], default=employee["role"])
    availability = st.multiselect("Availability", ["7:00-15:30", "14:00-22:00", "22:00-06:00"], default=employee["availability"])
    certificates = st.multiselect("Certifications", ["Working at Heights", "4 Steps", "WHMIS"], default=employee["certificates"])
    skills = st.multiselect("Skills", ["Boomlift", "Scissors Lift", "Forklift"], default=employee["skills"])
    rating = st.slider("Employee Rating", min_value=0.0, max_value=5.0, value=float(employee["rating"]), step=0.1)
    
    if st.button("Update Employee"):
        updated_data = {
            "first_name": first_name,
            "middle_name": middle_name,
            "sur_name": sur_name,
            "phone_number": phone_number,
            "home_address": home_address,
            "have_car": have_car,
            "role": role,
            "availability": availability,
            "certificates": certificates,
            "skills": skills,
            "rating": rating
        }
        try:
            employees_ref.document(employee["doc_id"]).update(updated_data)
            st.success("Employee updated successfully!")
            st.session_state.pop("selected_employee", None)
        except Exception as e:
            st.error(f"Error updating employee: {str(e)}")

# ✅ Streamlit UI for Finding and Updating a Job Site
def find_and_update_job_site():
    st.header("Find and Update Job Site")
    
    if st.button("New Search"):
        st.session_state.pop("selected_job_site", None)
        st.session_state.pop("search_term_job", None)
        st.rerun()
    
    search_term = st.text_input("Search by Site ID, Site Name, Company, or Address", value=st.session_state.get("search_term_job", "")).strip().lower()
    search_results = []

    if st.button("Search"):
        st.session_state["search_term_job"] = search_term
        query_ref = job_sites_ref.stream()
        
        for doc in query_ref:
            job_site = doc.to_dict()
            
            if any(search_term in str(job_site.get(field, "")).lower() for field in ["site_id", "site_name", "site_company", "address"]):
                job_site["doc_id"] = doc.id  # Store Firestore document ID for updates
                search_results.append(job_site)

        if search_results:
            selected_job_site = st.selectbox(
                "Select Job Site to Edit", 
                search_results, 
                format_func=lambda x: f"{x['site_name']} ({x['site_id']})"
            )
            if selected_job_site:
                st.session_state["selected_job_site"] = selected_job_site
    
    if "selected_job_site" in st.session_state:
        update_job_site_form(st.session_state["selected_job_site"]) 

# ✅ Streamlit UI for Updating Job Site Details
def update_job_site_form(job_site):
    st.subheader("Update Job Site Details")
    
    site_name = st.text_input("Site Name", job_site["site_name"])
    site_company = st.text_input("Site Company", job_site["site_company"])
    site_superintendent = st.text_input("Site Superintendent", job_site["site_superintendent"])
    site_contact_number = st.text_input("Site Contact Number", job_site["site_contact_number"])
    address = st.text_input("Site Address", job_site["address"])
    job_status = st.selectbox("Job Status", ["Active", "Inactive", "Completed"], index=["Active", "Inactive", "Completed"].index(job_site["job_status"]))
    work_start_date = st.date_input("Work Start Date", pd.to_datetime(job_site["work_start_date"]))
    work_end_date = st.date_input("Work End Date", pd.to_datetime(job_site["work_end_date"]))
    
    if st.button("Update Job Site"):
        updated_data = {
            "site_name": site_name,
            "site_company": site_company,
            "site_superintendent": site_superintendent,
            "site_contact_number": site_contact_number,
            "address": address,
            "job_status": job_status,
            "work_start_date": work_start_date.strftime('%Y-%m-%d'),
            "work_end_date": work_end_date.strftime('%Y-%m-%d')
        }
        try:
            job_sites_ref.document(job_site["doc_id"]).update(updated_data)
            st.success("Job Site updated successfully!")
            st.session_state.pop("selected_job_site", None)
        except Exception as e:
            st.error(f"Error updating job site: {str(e)}")

# ✅ Streamlit UI to select and display different actions
def main():
    menu1 = ["Add Employee", "View Employees", "Find and Update"]
    choice1 = st.sidebar.selectbox("Employees Actions selection:", menu1, index=None)

    menu2 = ["Add Job Site", "View Job Sites", "Find and Update"]
    choice2 = st.sidebar.selectbox("Job Sites Actions selection:", menu2, index=None)

    menu3 = ["View Assignments", "Do Assignments"]
    choice3 = st.sidebar.selectbox("Assignments Actions selection:", menu3, index=None)

    if choice1 == "Add Employee":
        add_employee_form()
    elif choice1 == "View Employees":
        view_employees()
    elif choice1 == "Find and Update":
        find_and_update_employee()
    
    if choice2 == "Add Job Site":
        add_job_site_form()
    elif choice2 == "View Job Sites":
        view_job_sites()
    elif choice2 == "Find and Update":
        find_and_update_job_site()
    
    if choice3 == "Do Assignments":
        do_assignments()
    elif choice3 == "View Assignments":
        view_assignments()

if __name__ == '__main__':
    main()
