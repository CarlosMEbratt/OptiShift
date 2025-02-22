import random
import string
import firebase_admin
from firebase_admin import credentials, firestore
import googlemaps
import re
import time

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

# Google Maps API Setup (Replace with your actual API key securely)
gmaps = googlemaps.Client(key='AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E')  # Store API key securely

# List of known cities
known_cities = {"toronto", "mississauga", "north york", "montreal", "oakville", "old toronto"}

# Generate a random worker ID
def generate_worker_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Generate a random name
def generate_random_name():
    first_names = ["Carlos", "José", "Luis", "Manuel", "Diego", "Antonio", "Pedro", "Juan", "Alejandro"]
    middle_names = ["Jose", "Miguel", "Hernando", "Mauricio", "Andres", "Estiven", "Felipe"]
    last_names = ["González", "Rodríguez", "Pérez", "Gómez", "Hernández", "Martínez", "López", "Vázquez", "Muñoz", "Ebratt"]
    return random.choice(first_names), random.choice(middle_names), random.choice(last_names)

# Generate a random phone number
def generate_random_phone_number():
    return str(random.randint(4373315311, 4379999999))

# Clean addresses
def clean_address(address):
    """Removes unit numbers and checks for valid street addresses."""
    address = re.sub(r'\b(Unit|Ste|#|Suite|Apt|Apartment|Floor|Rm|Room)\s*\d+\b', '', address, flags=re.IGNORECASE).strip()
    
    # Ensure address is more than just a city or single word
    if len(address.split()) < 2 or address.lower() in known_cities:
        return "Invalid Address"
    
    return address

def generate_random_real_address(existing_addresses, retry=5):
    """Fetches a real address from Google Places API using text search."""
    attempts = 0
    while attempts < retry:
        try:
            query = random.choice(["Street", "Road", "Avenue", "Boulevard", "Drive"]) + " in Toronto"
            places_result = gmaps.places(query=query, location=(43.65107, -79.347015), radius=30000)
            
            if places_result.get("status") == "OK" and places_result.get("results"):
                random_place = random.choice(places_result["results"])
                address = random_place.get("formatted_address", "Unknown Address")

                cleaned_address = clean_address(address)
                if cleaned_address not in existing_addresses and cleaned_address != "Invalid Address":
                    existing_addresses.add(cleaned_address)
                    return cleaned_address
                else:
                    print(f"🚨 Skipping duplicate or invalid address: {cleaned_address}")

        except googlemaps.exceptions.ApiError as e:
            print(f"Google Maps API error: {e}")
        except Exception as e:
            print(f"Unexpected error: {e}")

        attempts += 1
        

    return "Unknown Address"


# Generate availability
def generate_availability():
    return random.choice([["7:00-15:30"], ["14:00-22:00"], ["22:00-06:00"]])

# Generate certifications
def generate_certifications():
    return random.sample(["Working at Heights", "4 Steps", "WHMIS"], random.randint(1, 3))

# Generate skills
def generate_skills():
    return random.sample(["Boomlift", "Scissors Lift", "Forklift"], random.randint(1, 3))

# Generate car ownership
def generate_have_car():
    return random.choice(["Yes", "No"])

# Generate role
def generate_role():
    return random.choice(["Cleaner", "Labour", "Painter"])

# Generate rating
def generate_rating():
    return round(random.uniform(3.0, 5.0), 1)

# Create an employee and add to Firestore
def create_employee(existing_addresses):
    first_name, middle_name, last_name = generate_random_name()
    worker_id = generate_worker_id()
    home_address = generate_random_real_address(existing_addresses)

    if home_address == "Unknown Address":
        print(f"❌ Skipping employee {worker_id} due to invalid address.")
        return None  # Skip if no valid address

    return {
        "worker_id": worker_id,
        "first_name": first_name,
        "middle_name": middle_name,
        "sur_name": last_name,
        "phone_number": generate_random_phone_number(),
        "home_address": home_address,
        "have_car": generate_have_car(),
        "role": generate_role(),
        "availability": generate_availability(),
        "certificates": generate_certifications(),
        "skills": generate_skills(),
        "rating": generate_rating()
    }

# Batch write employees to Firestore
def batch_upload_employees(num_employees=60):
    existing_addresses = set()  # Track used addresses
    employees = []

    for _ in range(num_employees):
        employee = create_employee(existing_addresses)
        if employee:
            employees.append(employee)

    if employees:
        batch = db.batch()
        employees_ref = db.collection('employees')

        for emp in employees:
            batch.set(employees_ref.document(), emp)  # Use batch for efficiency

        batch.commit()
        print(f"✅ Successfully added {len(employees)} employees.")

# Cleanup invalid addresses
def delete_invalid_addresses():
    employees_ref = db.collection('employees')
    deleted_employees = []

    for doc in employees_ref.stream():
        employee_data = doc.to_dict()
        address = employee_data.get('home_address', '').strip()

        if not address or address.lower() in known_cities or "unknown" in address.lower():
            print(f"❌ Deleting employee {doc.id} due to invalid address: {address}")
            doc.reference.delete()
            deleted_employees.append((doc.id, address))

    # Log deleted employees for review
    print("\n🗑️ Deleted Employees Due to Invalid Addresses:")
    for emp_id, emp_address in deleted_employees:
        print(f"❌ {emp_id} - {emp_address}")

# Run script
if __name__ == "__main__":
    batch_upload_employees(100)  # Generate 100 employees
    delete_invalid_addresses()   # Cleanup
