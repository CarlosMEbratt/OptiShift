import streamlit as st
import firebase_admin
import pandas as pd
import requests
import random, string, os, json, time, subprocess, sys
from firebase_admin import credentials, firestore, auth
from twilio.rest import Client


import time
import googlemaps
import geopy.distance
import re
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut


# ✅ Load Firebase credentials correctly from Streamlit secrets
firebase_credentials = st.secrets["FIREBASE_CREDENTIALS"]

if firebase_credentials:
    cred_dict = json.loads(firebase_credentials)  # Convert string to dictionary
    if not firebase_admin._apps:  # ✅ Initialize Firebase only if not already initialized
        cred = credentials.Certificate(cred_dict)
        firebase_admin.initialize_app(cred)
else:
    raise ValueError("🔥 FIREBASE_CREDENTIALS not set. Configure it in Streamlit Secrets.")

# ✅ Initialize Firestore client
db = firestore.client()


#----------------------------------------------------------------------------------------

# Collection references
employees_ref = db.collection('employees')
job_sites_ref = db.collection('job_sites')
assignments_ref = db.collection('assignments')
users_ref = db.collection('users')  # 🔹 Collection for storing users

#----------------------------------------------------------------------------------------

# Streamlit UI for adding an employee
def add_employee_form():
    st.header("Add Employee")

    with st.form(key="add_employee_form"):
        worker_id = generate_worker_id()
        
        first_name = st.text_input("First Name")
        middle_name = st.text_input("Middle Name")
        sur_name = st.text_input("Surname")
        phone_number = st.text_input("Phone Number")  
        home_address = st.text_input("Home Location (e.g., 43.7,-79.3 for Toronto)")
        have_car = st.selectbox("Do you have a car?", ["Yes", "No"])
        role = st.multiselect("Role", ["Cleaner", "Labour", "Painter"])
        availability = st.multiselect("Availability", ["7:00-15:30", "14:00-22:00", "22:00-06:00"])
        certificates = st.multiselect("Certifications", ["Working at Heights", "4 Steps", "WHMIS"])
        skills = st.multiselect("Skills", ["Boomlift", "Scissors Lift", "Forklift"])
        rating = st.slider("Employee Rating", min_value=0.0, max_value=5.0, value=3.0, step=0.1)

        submit_button = st.form_submit_button("Add Employee")

    if submit_button:
        employee_data = {
            "worker_id": worker_id,
            "first_name": first_name.strip(),
            "middle_name": middle_name.strip(),
            "sur_name": sur_name.strip(),
            "phone_number": phone_number.strip(),
            "home_address": home_address.strip(),
            "have_car": have_car,
            "role": role,
            "availability": availability,
            "certificates": certificates,
            "skills": skills,
            "rating": rating
        }

        try:
            # ✅ Firestore add() now returns a DocumentReference, from which we get .id
            doc_ref = employees_ref.add(employee_data)[1]  # Correctly extract the Firestore ID
            st.success(f"✅ Employee added with ID: {doc_ref.id}")
        except Exception as e:
            st.error(f"❌ Error adding employee: {str(e)}")




#----------------------------------------------------------------------------------------

# ✅ Streamlit UI for Viewing Employees
def view_employees():
    st.header("View Employees")

    # Fetch and structure employee data efficiently
    employee_data = [
        {
            "worker_id": doc.get("worker_id", "N/A"),
            "first_name": doc.get("first_name", "N/A"),
            "middle_name": doc.get("middle_name", "N/A"),
            "sur_name": doc.get("sur_name", "N/A"),
            "phone_number": doc.get("phone_number", "N/A"),
            "home_address": doc.get("home_address", "N/A"),
            "have_car": doc.get("have_car", "No"),
            "role": ", ".join(doc.get("role", [])) if isinstance(doc.get("role"), list) else doc.get("role", "N/A"),
            "skills": ", ".join(doc.get("skills", [])) if isinstance(doc.get("skills"), list) else doc.get("skills", "N/A"),
            "availability": ", ".join(doc.get("availability", [])) if isinstance(doc.get("availability"), list) else doc.get("availability", "N/A"),
            "certificates": ", ".join(
                [
                    f"{cert} (Issued: {info.get('issue_date', 'N/A')}, Exp: {info.get('expiration_date', 'N/A')})"
                    for cert, info in doc.get("certificates", {}).items()
                ]
            ) if isinstance(doc.get("certificates"), dict) else "None",
            "rating": doc.get("rating", "N/A")
        }
        for doc in (d.to_dict() for d in employees_ref.stream())  # Efficient fetching
    ]

    # Convert data to DataFrame for better UI handling
    if employee_data:
        df = pd.DataFrame(employee_data)

        # Define the column order
        column_order = [
            "worker_id", "first_name", "middle_name", "sur_name", "phone_number", "home_address", "have_car",
            "role", "skills", "certificates", "availability", "rating"
        ]
        df = df[column_order]

        # ✅ Sorting & Filtering UI
        sort_col = st.selectbox("Sort by:", column_order, index=0)
        sort_order = st.radio("Sort Order", ["Ascending", "Descending"], horizontal=True)
        df = df.sort_values(by=sort_col, ascending=(sort_order == "Ascending"))

        # ✅ Search Feature
        search_query = st.text_input("Search Employees (by name or ID)")
        if search_query:
            df = df[
                df["worker_id"].str.contains(search_query, case=False, na=False) |
                df["first_name"].str.contains(search_query, case=False, na=False) |
                df["sur_name"].str.contains(search_query, case=False, na=False)
            ]

        # ✅ Display the table with better formatting
        st.dataframe(df, use_container_width=True)
    else:
        st.info("No employees found.")


