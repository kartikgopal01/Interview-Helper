from gevent import monkey
monkey.patch_all()

from flask import Flask, request
from flask_socketio import SocketIO, emit, join_room
from flask_cors import CORS
import logging
import os
import sys

# More detailed logging configuration
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('meet_server.log')
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# More permissive CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "X-Interview-ID", "X-User-Name"],
        "supports_credentials": True
    }
})

# Use environment variable for port, default to 5002
PORT = int(os.environ.get('PORT', 5002))

# More permissive Socket.IO configuration
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=30,
    ping_interval=10,
    logger=True,
    engineio_logger=True,
    cors_credentials=True,
    always_connect=True,
    path='socket.io'
)

# Add this near the top of the file, after imports
connections = {}

@app.route('/socket-test')
def socket_test():
    return 'Socket server is running'

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")
    logger.info(f"Connection details: {request.args}")
    logger.info(f"Headers: {dict(request.headers)}")
    logger.info(f"Environment: {request.environ}")

@socketio.on('disconnect')
def handle_disconnect():
    logger.info(f"Client disconnected: {request.sid}")

@socketio.on('join_room')
def on_join(data):
    logger.info(f"Raw join room data: {data}")
    
    # More flexible parameter extraction with extensive logging
    room_id = (
        data.get('roomId') or 
        data.get('room') or 
        data.get('interview_id')
    )
    user_name = (
        data.get('userName') or 
        data.get('user_name')
    )
    is_interviewer = (
        data.get('isInterviewer') or 
        data.get('is_interviewer', False)
    )
    
    logger.info(f"Processed join room parameters: room_id={room_id}, user_name={user_name}, is_interviewer={is_interviewer}")
    
    if not room_id:
        logger.error("No room ID provided in join_room")
        return
    
    logger.info(f"User {user_name} joining room {room_id} as {'interviewer' if is_interviewer else 'interviewee'}")
    
    join_room(room_id)
    
    # Track connection count
    connections[room_id] = connections.get(room_id, 0) + 1
    
    emit('user_joined', {
        'user': user_name,
        'isInterviewer': is_interviewer,
        'connectionCount': connections[room_id]
    }, room=room_id)

@socketio.on('offer')
def handle_offer(data):
    print("Handling offer")
    room_id = data['roomId']
    emit('offer', {
        'offer': data['offer']
    }, room=room_id, include_self=False)

@socketio.on('answer')
def handle_answer(data):
    print("Handling answer")
    room_id = data['roomId']
    emit('answer', {
        'answer': data['answer']
    }, room=room_id, include_self=False)

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    print("Handling ICE candidate")
    room_id = data['roomId']
    emit('ice_candidate', {
        'candidate': data['candidate']
    }, room=room_id, include_self=False)

@socketio.on('disconnect')
def on_disconnect():
    print("Client disconnected")
    for room_id in connections:
        connections[room_id] = max(0, connections[room_id] - 1)

if __name__ == '__main__':
    logger.info(f"Starting server on port {PORT}")
    socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0',
        port=PORT
    ) 