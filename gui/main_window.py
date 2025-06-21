"""
Main window for the MDX Generator application.

This module contains the MainWindow class which is the primary UI component
of the MDX Generator application.
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
import queue
import time
from datetime import datetime

from utils.logging_utils import get_logger
from utils.file_operations import is_valid_directory, get_core_modules, run_module_async
from utils.settings import update_last_directory, get_last_directory

# Initialize logger
logger = get_logger(__name__)

class MainWindow:
    """Main application window for the MDX Generator Tool."""
    
    def __init__(self, master):
        """
        Initialize the main window.
        
        Args:
            master: The root Tk window
        """
        self.master = master
        self.master.geometry("900x700")
        self.master.minsize(800, 600)
        
        # Set up variables
        self.selected_directory = None
        self.modules = get_core_modules()
        self.running_threads = {}
        self.steps = []
        
        logger.info(f"Loaded {len(self.modules)} core modules")
        
        # Set up UI
        self._setup_ui()
        
        # Start thread message processing
        self.master.after(15, self._process_thread_messages)
        
        # Try to load last directory
        self._load_last_directory()
    
    def _setup_ui(self):
        """Set up the user interface."""
        # Configure ttk styles
        style = ttk.Style()
        style.configure("TButton", padding=6)
        style.configure("Title.TLabel", font=("Arial", 16, "bold"))
        style.configure("TLabelframe", padding=10)
        
        # Create main frame with padding
        main_frame = ttk.Frame(self.master, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create title
        title = ttk.Label(main_frame, text="MDX Generator Tool", style="Title.TLabel")
        title.pack(pady=(0, 15))
        
        # Create directory selection frame
        dir_frame = ttk.LabelFrame(main_frame, text="Directory Selection")
        dir_frame.pack(fill=tk.X, pady=10, padx=5)
        
        # Directory selection components
        select_btn = ttk.Button(dir_frame, text="Select Directory", command=self._select_directory)
        select_btn.pack(side=tk.LEFT, padx=5, pady=5)
        
        # Add Last Directory button if a previous directory exists
        last_dir = get_last_directory()
        if last_dir:
            last_dir_btn = ttk.Button(dir_frame, text="Last Directory", command=self._load_last_directory)
            last_dir_btn.pack(side=tk.LEFT, padx=5, pady=5)
            
        # Directory label
        self.dir_label = ttk.Label(dir_frame, text="No directory selected")
        self.dir_label.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # Create a frame for the processing steps
        steps_frame = ttk.LabelFrame(main_frame, text="Processing Steps")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create the steps buttons and progress bars
        self._create_steps(steps_frame)
        
        # Create log frame
        log_frame = ttk.LabelFrame(main_frame, text="Log")
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create log text widget with scrollbar
        self.log_text = tk.Text(log_frame, height=10, width=80)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Add clear log button
        clear_btn = ttk.Button(log_frame, text="Clear Log", command=self._clear_log)
        clear_btn.pack(side=tk.BOTTOM, anchor=tk.E, padx=5, pady=5)
        
        # Pack log components
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Create action buttons
        actions_frame = ttk.Frame(main_frame)
        actions_frame.pack(fill=tk.X, pady=10)
        
        # Run all steps button
        self.run_all_btn = ttk.Button(actions_frame, text="Run All Steps", 
                                     command=self._run_all_steps,
                                     state=tk.DISABLED)
        self.run_all_btn.pack(side=tk.RIGHT, padx=5)
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.master, textvariable=self.status_var, 
                              relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def _create_steps(self, parent_frame):
        """Create the processing steps UI."""
        # Create a canvas with scrollbar for steps
        canvas = tk.Canvas(parent_frame)
        scrollbar = ttk.Scrollbar(parent_frame, orient="vertical", command=canvas.yview)
        
        # Configure canvas
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        
        # Create a frame inside the canvas to hold steps
        steps_inner = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=steps_inner, anchor="nw")
        
        # Pack canvas and scrollbar
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Add each module as a step
        for i, module in enumerate(self.modules):
            # Create frame for this step
            step_frame = ttk.LabelFrame(steps_inner, text=f"Step {i} - {module['display_name']}")
            step_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
            
            # Create inner frame for controls
            controls_frame = ttk.Frame(step_frame)
            controls_frame.pack(fill=tk.X, expand=True, padx=5, pady=5)
            
            # Create progress bar
            progress_var = tk.DoubleVar(value=0.0)
            progress_bar = ttk.Progressbar(controls_frame, variable=progress_var, 
                                        orient="horizontal", length=100, mode="determinate")
            progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True)
            
            # Create status label
            status_var = tk.StringVar(value="Ready")
            status_label = ttk.Label(controls_frame, textvariable=status_var)
            status_label.pack(side=tk.TOP, anchor=tk.W, padx=5, pady=2)
            
            # Create run button
            run_btn = ttk.Button(controls_frame, text="Run", state=tk.DISABLED,
                                command=lambda idx=i, mod=module: self._run_step(idx, mod))
            run_btn.pack(side=tk.LEFT, padx=5)
            
            # Store step information
            self.steps.append({
                'module': module,
                'progress_var': progress_var,
                'progress_bar': progress_bar,
                'status_var': status_var,
                'run_btn': run_btn
            })
    
    def _select_directory(self):
        """Open directory selector dialog."""
        directory = filedialog.askdirectory()
        if directory:
            self._set_directory(directory)
    
    def _load_last_directory(self):
        """Load the last used directory."""
        last_dir = get_last_directory()
        if last_dir and os.path.isdir(last_dir):
            self._set_directory(last_dir)
            return True
        return False
    
    def _set_directory(self, directory):
        """Set the working directory."""
        if not is_valid_directory(directory):
            messagebox.showwarning("Invalid Directory", 
                                 "The selected directory does not exist or contain MD/MDX files.")
            return
        
        self.selected_directory = directory
        self.dir_label.config(text=directory)
        self.status_var.set(f"Selected directory: {directory}")
        self.append_log(f"Selected directory: {directory}")
        
        # Enable buttons
        for step in self.steps:
            step['run_btn'].config(state=tk.NORMAL)
        
        self.run_all_btn.config(state=tk.NORMAL)
        
        # Save as last directory
        update_last_directory(directory)
    
    def _run_step(self, step_index, module_info):
        """Run a single processing step."""
        if not self.selected_directory:
            messagebox.showwarning("No Directory", "Please select a directory first.")
            return
        
        # Update UI
        step = self.steps[step_index]
        step['progress_var'].set(0)
        step['status_var'].set(f"Running {module_info['display_name']}...")
        
        # Disable step button
        step['run_btn'].config(state=tk.DISABLED)
        
        self.append_log(f"Starting: {module_info['display_name']}")
        
        # Set up message queue and stop event for the thread
        message_queue = queue.Queue()
        stop_event = threading.Event()
        
        # Store thread data
        self.running_threads[step_index] = {
            'module_info': module_info,
            'message_queue': message_queue,
            'stop_event': stop_event,
            'start_time': time.time(),
            'thread_active': [True]  # Using list for mutable reference
        }
        
        # Start worker thread
        worker = threading.Thread(
            target=run_module_async,
            args=(module_info, self.selected_directory, 
                 step['progress_var'], step['status_var'], 
                 stop_event, message_queue)
        )
        worker.daemon = True
        worker.start()
        
        # Store thread object
        self.running_threads[step_index]['worker_thread'] = worker
        
        # Start monitor thread
        monitor = threading.Thread(
            target=self._monitor_thread,
            args=(step_index, module_info)
        )
        monitor.daemon = True
        monitor.start()
    
    def _run_all_steps(self):
        """Run all processing steps in sequence."""
        if not self.selected_directory:
            messagebox.showwarning("No Directory", "Please select a directory first.")
            return
        
        # Disable all buttons
        for step in self.steps:
            step['run_btn'].config(state=tk.DISABLED)
        self.run_all_btn.config(state=tk.DISABLED)
        
        # Start with first step
        self.current_step_index = 0
        self._run_step(0, self.modules[0])
    
    def _monitor_thread(self, step_index, module_info):
        """Monitor thread execution and update UI when complete."""
        # Get thread info
        thread_info = self.running_threads.get(step_index)
        if not thread_info:
            return
        
        # Get thread object
        thread = thread_info.get('worker_thread')
        if not thread:
            return
            
        try:
            # Wait for thread to complete with timeout
            thread.join(timeout=300)  # 5 minute timeout
            
            # Mark thread as inactive
            thread_info['thread_active'][0] = False
            
            # Schedule UI update
            if thread.is_alive():
                # Thread is stuck
                self.master.after(0, lambda: self._update_step_error_ui(
                    step_index, module_info, "Thread timed out after 5 minutes"
                ))
            else:
                # Thread completed normally
                self.master.after(0, lambda: self._update_step_complete_ui(
                    step_index, module_info
                ))
        except Exception as e:
            # Handle any exception in monitor thread
            logger.error(f"Error monitoring thread: {str(e)}", exc_info=True)
            self.master.after(0, lambda: self._update_step_error_ui(
                step_index, module_info, str(e)
            ))
    
    def _update_step_complete_ui(self, step_index, module_info):
        """Update UI after step completes successfully."""
        step = self.steps[step_index]
        
        # Update progress and status
        step['progress_var'].set(100)
        step['status_var'].set("Complete")
        step['run_btn'].config(state=tk.NORMAL)
        
        # Log completion
        self.append_log(f"Completed: {module_info['display_name']}")
        
        # Clean up thread data
        if step_index in self.running_threads:
            del self.running_threads[step_index]
        
        # If running all steps, continue with next step
        if hasattr(self, 'current_step_index'):
            next_step = self.current_step_index + 1
            if next_step < len(self.modules):
                self.current_step_index = next_step
                self._run_step(next_step, self.modules[next_step])
            else:
                # All steps complete
                self.append_log("All steps completed successfully")
                del self.current_step_index
                self.run_all_btn.config(state=tk.NORMAL)
    
    def _update_step_error_ui(self, step_index, module_info, error_msg):
        """Update UI after step fails."""
        if step_index < len(self.steps):
            step = self.steps[step_index]
            
            # Update UI
            step['status_var'].set(f"Error: {error_msg}")
            step['run_btn'].config(state=tk.NORMAL)
            
            # Log error
            self.append_log(f"Error in {module_info['display_name']}: {error_msg}", "ERROR")
        
        # Clean up thread data
        if step_index in self.running_threads:
            del self.running_threads[step_index]
        
        # If running all steps, abort sequence
        if hasattr(self, 'current_step_index'):
            self.append_log("Step sequence aborted due to error", "WARNING")
            del self.current_step_index
            
            # Re-enable buttons
            for step in self.steps:
                step['run_btn'].config(state=tk.NORMAL)
            self.run_all_btn.config(state=tk.NORMAL)
    
    def _process_thread_messages(self):
        """Process messages from worker threads to update UI safely."""
        for step_index, thread_info in dict(self.running_threads).items():
            try:
                # Skip if thread_info is None
                if thread_info is None:
                    continue
                
                # Get the message queue
                message_queue = thread_info.get('message_queue')
                if message_queue is None:
                    continue
                    
                # Process pending messages
                try:
                    # Try to get and process messages without blocking
                    while True:
                        try:
                            msg_type, msg_data = message_queue.get_nowait()
                            
                            if msg_type == 'log':
                                level, message = msg_data
                                self.append_log(message, level)
                            
                            # Mark message as processed
                            message_queue.task_done()
                        except queue.Empty:
                            break
                except Exception as e:
                    logger.error(f"Error processing queue messages: {str(e)}")
            except Exception as e:
                logger.error(f"Error in thread message processing: {str(e)}", exc_info=True)
        
        # Schedule next check
        self.master.after(15, self._process_thread_messages)
    
    def append_log(self, message, level="INFO"):
        """Append a message to the log."""
        # Get timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format message
        log_msg = f"[{timestamp}] [{level}] {message}\n"
        
        # Insert into text widget
        self.log_text.config(state=tk.NORMAL)
        
        # Set tag based on level
        tag = level.lower()
        if tag not in self.log_text.tag_names():
            color = {
                "info": "black",
                "error": "red",
                "warning": "orange",
                "debug": "gray"
            }.get(tag, "black")
            self.log_text.tag_configure(tag, foreground=color)
        
        # Insert text with tag
        self.log_text.insert(tk.END, log_msg, tag)
        
        # Scroll to end
        self.log_text.see(tk.END)
        
        # Disable editing
        self.log_text.config(state=tk.DISABLED)
    
    def _clear_log(self):
        """Clear the log text widget."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
