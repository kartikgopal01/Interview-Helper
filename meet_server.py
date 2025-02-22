from gevent import monkey
monkey.patch_all()

from flask import Flask, render_template
from flask_socketio import SocketIO, emit, join_room, leave_room
import os

app = Flask(__name__, 
           template_folder='frontend',
           static_folder='frontend/assets')
socketio = SocketIO(app, async_mode='gevent')

# Store active meetings
active_meetings = {}

@app.route('/meet/<meeting_id>')
def meeting_room(meeting_id):
    return render_template('pages/meet_room.html', meeting_id=meeting_id)

@socketio.on('join_meeting')
def on_join(data):
    meeting_id = data.get('meeting_id')
    user_name = data.get('user_name')
    
    if meeting_id not in active_meetings:
        active_meetings[meeting_id] = set()
    
    active_meetings[meeting_id].add(user_name)
    join_room(meeting_id)
    
    emit('user_joined', {
        'user_name': user_name,
        'participants': list(active_meetings[meeting_id])
    }, room=meeting_id)

@socketio.on('leave_meeting')
def on_leave(data):
    meeting_id = data.get('meeting_id')
    user_name = data.get('user_name')
    
    if meeting_id in active_meetings:
        active_meetings[meeting_id].remove(user_name)
        if not active_meetings[meeting_id]:
            del active_meetings[meeting_id]
    
    leave_room(meeting_id)
    emit('user_left', {
        'user_name': user_name,
        'participants': list(active_meetings.get(meeting_id, set()))
    }, room=meeting_id)

@socketio.on('send_signal')
def on_signal(data):
    meeting_id = data.get('meeting_id')
    emit('signal_received', data, room=meeting_id, include_self=False)

if __name__ == '__main__':
    socketio.run(app, debug=True, host='127.0.0.1', port=5001) 