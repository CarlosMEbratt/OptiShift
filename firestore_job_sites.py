import random
import string
from datetime import datetime, timedelta
import firebase_admin
from firebase_admin import credentials, firestore
import googlemaps


cred = credentials.Certificate('serviceAccountKey.json')
gmaps = googlemaps.Client(key='AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E')

# Initialize Firebase Admin SDK
firebase_admin.initialize_app(cred)

# Use Firebase Admin's Firestore client
db = firestore.client()
job_sites_ref = db.collection("job_sites")

# Predefined data for randomization
site_names = [
    "Maple Construction", "Sunset Towers", "Skyline Residences", "Urban Hub",
    "Riverside Plaza", "Golden Heights", "Metro Complex", "Harbor View",
    "Evergreen Estates", "Silverlake Projects", "Grand Avenue", "Liberty Square",
    "Hilltop Developments", "Westwood Complex", "Downtown One", "Seaside Residences",
    "Northpoint Tower", "Greenfield Park", "Central Business Plaza", "Lakeshore Condos"
]

# Ontario addresses (50% within Toronto, 50% outside Toronto but within the GTA)
ontario_locations = [
    "3670 Hurontario Street, Mississauga", "10 Bay Street, Toronto", "55 University Avenue, Toronto",
    "1255 Bayly Street, Ajax", "2560 Matheson Boulevard, Mississauga", "3200 Dufferin Street, Toronto",
    "400 Front Street West, Toronto", "700 Lawrence Avenue West, Toronto", "10 Dundas Street East, Toronto",
    "650 King Street West, Toronto", "900 Derry Road West, Mississauga", "250 Yonge Street, Toronto",
    "2500 Simcoe Street North, Oshawa", "2401 Eglinton Avenue East, Toronto", "2100 Highway 7, Vaughan",
    "1250 Markham Road, Scarborough", "2055 Kennedy Road, Scarborough", "2120 Sheppard Avenue East, Toronto",
    "1035 Finch Avenue West, Toronto", "1300 Steeles Avenue West, Vaughan", "1 Bass Pro Mills Drive, Vaughan",
    "35 Lake Street, St. Catharines", "1001 Oakville Place, Oakville", "6500 Millcreek Drive, Milton",
    "55 King Street West, Kitchener", "150 Main Street West, Hamilton", "1 Summers Lane, Hamilton"
]


site_managers = ["Carlos López", "Maria Papadopoulos", "James Rodríguez", "Elena Vasquez", 
                 "Diego Martínez", "Sophia Georgiadis", "Antonio Pérez", "Isabella Nikolopoulos",
                 "Juan Hernández", "Carmen Katsaros"]

roles = ["Cleaner", "Labour", "Painter"]
schedules = ["7:00-15:30", "14:00-22:00", "22:00-06:00"]

# Generate and insert 20 random job sites
for _ in range(20):
    # Choose location based on the new Ontario addresses
    location = random.choice(ontario_locations)
    
    job_site_data = {
        "site_name": random.choice(site_names),
        "location": location,
        "site_manager": random.choice(site_managers),
        "contact_number": f"+1 647-{random.randint(100, 999)}-{random.randint(1000, 9999)}",
        "required_roles": random.sample(roles, k=random.randint(1, 3)),  # 1 to 3 roles
        "work_schedule": random.sample(schedules, k=random.randint(1, 2)),  # 1 to 3 shifts
        "active": True,
        "site_id": f"SITE{random.randint(1000, 9999)}"
    }

    # Add to Firestore
    job_sites_ref.add(job_site_data)

print("✅ A few random job sites added successfully with Ontario locations!")
