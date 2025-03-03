import gevent.monkey
gevent.monkey.patch_all()

# Now import other modules
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import os
from dotenv import load_dotenv
from bson import ObjectId
import json
import uuid
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from threading import Thread
import time
import logging
import warnings
from gemini_config import init_gemini, create_assessment_chain, create_question_chain, init_vector_store, get_similar_questions, check_ai_services_status
import atexit
import google.generativeai as genai
import sys
import random
from pathlib import Path
import requests

# Configure logging
logging.basicConfig(level=logging.WARNING)  # Change from INFO to WARNING
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__, 
    template_folder='frontend', 
    static_folder='frontend/assets',
    static_url_path='/assets'
)

# Configure the app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

# MongoDB Configuration
app.config['MONGO_URI'] = 'mongodb://localhost:27017/interview_platform'

# Initialize MongoDB with error handling
try:
    mongo = PyMongo(app)
    # Test the connection
    mongo.db.command('ping')
    print("MongoDB connected successfully")
except Exception as e:
    print(f"MongoDB connection error: {str(e)}")
    raise

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configure CORS
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Initialize SocketIO
socketio = SocketIO(
    app,
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=30,
    ping_interval=10,
    logger=True,
    engineio_logger=True
)

# Suppress specific warnings and logs
logging.getLogger('gevent').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Suppress Flask development server logs
logging.getLogger('sentence_transformers').setLevel(logging.ERROR)  # Suppress transformer logs

# Suppress specific warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Invalid HTTP method.*")
warnings.filterwarnings("ignore", message=".*HuggingFaceEmbeddings.*")  # Suppress HuggingFace warning

# Optional: Create a custom filter to ignore specific log messages
class SocketHandshakeFilter(logging.Filter):
    def filter(self, record):
        return not ('Invalid HTTP method' in record.getMessage() or 
                   'SSL/TLS handshake' in record.getMessage() or
                   'HuggingFaceEmbeddings' in record.getMessage())

# Apply the filter to your logger
logger.addFilter(SocketHandshakeFilter())

# Add connection tracking
connections = {}

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data
        self.id = str(user_data['_id'])
        self.email = user_data['email']
        self.name = user_data['name']

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    try:
        user_data = mongo.db.users.find_one({'_id': ObjectId(user_id)})
        return User(user_data) if user_data else None
    except Exception as e:
        print(f"Error loading user: {e}")
        return None

def get_ai_assistance(prompt, retries=3):
    """
    Get AI assistance with retry mechanism and better error handling
    """
    for attempt in range(retries):
        try:
            model = genai.GenerativeModel('gemini-1.5-pro-latest')
            response = model.generate_content(prompt)
            
            if not response or not response.text:
                raise ValueError("Empty response from Gemini")
                
            return response.text
            
        except Exception as e:
            logger.error(f"Gemini API error (attempt {attempt + 1}/{retries}): {str(e)}")
            if attempt == retries - 1:  # Last attempt
                raise
            time.sleep(1)  # Wait before retrying

