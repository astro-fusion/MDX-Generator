import tkinter as tk
from tkinter import ttk

class ProgressDialog:
    """Dialog showing progress of MDX processing operations."""
    
    def __init__(self, parent, total_steps):
        self.parent = parent
        self.total_steps = total_steps
        self.dialog = None
        self.progress_bar = None
        self.status_label = None
    
    def show(self):
        """Create and display the progress dialog."""
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Processing...")
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        
        # Make dialog modal
        self.dialog.protocol("WM_DELETE_WINDOW", self._on_close)
        
        # Set size and position
        width, height = 400, 150
        screen_width = self.parent.winfo_screenwidth()
        screen_height = self.parent.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create the UI elements
        frame = tk.Frame(self.dialog, padx=20, pady=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        # Status label
        self.status_label = tk.Label(frame, text="Starting processing...", anchor=tk.W)
        self.status_label.pack(fill=tk.X, pady=(0, 10))
        
        # Progress bar
        self.progress_bar = ttk.Progressbar(
            frame, orient=tk.HORIZONTAL, mode='determinate', 
            maximum=self.total_steps - 1, value=0
        )
        self.progress_bar.pack(fill=tk.X)
        
        # Step counter label
        self.step_label = tk.Label(frame, text=f"Step 1 of {self.total_steps}")
        self.step_label.pack(pady=10)
        
        # Cancel button
        self.cancel_button = tk.Button(frame, text="Cancel", command=self._on_cancel)
        self.cancel_button.pack()
    
    def update_progress(self, step_number):
        """Update the progress bar and step counter."""
        if self.dialog is None:
            return
            
        self.progress_bar['value'] = step_number
        self.step_label.config(text=f"Step {step_number + 1} of {self.total_steps}")
    
    def update_status(self, status_text):
        """Update the status message."""
        if self.dialog is None:
            return
            
        self.status_label.config(text=status_text)
    
    def done(self):
        """Mark the process as complete and allow closing."""
        if self.dialog is None:
            return
            
        self.progress_bar['value'] = self.total_steps - 1
        self.status_label.config(text="Processing complete!")
        self.cancel_button.config(text="Close", command=self._destroy_dialog)
    
    def _on_cancel(self):
        """Handle user cancellation."""
        # In a real implementation, you would signal the processing thread to stop
        self._destroy_dialog()
    
    def _on_close(self):
        """Handle window close via X button."""
        # Optionally ask for confirmation before closing
        self._destroy_dialog()
    
    def _destroy_dialog(self):
        """Close the dialog."""
        if self.dialog is not None:
            self.dialog.grab_release()
            self.dialog.destroy()
            self.dialog = None