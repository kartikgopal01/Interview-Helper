import subprocess
import sys
from threading import Thread
import time

def run_main_server():
    subprocess.run([sys.executable, 'app.py'])

def run_meet_server():
    subprocess.run([sys.executable, 'meet_server.py'])

if __name__ == '__main__':
    # Create threads for each server
    main_thread = Thread(target=run_main_server)
    meet_thread = Thread(target=run_meet_server)

    # Start meet server first
    meet_thread.start()
    time.sleep(2)  # Wait for meet server to initialize
    
    # Start main server
    main_thread.start()

    # Wait for both servers to complete
    main_thread.join()
    meet_thread.join() 