import firebase_admin
from firebase_admin import credentials, firestore
import geopy.distance
from sklearn.ensemble import RandomForestClassifier
import pickle
import pandas as pd
from datetime import datetime
from geopy.geocoders import Nominatim
from sklearn.preprocessing import LabelEncoder

# Initialize Firebase Admin SDK
def initialize_firebase():
    try:
        if not firebase_admin._apps:
            cred = credentials.Certificate('serviceAccountKey.json')
            firebase_admin.initialize_app(cred)
        else:
            print("Firebase already initialized.")
    except Exception as e:
        print(f"Error initializing Firebase: {e}")

initialize_firebase()

# Initialize Firestore client
db = firestore.client()

# Fetch employee and job site data
employees_ref = db.collection('employees')
job_sites_ref = db.collection('job_sites')

employees = [doc.to_dict() for doc in employees_ref.stream()]
job_sites = [doc.to_dict() for doc in job_sites_ref.stream()]

# Geocoding function
geolocator = Nominatim(user_agent="OptiShiftApp")

def geocode_address(address):
    try:
        location = geolocator.geocode(address, timeout=10)
        if location:
            return location.latitude, location.longitude
        else:
            print(f"Geocoding failed for address: {address}")
            return None, None
    except Exception as e:
        print(f"Geocoding error for address {address}: {e}")
        return None, None

# Update employee and job site data with latitude and longitude
for employee in employees:
    lat, lon = geocode_address(employee['home_address'])
    if lat is not None and lon is not None:
        employee['latitude'] = lat
        employee['longitude'] = lon
    else:
        print(f"Skipping employee {employee.get('worker_id')} due to missing coordinates.")

for site in job_sites:
    lat, lon = geocode_address(site['location'])
    if lat is not None and lon is not None:
        site['latitude'] = lat
        site['longitude'] = lon
    else:
        print(f"Skipping job site {site.get('site_id')} due to missing coordinates.")

# Feature Engineering
def calculate_distance(employee_location, site_location):
    return geopy.distance.distance(employee_location, site_location).km

# Create feature vectors
features = []
for employee in employees:
    if 'latitude' not in employee or 'longitude' not in employee or None in [employee['latitude'], employee['longitude']]:
        print(f"Skipping employee {employee.get('worker_id')} due to missing coordinates.")
        continue

    for site in job_sites:
        if 'latitude' not in site or 'longitude' not in site or None in [site['latitude'], site['longitude']]:
            print(f"Skipping job site {site.get('site_id')} due to missing coordinates.")
            continue

        employee_location = (employee['latitude'], employee['longitude'])
        site_location = (site['latitude'], site['longitude'])
        distance = calculate_distance(employee_location, site_location)

        feature_vector = {
            'employee_id': employee['worker_id'],
            'job_site_id': site['site_id'],
            'distance': distance,
            'available': 1 if '7:00-15:30' in employee.get('availability', []) else 0,  # Example availability check
            'role': employee.get('role', 'Unknown')
        }
        features.append(feature_vector)

# Encode 'role' as a numeric feature
label_encoder = LabelEncoder()
roles = [feature['role'] for feature in features]
label_encoder.fit(roles)

for feature in features:
    feature['role'] = label_encoder.transform([feature['role']])[0]

# Convert feature vectors to a DataFrame
df = pd.DataFrame(features)

# Ensure features list is not empty
if df.empty:
    print("No valid features generated. Exiting.")
else:
    # Train the model
    model = RandomForestClassifier()
    model.fit(df[['distance', 'available', 'role']], [1] * len(df))  # Dummy target for training

    # Save the model and label encoder
    with open('job_assignment_model.pkl', 'wb') as f:
        pickle.dump(model, f)
    with open('label_encoder.pkl', 'wb') as f:
        pickle.dump(label_encoder, f)

    print("Model and label encoder saved successfully.")

    # Load the trained model and label encoder
    with open('job_assignment_model.pkl', 'rb') as f:
        loaded_model = pickle.load(f)
    with open('label_encoder.pkl', 'rb') as f:
        loaded_label_encoder = pickle.load(f)

    # Assign employees to job sites
    for feature in features:
        prediction = loaded_model.predict([[feature['distance'], feature['available'], feature['role']]])
        if prediction == 1:
            db.collection('assignments').add({
                'employee_id': feature['employee_id'],
                'job_site_id': feature['job_site_id'],
                'assigned_date': datetime.now()
            })
            print(f"Assigned employee {feature['employee_id']} to job site {feature['job_site_id']}.")

    print("Assignments completed.")