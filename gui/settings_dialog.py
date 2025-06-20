import tkinter as tk
from tkinter import ttk, filedialog
import json
import os
from pathlib import Path

class SettingsDialog:
    """Dialog for configuring MDX Generator Tool settings."""
    
    def __init__(self, parent):
        self.parent = parent
        self.settings = self._load_settings()
        
        # Create the dialog
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Settings")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Set size and position
        width, height = 500, 400
        screen_width = parent.winfo_screenwidth()
        screen_height = parent.winfo_screenheight()
        x = (screen_width - width) // 2
        y = (screen_height - height) // 2
        self.dialog.geometry(f"{width}x{height}+{x}+{y}")
        
        # Create notebook for tab organization
        notebook = ttk.Notebook(self.dialog)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(notebook, padding=10)
        notebook.add(general_frame, text="General")
        self._create_general_tab(general_frame)
        
        # Processing settings tab
        processing_frame = ttk.Frame(notebook, padding=10)
        notebook.add(processing_frame, text="Processing")
        self._create_processing_tab(processing_frame)
        
        # Advanced settings tab
        advanced_frame = ttk.Frame(notebook, padding=10)
        notebook.add(advanced_frame, text="Advanced")
        self._create_advanced_tab(advanced_frame)
        
        # Buttons frame
        buttons_frame = ttk.Frame(self.dialog)
        buttons_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Save button
        save_btn = ttk.Button(buttons_frame, text="Save", command=self._save_settings)
        save_btn.pack(side=tk.RIGHT, padx=5)
        
        # Cancel button
        cancel_btn = ttk.Button(buttons_frame, text="Cancel", command=self._cancel)
        cancel_btn.pack(side=tk.RIGHT, padx=5)
        
        # Reset to defaults button
        reset_btn = ttk.Button(buttons_frame, text="Reset to Defaults", command=self._reset_defaults)
        reset_btn.pack(side=tk.LEFT, padx=5)
    
    def _create_general_tab(self, parent):
        """Create the general settings tab content."""
        # Default directory setting
        dir_frame = ttk.Frame(parent)
        dir_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(dir_frame, text="Default Directory:").grid(row=0, column=0, sticky=tk.W)
        
        self.default_dir_var = tk.StringVar(value=self.settings.get('default_directory', ''))
        dir_entry = ttk.Entry(dir_frame, textvariable=self.default_dir_var, width=40)
        dir_entry.grid(row=0, column=1, padx=5, sticky=tk.W+tk.E)
        
        browse_btn = ttk.Button(dir_frame, text="Browse", 
                             command=lambda: self._browse_directory(self.default_dir_var))
        browse_btn.grid(row=0, column=2, padx=5)
        
        # Auto-save setting
        autosave_frame = ttk.Frame(parent)
        autosave_frame.pack(fill=tk.X, pady=10)
        
        self.autosave_var = tk.BooleanVar(value=self.settings.get('autosave_changes', True))
        autosave_check = ttk.Checkbutton(autosave_frame, text="Automatically save changes to _meta.json files",
                                       variable=self.autosave_var)
        autosave_check.pack(anchor=tk.W)
    
    def _create_processing_tab(self, parent):
        """Create the processing settings tab content."""
        # Default steps to run
        steps_frame = ttk.LabelFrame(parent, text="Default Processing Steps")
        steps_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Get all available processing modules
        from utils.file_operations import get_core_modules
        modules = get_core_modules()
        
        # Create checkboxes for each module
        self.steps_vars = {}
        for i, module in enumerate(modules):
            var = tk.BooleanVar(value=self.settings.get('steps', {}).get(module['name'], True))
            self.steps_vars[module['name']] = var
            
            checkbox = ttk.Checkbutton(steps_frame, text=module['description'],
                                    variable=var)
            checkbox.grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
    
    def _create_advanced_tab(self, parent):
        """Create the advanced settings tab content."""
        # Logging settings
        log_frame = ttk.LabelFrame(parent, text="Logging")
        log_frame.pack(fill=tk.X, pady=5)
        
        log_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        self.log_level_var = tk.StringVar(value=self.settings.get('log_level', 'INFO'))
        
        ttk.Label(log_frame, text="Log Level:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        log_level_combo = ttk.Combobox(log_frame, textvariable=self.log_level_var,
                                     values=log_levels, state="readonly")
        log_level_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Log file setting
        ttk.Label(log_frame, text="Log File:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.log_file_var = tk.StringVar(value=self.settings.get('log_file', 'mdx_generator.log'))
        log_file_entry = ttk.Entry(log_frame, textvariable=self.log_file_var)
        log_file_entry.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Performance settings
        perf_frame = ttk.LabelFrame(parent, text="Performance")
        perf_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(perf_frame, text="Parallel Processing:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        self.parallel_var = tk.BooleanVar(value=self.settings.get('parallel_processing', False))
        parallel_check = ttk.Checkbutton(perf_frame, text="Enable multi-threaded processing",
                                      variable=self.parallel_var)
        parallel_check.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # File extensions to process
        ext_frame = ttk.LabelFrame(parent, text="File Extensions")
        ext_frame.pack(fill=tk.X, pady=10)
        
        self.extensions_var = tk.StringVar(value=', '.join(self.settings.get('extensions', ['.md', '.mdx'])))
        ttk.Label(ext_frame, text="Extensions to Process:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ext_entry = ttk.Entry(ext_frame, textvariable=self.extensions_var)
        ext_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        ttk.Label(ext_frame, text="(comma separated)").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
    
    def _browse_directory(self, var):
        """Open file dialog to select a directory."""
        directory = filedialog.askdirectory(initialdir=var.get())
        if directory:
            var.set(directory)
    
    def _load_settings(self):
        """Load settings from file or return defaults."""
        settings_file = self._get_settings_file()
        try:
            if settings_file.exists():
                with open(settings_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass  # Use defaults on any error
        
        # Default settings
        return {
            'default_directory': '',
            'autosave_changes': True,
            'log_level': 'INFO',
            'log_file': 'mdx_generator.log',
            'parallel_processing': False,
            'extensions': ['.md', '.mdx'],
            'steps': {}  # Will be filled with all steps enabled by default
        }
    
    def _save_settings(self):
        """Save current settings and close the dialog."""
        settings = {
            'default_directory': self.default_dir_var.get(),
            'autosave_changes': self.autosave_var.get(),
            'log_level': self.log_level_var.get(),
            'log_file': self.log_file_var.get(),
            'parallel_processing': self.parallel_var.get(),
            'extensions': [ext.strip() for ext in self.extensions_var.get().split(',') if ext.strip()],
            'steps': {name: var.get() for name, var in self.steps_vars.items()}
        }
        
        settings_file = self._get_settings_file()
        try:
            # Ensure the directory exists
            settings_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Write the settings file
            with open(settings_file, 'w') as f:
                json.dump(settings, f, indent=2)
        except Exception as e:
            tk.messagebox.showerror("Error", f"Could not save settings: {str(e)}")
        
        self.dialog.destroy()
    
    def _cancel(self):
        """Close the dialog without saving."""
        self.dialog.destroy()
    
    def _reset_defaults(self):
        """Reset settings to default values."""
        if tk.messagebox.askyesno("Reset Settings", "Reset all settings to default values?"):
            # Reset by recreating the dialog
            self.dialog.destroy()
            self.__init__(self.parent)
    
    def _get_settings_file(self):
        """Get the path to the settings file."""
        if os.name == 'nt':  # Windows
            app_data = os.getenv('APPDATA')
            if app_data:
                return Path(app_data) / "MDX-Generator" / "settings.json"
        
        # macOS and Linux
        return Path.home() / ".config" / "MDX-Generator" / "settings.json"