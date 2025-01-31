import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firestore
cred = credentials.Certificate('serviceAccountKey.json')
firebase_admin.initialize_app(cred)

db = firestore.client()

# List of known cities (normalize to lowercase for comparison)
known_cities = ["toronto", "mississauga", "north york", "montreal"]

def delete_city_only_addresses():
    employees_ref = db.collection('employees')  # Replace with your collection name

    # Process the employees collection
    for doc in employees_ref.stream():
        employee_data = doc.to_dict()  # Convert Firestore document to dictionary
        address = employee_data.get('home_address', '').strip()  # Fetch and strip spaces

        if not address:  # Skip if address is empty
            print(f"Skipping empty address for {doc.id}")
            continue

        # Print the fetched address for debugging
        print(f"Checking document {doc.id}: Address = '{address}'")

        # Normalize case and remove extra spaces before checking
        cleaned_address = address.lower().strip()
        
        # If the entire address is just a known city name, delete it
        if cleaned_address in known_cities:
            print(f"Deleting employee {doc.id} with city-only address: {address}")
            doc.reference.delete()
        else:
            print(f"Keeping employee {doc.id} with valid address: {address}")

# Run the function
delete_city_only_addresses()
