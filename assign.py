import time
import googlemaps
import firebase_admin
from firebase_admin import credentials, firestore
import pandas as pd
import geopy.distance
import re
from datetime import datetime
from geopy.geocoders import Nominatim
from geopy.exc import GeocoderTimedOut

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

# ✅ Step 2: Initialize Geocoders
GOOGLE_API_KEY = "AIzaSyADgR5Y3ARu69ClnxiAJ2XN5XZQ7OaY_0E"  # 🔥 Replace with your actual API key
gmaps = googlemaps.Client(key=GOOGLE_API_KEY)
geolocator_osm = Nominatim(user_agent="optishipp_geocoder")  # OSM as a backup

# ✅ Step 3: Geocoding Functions

def clean_geocode_address(address):
    """
    Cleans an address by removing unit numbers, shopping centers, and unnecessary details.
    """
    address = re.sub(r'\b(Unit|Suite|Apt|Floor|Rm|#)\s*\d+\b', '', address, flags=re.IGNORECASE)
    address = re.sub(r'\b(Shopping Center|Mall|Plaza|Building|Complex)\b', '', address, flags=re.IGNORECASE)
    return address.strip()

def google_geocode(address, max_retries=3):
    """
    Attempts to geocode an address using Google Maps API with retry logic.
    """
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
    """
    Attempts to geocode an address using OpenStreetMap (OSM) with retry logic.
    """
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
    """Attempts to geocode an address using Google Maps first, then OpenStreetMap as a backup."""
    lat, lon = google_geocode(address)
    if lat is None or lon is None:
        lat, lon = osm_geocode(address)
    return lat, lon

# ✅ Step 4: Fetch Employees & Job Sites
try:
    employees = [doc.to_dict() for doc in db.collection("employees").stream()]
    job_sites = [doc.to_dict() for doc in db.collection("job_sites").stream()]
    print(f"📋 Employees Loaded: {len(employees)}")
    print(f"🏗️ Job Sites Loaded: {len(job_sites)}")
except Exception as e:
    print(f"🔥 Firestore Error: {e}")
    employees, job_sites = [], []

# ✅ Step 5: Ensure Employees & Job Sites Have Latitude & Longitude
for entity in employees + job_sites:
    key = "home_address" if "home_address" in entity else "address"
    if "latitude" not in entity or "longitude" not in entity or entity["latitude"] is None or entity["longitude"] is None:
        lat, lon = geocode_address(entity.get(key, ""))
        if lat is None or lon is None:
            print(f"⚠️ Skipping {entity.get('worker_id', entity.get('site_id', 'UNKNOWN'))} due to missing geolocation data.")
            continue
        entity["latitude"] = lat
        entity["longitude"] = lon

# ✅ Step 6: Distance Calculation with Safety Checks

def calculate_distance(employee_location, site_location):
    if None in employee_location or None in site_location:
        print(f"⚠️ Cannot calculate distance. Missing coordinates: {employee_location}, {site_location}")
        return float('inf')
    return geopy.distance.distance(employee_location, site_location).km

# ✅ Step 7: Employee Assignment Logic
assigned_employees = set()
db.collection("assignments").document("all").delete()  # Delete old assignments

for site in job_sites:
    required_roles = site.get('required_roles', {})
    assigned_counts = {role: 0 for role in required_roles}

    for role, role_data in required_roles.items():
        required_count = role_data.get('num_workers', 0)
        if required_count == 0:
            continue

        employee_scores = []
        for employee in employees:
            score = 0
            if role in employee.get('role', []):
                score += 5
            if any(shift in employee.get('availability', []) for shift in role_data.get('work_schedule', [])):
                score += 4
            if employee.get('have_car', 'No') == 'Yes':
                score += 3

            distance = calculate_distance((employee['latitude'], employee['longitude']), (site['latitude'], site['longitude']))
            if distance <= 40:
                score += 2

            employee_scores.append({'employee': employee, 'score': score, 'distance': distance})

        sorted_employees = sorted(employee_scores, key=lambda x: (-x['score'], x['distance'], -x['employee'].get('rating', 0)))
        
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

print("🚀 Employee assignment completed!")
