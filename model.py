import firebase_admin
from firebase_admin import credentials, firestore
import geopy.distance
from sklearn.ensemble import RandomForestClassifier
import pickle
import pandas as pd
from datetime import datetime

# Initialize Firebase Admin SDK
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

# Firestore client
db = firestore.client()

# Fetch employee data
employees_ref = db.collection('employees')
employees = employees_ref.stream()

# Fetch job site data
job_sites_ref = db.collection('job_sites')
job_sites = job_sites_ref.stream()

# Example: employee and job site data
employee_data = [doc.to_dict() for doc in employees]
job_site_data = [doc.to_dict() for doc in job_sites]

# Geocoding function
from geopy.geocoders import Nominatim

geolocator = Nominatim(user_agent="OptiShiftApp")

def geocode_address(address):
    geolocator = Nominatim(user_agent="OptiShiftApp")
    location = geolocator.geocode(address, timeout=10)  # Increased timeout to 10 seconds
    if location:
        return location.latitude, location.longitude
    else:
        return None, None  # Return None if the geocoding fails

# Update employee and job site data with latitude and longitude
for employee in employee_data:
    lat, lon = geocode_address(employee['home_address'])
    employee['latitude'] = lat
    employee['longitude'] = lon

for site in job_site_data:
    lat, lon = geocode_address(site['location'])
    site['latitude'] = lat
    site['longitude'] = lon

# Feature Engineering
def calculate_distance(employee_location, site_location):
    """Calculate distance between two locations."""
    return geopy.distance.distance(employee_location, site_location).km

# Create feature vectors
features = []
for employee in employee_data:
    for site in job_site_data:
        if employee['latitude'] is not None and site['latitude'] is not None:
            # Calculate distance between employee and job site
            employee_location = (employee['latitude'], employee['longitude'])
            site_location = (site['latitude'], site['longitude'])
            distance = calculate_distance(employee_location, site_location)
            
            feature_vector = {
                'employee_id': employee['worker_id'],
                'job_site_id': site['site_id'],
                'distance': distance,
                'available': employee['availability'],  # Other relevant features
                'role': employee['role']
            }
            features.append(feature_vector)

# Machine Learning Model

# Convert feature vectors to a DataFrame
df = pd.DataFrame(features)

# Define the target variable (e.g., job_site_assignment: 1 for assigned, 0 for not assigned)
df['assigned'] = [1 if x['employee_id'] == x['job_site_id'] else 0 for x in features]  # Example target

# Split data into features (X) and target (y)
X = df[['distance', 'available', 'role']]  # Add more features as needed
y = df['assigned']

# Train the model
model = RandomForestClassifier()
model.fit(X, y)

# Save the model as a .pkl file
with open('job_assignment_model.pkl', 'wb') as f:
    pickle.dump(model, f)

print("Model trained and saved successfully.")

# Model Storage and Deployment

# Load the trained model when needed
with open('job_assignment_model.pkl', 'rb') as f:
    loaded_model = pickle.load(f)

# Use the model for predictions
new_data = pd.DataFrame({
    'distance': [10],
    'available': [1],  # Example feature
    'role': ['Cleaner']  # Example feature
})

prediction = loaded_model.predict(new_data)
print("Predicted assignment:", prediction)

# Daily predictions and updates

def assign_jobs_daily():
    # Fetch updated employee and job site data
    employees = employees_ref.stream()
    job_sites = job_sites_ref.stream()

    # Calculate new features
    features = []
    for employee in employees:
        for site in job_sites:
            # Calculate distance and generate feature vector as shown before
            employee_location = (employee['latitude'], employee['longitude'])
            site_location = (site['latitude'], site['longitude'])
            distance = calculate_distance(employee_location, site_location)
            
            feature_vector = {
                'employee_id': employee['worker_id'],
                'job_site_id': site['site_id'],
                'distance': distance,
                'available': employee['availability'],
                'role': employee['role']
            }
            features.append(feature_vector)

    # Predict using the saved model
    new_data = pd.DataFrame(features)
    predictions = loaded_model.predict(new_data)
    
    # Assign employees to job sites based on predictions
    for i, prediction in enumerate(predictions):
        if prediction == 1:
            employee_id = features[i]['employee_id']
            job_site_id = features[i]['job_site_id']
            # Update the assignment in Firestore
            db.collection('shift_assignments').add({
                'employee_id': employee_id,
                'job_site_id': job_site_id,
                'assigned_date': datetime.now()
            })

# Call daily assignment function
assign_jobs_daily()
