from gevent import monkey
monkey.patch_all()

from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
import os

app = Flask(__name__)
CORS(app, resources={
    r"/*": {
        "origins": ["http://127.0.0.1:5000"],
        "methods": ["GET", "POST"],
        "allow_headers": ["Content-Type"]
    }
})

socketio = SocketIO(app, 
    cors_allowed_origins=["http://127.0.0.1:5000"],
    async_mode='gevent',
    transport=['websocket']
)

# Store active connections
connections = {}

@socketio.on('join_room')
def on_join(data):
    room_id = data['roomId']
    user_name = data['userName']
    is_interviewer = data.get('isInterviewer', False)
    
    print(f"User {user_name} joining room {room_id} as {'interviewer' if is_interviewer else 'interviewee'}")
    
    join_room(room_id)
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
    socketio.run(app, 
        debug=True, 
        host='127.0.0.1', 
        port=5003,
        allow_unsafe_werkzeug=True
    ) 