# Auth Route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        confirm_password = data.get('confirm_password')
        
        print(f"Login Request Received:")
        print(f"Email: {email}")
        print(f"Password Provided: {'Yes' if password else 'No'}")
        print(f"Confirm Password Provided: {confirm_password}")
        
        if not email:
            print("Error: Email is required")
            return jsonify({
                'success': False, 
                'message': 'Email is required',
                'redirect': None
            }), 400
        
        if not password:
            print("Error: Password is required")
            return jsonify({
                'success': False, 
                'message': 'Password is required',
                'redirect': None
            }), 400
        
        user_data = mongo.db.users.find_one({'email': email})
        
        if user_data:
            # Login process
            print("User exists, attempting login")
            # Convert ObjectId to string if necessary
            user_data['_id'] = str(user_data['_id'])
            
            if check_password_hash(user_data['password'], password):
                user = User(user_data)
                login_user(user)
                print("Login successful")
                dashboard_url = url_for('dashboard', _external=True)  # Use external URL
                print(f"Redirect URL: {dashboard_url}")
                return jsonify({
                    'success': True, 
                    'message': 'Logged in successfully', 
                    'redirect': dashboard_url
                })
            else:
                print("Invalid credentials")
                return jsonify({
                    'success': False, 
                    'message': 'Invalid credentials',
                    'redirect': None
                }), 401
        else:
            # Registration process
            print("New user registration attempt")
            
            # Explicitly check if this is a signup attempt
            if confirm_password is None:
                print("Error: Confirm password is required for signup")
                return jsonify({
                    'success': False, 
                    'message': 'Confirm password is required for signup',
                    'redirect': None
                }), 400
            
            # Validate confirm_password
            if not confirm_password:
                print("Error: Confirm password cannot be empty")
                return jsonify({
                    'success': False, 
                    'message': 'Confirm password cannot be empty',
                    'redirect': None
                }), 400
            
            if password != confirm_password:
                print("Error: Passwords do not match")
                return jsonify({
                    'success': False, 
                    'message': 'Passwords do not match',
                    'redirect': None
                }), 400
            
            # Password strength validation
            if len(password) < 8:
                print("Error: Password too short")
                return jsonify({
                    'success': False, 
                    'message': 'Password must be at least 8 characters long',
                    'redirect': None
                }), 400
            
            user_data = {
                'email': email,
                'password': generate_password_hash(password),
                'name': email.split('@')[0],  # Use part of email as name
                'created_at': datetime.now(timezone.utc)
            }
            
            try:
                user_id = mongo.db.users.insert_one(user_data).inserted_id
                user_data['_id'] = str(user_id)
                user = User(user_data)
                login_user(user)
                print("User registration successful")
                dashboard_url = url_for('dashboard', _external=True)  # Use external URL
                print(f"Redirect URL: {dashboard_url}")
                return jsonify({
                    'success': True, 
                    'message': 'Account created successfully', 
                    'redirect': dashboard_url
                })
            except Exception as e:
                print(f"Registration error: {str(e)}")
                return jsonify({
                    'success': False, 
                    'message': f'Error: {str(e)}',
                    'redirect': None
                }), 500
    
    is_logged_in = current_user.is_authenticated
    print(f"Login accessed, isLoggedIn: {is_logged_in}")
    return render_template('pages/login.html', is_login_mode=True, isLoggedIn=is_logged_in)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
def index():
    is_logged_in = current_user.is_authenticated
    print(f"Index accessed, isLoggedIn: {is_logged_in}")
    return render_template('index.html', isLoggedIn=is_logged_in)

@app.route('/start')
def start():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    # Get interviews where user is either interviewer or interviewee
    my_interviews = list(mongo.db.interviews.find({
        '$or': [
            {'interviewer_id': current_user.id},
            {'interviewee_id': current_user.id}
        ]
    }))
    
    # Get available interviews (where user can join as interviewee)
    available_interviews = list(mongo.db.interviews.find({
        'interviewee_id': None,  # No interviewee yet
        'interviewer_id': {'$ne': current_user.id},  # Not the interviewer
        'status': 'waiting_for_interviewee'
    }))

    # Explicitly convert to string 'true' or 'false'
    is_logged_in = 'true' if current_user.is_authenticated else 'false'
    print(f"Dashboard accessed, isLoggedIn: {is_logged_in}")
    
    return render_template('pages/dashboard.html', 
                           my_interviews=my_interviews,
                           available_interviews=available_interviews,
                           isLoggedIn=is_logged_in,
                           current_user_email=current_user.email)

@app.route('/schedule_interview', methods=['GET', 'POST'])
@login_required
def schedule_interview():
    if request.method == 'POST':
        role = request.form.get('role')
        interview_key = request.form.get('interview_key')
        
        if role == 'interviewee' and interview_key:
            # Join existing interview as interviewee
            interview = mongo.db.interviews.find_one_and_update(
                {
                    'interview_key': interview_key,
                    'interviewee_id': None,
                    'status': 'waiting_for_interviewee'
                },
                {
                    '$set': {
                        'interviewee_id': current_user.id,
                        'interviewee_name': current_user.name,
                        'status': 'scheduled'
                    }
                }
            )
            
            if interview:
                return redirect(url_for('interview_room', interview_id=interview['_id']))
            else:
                flash('Invalid interview key or interview is no longer available')
                return redirect(url_for('dashboard'))
        
        elif role == 'interviewer':
            # Get interviewer form data
            title = request.form.get('title')
            description = request.form.get('description')
            required_role = request.form.get('required_role')
            experience_level = request.form.get('experience_level')
            date = request.form.get('date')
            time = request.form.get('time')
            
            interview_key = str(uuid.uuid4())[:8]
            meet_link = create_google_meet(interview_key)
            
            interview_data = {
                'interview_key': interview_key,
                'interviewer_id': current_user.id,
                'interviewer_name': current_user.name,
                'interviewee_id': None,
                'interviewee_name': None,
                'title': title,
                'description': description,
                'required_role': required_role,
                'experience_level': experience_level,
                'date': date,
                'time': time,
                'status': 'waiting_for_interviewee',
                'meet_link': meet_link,
                'created_at': datetime.now(timezone.utc)
            }
            mongo.db.interviews.insert_one(interview_data)
            flash(f'Interview created successfully. Key: {interview_key}')
            
        return redirect(url_for('dashboard'))
    
    is_logged_in = current_user.is_authenticated
    print(f"Schedule Interview accessed, isLoggedIn: {is_logged_in}")
    return render_template('pages/schedule_interview.html', isLoggedIn=is_logged_in)