#----------------------------------------------------------------------------------------

# ✅ Streamlit UI for Finding, Updating, and Deleting an Employee
def find_and_update_employee():
    st.header("Find, Update, or Delete Employee")

    # Reset search if "New Search" is clicked
    if st.button("🔄 New Search"):
        st.session_state.pop("selected_employee", None)
        st.session_state.pop("search_term", None)
        st.rerun()

    # Search input
    search_term = st.text_input(
        "🔍 Search by Worker ID, Phone Number, First Name, or Last Name",
        value=st.session_state.get("search_term", "")
    ).strip().lower()

    search_results = []
    if search_term:
        st.session_state["search_term"] = search_term
        for doc in employees_ref.stream():
            employee = doc.to_dict()
            if any(search_term in str(employee.get(field, "")).lower() for field in ["worker_id", "phone_number", "first_name", "sur_name"]):
                employee["doc_id"] = doc.id  # ✅ Store Firestore document ID
                search_results.append(employee)

    # Show search results
    if search_results:
        selected_employee = st.selectbox(
            "👤 Select Employee to Edit or Delete",
            search_results,
            format_func=lambda x: f"{x.get('first_name', 'N/A')} {x.get('sur_name', 'N/A')} ({x.get('worker_id', 'N/A')})"
        )

        if selected_employee:
            st.session_state["selected_employee"] = selected_employee

    # Show update form if an employee is selected
    if "selected_employee" in st.session_state:
        update_employee_form(st.session_state["selected_employee"])

        # ✅ Confirm deletion
        if st.button("❌ Delete Employee", help="This action cannot be undone!"):
         
            try:
                doc_id = st.session_state["selected_employee"]["doc_id"]
                employees_ref.document(doc_id).delete()
                st.success("✅ Employee deleted successfully!")
                st.session_state.pop("selected_employee", None)
                st.session_state.pop("search_term", None)
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error deleting employee: {e}")


#----------------------------------------------------------------------------------------


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

#----------------------------------------------------------------------------------------


# ✅ Streamlit UI for Adding a Job Site
def add_job_site_form():
    st.header("🏗️ Add Job Site")

    with st.form(key="add_job_site_form"):
        site_id = f"SITE{random.randint(1000, 9999)}"  # Auto-generated Site ID
        st.write(f"📌 Generated Site ID: `{site_id}`")  # Debugging output

        site_name = st.text_input("🏢 Site Name")
        site_company = st.text_input("🏗️ Site Company")
        site_superintendent = st.text_input("👷 Superintendent")
        site_contact_number = st.text_input("📞 Contact Number")
        address = st.text_input("📍 Site Address (Use Google Maps for accuracy)")

        # ✅ Job Site Status Selection
        job_status = st.selectbox("📌 Job Site Status", ["Active", "Inactive", "Completed"])

        # ✅ Date Selection with Calendar Widget
        work_start_date = st.date_input("📅 Work Start Date")
        work_end_date = st.date_input("📅 Work End Date")

        # ✅ Required roles selection
        st.subheader("🛠️ Required Roles")
        required_roles = {}
        roles = ["Cleaner", "Labour", "Painter"]

        for role in roles:
            with st.expander(f"⚙️ {role}"):
                work_schedule = st.multiselect(
                    f"🕒 Work Schedule for {role}",
                    ["7:00-15:30", "14:00-22:00", "22:00-06:00"],
                    key=f"schedule_{role}"
                )
                num_workers = st.number_input(
                    f"👥 Number of {role}s Required",
                    min_value=0, step=1, key=f"workers_{role}"
                )
                if num_workers > 0:
                    required_roles[role] = {"work_schedule": work_schedule, "num_workers": num_workers}

        submit_button = st.form_submit_button("✅ Add Job Site")

    if submit_button:
        if not site_name or not site_company or not site_superintendent or not site_contact_number or not address:
            st.error("❌ Please fill in all required fields.")
            return
        
        try:
            job_site_data = {
                "site_id": site_id,
                "site_name": site_name.strip(),
                "site_company": site_company.strip(),
                "site_superintendent": site_superintendent.strip(),
                "site_contact_number": site_contact_number.strip(),
                "address": address.strip(),
                "job_status": job_status,
                "work_start_date": work_start_date.strftime('%Y-%m-%d'),
                "work_end_date": work_end_date.strftime('%Y-%m-%d'),
                "required_roles": required_roles
            }
            
            doc_ref = job_sites_ref.document(site_id)
            doc_ref.set(job_site_data)

            # ✅ Verify if Firestore has stored the document correctly
            if doc_ref.get().exists:
                st.success(f"✅ Job Site **{site_name}** added successfully with ID: `{site_id}`")
            else:
                st.error("❌ Firestore write operation completed, but document not found.")
        except Exception as e:
            st.error(f"❌ Error adding job site: {str(e)}")


#----------------------------------------------------------------------------------------

