import subprocess
import sys
from threading import Thread
import time
import signal
import os

def run_server(script_name, port):
    try:
        subprocess.run([sys.executable, script_name], env={**os.environ, 'PORT': str(port)})
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Error running {script_name}: {e}")

def main():
    # Create threads for each server
    main_thread = Thread(target=run_server, args=('app.py', 5000))
    meet_thread = Thread(target=run_server, args=('meet_server.py', 5002))

    try:
        # Start meet server first
        meet_thread.start()
        time.sleep(2)  # Wait for meet server to initialize
        
        # Start main server
        main_thread.start()

        # Wait for both servers to complete
        main_thread.join()
        meet_thread.join()
    except KeyboardInterrupt:
        print("\nShutting down servers...")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == '__main__':
    main() 