import subprocess
import sys
import os

def run_dashboard():
    """Run the dashboard with the updated configuration"""
    print("=" * 50)
    print("Starting MSTP VLAN Dashboard")
    print("=" * 50)
    
    # Get the directory of this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Construct the path to desktop_app.py
    dashboard_path = os.path.join(script_dir, "dashboard", "desktop_app.py")
    
    print(f"Running dashboard from: {dashboard_path}")
    print("-" * 50)
    print("Note: The dashboard will automatically load the node configuration")
    print("      from dashboard_config.json with the updated IP addresses")
    print("-" * 50)
    
    # Start the dashboard
    if sys.platform == 'win32':
        # On Windows, use CREATE_NEW_CONSOLE to create a new window
        subprocess.Popen(['python', dashboard_path], 
                        creationflags=subprocess.CREATE_NEW_CONSOLE)
    else:
        # On Unix, just run it
        subprocess.Popen(['python', dashboard_path])
    
    print("Dashboard started!")
    print("You can close this window now.")

if __name__ == "__main__":
    run_dashboard()