def view_job_sites():
    st.header("🏗️ View Job Sites")

    # Fetch job sites from Firestore efficiently
    job_sites_data = [
        {
            "Site ID": doc.get("site_id", "N/A"),
            "Job Status": doc.get("job_status", "N/A"),
            "Work Start Date": doc.get("work_start_date", "N/A"),
            "Work End Date": doc.get("work_end_date", "N/A"),
            "Site Name": doc.get("site_name", "N/A"),
            "Company": doc.get("site_company", "N/A"),
            "Superintendent": doc.get("site_superintendent", "N/A"),
            "Contact Number": doc.get("site_contact_number", "N/A"),
            "Address": doc.get("address", "N/A"),
            "# Required Workers": sum(
                details.get("num_workers", 0) for details in doc.get("required_roles", {}).values()
            ),
            "Required Roles": ", ".join([
                f"{role} ({details.get('num_workers', 0)} workers, {', '.join(details.get('work_schedule', []))})"
                for role, details in doc.get("required_roles", {}).items()
            ]) if doc.get("required_roles") else "N/A"
        }
        for doc in (d.to_dict() for d in job_sites_ref.stream())  # Optimized fetching
    ]

    if job_sites_data:
        df = pd.DataFrame(job_sites_data)

        # Define column order
        column_order = [
            "Site ID", "Job Status", "Work Start Date", "Work End Date", "Site Name", "Company",
            "Superintendent", "Contact Number", "Address", "# Required Workers", "Required Roles"
        ]
        df = df[column_order]

        # ✅ Status Filter
        status_filter = st.selectbox("🔍 Filter by Job Site Status:", ["All", "Active", "Inactive", "Completed"], index=0)
        if status_filter != "All":
            df = df[df["Job Status"] == status_filter]

        # ✅ Sorting UI
        sort_col = st.selectbox("🔀 Sort by:", column_order, index=0)
        sort_order = st.radio("⬆️⬇️ Sort Order", ["Ascending", "Descending"], horizontal=True)
        df = df.sort_values(by=sort_col, ascending=(sort_order == "Ascending"))

        # ✅ Search Feature
        search_query = st.text_input("🔍 Search Job Sites (by Site Name, ID, or Company)")
        if search_query:
            df = df[
                df["Site ID"].str.contains(search_query, case=False, na=False) |
                df["Site Name"].str.contains(search_query, case=False, na=False) |
                df["Company"].str.contains(search_query, case=False, na=False)
            ]

        # ✅ Display DataFrame with enhanced UI
        st.dataframe(df, use_container_width=True)
    else:
        st.info("❌ No job sites found.")


#-----------------------------------------------------------------


# ✅ Streamlit UI for Finding and Updating a Job Site
def find_and_update_job_site():
    st.header("🏗️ Find and Update Job Site")
    
    if st.button("🔄 New Search"):
        st.session_state.pop("selected_job_site", None)
        st.session_state.pop("search_term_job", None)
        st.rerun()
    
    search_term = st.text_input(
        "🔍 Search by Site ID, Site Name, Company, or Address",
        value=st.session_state.get("search_term_job", "")
    ).strip().lower()

    search_results = []
    if search_term:
        st.session_state["search_term_job"] = search_term
        
        search_results = [
            {**doc.to_dict(), "doc_id": doc.id}
            for doc in job_sites_ref.stream()
            if any(search_term in str(doc.to_dict().get(field, "")).lower() for field in ["site_id", "site_name", "site_company", "address"])
        ]
    
    if search_results:
        selected_job_site = st.selectbox(
            "🏗️ Select Job Site to Edit",
            search_results,
            format_func=lambda x: f"{x.get('site_name', 'N/A')} ({x.get('site_id', 'N/A')})"
        )
        
        if selected_job_site:
            st.session_state["selected_job_site"] = selected_job_site
    
    if "selected_job_site" in st.session_state:
        update_job_site_form(st.session_state["selected_job_site"])

#----------------------------------------------------------------------------------------

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

#----------------------------------------------------------------------------------------


