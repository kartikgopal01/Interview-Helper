import subprocess
import sys
from threading import Thread
import time
import os
import socket
import signal
import psutil

def find_free_port():
    """Find a free port dynamically."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def is_port_in_use(port):
    """Check if a port is in use."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        try:
            s.bind(('localhost', port))
            return False
        except socket.error:
            return True

def kill_process_on_port(port):
    """Kill any process running on the specified port."""
    if not is_port_in_use(port):
        return

    if os.name == 'nt':  # Windows
        try:
            subprocess.run(['netstat', '-ano'], capture_output=True, text=True)
            subprocess.run(f'taskkill /F /PID $(netstat -ano | findstr :{port} | awk "{{print $5}}")', shell=True)
        except:
            pass
    else:  # Linux/Mac
        try:
            subprocess.run(f'lsof -ti:{port} | xargs kill -9', shell=True)
        except:
            pass
    
    time.sleep(1)  # Wait for port to be released

def run_server(script_name, suggested_port=None):
    try:
        port = suggested_port if suggested_port else find_free_port()
        kill_process_on_port(port)
        
        env = {**os.environ, 'PORT': str(port)}
        
        print(f"Starting {script_name} on port {port}")
        process = subprocess.Popen(
            [sys.executable, script_name],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        # Give the server a moment to start
        time.sleep(2)
        
        # Check if process is still running
        if process.poll() is None:
            return process, port
        else:
            error = process.stderr.read()
            print(f"Error starting {script_name}: {error}")
            return None, None
            
    except Exception as e:
        print(f"Error running {script_name}: {e}")
        return None, None

def main():
    processes = []
    try:
        # Start meet server
        meet_process, meet_port = run_server('meet_server.py', 5002)
        if meet_process:
            processes.append(meet_process)
        else:
            print("Failed to start meet server")
            return
        
        # Start main server
        main_process, main_port = run_server('app.py', 5001)
        if main_process:
            processes.append(main_process)
        else:
            print("Failed to start main server")
            return

        if main_port and meet_port:
            print(f"\nMain Server is running at: http://localhost:{main_port}")
            print(f"Meet Server is running at: http://localhost:{meet_port}")
            print("\nPress Ctrl+C to stop the servers.\n")

            def print_output(process, name):
                while True:
                    output = process.stdout.readline()
                    if output:
                        print(f"[{name}] {output.strip()}")
                    error = process.stderr.readline()
                    if error:
                        print(f"[{name} ERROR] {error.strip()}", file=sys.stderr)
                    if process.poll() is not None:
                        break

            # Start output monitoring threads
            Thread(target=print_output, args=(meet_process, "MEET"), daemon=True).start()
            Thread(target=print_output, args=(main_process, "MAIN"), daemon=True).start()

            # Wait for processes
            while all(p.poll() is None for p in processes):
                time.sleep(0.1)

    except KeyboardInterrupt:
        print("\nShutting down servers...")
    finally:
        for process in processes:
            try:
                process.terminate()
                process.wait(timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass

if __name__ == '__main__':
    main() 