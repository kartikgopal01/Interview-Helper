import os
import eventlet
import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# Use environment variable for port, default to 5001
PORT = int(os.environ.get('PORT', 5001))

socketio = SocketIO(app, cors_allowed_origins="*")

# Store active rooms and users
active_rooms = {}

@socketio.on('connect')
def handle_connect():
    logger.info('Client connected')

@socketio.on('join_room')
def on_join(data):
    try:
        room = data.get('room')
        user_id = data.get('user_id')
        user_name = data.get('user_name')
        is_interviewer = data.get('is_interviewer')

        # Join the room
        join_room(room)

        # Track room participants
        if room not in active_rooms:
            active_rooms[room] = {}
        
        active_rooms[room][user_id] = {
            'name': user_name,
            'is_interviewer': is_interviewer
        }

        # Notify room about new user
        emit('user_joined', {
            'user_id': user_id,
            'user_name': user_name,
            'is_interviewer': is_interviewer
        }, room=room)

        # Confirm room join to the client
        emit('room_joined', {
            'room': room,
            'user_id': user_id,
            'user_name': user_name
        })
    except Exception as e:
        logger.error(f"Error joining room: {e}")
        emit('error', {'message': str(e)})

@socketio.on('send_message')
def handle_message(data):
    room = data.get('room')
    message = data.get('message')
    user_id = data.get('user_id')
    user_name = data.get('user_name')

    # Broadcast message to all in the room
    emit('receive_message', {
        'room': room,
        'message': message,
        'user_id': user_id,
        'user_name': user_name
    }, room=room)

@socketio.on('leave_room')
def on_leave(data):
    room = data.get('room')
    user_id = data.get('user_id')

    # Remove user from room tracking
    if room in active_rooms and user_id in active_rooms[room]:
        del active_rooms[room][user_id]

    leave_room(room)
    
    # Notify room about user leaving
    emit('user_left', {
        'user_id': user_id
    }, room=room)

@socketio.on('disconnect')
def handle_disconnect():
    logger.info('Client disconnected')

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

if __name__ == '__main__':
    socketio.run(app, port=PORT, debug=True)