def view_assignments():
    st.header("📋 View Assignments")

    # Fetch assignments from Firestore
    assignments_data = [doc.to_dict() for doc in assignments_ref.stream()]

    # Fetch all employees as a dictionary {worker_id: employee_data}
    employees_dict = {doc.to_dict().get("worker_id"): doc.to_dict() for doc in employees_ref.stream()}

    # Prepare data for the table
    formatted_assignments = []
    
    for assignment in assignments_data:
        site_id = assignment.get("job_site_id", "N/A")
        site_doc = job_sites_ref.document(site_id).get()
        site_data = site_doc.to_dict() if site_doc.exists else {}

        employee_id = assignment.get("employee_id", "N/A")
        employee_data = employees_dict.get(employee_id, {})

        distance = assignment.get("distance", "N/A")  # ✅ Fetch Distance from Assignments Collection

        # Construct assignment record with safe default values
        formatted_assignments.append({
            "Site Name": site_data.get("site_name", "N/A"),
            "Company": site_data.get("site_company", "N/A"),
            "Address": site_data.get("address", "N/A"),
            "Num Workers": sum(
                details.get("num_workers", 0) for details in site_data.get("required_roles", {}).values()
            ) if site_data.get("required_roles") else 0,
            "Full Name": f"{employee_data.get('first_name', 'N/A')} {employee_data.get('middle_name', '')} {employee_data.get('sur_name', 'N/A')}",
            "Phone Number": employee_data.get("phone_number", "N/A"),
            "Home Address": employee_data.get("home_address", "N/A"),
            "Has Car": employee_data.get("have_car", "N/A"),
            "Employee Role": ", ".join(employee_data.get("role", [])) if isinstance(employee_data.get("role"), list) else employee_data.get("role", "N/A"),
            "Required Role": assignment.get("role", "N/A"),
            "Skills": ", ".join(employee_data.get("skills", [])) if isinstance(employee_data.get("skills"), list) else "N/A",
            "Certificates": ", ".join(employee_data.get("certificates", [])) if isinstance(employee_data.get("certificates"), list) else "N/A",
            "Availability": ", ".join(employee_data.get("availability", [])) if isinstance(employee_data.get("availability"), list) else "N/A",
            "Rating": employee_data.get("rating", "N/A"),
            "Distance (km)": f"{distance:.2f} km" if isinstance(distance, (int, float)) else "N/A",
        })

    # Convert data to DataFrame
    df = pd.DataFrame(formatted_assignments)

    # Define expected column order with "Employee Role" after "Has Car"
    column_order = [
        "Site Name", "Company", "Address", "Num Workers", "Required Role", "Full Name", "Phone Number",
        "Home Address", "Has Car", "Employee Role", "Skills", "Certificates", "Availability", "Rating", "Distance (km)"
    ]
    
    if not df.empty:
        df = df[column_order]
        
        # ✅ Sorting Feature
        sort_col = st.selectbox("🔀 Sort by:", column_order, index=0)
        sort_order = st.radio("⬆️⬇️ Sort Order", ["Ascending", "Descending"], horizontal=True)
        df = df.sort_values(by=sort_col, ascending=(sort_order == "Ascending"))

        # ✅ Search Feature
        search_query = st.text_input("🔍 Search Assignments (by Site Name, Employee, or Role)")
        if search_query:
            df = df[
                df["Site Name"].str.contains(search_query, case=False, na=False) |
                df["Full Name"].str.contains(search_query, case=False, na=False) |
                df["Required Role"].str.contains(search_query, case=False, na=False) |
                df["Employee Role"].str.contains(search_query, case=False, na=False)
            ]

        # ✅ Display DataFrame with enhanced UI
        st.dataframe(df, use_container_width=True)
    else:
        st.info("❌ No assignments found.")



#----------------------------------------------------------------------------------------


# ✅ Step 1: Initialize Firebase
def initialize_firebase():
    """Initializes Firebase if not already initialized."""
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate("serviceAccountKey.json")
            firebase_admin.initialize_app(cred)
            print("✅ Firebase successfully initialized.")
        else:
            print("✅ Firebase already initialized.")
        return firestore.client()
    except Exception as e:
        print(f"🔥 Firebase initialization failed: {e}")
        return None

# Initialize Firestore client
db = initialize_firebase()
if db is None:
    print("⚠️ Firestore initialization failed. Exiting.")
    exit()

assignments_ref = db.collection("assignments")

# ✅ Step 2: Initialize Geocoders
GOOGLE_API_KEY = "AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E"
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
geolocator_osm = Nominatim(user_agent="optishift_geocoder")  # OSM as a backup

# ✅ Step 3: Geocoding Functions
def clean_geocode_address(address):
    """Cleans an address by removing unnecessary details."""
    address = re.sub(r'\b(Unit|Suite|Apt|Floor|Rm|#)\s*\d+\b', '', address, flags=re.IGNORECASE)
    address = re.sub(r'\b(Shopping Center|Mall|Plaza|Building|Complex)\b', '', address, flags=re.IGNORECASE)
    return address.strip()

def google_geocode(address, max_retries=3):
    """Geocodes an address using Google Maps API with retry logic."""
    address = clean_geocode_address(address)
    for attempt in range(max_retries):
        try:
            geocode_result = gmaps.geocode(address)
            if geocode_result:
                lat = geocode_result[0]['geometry']['location']['lat']
                lon = geocode_result[0]['geometry']['location']['lng']
                return lat, lon
        except Exception as e:
            print(f"❌ Google Maps Geocode error for {address}: {e}")
        time.sleep(2)
    return None, None

def osm_geocode(address, max_retries=3):
    """Geocodes an address using OpenStreetMap (OSM) with retry logic."""
    address = clean_geocode_address(address)
    for attempt in range(max_retries):
        try:
            location = geolocator_osm.geocode(address, timeout=10)
            if location:
                return location.latitude, location.longitude
        except GeocoderTimedOut:
            print(f"⏳ OSM Timeout error for {address}. Attempt {attempt+1}/{max_retries}")
        time.sleep(2)
    return None, None

def geocode_address(address):
    """Tries Google Maps first, then OSM if it fails."""
    lat, lon = google_geocode(address)
    if lat is None or lon is None:
        lat, lon = osm_geocode(address)
    return lat, lon

# ✅ Step 4: Distance Calculation
def calculate_distance(employee_location, site_location):
    if None in employee_location or None in site_location:
        print(f"⚠️ Cannot calculate distance. Missing coordinates: {employee_location}, {site_location}")
        return float('inf')
    return geopy.distance.distance(employee_location, site_location).km

