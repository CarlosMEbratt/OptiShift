import streamlit as st
import firebase_admin
import pandas as pd
from firebase_admin import credentials, firestore, exceptions
import random, string


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


# Streamlit UI for adding a job site
def add_job_site_form():
    st.header("Add Job Site")

    site_id = f"SITE{random.randint(1000, 9999)}"  # Auto-generated site ID
    st.write(f"Generated Site ID: {site_id}")  # Debugging output
    
    site_name = st.text_input("Site Name")
    site_company = st.text_input("Site Company")
    site_superintendent = st.text_input("Site Superintendent")
    site_contact_number = st.text_input("Site Contact Number")
    address = st.text_input("Site Address (Use Google Maps for accuracy)")
    
    # Required roles selection with toggle
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
            "site_id": job_site.get("site_id", "N/A"),
            "site_name": job_site.get("site_name", "N/A"),
            "site_company": job_site.get("site_company", "N/A"),
            "site_superintendent": job_site.get("site_superintendent", "N/A"),
            "site_contact_number": job_site.get("site_contact_number", "N/A"),
            "address": job_site.get("address", "N/A"),
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

        job_site_data["num_workers"] = total_workers  # Add computed num_workers
        job_site_data["required_roles"] = ", ".join(formatted_roles) if formatted_roles else "N/A"

        job_sites_data.append(job_site_data)

    # Convert data to a DataFrame
    job_sites_df = pd.DataFrame(job_sites_data)

    # Define the correct column order
    column_order = ["site_id", "site_name", "site_company", "site_superintendent", 
                    "site_contact_number", "address", "num_workers", "required_roles"]

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

# Streamlit UI to select and display different actions
def main():
    menu1 = ["Add Employee", "View Employees"]
    choice1 = st.sidebar.selectbox("Employees Actions selection:", menu1, index=None)

    menu2 = ["Add Job Site", "View Job Sites"]
    choice2 = st.sidebar.selectbox("Job Sites Actions selection:", menu2, index=None)

    menu3 = ["Assign Employee", "View Assignments"]
    choice3 = st.sidebar.selectbox("Assignments actions selection:", menu3, index=None)

    # Default view: Show image in the center before selection
    if choice1 is None and choice2 is None and choice3 is None:
        st.image("optishift_logo.png", use_container_width=True)

    if choice1 == "Add Employee":
        add_employee_form()
    elif choice1 == "View Employees":
        view_employees()
    
    if choice2 == "Add Job Site":
        add_job_site_form()
    elif choice2 == "View Job Sites":
        view_job_sites()
    
    if choice3 == "Assign Employee":
        assign_employee_form()
    elif choice3 == "View Assignments":
        view_assignments()

if __name__ == '__main__':
    main()

