from datetime import datetime, timezone
from pymongo import MongoClient, ASCENDING, DESCENDING
from werkzeug.security import generate_password_hash

# Connect to MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['interview_platform']

# Create Collections
def setup_collections():
    # Users Collection
    if 'users' not in db.list_collection_names():
        users = db.create_collection('users')
        
        # Create indexes
        users.create_index([('email', ASCENDING)], unique=True)
        users.create_index([('created_at', DESCENDING)])
        
        # Sample user data
        users.insert_many([
            {
                'email': 'admin@example.com',
                'password': generate_password_hash('admin123'),
                'name': 'Admin User',
                'role': 'admin',
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'profile': {
                    'title': 'Senior Interviewer',
                    'experience': '5 years',
                    'skills': ['Python', 'JavaScript', 'System Design']
                }
            },
            {
                'email': 'user@example.com',
                'password': generate_password_hash('user123'),
                'name': 'User',
                'role': 'user',
                'created_at': datetime.now(timezone.utc),
                'last_login': None,
                'profile': {
                    'title': 'Software Engineer',
                    'experience': '0 years',
                    'skills': ['Python']
                }
            }
        ])

    # Interviews Collection
    if 'interviews' not in db.list_collection_names():
        interviews = db.create_collection('interviews')
        
        # Create indexes
        interviews.create_index([('interviewer_id', ASCENDING)])
        interviews.create_index([('interviewee_id', ASCENDING)])
        interviews.create_index([('date', ASCENDING)])
        interviews.create_index([('status', ASCENDING)])
        
        # Sample interview data
        interviews.insert_one({
            'interviewer_id': 'interviewer_object_id',
            'interviewee_id': 'interviewee_object_id',
            'date': datetime.now(timezone.utc),
            'time': '14:00',
            'duration': 60,  # in minutes
            'status': 'scheduled',  # scheduled, ongoing, completed, cancelled
            'type': 'technical',
            'created_at': datetime.now(timezone.utc),
            'updated_at': datetime.now(timezone.utc),
            'meeting_link': 'room_id',
            'notes': '',
            'feedback': None
        })

    # Interview Feedback Collection
    if 'feedback' not in db.list_collection_names():
        feedback = db.create_collection('feedback')
        
        # Create indexes
        feedback.create_index([('interview_id', ASCENDING)])
        feedback.create_index([('created_at', DESCENDING)])
        
        # Sample feedback data
        feedback.insert_one({
            'interview_id': 'interview_object_id',
            'interviewer_id': 'interviewer_object_id',
            'rating': 4,  # 1-5 scale
            'technical_skills': {
                'problem_solving': 4,
                'code_quality': 3,
                'system_design': 4
            },
            'soft_skills': {
                'communication': 4,
                'attitude': 5
            },
            'notes': 'Good understanding of algorithms',
            'recommendations': 'Should focus more on code optimization',
            'decision': 'move_forward',  # move_forward, reject, need_more_interviews
            'created_at': datetime.now(timezone.utc)
        })

    # Chat Messages Collection
    if 'messages' not in db.list_collection_names():
        messages = db.create_collection('messages')
        
        # Create indexes
        messages.create_index([('interview_id', ASCENDING)])
        messages.create_index([('timestamp', DESCENDING)])
        
        # Sample message data
        messages.insert_one({
            'interview_id': 'interview_object_id',
            'sender_id': 'user_object_id',
            'message_type': 'text',  # text, code, system
            'content': 'Hello, let\'s start with algorithms',
            'timestamp': datetime.now(timezone.utc)
        })

    # AI Assistance History Collection
    if 'ai_assistance' not in db.list_collection_names():
        ai_assistance = db.create_collection('ai_assistance')
        
        # Create indexes
        ai_assistance.create_index([('interview_id', ASCENDING)])
        ai_assistance.create_index([('timestamp', DESCENDING)])
        
        # Sample AI assistance data
        ai_assistance.insert_one({
            'interview_id': 'interview_object_id',
            'interviewer_id': 'interviewer_object_id',
            'prompt': 'Suggest next question for algorithms',
            'response': 'Consider asking about time complexity...',
            'timestamp': datetime.now(timezone.utc)
        })

# Collection Schemas
COLLECTION_SCHEMAS = {
    'users': {
        'email': str,  # unique
        'password': str,  # hashed
        'name': str,
        'role': str,  # admin, interviewer, candidate
        'created_at': datetime,
        'last_login': datetime,
        'profile': {
            'title': str,
            'experience': str,
            'skills': list
        }
    },
    
    'interviews': {
        'interviewer_id': str,  # reference to users
        'interviewee_id': str,  # reference to users
        'date': datetime,
        'time': str,
        'duration': int,  # minutes
        'status': str,  # scheduled, ongoing, completed, cancelled
        'type': str,  # technical, behavioral, system design
        'created_at': datetime,
        'updated_at': datetime,
        'meeting_link': str,
        'notes': str,
        'feedback': dict  # or reference to feedback collection
    },
    
    'feedback': {
        'interview_id': str,  # reference to interviews
        'interviewer_id': str,  # reference to users
        'rating': int,  # 1-5
        'technical_skills': {
            'problem_solving': int,
            'code_quality': int,
            'system_design': int
        },
        'soft_skills': {
            'communication': int,
            'attitude': int
        },
        'notes': str,
        'recommendations': str,
        'decision': str,
        'created_at': datetime
    },
    
    'messages': {
        'interview_id': str,  # reference to interviews
        'sender_id': str,  # reference to users
        'message_type': str,  # text, code, system
        'content': str,
        'timestamp': datetime
    },
    
    'ai_assistance': {
        'interview_id': str,  # reference to interviews
        'interviewer_id': str,  # reference to users
        'prompt': str,
        'response': str,
        'timestamp': datetime
    }
}

if __name__ == '__main__':
    setup_collections()
    print("MongoDB collections and indexes created successfully!")