# ✅ Step 5: Assignment Function
def do_assignments():
    st.header("🔄 Run Assignments")
    st.write("Click below to run the assignment process and match employees to job sites.")

    if st.button("Run Assignments"):
        with st.spinner("🗑️ Deleting old assignments..."):
            try:
                old_assignments = assignments_ref.stream()
                batch = db.batch()
                for doc in old_assignments:
                    batch.delete(doc.reference)
                batch.commit()
                time.sleep(2)  # Firestore sync
                st.success("✅ Old assignments deleted successfully!")
            except Exception as e:
                st.error(f"❌ Error deleting assignments: {e}")
                return

        with st.spinner("⚡ Running assignment process..."):
            try:
                employees = [doc.to_dict() for doc in db.collection("employees").stream()]
                
                # ✅ Filter only active job sites
                job_sites = [doc.to_dict() for doc in db.collection("job_sites").stream() if doc.to_dict().get("job_status", "").lower() == "active"]
                
                assigned_employees = set()

                if not job_sites:
                    st.warning("⚠️ No active job sites found.")
                    return

                # Ensure employees and job sites have coordinates
                for entity in employees + job_sites:
                    key = "home_address" if "home_address" in entity else "address"
                    if "latitude" not in entity or "longitude" not in entity or entity["latitude"] is None or entity["longitude"] is None:
                        lat, lon = geocode_address(entity.get(key, ""))
                        if lat is None or lon is None:
                            print(f"⚠️ Skipping {entity.get('worker_id', entity.get('site_id', 'UNKNOWN'))} due to missing geolocation data.")
                            continue
                        entity["latitude"] = lat
                        entity["longitude"] = lon

                # ✅ Assignment Logic: Strict Role Matching
                for site in job_sites:
                    required_roles = site.get('required_roles', {})
                    assigned_counts = {role: 0 for role in required_roles}

                    for role, role_data in required_roles.items():
                        required_count = role_data.get('num_workers', 0)
                        if required_count == 0:
                            continue

                        employee_scores = []
                        for employee in employees:
                            # ✅ Ensure the employee's role matches the site's required role
                            employee_roles = employee.get('role', [])
                            if isinstance(employee_roles, str):  # If stored as a single string
                                employee_roles = [employee_roles]

                            if role not in employee_roles:
                                continue  # ❌ Skip this employee if their role doesn't match

                            # ✅ Scoring System (Prioritizing Role Match First)
                            score = 5  # Base score since role already matches
                            if any(shift in employee.get('availability', []) for shift in role_data.get('work_schedule', [])):
                                score += 4
                            if employee.get('have_car', 'No') == 'Yes':
                                score += 3

                            distance = calculate_distance(
                                (employee['latitude'], employee['longitude']), 
                                (site['latitude'], site['longitude'])
                            )
                            if distance <= 40:
                                score += 2

                            employee_scores.append({'employee': employee, 'score': score, 'distance': distance})

                        # ✅ Sort employees by score (higher is better), then by distance (lower is better)
                        sorted_employees = sorted(
                            employee_scores, 
                            key=lambda x: (-x['score'], x['distance'], -x['employee'].get('rating', 0))
                        )

                        assigned = 0
                        for emp_data in sorted_employees:
                            if assigned >= required_count:
                                break
                            employee = emp_data['employee']
                            if employee['worker_id'] in assigned_employees:
                                continue

                            try:
                                db.collection('assignments').add({
                                    'employee_id': employee['worker_id'],
                                    'job_site_id': site['site_id'],
                                    'role': role,
                                    'distance': emp_data['distance'],
                                    'assigned_date': datetime.now()
                                })
                                assigned_employees.add(employee['worker_id'])
                                assigned += 1
                            except Exception as e:
                                print(f"❌ Firestore Write Failed: {e}")

                st.success("✅ Assignments have been updated!")

            except Exception as e:
                st.error(f"❌ Error running assignments: {e}")
                return

        # ✅ Refresh UI
        view_assignments()






#----------------------------------------------------------------------------------------


# ✅ Twilio Credentials (Replace these with your actual credentials)
TWILIO_SID = "ACea4083caabbc067e4b57269ee7e90f8e"
TWILIO_AUTH_TOKEN = "1a0e3164e8faf75f4286c4bde720c5b3"
TWILIO_PHONE_NUMBER = "+18573492964"

# ✅ Function to Send SMS
def send_sms(to, message):
    """Sends an SMS message using Twilio API"""
    client = Client(TWILIO_SID, TWILIO_AUTH_TOKEN)
    try:
        sms = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to  # Recipient's phone number
        )
        st.success(f"✅ Message sent successfully! SID: {sms.sid}")
    except Exception as e:
        st.error(f"❌ Error sending message: {e}")

# ✅ Streamlit UI for Sending SMS Notifications
def notify_employees():
    st.header("📲 Notify Employees via SMS")
    recipient_number = st.text_input("Enter Recipient's Phone Number (E.g., +1234567890)")
    sms_message = st.text_area("Enter your message")

    if st.button("Send SMS"):
        if recipient_number and sms_message:
            send_sms(recipient_number, sms_message)
        else:
            st.warning("⚠️ Please enter a phone number and message.")





#----------------------------------------------------------------------------------------


FIREBASE_WEB_API_KEY = "AIzaSyCZD1HVMBWaDHh2DlAI8gIFiNvHiOoRxiU"

