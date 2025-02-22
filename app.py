from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timezone
import google.generativeai as genai
import os
from dotenv import load_dotenv
from bson import ObjectId
import json

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
        email = request.json.get('email')
        password = request.json.get('password')
        confirm_password = request.json.get('confirm_password')
        
        if not password:
            return jsonify({'success': False, 'message': 'Password is required'}), 400
        
        user_data = mongo.db.users.find_one({'email': email})
        
        if user_data:
            # Login process
            if check_password_hash(user_data['password'], password):
                user = User(user_data)
                login_user(user)
                return jsonify({'success': True, 'message': 'Logged in successfully', 'redirect': url_for('dashboard')})
            else:
                return jsonify({'success': False, 'message': 'Invalid credentials'}), 401
        else:
            # Registration process
            if password != confirm_password:
                return jsonify({'success': False, 'message': 'Passwords do not match'}), 400
            
            user_data = {
                'email': email,
                'password': generate_password_hash(password),
                'name': email.split('@')[0],  # Use part of email as name
                'created_at': datetime.now(timezone.utc)
            }
            
            try:
                user_id = mongo.db.users.insert_one(user_data).inserted_id
                user_data['_id'] = user_id
                user = User(user_data)
                login_user(user)
                return jsonify({'success': True, 'message': 'Account created successfully', 'redirect': url_for('dashboard')})
            except Exception as e:
                return jsonify({'success': False, 'message': f'Error: {str(e)}'}), 500
    
    return render_template('pages/login.html', is_login_mode=True)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# Main Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/start')
def start():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    interviews = list(mongo.db.interviews.find({
        '$or': [
            {'interviewer_id': current_user.id},
            {'interviewee_id': current_user.id}
        ]
    }))
    return render_template('pages/dashboard.html', interviews=interviews)

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
                'created_at': datetime.now(timezone.utc)
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
    
    return render_template('pages/schedule_interview.html')

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
                    'created_at': datetime.now(timezone.utc)
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
                        'created_at': datetime.now(timezone.utc)
                    })
                except Exception as e:
                    flash(f'Error getting AI response: {str(e)}')
                return redirect(url_for('interview_room', interview_id=interview_id))
        
        return render_template('pages/interview_room.html', 
                             interview=interview,
                             messages=messages,
                             is_interviewer=is_interviewer)
    except Exception as e:
        flash('Invalid interview ID')
        return redirect(url_for('dashboard'))

@app.route('/check-email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    user_data = mongo.db.users.find_one({'email': email})
    return jsonify({'exists': bool(user_data)})

@app.route('/favicon.ico')
def favicon():
    return '', 204

@app.route('/practice', methods=['GET'])
@login_required
def practice():
    return render_template('pages/practice.html')

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
    return render_template('pages/analytics.html')

@app.errorhandler(400)
def bad_request(e):
    return jsonify(error=str(e)), 400

@app.errorhandler(404)
def not_found(e):
    return jsonify(error=str(e)), 404

@app.errorhandler(500)
def server_error(e):
    return jsonify(error=str(e)), 500

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000, threaded=True, ssl_context=None)