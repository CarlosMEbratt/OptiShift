import streamlit as st
import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore, exceptions
import random
from datetime import datetime

# Initialize Firebase only if not already initialized
def initialize_firebase():
    try:
        # Check if Firebase has already been initialized
        if not firebase_admin._apps:
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        else:
            st.write("Firebase already initialized.")
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

# Streamlit UI for creating employee
def add_employee_form():
    st.header("Add Employee")

    first_name = st.text_input("First Name")
    middle_name = st.text_input("Middle Name")
    sur_name = st.text_input("Surname")
    phone_number = st.number_input("Phone Number")
    role = st.selectbox("Role", ["Cleaner", "Labour", "Painter"])
    skills = st.multiselect("Skills", ["Cleaning", "Labour", "Painter"])
    certificates = st.multiselect("Certifications", ["WHMIS", "4 Steps", "Forklift", "Boomlift", "Working at Heights", "Scissors Lift"])
    availability = st.multiselect("Availability", ["7:00-15:30", "14:00-22:00", "22:00-06:00", "Full-Availability"])
    home_address = st.text_input("Home Location (e.g., 43.7,-79.3 for Toronto)")

    if st.button("Add Employee"):
        employee_data = {
            "availability": availability,
            "certificates": certificates,
            "first_name": first_name,
            "middle_name": middle_name,
            "sur_name": sur_name,
            "phone_number": phone_number,
            "skills": skills,
            "role": role,
            "home_address": home_address,
            "worker_id": f"EMP{random.randint(1000, 9999)}"
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
def view_employees():
    st.header("View Employees")

    # Fetch employee data
    docs = employees_ref.stream()
    employee_data = []

    for doc in docs:
        data = doc.to_dict()
        # Fetch the worker_id from Firestore document
        if 'worker_id' in data:
            data['worker_id'] = data['worker_id']  # Worker ID stored in Firestore
        else:
            data['worker_id'] = "N/A"  # Fallback if worker_id is not found
        employee_data.append(data)

    # Define the desired column order
    column_order = [
        'worker_id', 'first_name', 'middle_name', 'sur_name', 'phone_number', 'home_address',
        'role', 'skills', 'certificates', 'availability'
    ]

    # Convert to DataFrame and display in the specified order
    if employee_data:
        df = pd.DataFrame(employee_data)

        # Ensure the columns are displayed in the desired order
        df = df[column_order]

        st.dataframe(df)
    else:
        st.write("No employees found.")

# Streamlit UI for adding a job site
def add_job_site_form():
    st.header("Add Job Site")

    site_name = st.text_input("Site Name")
    location = st.text_input("Location (e.g., 43.7,-79.3 for Toronto)")
    start_date = st.date_input("Start Date")
    end_date = st.date_input("End Date")
    cleaning_scope = st.text_area("Cleaning Scope")

    if st.button("Add Job Site"):
        job_site_data = {
            "site_name": site_name,
            "location": firestore.GeoPoint(float(location.split(",")[0]), float(location.split(",")[1])),
            "start_date": firestore.Timestamp.from_datetime(datetime.combine(start_date, datetime.min.time())),
            "end_date": firestore.Timestamp.from_datetime(datetime.combine(end_date, datetime.min.time())),
            "cleaning_scope": cleaning_scope
        }
        doc_ref = job_sites_ref.add(job_site_data)
        st.success(f"Job Site {site_name} added with ID: {doc_ref.id}")

# Streamlit UI for viewing job sites
def view_job_sites():
    st.header("View Job Sites")

    # Fetch job sites from Firestore
    docs = job_sites_ref.stream()

    # Prepare data for the table
    job_sites_data = []
    for doc in docs:
        job_site = doc.to_dict()
        # Check if 'site_id' is in the document, else use a fallback or generate it
        if 'site_id' in job_site:
            job_site["site_id"] = job_site['site_id']  # Use the site_id stored in Firestore
        else:
            job_site["site_id"] = "N/A"  # Fallback if site_id is not found
        job_sites_data.append(job_site)

    # Convert data to a DataFrame for better table formatting
    job_sites_df = pd.DataFrame(job_sites_data)

    # Define the order of columns
    column_order = ["site_name", "site_manager", "contact_number", "location", "required_roles", "work_schedule", "active", "site_id"]
    
    # Reorder columns as per the column_order
    job_sites_df = job_sites_df[column_order]

    # Display the data in a table format
    st.dataframe(job_sites_df)

# Streamlit UI for assigning employees to job sites
def assign_employee_form():
    st.header("Assign Employee to Job Site")

    employee_id = st.text_input("Employee ID")
    job_site_id = st.text_input("Job Site ID")
    shift = st.selectbox("Shift", ["7:00-15:30", "14:00-22:00", "22:00-06:00"])
    assigned_by = st.text_input("Assigned By")

    if st.button("Assign Employee"):
        assignment_data = {
            "employee_id": employee_id,
            "job_site_id": job_site_id,
            "shift": shift,
            "assigned_by": assigned_by,
            "assigned_on": firestore.SERVER_TIMESTAMP
        }
        doc_ref = assignments_ref.add(assignment_data)
        st.success(f"Employee {employee_id} assigned to Job Site {job_site_id} with assignment ID: {doc_ref.id}")

# Streamlit UI for viewing assignments
def view_assignments():
    st.header("View Assignments")

    # Fetch assignments from Firestore
    docs = assignments_ref.stream()

    # Prepare data for the table
    assignments_data = []
    for doc in docs:
        assignment = doc.to_dict()
        # Extract the assigned_employee and site details
        assigned_employee = assignment.get("assigned_employee", {})
        assignment_data = {
            "worker_id": assigned_employee.get("worker_id", "N/A"),
            "first_name": assigned_employee.get("first_name", "N/A"),
            "last_name": assigned_employee.get("last_name", "N/A"),
            "phone_number": assigned_employee.get("phone_number", "N/A"),
            "distance": assigned_employee.get("distance", "N/A"),
            "rating": assigned_employee.get("rating", "N/A"),
            "site_address": assignment.get("site_address", "N/A"),
            "site_name": assignment.get("site_name", "N/A")
        }
        assignments_data.append(assignment_data)

    # Convert data to a DataFrame for better table formatting
    if assignments_data:
        df = pd.DataFrame(assignments_data)

        # Reorder columns to match the specified order
        column_order = [
            "worker_id",
            "first_name",
            "last_name",
            "phone_number",
            "distance",
            "rating",
            "site_address",
            "site_name"
        ]
        df = df[column_order]

        # Display the data in a table format
        st.dataframe(df)
    else:
        st.write("No assignments found.")

# Main function to organize the app
def main():
    st.title("Employee and Job Site Management")

    # Sidebar with grouped options
    st.sidebar.header("Navigation")

    # Employees section
    st.sidebar.subheader("Employees")
    if st.sidebar.page_link("app.py", label="Add Employee"):
        add_employee_form()
    if st.sidebar.page_link("app.py", label="View Employees"):
        view_employees()

    # Job Sites section
    st.sidebar.subheader("Job Sites")
    if st.sidebar.page_link("app.py", label="Add Job Site"):
        add_job_site_form()
    if st.sidebar.page_link("app.py", label="View Job Sites"):
        view_job_sites()

    # Assignments section
    st.sidebar.subheader("Assignments")
    if st.sidebar.page_link("app.py", label="Assign Employee"):
        assign_employee_form()
    if st.sidebar.page_link("app.py", label="View Assignments"):
        view_assignments()

if __name__ == '__main__':
    main()