# ✅ Initialize Firebase Admin (Only Once)
if not firebase_admin._apps:
    cred = credentials.Certificate("serviceAccountKey.json")  # Make sure you have this key file
    firebase_admin.initialize_app(cred)

db = firestore.client()
users_ref = db.collection("users")  # Stores user authentication & role info
employees_ref = db.collection("employees")  # Stores employee profile data

def generate_worker_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# ✅ Function to Register a User and Add to Employees Database
def register_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_WEB_API_KEY}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=data)
    result = response.json()

    if "idToken" in result:
        user_id = result["localId"]
        worker_id = generate_worker_id()  # Generate a unique worker ID

        st.success(f"✅ Account created successfully: {email}")

        # ✅ Store user data in Firestore (Default role: Employee)
        users_ref.document(user_id).set({
            "email": email,
            "role": "employee"
        })

        # ✅ Store employee profile with default values in Firestore
        employees_ref.document(user_id).set({
            "worker_id": worker_id,  # Store the generated worker ID
            "email": email,
            "first_name": "",
            "middle_name": "",
            "sur_name": "",
            "phone_number": "",
            "home_address": "",
            "have_car": "No",
            "role": [],
            "availability": [],
            "certificates": [],
            "skills": [],
            "rating": 3.0  # Default rating
        })

        # ✅ Update session and redirect
        st.session_state["authenticated"] = True
        st.session_state["user_id"] = user_id
        st.session_state["user_email"] = email
        st.session_state["user_role"] = "employee"
        st.rerun()
    else:
        error_message = result.get('error', {}).get('message', 'Unknown error')
        st.error(f"❌ Registration failed: {error_message}")


#----------------------------------------------------------------------------------------


# ✅ Function to Log In a User
def login_user(email, password):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
    data = {"email": email, "password": password, "returnSecureToken": True}
    response = requests.post(url, json=data)
    result = response.json()

    if "idToken" in result:
        user_id = result["localId"]
        user_doc = users_ref.document(user_id).get()

        if user_doc.exists:
            user_data = user_doc.to_dict()
            st.session_state["authenticated"] = True
            st.session_state["user_id"] = user_id
            st.session_state["user_email"] = email
            st.session_state["user_role"] = user_data.get("role", "employee")
            st.session_state["login_error"] = None  # ✅ Clear previous errors
            st.rerun()
        else:
            st.session_state["login_error"] = "❌ User not found in Firestore. Contact admin."
    else:
        error_message = result.get('error', {}).get('message', 'Invalid credentials')
        st.session_state["login_error"] = f"❌ Login failed: {error_message}"  # ✅ Store error message persistently


#----------------------------------------------------------------------------------------


# ✅ Profile Update (For Employees) with Certificate Dates
def update_profile():
    st.subheader("📝 Update Your Profile")

    if "selected_section" in st.session_state and st.session_state["selected_section"] != "profile":
        return  # Ensures the function only runs when the correct section is selected
    
    user_id = st.session_state.get("user_id")
    if not user_id:
        st.error("❌ User ID not found. Please log in again.")
        return

    employee_doc = employees_ref.document(user_id).get()

    if employee_doc.exists:
        employee = employee_doc.to_dict()

        if "worker_id" not in employee or not employee["worker_id"]:
            worker_id = generate_worker_id()
            employees_ref.document(user_id).update({"worker_id": worker_id})
        else:
            worker_id = employee["worker_id"]

        with st.form("update_profile_form"):
            first_name = st.text_input("First Name", employee.get("first_name", "").strip())
            middle_name = st.text_input("Middle Name", employee.get("middle_name", "").strip())
            sur_name = st.text_input("Surname", employee.get("sur_name", "").strip())
            phone_number = st.text_input("Phone Number", employee.get("phone_number", "").strip())
            
            home_address = st.text_input(
            "Home Address. 📍 Use Google Maps to copy paste the exact address. Example: 👇🏻",
            value=employee.get("home_address", "").strip() or "1110 Atwater Ave, Mississauga, ON L5E 1M9"
            )

            have_car = st.selectbox("Do you have a car?", ["Yes", "No"], index=["Yes", "No"].index(employee.get("have_car", "No")))
            role = st.multiselect("Role", ["Cleaner", "Labour", "Painter"], default=employee.get("role", []))
            availability = st.multiselect("Availability", ["7:00-15:30", "14:00-22:00", "22:00-06:00"], default=employee.get("availability", []))
            skills = st.multiselect("Skills", ["Boomlift", "Scissors Lift", "Forklift"], default=employee.get("skills", []))
            
            st.subheader("📜 Certifications")
            updated_certificates = {}

            certificates = employee.get("certificates", {})
            if isinstance(certificates, list):
                certificates = {cert: {"issue_date": "2024-01-01", "expiration_date": "2026-01-01"} for cert in certificates}

            for cert in ["Working at Heights", "4 Steps", "WHMIS"]:
                col1, col2, col3 = st.columns(3)
                with col1:
                    cert_selected = st.checkbox(cert, value=(cert in certificates))
                with col2:
                    issue_date = st.date_input(
                        f"Issue Date for {cert}",
                        value=pd.to_datetime(certificates.get(cert, {}).get("issue_date", "2024-01-01")),
                        disabled=not cert_selected
                    )
                with col3:
                    expiration_date = st.date_input(
                        f"Expiration Date for {cert}",
                        value=pd.to_datetime(certificates.get(cert, {}).get("expiration_date", "2026-01-01")),
                        disabled=not cert_selected
                    )
                
                if cert_selected:
                    updated_certificates[cert] = {
                        "issue_date": issue_date.strftime("%Y-%m-%d"),
                        "expiration_date": expiration_date.strftime("%Y-%m-%d")
                    }
            
            rating_locked = employee.get("rating_locked", False)
            if not rating_locked:
                rating = st.slider("Employee Rating (One-Time Auto-Evaluation)", min_value=0.0, max_value=5.0, value=float(employee.get("rating", 3.0)), step=0.1)
                st.warning("⚠️ You can only set your rating once.")
            else:
                rating = employee.get("rating", "N/A")
                st.info(f"⭐ Your current rating: **{rating}** (Auto-evaluation complete)")
            
            submit_button = st.form_submit_button("✅ Update Profile")
        
        if submit_button:
            updated_data = {
                "worker_id": worker_id,
                "first_name": first_name.strip(),
                "middle_name": middle_name.strip(),
                "sur_name": sur_name.strip(),
                "phone_number": phone_number.strip(),
                "home_address": home_address.strip(),
                "have_car": have_car,
                "role": role,
                "availability": availability,
                "skills": skills,
                "certificates": updated_certificates
            }
            
            if not rating_locked:
                updated_data["rating"] = rating
                updated_data["rating_locked"] = True

            try:
                employees_ref.document(user_id).update(updated_data)
                st.success("✅ Profile updated successfully!")
                st.session_state["profile_updated"] = True
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error updating profile: {str(e)}")


