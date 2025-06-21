import tkinter as tk
from tkinter import ttk
from datetime import datetime

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
        
        # Configure text tags for different log levels
        self.log_text.tag_configure("info", foreground="black")
        self.log_text.tag_configure("warning", foreground="orange")
        self.log_text.tag_configure("error", foreground="red")
        self.log_text.tag_configure("debug", foreground="gray")
    
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
        
        # Scroll to the end
        self.log_text.see(tk.END)
        
        # Disable the text widget again
        self.log_text.config(state=tk.DISABLED)
    
    def clear_log(self):
        """Clear the log viewer."""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)