from gevent import monkey
monkey.patch_all()

# Now import other modules
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone, timedelta
import google.generativeai as genai
import os
from dotenv import load_dotenv
from bson import ObjectId
import json
import uuid
from flask_socketio import SocketIO, emit
import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords
from flask_cors import CORS
from threading import Thread
import time
import logging
import warnings

# Load environment variables
load_dotenv()

app = Flask(__name__, 
            template_folder='frontend', 
            static_folder='frontend/assets',
            static_url_path='/assets')

# Configure the app
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['MONGO_URI'] = os.getenv('MONGO_URI')

# Initialize MongoDB
mongo = PyMongo(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

# Initialize SocketIO with gevent
CORS(app, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:5002"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=10,
    ping_interval=5,
    transports=['websocket'],
    logger=False,  # Disable SocketIO logging
    engineio_logger=False  # Disable engine.io logging
)

# Download required NLTK data
nltk.download('punkt')
nltk.download('stopwords')

# Suppress specific warnings and logs
logging.getLogger('gevent').setLevel(logging.ERROR)
logging.getLogger('engineio').setLevel(logging.ERROR)
logging.getLogger('socketio').setLevel(logging.ERROR)

# Suppress specific warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)
warnings.filterwarnings("ignore", message=".*Invalid HTTP method.*")

# Optional: Create a custom filter to ignore specific log messages
class SocketHandshakeFilter(logging.Filter):
    def filter(self, record):
        return not ('Invalid HTTP method' in record.getMessage() or 
                    'SSL/TLS handshake' in record.getMessage())

# Apply the filter to your logger
logger = logging.getLogger()
logger.addFilter(SocketHandshakeFilter())

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

def get_ai_assistance(prompt):
    model = genai.GenerativeModel('gemini-pro')
    response = model.generate_content(prompt)
    return response.text

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

@app.route('/get-random-question', methods=['GET'])
@login_required
def get_random_question():
    role = request.args.get('role')
    # Find role questions from questions.json
    with open('frontend/assets/questions.json') as f:
        data = json.load(f)
        role_data = next((r for r in data['job_roles'] if r['role'] == role), None)
        if role_data:
            import random
            question = random.choice(role_data['questions'])
            return jsonify({'success': True, 'question': question})
    return jsonify({'success': False, 'message': 'Role not found'}), 404

@app.route('/submit-answer', methods=['POST'])
@login_required
def submit_answer():
    try:
        data = request.json
        if not data:
            return jsonify({'success': False, 'message': 'No data provided'}), 400
        
        role = data.get('role')
        question = data.get('question')
        answer = data.get('answer')
        
        if not all([role, question, answer]):
            return jsonify({'success': False, 'message': 'Missing required fields'}), 400
        
        # Generate AI assessment with more structured prompt
        prompt = f"""
        Analyze the following answer for a technical interview question.
        
        Question: {question}
        Answer: {answer}
        
        Provide your assessment in the following JSON format:
        {{
            "score": <number between 0 and 100>,
            "strengths": "<bullet points of strengths>",
            "improvements": "<bullet points of areas for improvement>",
            "feedback": "<overall feedback>"
        }}
        
        Be specific and constructive in your feedback.
        """
        
        try:
            ai_response = get_ai_assistance(prompt)
            # Clean the response to ensure it's valid JSON
            ai_response = ai_response.strip()
            if ai_response.startswith('```json'):
                ai_response = ai_response[7:-3]  # Remove ```json and ``` if present
            assessment = json.loads(ai_response)
            
            # Validate assessment structure
            required_keys = ['score', 'strengths', 'improvements', 'feedback']
            if not all(key in assessment for key in required_keys):
                raise ValueError("Invalid assessment format")
            
            # Ensure score is an integer between 0 and 100
            assessment['score'] = max(0, min(100, int(float(assessment['score']))))
            
        except Exception as e:
            print(f"Error processing AI response: {str(e)}")
            print(f"Raw AI response: {ai_response}")
            # Provide a fallback assessment if AI parsing fails
            assessment = {
                'score': 70,
                'strengths': 'Answer shows understanding of the concept.',
                'improvements': 'Could provide more detailed examples.',
                'feedback': 'Good attempt, but could be more comprehensive.'
            }
        
        # Store the assessment
        assessment_data = {
            'user_id': current_user.id,
            'role': role,
            'question': question,
            'answer': answer,
            'assessment': assessment,
            'created_at': datetime.now(timezone.utc)
        }
        mongo.db.assessments.insert_one(assessment_data)
        
        return jsonify({
            'success': True,
            'assessment': assessment
        })
        
    except Exception as e:
        print(f"Submit answer error: {str(e)}")  # Add logging
        return jsonify({
            'success': False,
            'message': f"Error processing submission: {str(e)}"
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
        
        # Get predefined questions
        questions = get_interview_questions(role)
        
        # Use Gemini to customize questions based on context
        if context:
            prompt = f"""
            Based on this interview context: "{context}"
            And considering these base questions: {questions}
            Suggest 3 relevant follow-up technical questions.
            Format the response as a JSON array of questions.
            """
            
            ai_suggestions = get_ai_assistance(prompt)
            try:
                # Try to parse AI response as JSON
                import json
                suggested_questions = json.loads(ai_suggestions)
                questions = suggested_questions
            except:
                # Fallback to predefined questions if AI response isn't valid JSON
                pass
        
        return jsonify({
            'success': True,
            'questions': questions[:3]  # Return top 3 questions
        })
        
    except Exception as e:
        print(f"Error getting interview questions: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

# Add this function to generate interview questions
def get_interview_questions(role, level='intermediate'):
    questions_by_role = {
        'frontend': [
            "Explain the difference between let, const, and var in JavaScript.",
            "What is the virtual DOM in React?",
            "How does CSS specificity work?",
            "Explain event bubbling in JavaScript.",
            "What are closures in JavaScript?"
        ],
        'backend': [
            "What is REST API?",
            "Explain database indexing.",
            "What is dependency injection?",
            "How do you handle API security?",
            "Explain the concept of caching."
        ],
        'fullstack': [
            "Compare SQL and NoSQL databases.",
            "Explain JWT authentication.",
            "What is CORS?",
            "Describe the MVC pattern.",
            "How do you optimize website performance?"
        ]
    }
    
    return questions_by_role.get(role, ["General coding question 1", "General coding question 2"])

# Add socket event for getting next question
@socketio.on('get_next_question')
def handle_next_question(data):
    try:
        room_id = data['roomId']
        context = data.get('currentContext', '')
        
        # Load questions
        with open('frontend/assets/questions.json', 'r') as f:
            questions_data = json.load(f)
        
        # Get random question (you can implement more sophisticated selection)
        import random
        role = random.choice(questions_data['job_roles'])
        question = random.choice(role['questions'])
        
        emit('ai_question', {
            'question': question,
            'topics': ['technical', 'interview']  # You can enhance this
        }, room=room_id)
        
    except Exception as e:
        print(f"Error generating next question: {e}")

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
        print(f"Error processing voice transcript: {e}")

@socketio.on('join_room')
def on_join(data):
    room = data.get('room') or data.get('interview_id')
    
    if not room:
        print("No room/interview_id provided")
        return
    
    interview = mongo.db.interviews.find_one({'_id': ObjectId(room)})
    
    if interview:
        # Calculate deadline based on interview's scheduled date and time
        interview_datetime = datetime.combine(
            datetime.strptime(interview['date'], '%Y-%m-%d').date(),
            datetime.strptime(interview['time'], '%H:%M').time()
        )
        interview_datetime = interview_datetime.replace(tzinfo=timezone.utc)
        
        # Schedule room closure at interview's scheduled time
        socketio.start_background_task(
            target=close_room_at_deadline, 
            room=room, 
            deadline=interview_datetime
        )

def close_room_at_deadline(room, deadline):
    # Wait until deadline
    current_time = datetime.now(timezone.utc)
    wait_time = (deadline - current_time).total_seconds()
    
    if wait_time > 0:
        socketio.sleep(wait_time)
    
    # Emit room closure event
    socketio.emit('room_closed', {
        'reason': 'Interview time limit reached'
    }, room=room)
    
    # Update interview status
    mongo.db.interviews.update_one(
        {'_id': ObjectId(room)},
        {'$set': {'status': 'completed'}}
    )

@socketio.on('offer')
def handle_offer(data):
    print("Handling offer")
    room = data['roomId']
    emit('offer', {
        'offer': data['offer']
    }, room=room, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    print("Handling answer")
    room = data['roomId']
    emit('answer', {
        'answer': data['answer']
    }, room=room, include_self=False)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    print("Handling ICE candidate")
    room = data['roomId']
    emit('ice_candidate', {
        'candidate': data['candidate']
    }, room=room, include_self=False)

@socketio.on('connect')
def handle_connect():
    print('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

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

# Modify your main block or app initialization
if __name__ == '__main__':
    # Start the interview expiration thread
    start_interview_expiration_thread()
    
    port = int(os.environ.get('PORT', 5000))
    socketio.run(app, debug=True, host='127.0.0.1', port=port)