#----------------------------------------------------------------------------------------


# def sidebar_menu():
#     st.sidebar.header("📋 Navigation")
#     st.sidebar.image("optishift_logo.png", use_container_width=True)
    
#     user_role = st.session_state.get("user_role", "employee")
    
#     if user_role == "admin":
#         menu_options = {
#             "👥 Employees": "employees",
#             "🏗️ Job Sites": "job_sites",
#             "📋 Assignments": "assignments"
#         }
#         selected_option = st.sidebar.radio("Select an option:", list(menu_options.keys()))
#         if selected_option:
#             st.session_state["selected_section"] = menu_options[selected_option]
#     else:
#         if st.sidebar.button("📝 Update Profile"):
#             st.session_state["selected_section"] = "profile"
    
#     st.sidebar.write("---")
#     if st.sidebar.button("🚪 Logout"):
#         st.session_state.clear()
#         st.rerun()


#----------------------------------------------------------------------------------------               

# ✅ Main View (For Admins)
def main_view():
    if not st.session_state.get("authenticated"):
        st.image("optishift_logo.png", use_container_width=True)

    st.title("📊 OptiShift Dashboard")
    st.subheader("Welcome to the workforce management system")
    st.write("Select an option below:")

    user_id = st.session_state.get("user_id")  # This is the document ID in "users" collection
    user_role = st.session_state.get("user_role", "employee")  # Default role is "employee"

    # Step 1: Fetch the Employee's Worker ID using the User's Document ID
    worker_id = None
    if user_role == "employee":
        employee_doc = employees_ref.document(user_id).get()  # Fetch employee document
        if employee_doc.exists:
            worker_id = employee_doc.to_dict().get("worker_id")  # Extract worker_id

    # Step 2: Fetch the Assignment using Worker ID
    assigned_job = None
    if worker_id:
        def get_assigned_job(worker_id):
            assigned_job = assignments_ref.where("employee_id", "==", worker_id).stream()
            for job in assigned_job:
                return job.to_dict()  # Return the first found assignment
            return None  # No job assigned

        assigned_job = get_assigned_job(worker_id)  # Retrieve assigned job

        if st.button("📝 Update your Information"):
            st.session_state["selected_section"] = "profile"

        st.write("---")  # First horizontal line

        # 🔹 **Display Job Assignment Details ONLY for Employees**
        if assigned_job:
            job_site = job_sites_ref.document(assigned_job['job_site_id']).get()
            job_site_data = job_site.to_dict() if job_site.exists else {}

            st.success("✅ You have been assigned to a job site!")
            st.write(f"🏗 **Site Name:** {job_site_data.get('site_name', 'Unknown')}")
            st.write(f"📍 **Address:** {job_site_data.get('address', 'Unknown')}")
            st.write(f"👷 **Role:** {assigned_job['role']}")
            st.write(f"📏 **Distance:** {round(assigned_job.get('distance', 0), 2)} km")
            st.write(f"📅 **Assigned On:** {assigned_job['assigned_date'].strftime('%Y-%m-%d %H:%M')}")
        else:
            st.warning("⚠️ No job site assigned yet.")

        st.write("---")  # Second horizontal line

    # 🔹 **For Admins, Don't Show Blank Row**
    elif user_role == "admin":
        st.write("")  # No blank space; avoids extra empty rows

    # Admin View: Show Employee, Job Site, and Assignment Options
    if user_role == "admin":
        menu_options = {
            "👥 Employees": "employees",
            "🏗️ Job Sites": "job_sites",
            "📋 Assignments": "assignments"
        }
        selected_option = st.radio("Navigation:", list(menu_options.keys()), horizontal=True, index=None)
        if selected_option:
            st.session_state["selected_section"] = menu_options[selected_option]

    # Load relevant section
    if st.session_state.get("selected_section") == "employees":
        st.subheader("👥 Employee Actions")
        menu = ["Add Employee", "View Employees", "Find and Update Employee"]
        choice = st.selectbox("Select an option", menu, index=None, placeholder="Select an action", label_visibility="collapsed")
        if choice == "Add Employee":
            add_employee_form()
        elif choice == "View Employees":
            view_employees()
        elif choice == "Find and Update Employee":
            find_and_update_employee()

    elif st.session_state.get("selected_section") == "job_sites":
        st.subheader("🏗️ Job Site Actions")
        menu = ["Add Job Site", "View Job Sites", "Find and Update Job Site"]
        choice = st.selectbox("Select an option", menu, index=None, placeholder="Select an action", label_visibility="collapsed")
        if choice == "Add Job Site":
            add_job_site_form()
        elif choice == "View Job Sites":
            view_job_sites()
        elif choice == "Find and Update Job Site":
            find_and_update_job_site()

    elif st.session_state.get("selected_section") == "assignments":
        st.subheader("📋 Assignments Actions")
        menu = ["View Assignments", "Do Assignments", "Notify Employees"]
        choice = st.selectbox("Select an option", menu, index=None, placeholder="Select an action", label_visibility="collapsed")
        if choice == "View Assignments":
            view_assignments()
        elif choice == "Do Assignments":
            do_assignments()
        elif choice == "Notify Employees":
            notify_employees()

    elif st.session_state.get("selected_section") == "profile":
        update_profile()

    st.write("---")

    if st.button("🚪 Logout"):
        st.session_state.clear()
        st.rerun()





