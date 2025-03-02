import os
import eventlet
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
eventlet.monkey_patch()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type"]
    }
})

# Use environment variable for port, default to 5002
PORT = int(os.environ.get('PORT', 5002))

socketio = SocketIO(app, 
    cors_allowed_origins="*",
    async_mode='gevent',
    ping_timeout=30,
    ping_interval=10,
    logger=True,
    engineio_logger=True
)

# Store active connections
connections = {}

@app.route('/')
def index():
    return 'Interview Server Running'

@socketio.on('connect')
def handle_connect():
    logger.info(f"Client connected: {request.sid}")

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
        
        # Send offer to the other peer
        emit('offer', {
            'offer': data['offer'],
            'from': request.sid
        }, room=room_id)
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
        
        # Send answer to the other peer
        emit('answer', {
            'answer': data['answer'],
            'from': request.sid
        }, room=room_id)
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
        
        # Send ICE candidate to the other peer
        emit('ice_candidate', {
            'candidate': data['candidate'],
            'from': request.sid
        }, room=room_id)
        logger.info(f"ICE candidate relayed in room {room_id}")
    
    except Exception as e:
        logger.error(f"Error handling ICE candidate: {str(e)}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=PORT, debug=True)