from flask import Flask, request, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)
CORS(app)

@app.route('/interview-stream/<interview_id>', methods=['POST'])
def interview_stream(interview_id):
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio file'}), 400
    
    audio_file = request.files['audio']
    
    # Process and store the audio stream
    # You can implement real-time audio processing here
    
    return jsonify({'success': True})

@app.route('/interview-status/<interview_id>', methods=['GET'])
def interview_status(interview_id):
    # Return interview status, participants, etc.
    return jsonify({
        'status': 'active',
        'participants': 2,
        'duration': '00:30:00'
    })

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5001, debug=True) 