#----------------------------------------------------------------------------------------

# ✅ Ensure session state is initialized
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False
if "user_email" not in st.session_state:
    st.session_state["user_email"] = None
if "user_role" not in st.session_state:
    st.session_state["user_role"] = "employee"  # Default role is employee
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "selected_section" not in st.session_state:
    st.session_state["selected_section"] = None  # ✅ Ensure this key exists
if "auth_page" not in st.session_state:
    st.session_state["auth_page"] = None  # ✅ Ensure auth_page is initialized
if "show_logo_after_auth" not in st.session_state:
    st.session_state["show_logo_after_auth"] = False  # ✅ Ensure this key exists

#----------------------------------------------------------------------------------------

# ✅ Authentication UI with Persistent Error Messages
def authentication_ui():
    if st.session_state.get("authenticated"):
        return  # Hide authentication UI after login

    st.title("Welcome to")
    st.image("optishift_logo.png", use_container_width=True)
    st.subheader("Please log in or register to continue.")

    col1, col2 = st.columns(2)

    if col1.button("🔐 Login"):
        st.session_state["auth_page"] = "login"
        st.session_state["login_error"] = None
    if col2.button("📝 Register"):
        st.session_state["auth_page"] = "register"
        st.session_state["login_error"] = None

    st.write("---")

    if st.session_state.get("auth_page") == "login":
        st.subheader("🔐 Login to Your Account")
        email = st.text_input("Enter Email Address")
        password = st.text_input("Enter Password", type="password")

        if st.button("Login"):
            login_user(email, password)

        if st.session_state.get("login_error"):
            st.error(st.session_state["login_error"])

    elif st.session_state.get("auth_page") == "register":
        st.subheader("📝 Create a New Account")
        email = st.text_input("Enter Email Address")
        password = st.text_input("Enter Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")

        if st.button("Register"):
            if password == confirm_password:
                register_user(email, password)
                st.session_state["show_logo_after_auth"] = True
                st.session_state["login_error"] = None
                st.rerun()
            else:
                st.warning("⚠️ Passwords do not match. Please try again.")


#----------------------------------------------------------------------------------------


# ✅ Main UI with OptiShift Logo for Employees Until Profile Update
def main():

    # Sidebar is always present but remains hidden
    # Sidebar is always present but remains hidden
    with st.sidebar:
        st.image("optishift_logo.png", use_container_width=True)
        st.write("### 🚀 OptiShift: Smart Workforce Management System")
        st.write("**OptiShift** ensures smart workforce assignments by prioritizing:")
        st.write("- **Best-fit employees** based on role, availability, and location")
        st.write("- **Scoring system** that ranks workers by skills, distance & transport")
        st.write("- **Automated job assignments** for efficiency and fairness")

        st.write("If you're an 👷🏻‍♀ **employee**, register today to be among the first to get assigned to job sites across the GTA as a Labourer, Cleaner, or Painter!")        

        st.write("#### Read about how the optimized scoring systemworks:")

        st.write("- 🏆 **Role Match:** +5 pts if the employee’s role fits the job.")
        st.write("- ⏳ **Availability Match:** +4 pts if schedules align.")
        st.write("- 🚗 **Owns a Car:** +3 pts for easier commute.")
        st.write("- 📍 **Close to Job Site:** +2 pts if within 40 km.")

        st.write("⚡ Employees with the **highest score** are assigned first, ensuring fairness & efficiency.")
        st.write("📊 **Automated, dynamic assignments** keep your workforce optimized in real-time!")


    authentication_ui()
    
    if not st.session_state.get("authenticated"):
        return
    
    main_view()


# ✅ Run App
if __name__ == '__main__':
    main()