@app.route('/interview-room/<interview_id>')
@login_required
def interview_room(interview_id):
    interview = mongo.db.interviews.find_one({'_id': ObjectId(interview_id)})
    if not interview:
        flash('Interview not found')
        return redirect(url_for('dashboard'))
    
    # Explicitly check if current user is interviewer or interviewee
    is_interviewer = str(interview.get('interviewer_id', '')) == str(current_user.id)
    is_interviewee = str(interview.get('interviewee_id', '')) == str(current_user.id)
    
    if not (is_interviewer or is_interviewee):
        flash('You are not authorized to join this interview')
        return redirect(url_for('dashboard'))
    
    messages = list(mongo.db.messages.find({'interview_id': interview_id}))
    
    is_logged_in = current_user.is_authenticated
    print(f"Interview Room accessed, isLoggedIn: {is_logged_in}")
    return render_template('pages/interview_room.html',
                           interview=interview,
                           messages=messages,
                           is_interviewer=is_interviewer,
                           user_name=current_user.name,
                           user_id=current_user.id,
                           isLoggedIn=is_logged_in)

@app.route('/check-email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    print(f"Check Email Request: {email}")
    user_data = mongo.db.users.find_one({'email': email})
    result = {'exists': bool(user_data)}
    print(f"Check Email Result: {result}")
    return jsonify(result)

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/practice', methods=['GET'])
@login_required
def practice():
    is_logged_in = current_user.is_authenticated
    return render_template('pages/practice.html', 
        isLoggedIn='true' if is_logged_in else 'false')

def load_question_bank():
    try:
        question_bank_path = os.path.join('frontend', 'assets', 'question_bank.json')
        if not os.path.exists(question_bank_path):
            logger.error(f"Question bank file not found at {question_bank_path}")
            return None
            
        with open(question_bank_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading question bank: {str(e)}")
        return None

def get_random_question_from_bank(role='Software Engineer'):  # Default to first role in questions.json
    try:
        # Load questions from questions.json
        with open('frontend/assets/questions.json', 'r') as f:
            questions_data = json.load(f)
            
        # Find the role in job_roles array
        role_data = next((r for r in questions_data['job_roles'] if r['role'] == role), None)
        
        if role_data and role_data['questions']:
            # Select a random question
            selected_question = random.choice(role_data['questions'])
            return {
                'question': selected_question,
                'topics': ['technical', 'interview']
            }
        else:
            # If role not found, use first role as default (Software Engineer)
            default_role = questions_data['job_roles'][0]  # Software Engineer
            selected_question = random.choice(default_role['questions'])
            return {
                'question': selected_question,
                'topics': ['technical', 'interview']
            }
            
    except Exception as e:
        logger.error(f"Error getting random question: {str(e)}")
        return {
            'question': "Error loading questions. Please try again.",
            'topics': ['error']
        }

def get_default_role():
    try:
        with open('frontend/assets/questions.json', 'r') as f:
            data = json.load(f)
            if data.get('job_roles') and len(data['job_roles']) > 0:
                return data['job_roles'][0]['role_name']
    except Exception as e:
        print(f"Error loading default role: {e}")
    return None

@app.route('/get-random-question', methods=['GET'])
def get_random_question():
    role = request.args.get('role') or get_default_role()
    if not role:
        return jsonify({'error': 'No role specified and no default role available'}), 400

    try:
        with open('frontend/assets/questions.json', 'r') as f:
            data = json.load(f)
            
        # Find the role in job_roles
        role_data = next((r for r in data['job_roles'] if r['role_name'] == role), None)
        if not role_data or not role_data.get('questions'):
            # If role not found or has no questions, use first available role
            role_data = data['job_roles'][0]
            
        questions = role_data.get('questions', [])
        if not questions:
            return jsonify({'error': 'No questions available for this role'}), 404
            
        question = random.choice(questions)
        return jsonify({'question': question})
            
    except Exception as e:
        print(f"Error getting random question: {e}")
        return jsonify({'error': 'Failed to get question'}), 500

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    try:
        data = request.get_json()
        role = data.get('role', 'fullstack')
        question = data.get('question', '')
        answer = data.get('answer', '')
        
        if not question or not answer:
            return jsonify({
                'error': 'Question and answer are required'
            }), 400
            
        # Get assessment using the global model
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        prompt = f"""
        Assess this technical interview answer for a {role} position.
        
        Question: {question}
        
        Answer: {answer}
        
        Provide a detailed assessment in JSON format:
        {{
            "score": <0-100>,
            "strengths": ["strength1", "strength2", ...],
            "improvements": ["improvement1", "improvement2", ...],
            "feedback": "detailed feedback"
        }}
        
        Base the assessment on:
        1. Technical accuracy
        2. Completeness of the answer
        3. Clear explanation
        4. Practical examples or use cases
        """
        
        try:
            response = model.generate_content(prompt)
            if not response or not response.text:
                raise ValueError("Empty response from model")
                
            # Parse the response text as JSON
            text = response.text.strip()
            start_idx = text.find('{')
            end_idx = text.rfind('}')
            
            if start_idx == -1 or end_idx == -1:
                raise ValueError("Invalid JSON response from model")
                
            text = text[start_idx:end_idx+1]
            assessment = json.loads(text)
            
            # Validate assessment structure
            if not isinstance(assessment.get('score'), (int, float)):
                assessment['score'] = 70
            if not isinstance(assessment.get('strengths'), list):
                assessment['strengths'] = ["Basic understanding shown"]
            if not isinstance(assessment.get('improvements'), list):
                assessment['improvements'] = ["Add more detail"]
            if not isinstance(assessment.get('feedback'), str):
                assessment['feedback'] = "Answer shows basic understanding but needs more depth."
                
            # Store the assessment in the database
            assessment_record = {
                'user_id': current_user.id,
                'role': role,
                'question': question,
                'answer': answer,
                'assessment': assessment,
                'timestamp': datetime.now(timezone.utc)
            }
            
            mongo.db.assessments.insert_one(assessment_record)
            
            return jsonify(assessment)
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error: {str(e)}")
            return jsonify({
                'error': 'Failed to parse assessment response',
                'details': str(e)
            }), 500
            
        except Exception as e:
            logger.error(f"Model error: {str(e)}")
            return jsonify({
                'error': 'Failed to get assessment from model',
                'details': str(e)
            }), 500
            
    except Exception as e:
        logger.error(f"Error assessing answer: {str(e)}")
        return jsonify({
            'error': 'Failed to process assessment request',
            'details': str(e)
        }), 500

@app.route('/practice-analytics')
@login_required
def practice_analytics():
    # Get user's assessment history
    assessments = list(mongo.db.assessments.find({
        'user_id': current_user.id
    }).sort('created_at', -1))
    
    # Calculate analytics
    analytics = {
        'total_practices': len(assessments),
        'average_score': sum(a['assessment']['score'] for a in assessments) / len(assessments) if assessments else 0,
        'by_role': {}
    }
    
    for assessment in assessments:
        role = assessment['role']
        if role not in analytics['by_role']:
            analytics['by_role'][role] = {
                'count': 0,
                'total_score': 0
            }
        analytics['by_role'][role]['count'] += 1
        analytics['by_role'][role]['total_score'] += assessment['assessment']['score']
    
    for role_stats in analytics['by_role'].values():
        role_stats['average_score'] = role_stats['total_score'] / role_stats['count']
    
    return jsonify(analytics)

@app.route('/analytics')
@login_required
def analytics():
    is_logged_in = current_user.is_authenticated
    return render_template('pages/analytics.html', 
        isLoggedIn='true' if is_logged_in else 'false')

@app.route('/get-interview-questions/<interview_id>', methods=['POST'])
@login_required
def get_interview_questions_route(interview_id):
    try:
        data = request.get_json()
        role = data.get('role', 'general')
        context = data.get('context', '')  # Previous conversation context
        
        # First try to get questions from vector store
        questions = []
        if vector_store and context:
            try:
                questions = get_similar_questions(vector_store, context, role)
            except Exception as e:
                logger.error(f"Vector store error: {str(e)}")
                # Continue to fallback if vector store fails
        
        # If no questions from vector store, use predefined questions
        if not questions:
            questions = get_interview_questions(role)
            
            # If we have context, try to use Gemini to customize questions
            if context:
                try:
                    prompt = f"""
                    Based on this interview context: "{context}"
                    And considering these base questions: {questions}
                    Suggest 3 relevant follow-up technical questions.
                    Format the response as a JSON array of questions.
                    """
                    
                    ai_suggestions = get_ai_assistance(prompt)
                    suggested_questions = json.loads(ai_suggestions)
                    if suggested_questions and isinstance(suggested_questions, list):
                        questions = suggested_questions
                except Exception as e:
                    logger.error(f"AI suggestion error: {str(e)}")
                    # Continue with predefined questions if AI fails
        
        # Ensure we have at least some questions
        if not questions:
            questions = [
                "Explain your approach to problem-solving in software development.",
                "How do you handle technical challenges in your projects?",
                "What's your experience with version control systems?"
            ]
        
        # Format response
        return jsonify({
            'success': True,
            'questions': questions[:3]  # Return top 3 questions
        })
        
    except Exception as e:
        logger.error(f"Error getting interview questions: {str(e)}")
        # Return fallback questions instead of error
        return jsonify({
            'success': True,
            'questions': [
                "Tell me about your technical background.",
                "What programming languages are you most comfortable with?",
                "Describe a challenging project you've worked on."
            ]
        })

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify(error=str(e)), 500

@app.errorhandler(Exception)
def handle_unexpected_error(e):
    print(f"Unexpected error: {type(e).__name__} - {str(e)}")
    return jsonify(error='Unexpected error'), 500

# Modify create_google_meet function
def create_google_meet(interview_id):
    # Create a room URL for our second server
    return f"http://localhost:5001/meet/{interview_id}"

def get_interview_questions(role='Software Engineer'):  # Default to first role
    try:
        # Load questions from questions.json
        with open('frontend/assets/questions.json', 'r') as f:
            questions_data = json.load(f)
            
        # Find the role in job_roles array
        role_data = next((r for r in questions_data['job_roles'] if r['role'] == role), None)
        
        if role_data and role_data['questions']:
            return role_data['questions']
        else:
            # If role not found, return first role's questions as default
            default_role = questions_data['job_roles'][0]  # Software Engineer
            return default_role['questions']
            
    except Exception as e:
        logger.error(f"Error loading questions: {str(e)}")
        return ["Error loading questions. Please try again."]

@socketio.on('get_next_question')
def handle_next_question(data):
    try:
        room_id = data['roomId']
        context = data.get('currentContext', '')
        role = data.get('role', 'Software Engineer')  # Default to first role
        
        # Use vector search to find relevant questions
        if vector_store and context:
            questions = get_similar_questions(vector_store, context, role)
            if questions:
                emit('ai_question', {
                    'question': questions[0],
                    'topics': ['technical', 'interview']
                }, room=room_id)
                return
        
        # Fallback to random question if vector search fails
        with open('frontend/assets/questions.json', 'r') as f:
            questions_data = json.load(f)
        
        # Find role or use default
        role_data = next((r for r in questions_data['job_roles'] if r['role'] == role), None)
        
        if not role_data:
            # Use first role as default (Software Engineer)
            role_data = questions_data['job_roles'][0]
        
        # Get random question
        question = random.choice(role_data['questions'])
        
        emit('ai_question', {
            'question': question,
            'topics': ['technical', 'interview']
        }, room=room_id)
        
    except Exception as e:
        logger.error(f"Error generating next question: {e}")

# Add this function to check if interview is expired
def is_interview_expired(interview):
    interview_datetime = datetime.strptime(f"{interview['date']} {interview['time']}", "%Y-%m-%d %H:%M")
    interview_datetime = interview_datetime.replace(tzinfo=timezone.utc)
    current_time = datetime.now(timezone.utc)
    return current_time > (interview_datetime + timedelta(minutes=15))

# Add new route for deleting interviews
@app.route('/delete-interview/<interview_id>', methods=['POST'])
@login_required
def delete_interview(interview_id):
    try:
        # Only allow interviewer to delete
        interview = mongo.db.interviews.find_one_and_delete({
            '_id': ObjectId(interview_id),
            'interviewer_id': current_user.id
        })
        
        if interview:
            # Delete associated messages
            mongo.db.messages.delete_many({'interview_id': interview_id})
            flash('Interview deleted successfully')
        else:
            flash('Interview not found or unauthorized')
            
    except Exception as e:
        flash('Error deleting interview')
        
    return redirect(url_for('dashboard'))

# Add these socket events
@socketio.on('voice_transcript')
def handle_voice_transcript(data):
    try:
        transcript = data['transcript']
        room_id = data['roomId']
        
        # Use vector search to find relevant questions based on transcript
        if vector_store:
            questions = get_similar_questions(vector_store, transcript)
            if questions:
                emit('voice_analysis', {
                    'analysis': f"Analyzing transcript...",
                    'questions': [{'question': q, 'topics': ['technical', 'interview']} for q in questions[:3]]
                }, room=room_id)
                return
        
        # Fallback to keyword analysis if vector search fails
        try:
            from nltk.tokenize import word_tokenize
            from nltk.corpus import stopwords
            
            # Analyze transcript
            tokens = word_tokenize(transcript.lower())
            stop_words = set(stopwords.words('english'))
            keywords = [word for word in tokens if word not in stop_words]
            
            # Load questions from JSON
            with open('frontend/assets/questions.json', 'r') as f:
                questions_data = json.load(f)
            
            # Find relevant questions based on keywords
            relevant_questions = []
            for role in questions_data['job_roles']:
                for question in role['questions']:
                    if any(keyword in question.lower() for keyword in keywords):
                        relevant_questions.append({
                            'question': question,
                            'topics': keywords[:3]  # Use top 3 keywords as topics
                        })
            
            # Send analysis back to room
            emit('voice_analysis', {
                'analysis': f"Keywords detected: {', '.join(keywords[:5])}",
                'questions': relevant_questions[:3]  # Send top 3 relevant questions
            }, room=room_id)
        except Exception as e:
            logger.error(f"Error in keyword analysis: {str(e)}")
            
    except Exception as e:
        logger.error(f"Error processing voice transcript: {str(e)}")

@socketio.on('join_room')
def on_join(data):
    try:
        room_id = data.get('roomId')
        user_name = data.get('userName')
        is_interviewer = data.get('isInterviewer', False)
        
        if not room_id or not user_name:
            logger.error("Missing room ID or user name")
            return
        
        join_room(room_id)
        
        # Initialize room if it doesn't exist
        if room_id not in connections:
            connections[room_id] = {
                'count': 0,
                'users': set(),
                'interviewer': None,
                'interviewee': None
            }
        
        # Add user to room
        connections[room_id]['users'].add(request.sid)
        connections[room_id]['count'] += 1
        
        if is_interviewer:
            connections[room_id]['interviewer'] = request.sid
        else:
            connections[room_id]['interviewee'] = request.sid
        
        logger.info(f"User {user_name} joined room {room_id} as {'interviewer' if is_interviewer else 'interviewee'}")
        
        # Notify room of new user
        emit('user_joined', {
            'userId': request.sid,
            'userName': user_name,
            'isInterviewer': is_interviewer,
            'count': connections[room_id]['count']
        }, room=room_id)
        
        # If both users are present, signal to start connection
        if connections[room_id]['count'] == 2:
            emit('ready_to_connect', {
                'initiator': connections[room_id]['interviewer']
            }, room=room_id)
    
    except Exception as e:
        logger.error(f"Error in join_room: {str(e)}")

@socketio.on('offer')
def handle_offer(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with offer")
            return
        
        # Send offer to the other peer only
        emit('offer', {
            'offer': data['offer']
        }, room=room_id, include_self=False)
        logger.info(f"Offer relayed in room {room_id}")
    
    except Exception as e:
        logger.error(f"Error handling offer: {str(e)}")

@socketio.on('answer')
def handle_answer(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with answer")
            return
        
        # Send answer to the other peer only
        emit('answer', {
            'answer': data['answer']
        }, room=room_id, include_self=False)
        logger.info(f"Answer relayed in room {room_id}")
    
    except Exception as e:
        logger.error(f"Error handling answer: {str(e)}")

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with ICE candidate")
            return
        
        # Send ICE candidate to the other peer only
        emit('ice_candidate', {
            'candidate': data['candidate']
        }, room=room_id, include_self=False)
        logger.info(f"ICE candidate relayed in room {room_id}")
    
    except Exception as e:
        logger.error(f"Error handling ICE candidate: {str(e)}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")
    # Clean up any rooms this user was in
    for room_id in list(connections.keys()):
        if request.sid in connections[room_id]['users']:
            leave_room(room_id)
            connections[room_id]['users'].remove(request.sid)
            connections[room_id]['count'] -= 1
            
            # Notify others in the room
            emit('user_disconnected', {
                'userId': request.sid,
                'count': connections[room_id]['count']
            }, room=room_id)
            
            # Clean up empty rooms
            if connections[room_id]['count'] == 0:
                del connections[room_id]

def check_and_update_interviews():
    while True:
        try:
            # Get current time in UTC
            current_time = datetime.now(timezone.utc)
            
            # Convert date to string for comparison
            current_date_str = current_time.strftime('%Y-%m-%d')
            current_time_str = current_time.strftime('%H:%M')
            
            # Find interviews that are past their scheduled time
            expired_interviews = mongo.db.interviews.find({
                'status': {'$in': ['scheduled', 'waiting_for_interviewee']},
                '$or': [
                    # Interviews where scheduled date is before current date
                    {'date': {'$lt': current_date_str}},
                    
                    # Interviews on current date where time is before current time
                    {
                        'date': current_date_str,
                        'time': {'$lt': current_time_str}
                    }
                ]
            })
            
            # Update expired interviews
            for interview in expired_interviews:
                mongo.db.interviews.update_one(
                    {'_id': interview['_id']},
                    {'$set': {
                        'status': 'expired',
                        'end_reason': 'Not attended by scheduled time'
                    }}
                )
                
                print(f"Interview {interview['_id']} has expired")
            
        except Exception as e:
            print(f"Error in interview expiration check: {e}")
        
        # Wait for 5 minutes before next check
        time.sleep(300)

def start_interview_expiration_thread():
    thread = Thread(target=check_and_update_interviews, daemon=True)
    thread.start()

# Initialize AI components with better error handling and global variables
llm = None
assessment_chain = None
question_chain = None
vector_store = None

def initialize_ai_components():
    global llm, assessment_chain, question_chain, vector_store
    try:
        print("Initializing AI components...")
        # Clear existing components
        llm = None
        assessment_chain = None
        question_chain = None
        vector_store = None
        
        # Initialize new components
        llm = genai.GenerativeModel('gemini-1.5-pro-latest')
        if llm is None:
            raise ValueError("Failed to initialize Gemini model")
        
        # Test LLM immediately
        test_response = llm.generate_content("test")
        if not test_response:
            raise ValueError("LLM test failed immediately after initialization")
        
        # Initialize chains
        assessment_chain = create_assessment_chain(llm)
        if not assessment_chain:
            raise ValueError("Failed to create assessment chain")
            
        question_chain = create_question_chain(llm)
        if not question_chain:
            raise ValueError("Failed to create question chain")
            
        vector_store = init_vector_store()
        
        print("AI components initialized successfully")
        return True
    except Exception as e:
        print(f"Error initializing AI components: {str(e)}")
        logger.error(f"AI initialization error: {str(e)}")
        llm = None
        assessment_chain = None
        question_chain = None
        vector_store = None
        return False

def check_and_restart_ai_components():
    """Check AI components and restart if needed"""
    global llm, assessment_chain, question_chain, vector_store
    try:
        # Check if components are initialized
        if not all([llm, assessment_chain, question_chain]):
            logger.warning("AI components not initialized, attempting to initialize...")
            return initialize_ai_components()
            
        # Test LLM
        try:
            test_response = llm.invoke("test")
            if not test_response:
                raise ValueError("LLM test failed")
        except Exception as e:
            logger.error(f"LLM test failed, reinitializing: {str(e)}")
            return initialize_ai_components()
            
        return True
    except Exception as e:
        logger.error(f"Error in AI components check: {str(e)}")
        return initialize_ai_components()

@app.route('/ai-status', methods=['GET'])
def ai_status():
    """Check the status of AI services"""
    try:
        # Make a test call to the Gemini API
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": "AIzaSyBFdcHnWKVwWMtTqpKDDeamilyxHg69YeQ"}
        data = {
            "contents": [{"parts": [{"text": "test"}]}]
        }
        
        response = requests.post(url, headers=headers, params=params, json=data)
        
        if response.status_code == 200:
            ai_services = {
                'status': 'ready',
                'message': 'AI services are operational',
                'last_check': datetime.now(timezone.utc).isoformat()
            }
            return jsonify({
                'success': True,
                'ai_services': ai_services
            })
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            return jsonify({
                'success': False,
                'error': error_msg,
                'ai_services': {
                    'status': 'error',
                    'message': f'API Error: {error_msg}',
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error checking AI status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'ai_services': {
                'status': 'error',
                'message': f'Service Error: {str(e)}',
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        }), 500

def periodic_ai_health_check():
    """Periodically check and restart AI components if needed"""
    while True:
        try:
            # Sleep first to allow initial startup to complete
            time.sleep(300)  # Check every 5 minutes
            
            logger.info("Running periodic AI health check")
            check_and_restart_ai_components()
            
        except Exception as e:
            logger.error(f"Error in AI health check: {str(e)}")

def start_ai_health_check_thread():
    """Start the AI health check thread"""
    thread = Thread(target=periodic_ai_health_check, daemon=True)
    thread.start()
    logger.info("AI health check thread started")

# Update the main block
if __name__ == '__main__':
    try:
        # Initialize AI components first
        if not initialize_ai_components():
            logger.warning("Failed to initialize AI components on startup")
        
        # Start the AI health check thread
        start_ai_health_check_thread()
        
        # Use port 5000 by default
        port = int(os.getenv('PORT', 5000))
        host = os.getenv('HOST', '0.0.0.0')
        
        logger.info(f"Starting server on {host}:{port}")
        socketio.run(
            app,
            host=host,
            port=port,
            debug=True,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
            
    except Exception as e:
        logger.error(f"Error starting server: {str(e)}")
        if 'ollama_process' in globals():
            logger.info("Ollama server stopped")

@app.route('/reinitialize-ai', methods=['POST'])
@login_required
def reinitialize_ai():
    """Manually reinitialize AI components"""
    try:
        # Test the API with a simple request
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
        headers = {"Content-Type": "application/json"}
        params = {"key": "AIzaSyBFdcHnWKVwWMtTqpKDDeamilyxHg69YeQ"}
        data = {
            "contents": [{"parts": [{"text": "test"}]}]
        }
        
        response = requests.post(url, headers=headers, params=params, json=data)
        
        if response.status_code == 200:
            return jsonify({
                'success': True,
                'message': "AI services reinitialized successfully",
                'ai_services': {
                    'status': 'ready',
                    'message': 'AI services are operational',
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
            })
        else:
            error_msg = response.json().get('error', {}).get('message', 'Unknown error')
            return jsonify({
                'success': False,
                'message': f"Failed to reinitialize AI services: {error_msg}",
                'ai_services': {
                    'status': 'error',
                    'message': f'API Error: {error_msg}',
                    'last_check': datetime.now(timezone.utc).isoformat()
                }
            }), 500
            
    except Exception as e:
        logger.error(f"Error in reinitialize-ai endpoint: {str(e)}")
        return jsonify({
            'success': False,
            'message': f"Error: {str(e)}",
            'ai_services': {
                'status': 'error',
                'message': f'Service Error: {str(e)}',
                'last_check': datetime.now(timezone.utc).isoformat()
            }
        }), 500

@app.route('/api/ai-status', methods=['GET'])
def check_ai_status():
    """Check the status of all AI services."""
    try:
        status = check_ai_services_status()
        return jsonify({
            'success': True,
            'status': status,
            'message': 'AI services status checked successfully'
        })
    except Exception as e:
        logger.error(f"Error checking AI status: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e),
            'message': 'Error checking AI services status'
        }), 500