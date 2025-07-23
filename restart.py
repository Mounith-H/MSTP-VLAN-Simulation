import os
import sys
import subprocess
import time

def kill_python_processes():
    """Kill all running Python processes except this script."""
    current_pid = os.getpid()
    
    print("Killing any running Python processes...")
    if sys.platform == 'win32':
        # Windows approach
        subprocess.run(["taskkill", "/F", "/IM", "python.exe"],capture_output=True, text=True, creationflags=subprocess.CREATE_NO_WINDOW)
    else:
        # Unix approach using pkill (safer than killall)
        try:
            subprocess.run(["pkill", "-f", "python"], capture_output=True, text=True)
        except Exception:
            print("Warning: Could not kill Python processes automatically")

def restart_all():
    """Restart all nodes and the dashboard"""
    print("Starting complete restart sequence...")
    
    # Kill any existing Python processes
    kill_python_processes()
    time.sleep(2)
    
    # Start Node A
    print("Starting Node A...")
    if sys.platform == 'win32':
        node_a = subprocess.Popen(['python', 'main.py', 'A'], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        node_a = subprocess.Popen(['python', 'main.py', 'A'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    time.sleep(3)
    
    # Start Dashboard
    print("Starting Dashboard...")
    if sys.platform == 'win32':
        dashboard = subprocess.Popen(['python', 'dashboard/desktop_app.py'], creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        dashboard = subprocess.Popen(['python', 'dashboard/desktop_app.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    print("Restart completed! Node A and Dashboard are running.")
    print("To run nodes B and C, copy the project to other laptops and run:")
    print("1. Update config.py with Current_Node_id = 'B' or 'C'")
    print("2. Run python main.py")
    
    return node_a, dashboard

if __name__ == "__main__":
    try:
        restart_all()
        print("\nPress Ctrl+C to exit and kill all processes...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nExiting and cleaning up...")
        kill_python_processes()