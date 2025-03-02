import gevent.monkey
gevent.monkey.patch_all()

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
    try:
        room_id = data.get('roomId')
        user_name = data.get('userName')
        is_interviewer = data.get('isInterviewer', False)
        
        if not all([room_id, user_name]):
            logger.error("Missing required join data")
            return
        
        logger.info(f"User {user_name} joining room {room_id} as {'interviewer' if is_interviewer else 'interviewee'}")
        
        join_room(room_id)
        
        # Track connection
        if room_id not in connections:
            connections[room_id] = {'count': 0, 'users': set()}
        
        connections[room_id]['count'] += 1
        connections[room_id]['users'].add(user_name)
        
        # Emit join event with connection info
        emit('user_joined', {
            'user': user_name,
            'isInterviewer': is_interviewer,
            'connectionCount': connections[room_id]['count'],
            'users': list(connections[room_id]['users'])
        }, room=room_id)
        
        logger.info(f"Room {room_id} now has {connections[room_id]['count']} users")
        
    except Exception as e:
        logger.error(f"Error in join_room: {str(e)}")

@socketio.on('offer')
def handle_offer(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with offer")
            return
            
        logger.info(f"Relaying offer in room {room_id}")
        emit('offer', {
            'offer': data['offer']
        }, room=room_id, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling offer: {str(e)}")

@socketio.on('answer')
def handle_answer(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with answer")
            return
            
        logger.info(f"Relaying answer in room {room_id}")
        emit('answer', {
            'answer': data['answer']
        }, room=room_id, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling answer: {str(e)}")

@socketio.on('ice_candidate')
def handle_ice_candidate(data):
    try:
        room_id = data.get('roomId')
        if not room_id:
            logger.error("No room ID provided with ICE candidate")
            return
            
        logger.info(f"Relaying ICE candidate in room {room_id}")
        emit('ice_candidate', {
            'candidate': data['candidate']
        }, room=room_id, include_self=False)
        
    except Exception as e:
        logger.error(f"Error handling ICE candidate: {str(e)}")

@socketio.on('disconnect')
def on_disconnect():
    try:
        for room_id in connections:
            if request.sid in socketio.server.manager.rooms.get(room_id, set()):
                connections[room_id]['count'] = max(0, connections[room_id]['count'] - 1)
                logger.info(f"User disconnected from room {room_id}. Users remaining: {connections[room_id]['count']}")
                
                # Notify remaining users
                emit('user_disconnected', {
                    'connectionCount': connections[room_id]['count']
                }, room=room_id)
                
    except Exception as e:
        logger.error(f"Error in disconnect: {str(e)}")

if __name__ == '__main__':
    logger.info(f"Starting server on port {PORT}")
    socketio.run(
        app, 
        debug=True, 
        host='0.0.0.0',
        port=PORT,
        use_reloader=False
    ) 