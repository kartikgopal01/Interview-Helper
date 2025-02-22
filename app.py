from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import google.generativeai as genai
import os
from dotenv import load_dotenv
from bson import ObjectId

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key')
app.config['MONGO_URI'] = os.getenv('MONGO_URI', 'mongodb://localhost:27017/interview_platform')
mongo = PyMongo(app)

# Initialize Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Gemini AI
genai.configure(api_key=os.getenv('GEMINI_API_KEY'))

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

# Auth Routes
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        
        # Validate required fields
        if not all([email, password, name]):
            flash('All fields are required')
            return redirect(url_for('register'))
        
        if mongo.db.users.find_one({'email': email}):
            flash('Email already exists')
            return redirect(url_for('register'))
        
        user_data = {
            'email': email,
            'password': generate_password_hash(password),
            'name': name,
            'created_at': datetime.utcnow()
        }
        
        try:
            user_id = mongo.db.users.insert_one(user_data).inserted_id
            user_data['_id'] = user_id
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        except Exception as e:
            flash(f'Error: {str(e)}')
            return redirect(url_for('register'))
    
    return render_template('register.html')
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user_data = mongo.db.users.find_one({'email': email})
        if user_data and check_password_hash(user_data['password'], password):
            user = User(user_data)
            login_user(user)
            return redirect(url_for('dashboard'))
        
        flash('Invalid credentials')
    return render_template('login.html')
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/dashboard')
@login_required
def dashboard():
    # Get interviews where user is either interviewer or interviewee
    interviews = list(mongo.db.interviews.find({
        '$or': [
            {'interviewer_id': current_user.id},
            {'interviewee_id': current_user.id}
        ]
    }))
    return render_template('dashboard.html', interviews=interviews)

@app.route('/schedule-interview', methods=['GET', 'POST'])
@login_required
def schedule_interview():
    if request.method == 'POST':
        interview_key = request.form.get('interview_key')
        role = request.form.get('role')
        date = request.form.get('date')
        time = request.form.get('time')
        
        # Check if interview with this key exists
        existing_interview = mongo.db.interviews.find_one({'interview_key': interview_key})
        
        if role == 'interviewer':
            if existing_interview:
                flash('Interview key already exists. Please choose a different key.')
                return redirect(url_for('schedule_interview'))
            
            # Generate Google Meet link
            meet_link = f"https://meet.google.com/{interview_key}"
            
            # Create new interview
            interview_data = {
                'interview_key': interview_key,
                'interviewer_id': current_user.id,
                'interviewee_id': None,  # Will be filled when interviewee joins
                'date': date,
                'time': time,
                'status': 'waiting_for_interviewee',
                'meet_link': meet_link,
                'created_at': datetime.utcnow()
            }
            mongo.db.interviews.insert_one(interview_data)
            flash('Interview created successfully. Share the key with the interviewee.')
            
        elif role == 'interviewee':
            if not existing_interview:
                flash('Interview key not found. Please check the key.')
                return redirect(url_for('schedule_interview'))
            
            if existing_interview['interviewee_id']:
                flash('This interview already has an interviewee.')
                return redirect(url_for('schedule_interview'))
            
            # Join existing interview as interviewee
            mongo.db.interviews.update_one(
                {'interview_key': interview_key},
                {
                    '$set': {
                        'interviewee_id': current_user.id,
                        'status': 'scheduled'
                    }
                }
            )
            flash('Successfully joined the interview.')
        
        return redirect(url_for('dashboard'))
    
    return render_template('schedule_interview.html')

@app.route('/interview-room/<interview_id>', methods=['GET', 'POST'])
@login_required
def interview_room(interview_id):
    try:
        interview = mongo.db.interviews.find_one({'_id': ObjectId(interview_id)})
        if not interview:
            flash('Interview not found')
            return redirect(url_for('dashboard'))
        
        is_interviewer = current_user.id == interview['interviewer_id']
        messages = list(mongo.db.messages.find({'interview_id': interview_id}).sort('created_at', 1))
        
        if request.method == 'POST':
            if 'message' in request.form:
                # Handle chat message
                message = request.form.get('message')
                mongo.db.messages.insert_one({
                    'interview_id': interview_id,
                    'user_id': current_user.id,
                    'user_name': current_user.name,
                    'content': message,
                    'created_at': datetime.utcnow()
                })
                return redirect(url_for('interview_room', interview_id=interview_id))
            
            elif 'ai_prompt' in request.form:
                # Handle AI assistance
                prompt = request.form.get('ai_prompt')
                try:
                    ai_response = get_ai_assistance(prompt)
                    mongo.db.messages.insert_one({
                        'interview_id': interview_id,
                        'user_id': 'AI',
                        'user_name': 'AI Assistant',
                        'content': ai_response,
                        'created_at': datetime.utcnow()
                    })
                except Exception as e:
                    flash(f'Error getting AI response: {str(e)}')
                return redirect(url_for('interview_room', interview_id=interview_id))
        
        return render_template('interview_room.html', 
                             interview=interview,
                             messages=messages,
                             is_interviewer=is_interviewer)
    except Exception as e:
        flash('Invalid interview ID')
        return redirect(url_for('dashboard'))

if __name__ == '__main__':
    port = 8000
    max_attempts = 10
    
    while port < 8000 + max_attempts:
        try:
            print(f"Attempting to start server on port {port}")
            app.run(host='127.0.0.1', port=port, debug=True)
            break
        except OSError:
            print(f"Port {port} is in use, trying next port")
            port += 1
        except Exception as e:
            print(f"An error occurred: {e}")
            break
    else:
        print(f"Could not find an available port after {max_attempts} attempts")