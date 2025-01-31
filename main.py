import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore


# Fetch the service account key JSON file contents
cred = credentials.Certificate('serviceAccountKey.json')

# Initialize the app with a service account, granting admin privileges
firebase_admin.initialize_app(cred)

db = firestore.client()

# 3. Create a collection and add a document (example)

# a) Add a document with a generated ID:
doc_ref = db.collection('users').document()  # Let Firestore generate the ID
doc_ref.set({
    'first': 'Grace',
    'last': 'Hopper',
    'born': 1906
})
print(f"Document added with ID: {doc_ref.id}")


# b) Add a document with a specific ID:
doc_ref = db.collection('sites').document('site_123')  # Use a specific ID
doc_ref.set({
    'location': '123 Main St',
    'size': 1000,
    'required_skills': ['cleaning', 'maintenance']
})
print(f"Document added with ID: {doc_ref.id}")



# c) Add a document to a subcollection:
doc_ref = db.collection('users').document('grace_hopper').collection('work_history').document('job1')
doc_ref.set({
    'start_date': '1940-01-01',
    'end_date': '1950-01-01',
    'title': 'Computer Scientist'
})