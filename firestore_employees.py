import random
import string
import firebase_admin
from firebase_admin import credentials, firestore
import googlemaps
import re

# Initialize Firebase
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)
db = firestore.client()

gmaps = googlemaps.Client(key='AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E')  # Replace with actual API key

# List of known cities (normalize to lowercase for comparison)
known_cities = ["toronto", "mississauga", "north york", "montreal"]

# Function to generate a random worker ID
def generate_worker_id():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

# Random Name Generator
def generate_random_name():
    first_names = ["Carlos", "José", "Luis", "Manuel", "Diego", "Antonio", "Pedro", "Juan", "Alejandro"]
    middle_names = ["Jose", "Miguel", "Hernando", "Mauricio", "Andres", "Estiven", "Felipe"]
    last_names = ["González", "Rodríguez", "Pérez", "Gómez", "Hernández", "Martínez", "López", "Vázquez", "Munoz", "Ebratt"]
    return random.choice(first_names), random.choice(middle_names), random.choice(last_names)

# Random phone number generator
def generate_random_phone_number():
    return str(random.randint(4373315311, 4379999999))

# Function to clean addresses
def clean_address(address):
    cleaned_address = re.sub(r'\b(Unit|Ste|Suite|Apt|Apartment|Floor|Rm|Room)\s*\d+\b', '', address, flags=re.IGNORECASE).strip()
    return cleaned_address

# Function to generate random real addresses using Google Places API
def generate_random_real_address():
    location = (43.6, -79.64)
    radius = 1000000
    try:
        places = gmaps.places_nearby(location, radius=radius)
        if places["status"] == "OK":
            random_place = random.choice(places["results"])
            address = random_place.get("vicinity", "Unknown Address")
            return clean_address(address)
    except googlemaps.exceptions.ApiError:
        return "Unknown Address"

# Generate random availability
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

# Generate skills
def generate_role():
    return random.sample(["Cleaner", "Labour", "Painter"], random.randint(1, 3))

# Generate rating
def generate_rating():
    return round(random.uniform(3.0, 5.0), 1)

# Function to create and add an employee
def create_employee():
    first_name, middle_name, last_name = generate_random_name()
    worker_id = generate_worker_id()
    home_address = generate_random_real_address()

    employee_data = {
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
    
    employees_ref = db.collection('employees')
    employees_ref.add(employee_data)
    print(f"Employee {worker_id} added to Firestore.")

# Function to delete city-only addresses
def delete_city_only_addresses():
    employees_ref = db.collection('employees')
    for doc in employees_ref.stream():
        employee_data = doc.to_dict()
        address = employee_data.get('home_address', '').strip()
        if not address:
            print(f"Skipping empty address for {doc.id}")
            continue
        cleaned_address = address.lower().strip()
        if cleaned_address in known_cities:
            print(f"Deleting employee {doc.id} with city-only address: {address}")
            doc.reference.delete()
        else:
            print(f"Keeping employee {doc.id} with valid address: {address}")

# Create 10 dummy employees
for _ in range(60):
    create_employee()

print("Employees have been added to the 'employees' collection.")

# Run the cleanup function
delete_city_only_addresses()