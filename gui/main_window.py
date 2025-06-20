import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import threading
from typing import Callable, Optional, List, Dict
import time
from datetime import datetime

from utils.logging_utils import get_logger, setup_logger
from utils.file_operations import is_valid_directory, get_core_modules, run_module_async
from gui.progress_dialog import ProgressDialog

logger = get_logger(__name__)

# Define constants
CORE_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src", "core")

class SimpleDragDropFrame(tk.Frame):
    """A simple frame with a button to select directories."""
    
    def __init__(self, master, on_drop_callback: Optional[Callable[[str], None]] = None):
        super().__init__(master, bd=2, relief=tk.GROOVE)
        self.on_drop_callback = on_drop_callback
        
        # Create a frame with a button - use system colors instead of hardcoded white
        self.frame = tk.Frame(self)
        self.frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add descriptive text
        self.label = tk.Label(self.frame, text="Select a directory to process",
                             font=("Arial", 12, "bold"))
        self.label.pack(pady=(20, 10))
        
        # Add selection button - using ttk for better theming
        self.button = ttk.Button(self.frame, text="Browse...", 
                              command=self._select_directory)
        self.button.pack(pady=10)
        
        # Create a more prominent path display frame
        path_frame = tk.LabelFrame(self.frame, text="Selected Directory", padx=5, pady=5)
        path_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Add current selection display - more prominent
        self.path_var = tk.StringVar()
        self.path_var.set("No directory selected")
        self.path_label = tk.Label(path_frame, textvariable=self.path_var,
                                  font=("Arial", 10), wraplength=700, justify=tk.LEFT,
                                  anchor=tk.W)
        self.path_label.pack(fill=tk.X, pady=10, padx=10)
    
    def _select_directory(self):
        """Open a file dialog to select a directory."""
        directory = filedialog.askdirectory(title="Select Directory")
        if directory and self.on_drop_callback:
            # More clear path display
            self.path_var.set(directory)
            self.on_drop_callback(directory)

class LogViewerFrame(tk.Frame):
    """A frame for displaying log messages."""
    
    def __init__(self, master):
        super().__init__(master)
        
        # Create a label frame
        self.frame = tk.LabelFrame(self, text="Processing Log", padx=5, pady=5)
        self.frame.pack(fill=tk.BOTH, expand=True)
        
        # Create a text widget with scrollbar
        self.log_text = tk.Text(self.frame, wrap=tk.WORD, height=8, 
                              width=60, state=tk.DISABLED)
        scrollbar = ttk.Scrollbar(self.frame, orient=tk.VERTICAL, 
                               command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=scrollbar.set)
        
        # Pack the widgets
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Button to clear logs
        self.clear_button = ttk.Button(self.frame, text="Clear Log", command=self.clear_log)
        self.clear_button.pack(side=tk.BOTTOM, padx=5, pady=5)
    
    def append_log(self, message, level="INFO"):
        """
        Append a message to the log viewer with timestamp.
        
        Args:
            message (str): The log message
            level (str): Log level (INFO, WARNING, ERROR, etc.)
        """
        # Get current timestamp
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Format the log message
        formatted_msg = f"[{timestamp}] {level}: {message}\n"
        
        # Configure tag for log level
        tag = level.lower()
        
        # Enable text widget for editing
        self.log_text.config(state=tk.NORMAL)
        
        # Insert the log message with appropriate tag
        self.log_text.insert(tk.END, formatted_msg, tag)
        
        # Configure tag colors if not already done
        try:
            self.log_text.tag_configure("info", foreground="black")
            self.log_text.tag_configure("warning", foreground="orange")
            self.log_text.tag_configure("error", foreground="red")
            self.log_text.tag_configure("success", foreground="green")
        except:
            pass  # Tags might already be configured
        
        # Scroll to the end
        self.log_text.see(tk.END)
        
        # Disable the text widget again
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Clear the log viewer."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)

