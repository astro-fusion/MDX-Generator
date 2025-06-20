#!/usr/bin/env python3
"""
Watchdog launcher for MDX-Generator that prevents zombie processes.
"""

import os
import sys
import time
import signal
import subprocess
import threading
from pathlib import Path

def monitor_process(process, timeout_seconds=120):
    """Monitor a process and terminate it if it runs longer than timeout_seconds."""
    print(f"Watchdog: Monitoring process {process.pid} with {timeout_seconds}s timeout")
    
    # Give the process time to run
    time.sleep(timeout_seconds)
    
    # Check if process is still running after timeout
    if process.poll() is None:
        print(f"Watchdog: Process {process.pid} exceeded timeout of {timeout_seconds}s")
        print("Watchdog: Sending SIGTERM...")
        
        try:
            # First try SIGTERM
            process.terminate()
            # Give it 5 seconds to clean up
            time.sleep(5)
            
            # If still running, use SIGKILL
            if process.poll() is None:
                print("Watchdog: Process still running after SIGTERM, sending SIGKILL...")
                process.kill()
                
            print(f"Watchdog: Process {process.pid} terminated")
        except Exception as e:
            print(f"Watchdog: Error terminating process: {str(e)}")

def run_with_watchdog(command, timeout_seconds=120):
    """Run a command with a watchdog monitor."""
    print(f"Starting '{' '.join(command)}' with {timeout_seconds}s watchdog")
    
    # Create a process that will generate its own process group
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid  # Create new process group
    )
    
    # Start watchdog thread
    watchdog = threading.Thread(
        target=monitor_process,
        args=(process, timeout_seconds),
        daemon=True
    )
    watchdog.start()
    
    try:
        # Stream output in real-time
        while True:
            stdout_line = process.stdout.readline()
            if stdout_line:
                print(stdout_line.strip())
            
            stderr_line = process.stderr.readline()
            if stderr_line:
                print(f"ERROR: {stderr_line.strip()}")
            
            # Break if process is done
            if process.poll() is not None and not stdout_line and not stderr_line:
                break
        
        # Get final exit code
        exit_code = process.poll()
        print(f"Process exited with code {exit_code}")
        return exit_code
    
    except KeyboardInterrupt:
        print("Interrupted by user, terminating process...")
        try:
            # Kill the entire process group on Ctrl+C
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            time.sleep(2)
            if process.poll() is None:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except Exception as e:
            print(f"Error terminating process: {str(e)}")
        return 1

if __name__ == "__main__":
    # Command-line arguments determine what to run
    if len(sys.argv) > 1:
        command = sys.argv[1:]
    else:
        # Default to running the main app
        command = [sys.executable, "main.py"]
    
    # Add an option to run with safe mode
    if "--watchdog-safe-mode" in command:
        command.remove("--watchdog-safe-mode")
        command.append("--safe-mode")
    
    # Run with watchdog
    sys.exit(run_with_watchdog(command, timeout_seconds=300))  # 5 minute timeout