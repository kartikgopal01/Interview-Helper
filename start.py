import subprocess
import sys
from threading import Thread
import time
import signal
import os
import socket

def find_free_port():
    """Find a free port dynamically."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def run_server(script_name, suggested_port=None):
    try:
        # If no suggested port, find a free port
        port = suggested_port if suggested_port else find_free_port()
        
        # Set environment variable for the port
        env = {**os.environ, 'PORT': str(port)}
        
        print(f"Starting {script_name} on port {port}")
        subprocess.run([sys.executable, script_name], env=env)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running {script_name}: {e}")

def main():
    # Find free ports dynamically
    main_port = find_free_port()
    meet_port = find_free_port()

    # Create threads for each server
    main_thread = Thread(target=run_server, args=('app.py', main_port))
    meet_thread = Thread(target=run_server, args=('meet_server.py', meet_port))

    try:
        # Start meet server first
        meet_thread.start()
        time.sleep(2)  # Wait for meet server to initialize
        
        # Start main server
        main_thread.start()

        # Print main server URL
        print(f"\nMain Server is running at: http://localhost:{main_port}")
        print("\nPress Ctrl+C to stop the servers.\n")

        # Wait for both servers to complete
        main_thread.join()
        meet_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main() 