class MainWindow:
    """Main application window for the MDX Generator Tool."""
    
    def __init__(self, master):
        self.master = master
        self.master.geometry("900x800")  # Increased height for log viewer
        self.master.minsize(800, 700)
        
        # Configure style for ttk widgets
        self._configure_styles()
        
        # Store the selected directory
        self.selected_directory = None
        
        # Dictionary to keep track of running threads
        self.running_threads = {}
        
        # Load processing modules - MOVED THIS LINE EARLIER
        self.modules = get_core_modules()
        logger.info(f"Loaded {len(self.modules)} core modules")
        
        # Create the main notebook for tabbed interface
        self.notebook = ttk.Notebook(master)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Create main processing tab
        self.main_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.main_tab, text="Processing")
        
        # Create GenAI tab
        self.genai_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.genai_tab, text="GenAI Content")
        
        # Initialize the main processing tab
        self._init_main_tab()
        
        # Initialize the GenAI tab
        self._init_genai_tab()
        
        # Status bar
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        status_bar = ttk.Label(master, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Start the message processing timer
        self.master.after(100, self._process_thread_messages)
        
        # Start periodic thread checker (after 10 seconds)
        self.master.after(10000, self._check_running_threads)
    
    def _configure_styles(self):
        """Configure styles for ttk widgets."""
        style = ttk.Style()
        
        # Create a style for accent buttons
        style.configure("Accent.TButton", font=("Arial", 11))
        
        # Create styles for step frames
        style.configure("Step.TLabelframe", padding=10)
        style.configure("Step.TLabelframe.Label", font=("Arial", 10, "bold"))
        
        # Configure progress bars
        style.configure("TProgressbar", thickness=20)
    
    def _init_main_tab(self):
        """Initialize the main processing tab."""
        main_frame = ttk.Frame(self.main_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title label
        title_label = ttk.Label(main_frame, text="MDX Generator Tool", 
                              font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Directory selection frame
        self.drag_drop_frame = SimpleDragDropFrame(main_frame, on_drop_callback=self.set_directory)
        self.drag_drop_frame.pack(fill=tk.X, pady=10)
        
        # Create a frame for file statistics
        self.stats_frame = ttk.LabelFrame(main_frame, text="Directory Statistics", padding=10)
        self.stats_frame.pack(fill=tk.X, pady=10)
        
        # File count labels
        self.file_stats_var = tk.StringVar(value="No directory selected")
        ttk.Label(self.stats_frame, textvariable=self.file_stats_var).pack(anchor=tk.W)
        
        # Create a paned window for steps and logs
        paned_window = ttk.PanedWindow(main_frame, orient=tk.VERTICAL)
        paned_window.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Create the steps frame
        steps_frame = ttk.Frame(paned_window)
        
        # Create the steps label frame
        self.steps_label_frame = ttk.LabelFrame(steps_frame, text="Processing Steps", padding=10)
        self.steps_label_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add the steps frame to the paned window
        paned_window.add(steps_frame, weight=3)
        
        # Create and add the log viewer frame
        self.log_viewer = LogViewerFrame(paned_window)
        paned_window.add(self.log_viewer, weight=1)
        
        # Create a canvas with scrollbar for the steps
        canvas_frame = ttk.Frame(self.steps_label_frame)
        canvas_frame.pack(fill=tk.BOTH, expand=True)
        
        self.steps_canvas = tk.Canvas(canvas_frame)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=self.steps_canvas.yview)
        
        self.steps_frame = ttk.Frame(self.steps_canvas)
        
        self.steps_frame.bind(
            "<Configure>",
            lambda e: self.steps_canvas.configure(scrollregion=self.steps_canvas.bbox("all"))
        )
        
        self.steps_canvas.create_window((0, 0), window=self.steps_frame, anchor="nw")
        self.steps_canvas.configure(yscrollcommand=scrollbar.set)
        
        scrollbar.pack(side="right", fill="y")
        self.steps_canvas.pack(side="left", fill="both", expand=True)
        
        # Create processing steps UI
        self._create_processing_steps()
        
        # Action buttons frame
        buttons_frame = ttk.Frame(main_frame)
        buttons_frame.pack(fill=tk.X, pady=10)
        
        # Run all steps button
        self.run_all_button = ttk.Button(buttons_frame, text="Run All Steps", 
                                      command=self.run_all_steps,
                                      state=tk.DISABLED)
        self.run_all_button.pack(side=tk.RIGHT, padx=5)
        
        # Settings button
        settings_button = ttk.Button(buttons_frame, text="Settings", 
                                  command=self.show_settings)
        settings_button.pack(side=tk.RIGHT, padx=5)
    
    def _create_processing_steps(self):
        """Create UI elements for each processing step."""
        self.steps = []
        
        # Clear existing steps if any
        for widget in self.steps_frame.winfo_children():
            widget.destroy()
        
        # No modules loaded message if needed
        if not self.modules:
            no_modules_label = ttk.Label(
                self.steps_frame,
                text="No processing modules found in core directory.",
                font=("Arial", 12),
                foreground="red"
            )
            no_modules_label.pack(pady=20)
            self.log_viewer.append_log("No processing modules found in core directory.", "ERROR")
            return
        
        # Create a step UI for each module
        for i, module in enumerate(self.modules):
            # Step container frame
            step_frame = ttk.LabelFrame(
                self.steps_frame, 
                text=f"Step {module['order']}: {module['display_name']}", 
                style="Step.TLabelframe"
            )
            step_frame.pack(fill=tk.X, pady=5, padx=5)
            
            # Step description - Get from module docstring if available
            desc_text = f"Runs {module['display_name']} module on the selected directory."
            step_desc = ttk.Label(
                step_frame, 
                text=desc_text,
                wraplength=700
            )
            step_desc.pack(anchor=tk.W, pady=5)
            
            # Step controls frame
            controls_frame = ttk.Frame(step_frame)
            controls_frame.pack(fill=tk.X, pady=5)
            
            # Enable checkbox
            enable_var = tk.BooleanVar(value=True)
            enable_check = ttk.Checkbutton(
                controls_frame, 
                text="Enable", 
                variable=enable_var
            )
            enable_check.pack(side=tk.LEFT)
            
            # Progress bar
            progress_var = tk.DoubleVar(value=0)
            progress_bar = ttk.Progressbar(
                controls_frame, 
                variable=progress_var,
                length=400
            )
            progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
            
            # Status label
            status_var = tk.StringVar(value="Ready")
            status_label = ttk.Label(
                controls_frame, 
                textvariable=status_var, 
                width=15
            )
            status_label.pack(side=tk.LEFT, padx=5)
            
            # Run button
            run_button = ttk.Button(
                controls_frame, 
                text="Run", 
                command=lambda idx=i, mod=module: self.run_step(idx, mod),
                state=tk.DISABLED
            )
            run_button.pack(side=tk.LEFT, padx=5)
            
            # Stop button (initially disabled)
            stop_button = ttk.Button(
                controls_frame, 
                text="Stop", 
                command=lambda idx=i: self.stop_step(idx),
                state=tk.DISABLED
            )
            stop_button.pack(side=tk.LEFT, padx=5)
            
            # Store step info
            self.steps.append({
                'index': i,
                'module': module,
                'var': enable_var,
                'progress_var': progress_var,
                'progress_bar': progress_bar,
                'status_var': status_var,
                'run_button': run_button,
                'stop_button': stop_button,
                'frame': step_frame,
                'running': False
            })
    
    def _init_genai_tab(self):
        """Initialize the GenAI content tab."""
        genai_frame = ttk.Frame(self.genai_tab, padding=10)
        genai_frame.pack(fill=tk.BOTH, expand=True)
        
        # Add a title label
        title_label = ttk.Label(genai_frame, text="Generate AI Content", 
                             font=("Arial", 16, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Create a description
        desc_label = ttk.Label(genai_frame, 
                            text="Use Generative AI to create content based on templates and knowledge base.",
                            wraplength=600)
        desc_label.pack(pady=10)
        
        # Form for GenAI content generation
        form_frame = ttk.LabelFrame(genai_frame, text="Content Generation Form", padding=10)
        form_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # Title input
        title_frame = ttk.Frame(form_frame)
        title_frame.pack(fill=tk.X, pady=5)
        ttk.Label(title_frame, text="Title:", width=15).pack(side=tk.LEFT)
        title_var = tk.StringVar()
        ttk.Entry(title_frame, textvariable=title_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Description input
        desc_frame = ttk.Frame(form_frame)
        desc_frame.pack(fill=tk.X, pady=5)
        ttk.Label(desc_frame, text="Description:", width=15).pack(side=tk.LEFT)
        desc_var = tk.StringVar()
        ttk.Entry(desc_frame, textvariable=desc_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # Template selection
        template_frame = ttk.Frame(form_frame)
        template_frame.pack(fill=tk.X, pady=5)
        ttk.Label(template_frame, text="Template:", width=15).pack(side=tk.LEFT)
        template_var = tk.StringVar()
        template_combo = ttk.Combobox(template_frame, textvariable=template_var)
        template_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        template_combo['values'] = ['Blog Post', 'Article', 'Product Description']
        
        # Knowledge base input
        kb_frame = ttk.Frame(form_frame)
        kb_frame.pack(fill=tk.X, pady=5)
        ttk.Label(kb_frame, text="Knowledge Base:").pack(anchor=tk.W, pady=5)
        kb_text = tk.Text(kb_frame, height=10)
        kb_text.pack(fill=tk.BOTH, expand=True)
        
        # GenAI provider selection
        provider_frame = ttk.Frame(form_frame)
        provider_frame.pack(fill=tk.X, pady=10)
        ttk.Label(provider_frame, text="AI Provider:", width=15).pack(side=tk.LEFT)
        provider_var = tk.StringVar(value="Perplexity AI")
        provider_combo = ttk.Combobox(provider_frame, textvariable=provider_var, state="readonly")
        provider_combo.pack(side=tk.LEFT, fill=tk.X, expand=True)
        provider_combo['values'] = ['Perplexity AI']
        
        # Progress bar for generation
        progress_frame = ttk.Frame(form_frame)
        progress_frame.pack(fill=tk.X, pady=10)
        
        genai_progress_var = tk.DoubleVar(value=0)
        genai_progress = ttk.Progressbar(progress_frame, variable=genai_progress_var)
        genai_progress.pack(fill=tk.X, pady=5)
        
        genai_status_var = tk.StringVar(value="Ready to generate")
        ttk.Label(progress_frame, textvariable=genai_status_var).pack(anchor=tk.W)
        
        # Action buttons
        button_frame = ttk.Frame(form_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        generate_button = ttk.Button(button_frame, text="Generate Content", 
                                   command=lambda: self.generate_ai_content(
                                       title_var.get(), desc_var.get(), 
                                       template_var.get(), kb_text.get("1.0", tk.END)
                                   ))
        generate_button.pack(side=tk.RIGHT, padx=5)
    
    def count_directory_files(self, directory):
        """Count the number of files in the directory."""
        if not directory or not os.path.isdir(directory):
            return 0, 0, 0
        
        total_files = 0
        md_files = 0
        mdx_files = 0
        
        for root, _, files in os.walk(directory):
            total_files += len(files)
            for file in files:
                if file.endswith('.md'):
                    md_files += 1
                elif file.endswith('.mdx'):
                    mdx_files += 1
        
        return total_files, md_files, mdx_files
    
    def set_directory(self, directory):
        """Set the directory to process and update UI accordingly."""
        if not is_valid_directory(directory):
            messagebox.showwarning("Invalid Directory", 
                                 "The selected directory does not contain any MD/MDX files.")
            self.log_viewer.append_log(f"Invalid directory selected: {directory}", "WARNING")
            return
        
        self.selected_directory = directory
        self.log_viewer.append_log(f"Selected directory: {directory}", "INFO")
        
        # Update directory stats
        total, md, mdx = self.count_directory_files(directory)
        self.file_stats_var.set(
            f"Total Files: {total}\n"
            f"Markdown Files (.md): {md}\n"
            f"MDX Files (.mdx): {mdx}"
        )
        self.log_viewer.append_log(f"Directory stats: Total={total}, MD={md}, MDX={mdx}", "INFO")
        
        # Update status bar
        self.status_var.set(f"Selected directory: {directory}")
        
        # Enable buttons
        self.run_all_button.config(state=tk.NORMAL)
        for step in self.steps:
            step['run_button'].config(state=tk.NORMAL)
    
    def run_step(self, step_index, module_info):
        """Run a specific processing step."""
        if not self.selected_directory:
            messagebox.showerror("Error", "No directory selected")
            return
        
        step = self.steps[step_index]
        
        # Skip if already running
        if step['running']:
            self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} is already running", "WARNING")
            return
        
        # Reset progress
        step['progress_var'].set(0)
        step['status_var'].set("Starting...")
        
        # Update button states
        step['run_button'].config(state=tk.DISABLED)
        step['stop_button'].config(state=tk.NORMAL)
        step['running'] = True
        
        # Log the start
        self.log_viewer.append_log(f"Starting Step {module_info['order']}: {module_info['display_name']}", "INFO")
        
        # Create a thread info structure for processing
        thread_info = run_module_async(
            module_info,
            self.selected_directory
        )
        
        # Store thread info
        self.running_threads[step_index] = thread_info
    
    def _monitor_step_completion(self, step_index, module_info):
        """Monitor a step thread for completion and update the UI."""
        import time
        thread = self.running_threads.get(step_index)
        if not thread:
            return
        
        try:
            # Wait for the thread with a timeout (prevent infinite waiting)
            MAX_WAIT_TIME = 30  # 30 seconds max before considering it stuck
            thread_obj = thread.get("worker_thread")
            if thread_obj:
                thread_obj.join(timeout=MAX_WAIT_TIME)
                
                if thread_obj.is_alive():
                    # Thread is still running after timeout
                    print(f"Module {module_info['display_name']} may be stuck, forcing UI update")
                    # Force update UI
                    self.master.after(0, lambda: self._update_step_error_ui(step_index, module_info, "Operation timed out or became unresponsive"))
                else:
                    # Thread completed normally
                    self.master.after(0, lambda: self._update_step_complete_ui(step_index, module_info))
            else:
                self.master.after(0, lambda: self._update_step_error_ui(step_index, module_info, "Thread information missing"))
        except Exception as e:
            print(f"Error monitoring thread for {module_info['display_name']}: {str(e)}")
            self.master.after(0, lambda: self._update_step_error_ui(step_index, module_info, str(e)))
        """Monitor a step thread for completion and update the UI."""
        thread = self.running_threads.get(step_index)
        if not thread:
            return
        
        try:
            # Wait for the thread with a timeout (prevent infinite waiting)
            MAX_WAIT_TIME = 600  # 10 minutes max
            thread.join(timeout=MAX_WAIT_TIME)
            
            if thread.is_alive():
                # Thread is still running after timeout
                logger.error(f"Module {module_info['display_name']} timed out after {MAX_WAIT_TIME} seconds")
                # Force stop
                if hasattr(thread, 'stop_event'):
                    thread.stop_event.set()
                    
                # Update UI from main thread
                self.master.after(0, lambda: self._update_step_timeout_ui(step_index, module_info))
            else:
                # Thread completed normally
                self.master.after(0, lambda: self._update_step_complete_ui(step_index, module_info))
        except Exception as e:
            logger.error(f"Error monitoring thread for {module_info['display_name']}: {str(e)}", exc_info=True)
            self.master.after(0, lambda: self._update_step_error_ui(step_index, module_info, str(e)))
    
    def _update_step_complete_ui(self, step_index, module_info):
        """Update UI after a step completes."""
        step = self.steps[step_index]
        
        # Reset button states
        step['run_button'].config(state=tk.NORMAL)
        step['stop_button'].config(state=tk.DISABLED)
        step['running'] = False
        
        # Get final status
        status = step['status_var'].get()
        
        # Log completion
        if "error" in status.lower():
            self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} failed: {status}", "ERROR")
        else:
            self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} completed successfully", "SUCCESS")
        
        # Remove thread from running threads
        if step_index in self.running_threads:
            del self.running_threads[step_index]
    
    def _update_step_timeout_ui(self, step_index, module_info):
        """Update UI after a step times out."""
        step = self.steps[step_index]
        
        # Reset button states
        step['run_button'].config(state=tk.NORMAL)
        step['stop_button'].config(state=tk.DISABLED)
        step['running'] = False
        step['status_var'].set("Timed out")
        
        # Log timeout
        self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} timed out after 10 minutes", "ERROR")
        
        # Remove thread from running threads
        if step_index in self.running_threads:
            del self.running_threads[step_index]
    
    def _update_step_error_ui(self, step_index, module_info, error_msg):
        """Update UI after a step encounters an error."""
        step = self.steps[step_index]
        
        # Reset button states
        step['run_button'].config(state=tk.NORMAL)
        step['stop_button'].config(state=tk.DISABLED)
        step['running'] = False
        step['status_var'].set(f"Error: {error_msg[:20]}...")
        
        # Log error
        self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} failed with error: {error_msg}", "ERROR")
        
        # Remove thread from running threads
        if step_index in self.running_threads:
            del self.running_threads[step_index]
    
    def stop_step(self, step_index):
        """Stop a running processing step."""
        thread_info = self.running_threads.get(step_index)
        if not thread_info:
            return
        
        stop_event = thread_info.get('stop_event')
        if not stop_event:
            return
            
        # Set stop event
        stop_event.set()
        
        # Update UI
        step = self.steps[step_index]
        step['status_var'].set("Stopping...")
        
        # Log the stop
        module_info = step['module']
        self.log_viewer.append_log(f"Stopping Step {module_info['order']}: {module_info['display_name']}", "WARNING")
        
        # Create a monitoring thread to update UI when stopped
        monitor_thread = threading.Thread(
            target=self._monitor_step_stop,
            args=(step_index, module_info),
            daemon=True
        )
        monitor_thread.start()
    
    def _monitor_step_stop(self, step_index, module_info):
        """Monitor a step thread for stopping and update the UI."""
        thread = self.running_threads.get(step_index)
        if not thread:
            return
        
        # Wait for thread to complete or timeout after 5 seconds
        thread.join(timeout=5)
        
        # Force thread termination if needed (not ideal but may be necessary)
        # Note: Python threads can't be forcibly terminated, this is just cleanup
        
        # Update UI from main thread
        self.master.after(0, lambda: self._update_step_stopped_ui(step_index, module_info))
    
    def _update_step_stopped_ui(self, step_index, module_info):
        """Update UI after a step is stopped."""
        step = self.steps[step_index]
        
        # Reset button states
        step['run_button'].config(state=tk.NORMAL)
        step['stop_button'].config(state=tk.DISABLED)
        step['running'] = False
        step['status_var'].set("Stopped")
        
        # Log completion
        self.log_viewer.append_log(f"Step {module_info['order']}: {module_info['display_name']} was stopped", "WARNING")
        
        # Remove thread from running threads
        if step_index in self.running_threads:
            del self.running_threads[step_index]
    
    def run_all_steps(self):
        """Run all enabled processing steps in sequence."""
        if not self.selected_directory:
            messagebox.showerror("Error", "No directory selected")
            return
        
        # Get enabled steps
        enabled_steps = [i for i, step in enumerate(self.steps) if step['var'].get()]
        
        if not enabled_steps:
            messagebox.showinfo("No Steps Selected", "Please select at least one processing step.")
            return
        
        # Disable run all button
        self.run_all_button.config(state=tk.DISABLED)
        
        # Log start of run all
        self.log_viewer.append_log(f"Starting execution of {len(enabled_steps)} steps", "INFO")
        
        # Create a thread for processing
        thread = threading.Thread(
            target=self._run_all_steps_thread,
            args=(enabled_steps,),
            daemon=True
        )
        thread.start()
    
    def _run_all_steps_thread(self, step_indices):
        """Thread function for running all steps."""
        try:
            # Create progress dialog
            self.master.after(0, lambda: self._show_progress_dialog(len(step_indices)))
            
            # Run each step
            for i, step_index in enumerate(step_indices):
                step = self.steps[step_index]
                module = step['module']
                
                # Update progress dialog
                self.master.after(0, lambda idx=i, mod=module: self._update_progress_dialog(idx, mod))
                
                # Run the step if not already running
                if not step['running']:
                    # Need to use after() to run in main thread
                    self.master.after(0, lambda idx=step_index, mod=module: self.run_step(idx, mod))
                    
                    # Wait for step to complete
                    while step_index in self.running_threads:
                        time.sleep(0.1)  # Small delay to prevent CPU hogging
                
                # Small delay between steps
                time.sleep(0.5)
            
            # Complete the progress dialog
            self.master.after(0, self._complete_progress_dialog)
            
        except Exception as e:
            logger.error(f"Error running all steps: {str(e)}", exc_info=True)
            self.log_viewer.append_log(f"Error running all steps: {str(e)}", "ERROR")
            
        finally:
            # Re-enable the run all button
            self.master.after(0, lambda: self.run_all_button.config(state=tk.NORMAL))
    
    def _show_progress_dialog(self, total_steps):
        """Show the progress dialog."""
        self.progress_dialog = ProgressDialog(self.master, total_steps)
        self.progress_dialog.show()
    
    def _update_progress_dialog(self, step_number, module):
        """Update the progress dialog."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog.dialog is not None:
            self.progress_dialog.update_progress(step_number)
            self.progress_dialog.update_status(f"Running {module['display_name']}...")
    
    def _complete_progress_dialog(self):
        """Complete the progress dialog."""
        if hasattr(self, 'progress_dialog') and self.progress_dialog.dialog is not None:
            self.progress_dialog.done()
    
    def generate_ai_content(self, title, description, template, knowledge_base):
        """Generate AI content using provided inputs."""
        if not title or not description:
            messagebox.showerror("Missing Information", "Please provide a title and description.")
            return
        
        # Show a message for this demo version
        messagebox.showinfo("GenAI Content Generation", 
                          "This feature is not fully implemented in this demo.\n\n"
                          f"Would generate content with:\n"
                          f"Title: {title}\n"
                          f"Description: {description}\n"
                          f"Template: {template}")
    
    def show_settings(self):
        """Show the settings dialog."""
        messagebox.showinfo("Settings", "Settings dialog would appear here")
    
    def _check_running_threads(self):
        """Periodically check running threads to detect stuck operations."""
        for step_index, thread_info in list(self.running_threads.items()):
            try:
                # Check if worker thread is still alive but may be stuck
                worker_thread = thread_info.get('worker_thread')
                last_heartbeat = thread_info.get('last_heartbeat', [0])[0]
                
                # If no heartbeat for 60 seconds, thread is likely stuck
                if worker_thread and time.time() - last_heartbeat > 60:
                    module_info = thread_info.get('module_info')
                    self.log_viewer.append_log(f"Thread for {module_info['display_name']} appears stuck - forcing termination", "ERROR")
                    
                    # Force UI update to show error
                    self._update_step_timeout_ui(step_index, module_info)
            except Exception as e:
                logger.error(f"Error checking thread: {str(e)}", exc_info=True)
        
        # Schedule next check
        self.master.after(5000, self._check_running_threads)
    
    def _process_thread_messages(self):
        """Process messages from worker threads to update UI safely."""
        # Process queue messages from all running threads
        for step_index, thread_info in list(self.running_threads.items()):
            try:
                # Get message queue
                message_queue = thread_info.get('message_queue')
                if not message_queue:
                    continue
                
                # Process all pending messages (non-blocking)
                while True:
                    try:
                        # Get message with small timeout to prevent blocking
                        msg_type, msg_value = message_queue.get(block=False)
                        
                        # Update last heartbeat time
                        if 'last_heartbeat' in thread_info:
                            thread_info['last_heartbeat'][0] = time.time()
                        
                        # Process message based on type
                        if msg_type == 'progress':
                            step = self.steps[step_index]
                            step['progress_var'].set(msg_value)
                        elif msg_type == 'status':
                            step = self.steps[step_index]
                            step['status_var'].set(msg_value)
                        elif msg_type == 'heartbeat':
                            # Just update the heartbeat time
                            pass
                            
                        # Mark message as processed
                        message_queue.task_done()
                        
                    except queue.Empty:
                        # No more messages
                        break
                    
                # Check if worker thread is still alive
                worker_thread = thread_info.get('worker_thread')
                if worker_thread and not worker_thread.is_alive() and thread_info.get('thread_active')[0] == False:
                    # Thread is complete, update UI
                    module_info = thread_info.get('module_info')
                    self._update_step_complete_ui(step_index, module_info)
                    
                # Check for heartbeat timeout (30 seconds)
                last_heartbeat = thread_info.get('last_heartbeat', [0])[0]
                if time.time() - last_heartbeat > 30 and thread_info.get('thread_active')[0]:
                    # Thread appears stuck, log warning and potentially stop it
                    module_info = thread_info.get('module_info')
                    logger.warning(f"Thread for {module_info['display_name']} may be stuck - no updates for 30 seconds")
                    self.log_viewer.append_log(f"Thread for {module_info['display_name']} may be stuck - attempting to stop", "WARNING")
                    
                    # Try to stop the thread
                    stop_event = thread_info.get('stop_event')
                    if stop_event:
                        stop_event.set()
                    
                    # Update UI to show timeout warning
                    step = self.steps[step_index]
                    step['status_var'].set("Warning: Operation may be stuck...")
                    
            except Exception as e:
                logger.error(f"Error processing thread messages: {str(e)}", exc_info=True)
        
        # Schedule next check (15ms, fast enough for UI responsiveness)
        self.master.after(15, self._process_thread_messages)