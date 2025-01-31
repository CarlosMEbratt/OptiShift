import random
import string
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import googlemaps
import random
import re
import time


cred = credentials.Certificate('serviceAccountKey.json')
gmaps = googlemaps.Client(key='AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E')

firebase_admin.initialize_app(cred)

db = firestore.client()

# Random First Name, Middle Name, and Surname
def generate_random_name():
    # Spanish names (Male & Female)
    first_names_male_spanish = ["Carlos", "José", "Luis", "Manuel", "Diego", "Antonio", "Pedro", "Juan", "Alejandro"]
    first_names_female_spanish = ["María", "Ana", "Sofia", "Isabella", "Elena", "Gabriela", "Carmen", "Lucía", "Patricia"]
    
    middle_names_male_spanish = ["Jose", "Miguel", "Hermnando", "Mauricio", "Andres", "Estiven", "Felipe"]
    middle_names_female_spanish = ["Lucia", "Andrea", "Carolina", "Adina", "Ivanna", "Julia", "Elizabeth"]

    last_names_spanish = ["González", "Rodríguez", "Pérez", "Gómez", "Hernández", "Martínez", "López", "Vázquez"]

    # Greek names (Only Male)
    first_names_male_greek = ["Alex", "Dimitrios", "Georgios", "Christos", "Panagiotis", "Ioannis", "Andreas"]
    middle_names_male_greek = ["Theodoros", "Konstantinos", "Vasileios", "Evangelos", "Spyros", "Leonidas"]
    last_names_greek = ["Papadopoulos", "Nikolopoulos", "Katsaros", "Christopoulos", "Vasilakis", "Georgiadis"]

    # Randomly decide between Spanish or Greek
    if random.choice([True, False]):  # 50% chance of Spanish or Greek
        if random.choice([True, False]):  # 50% chance of Male or Female
            first_name = random.choice(first_names_male_spanish)
            middle_name = random.choice(middle_names_male_spanish)
        else:
            first_name = random.choice(first_names_female_spanish)
            middle_name = random.choice(middle_names_female_spanish)
        last_name = random.choice(last_names_spanish)
    else:
        first_name = random.choice(first_names_male_greek)
        middle_name = random.choice(middle_names_male_greek)
        last_name = random.choice(last_names_greek)

    return first_name, middle_name, last_name

# Random phone number generation (as a string)
def generate_random_phone_number():
    return str(random.randint(4373315311, 4379999999))

# Random skills assignment
def generate_random_skills():
    skills = ["Cleaning", "Labour", "Painter"]
    return random.sample(skills, random.randint(1, len(skills)))

# Random certifications
def generate_random_certifications():
    certifications = ["WHMIS", "4 Steps", "Forklift", "Boomlift", "Working at Heights", "Scissors Lift"]
    return random.sample(certifications, random.randint(2, len(certifications)))


# --------------------------------------------------------------------------------------------------------------------
# Function to generate random real addresses using Google Places API
def generate_random_real_address():
    # Example location within GTA (Toronto, Ontario)
    location = (43.6, -79.64)  # Latitude and longitude for the center of Toronto
    radius = 1000000  # Search within a 100 km radius

    try:
        # Fetch places near the location
        places = gmaps.places_nearby(location, radius=radius)

        if places["status"] == "OK":
            # Pick a random place from the results
            random_place = random.choice(places["results"])
            address = random_place.get("vicinity", "Unknown Address")
            print(f"Random Address: {address}")
            return address
        else:
            print(f"Error fetching places: {places['status']}")
            return None
    except googlemaps.exceptions.ApiError as e:
        print(f"API Error: {e}")
        return None

# --------------------------------------------------------------------------------------------------------------------

# Random shift availability (80% daytime, 20% overnight)
def generate_availability():
    if random.random() < 0.8:
        return ["7:00-15:30"]
    else:
        return random.choice([["22:00-06:00"], ["7:00-15:30", "22:00-06:00"]])

# Function to create and add an employee
def create_employee():
    first_name, middle_name, last_name = generate_random_name()
    availability = generate_availability()
    certifications = generate_random_certifications()
    skills = generate_random_skills()
    home_address = generate_random_real_address()  # Get real address using Google Places API
    phone_number = generate_random_phone_number()  # Phone number as a string
    
    role = random.choice(["Cleaner", "Labour", "Painter"])
    
    worker_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))  # Random worker ID

    # Employee data structure (removed 'tenure' and using phone number as string)
    employee_data = {
        "availability": availability,
        "certificates": certifications,
        "first_name": first_name,
        "middle_name": middle_name,
        "sur_name": last_name,
        "home_address": home_address,  # Store the random real address here
        "phone_number": phone_number,  # Phone number as a string
        "rating": round(random.uniform(1, 5), 1),  # Random rating between 1 and 5
        "skills": skills,
        "role": role,
        "worker_id": worker_id
    }
    
    # Add employee to Firestore
    employees_ref = db.collection('employees2')
    employees_ref.add(employee_data)
    print(f"Employee {worker_id} added to Firestore.")

# Create 100 dummy employees
for _ in range(10):
    create_employee()

print("100 employees have been added to the 'employees' collection.")
