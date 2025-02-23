let localStream;
let peerConnection;
let socket;

const configuration = {
    iceServers: [
        { urls: 'stun:stun.l.google.com:19302' }
    ]
};

class SocketHandler {
    constructor() {
        this.socket = null;
        this.connectionDetails = null;
    }

    initialize(connectionDetails) {
        if (!connectionDetails?.roomId || !connectionDetails?.userName) {
            console.error("Missing required connection details", connectionDetails);
      return;
    }

        this.connectionDetails = connectionDetails;
        
        try {
            // Determine socket URL dynamically
            const socketUrl = this.getSocketUrl();
            
            console.log("Connecting to socket server:", socketUrl);

            // Initialize socket connection with more robust configuration
            this.socket = io(socketUrl, {
                transports: ['websocket', 'polling'], // Fallback to polling
      reconnection: true,
                reconnectionAttempts: 5,
      reconnectionDelay: 1000,
      timeout: 10000,
      query: {
                    room: connectionDetails.roomId,
                    user_id: connectionDetails.userId,
                    user_name: connectionDetails.userName,
                    is_interviewer: connectionDetails.isInterviewer
                }
            });

            // Setup socket event handlers
            this.setupSocketEvents();
            
        } catch (error) {
            console.error("Socket initialization error:", error);
            this.handleConnectionError(error);
        }
    }

    getSocketUrl() {
        // Dynamically determine socket server URL
        const host = window.location.hostname;
        const protocol = window.location.protocol;
        
        // Fallback URLs in order of preference
        const possibleUrls = [
            `${protocol}//${host}:5002`, // Primary
            `http://${host}:5002`,        // Alternate http
            `http://localhost:5002`       // Localhost fallback
        ];

        return possibleUrls.find(url => this.isUrlReachable(url)) || possibleUrls[0];
    }

    isUrlReachable(url) {
        // Simple synchronous check (can be expanded)
        try {
            const xhr = new XMLHttpRequest();
            xhr.open('GET', `${url}/socket-test`, false);
            xhr.send();
            return xhr.status === 200;
        } catch (error) {
            return false;
        }
    }

    setupSocketEvents() {
        if (!this.socket) return;

        this.socket.on('connect', () => {
            console.log('Socket connected with ID:', this.socket.id);
            
            // Join the room after connection
            this.socket.emit('join_room', {
                room: this.connectionDetails.roomId,
                user_id: this.connectionDetails.userId,
                user_name: this.connectionDetails.userName,
                is_interviewer: this.connectionDetails.isInterviewer
      });
    });

        this.socket.on('connect_error', (error) => {
            console.error('Socket connection error:', error);
            this.handleConnectionError(error);
        });

        this.socket.on('disconnect', (reason) => {
            console.log('Socket disconnected:', reason);
            this.handleConnectionError(new Error('Disconnected'));
        });

        // WebRTC signaling events
        this.setupWebRTCEvents();
    }

    setupWebRTCEvents() {
        if (!this.socket) return;

        this.socket.on('offer', (data) => {
            console.log('Received offer');
            if (window.webRTC) {
                window.webRTC.handleOffer(data.offer);
            }
        });

        this.socket.on('answer', (data) => {
            console.log('Received answer');
            if (window.webRTC) {
                window.webRTC.handleAnswer(data.answer);
            }
        });

        this.socket.on('ice_candidate', (data) => {
            console.log('Received ICE candidate');
            if (window.webRTC) {
                window.webRTC.handleIceCandidate(data.candidate);
            }
        });
    }

    handleConnectionError(error) {
        // Show user-friendly error
        const errorMessage = `Connection failed. Please check your network and try again. (${error.message})`;
        
        // Optional: Show a toast or alert
        alert(errorMessage);

        // Optional: Attempt reconnection after a delay
        setTimeout(() => {
            this.initialize(this.connectionDetails);
        }, 3000);
    }

    getSocket() {
        return this.socket;
    }

    sendMessage(message) {
        if (this.socket) {
            this.socket.emit('send_message', {
                room: this.connectionDetails.roomId,
                message,
                user_id: this.connectionDetails.userId,
                user_name: this.connectionDetails.userName
            });
        }
    }
}

// Create global instance
window.socketHandler = new SocketHandler();

async function init() {
    try {
        // Get local media stream
        localStream = await navigator.mediaDevices.getUserMedia({
            video: true,
            audio: true
        });
        document.getElementById('localVideo').srcObject = localStream;

        // Initialize socket connection
        socket = io('http://localhost:5003', {
            transports: ['websocket']
        });

        // Setup socket event handlers
        setupSocketHandlers();

        // Initialize WebRTC peer connection
        setupPeerConnection();

        // Setup media controls
        setupControls();

    } catch (error) {
        console.error('Initialization error:', error);
    }
}

function setupSocketHandlers() {
    socket.on('connect', () => {
        console.log('Connected to signaling server');
        
        // Join room
        const roomId = new URLSearchParams(window.location.search).get('room') || 'default-room';
        socket.emit('join_room', {
        roomId,
            userName: 'User' + Math.floor(Math.random() * 1000)
      });
    });

    socket.on('offer', async ({ offer }) => {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(offer));
        const answer = await peerConnection.createAnswer();
        await peerConnection.setLocalDescription(answer);
        socket.emit('answer', { answer, roomId: socket.roomId });
    });

    socket.on('answer', async ({ answer }) => {
        await peerConnection.setRemoteDescription(new RTCSessionDescription(answer));
    });

    socket.on('ice_candidate', async ({ candidate }) => {
        try {
            await peerConnection.addIceCandidate(new RTCIceCandidate(candidate));
        } catch (e) {
            console.error('Error adding received ice candidate:', e);
        }
    });
}

function setupPeerConnection() {
    peerConnection = new RTCPeerConnection(configuration);

    // Add local tracks to peer connection
    localStream.getTracks().forEach(track => {
        peerConnection.addTrack(track, localStream);
    });

    // Handle incoming tracks
    peerConnection.ontrack = event => {
        const remoteVideo = document.getElementById('remoteVideo');
        if (remoteVideo.srcObject !== event.streams[0]) {
            remoteVideo.srcObject = event.streams[0];
        }
    };

    // Handle ICE candidates
    peerConnection.onicecandidate = event => {
        if (event.candidate) {
            socket.emit('ice_candidate', {
                candidate: event.candidate,
                roomId: socket.roomId
            });
        }
    };

    // Create and send offer when connected
    peerConnection.onnegotiationneeded = async () => {
        try {
            const offer = await peerConnection.createOffer();
            await peerConnection.setLocalDescription(offer);
            socket.emit('offer', { offer, roomId: socket.roomId });
        } catch (e) {
            console.error('Error creating offer:', e);
        }
    };
}

function setupControls() {
    const toggleVideo = document.getElementById('toggleVideo');
    const toggleAudio = document.getElementById('toggleAudio');

    toggleVideo.onclick = () => {
        const videoTrack = localStream.getVideoTracks()[0];
        if (videoTrack) {
            videoTrack.enabled = !videoTrack.enabled;
            toggleVideo.textContent = videoTrack.enabled ? 'Toggle Video' : 'Video Off';
        }
    };

    toggleAudio.onclick = () => {
        const audioTrack = localStream.getAudioTracks()[0];
        if (audioTrack) {
            audioTrack.enabled = !audioTrack.enabled;
            toggleAudio.textContent = audioTrack.enabled ? 'Toggle Audio' : 'Audio Off';
        }
    };
}

// Initialize when page loads
window.addEventListener('load', init);