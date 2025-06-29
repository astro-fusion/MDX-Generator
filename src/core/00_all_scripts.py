#!/usr/bin/env python3
"""
MDX Generator - All Scripts Runner

This script runs all the core MDX processing scripts in sequence:
1. 01_normalize_filenames.py - Normalize file and folder names
2. 02_fix_mdx_frontmatter.py - Fix YAML frontmatter issues
3. 03_generate_index.py - Generate index.mdx from meta structure
4. 04_generate_all_meta_json.py - Generate _meta.json files in all folders
5. 05_generate_nav_links.py - Add prev/next navigation links
6. 06_generate_root_meta_json.py - Generate root _meta.json
7. 07_validate_meta_json.py - Validate all _meta.json files

Usage:
    python 00_all_scripts.py [target_directory] [options]

Examples:
    # Process current directory with confirmations
    python 00_all_scripts.py

    # Process specific directory
    python 00_all_scripts.py /path/to/content

    # Run without confirmations (auto-continue)
    python 00_all_scripts.py /path/to/content --yes

    # Dry run only (no actual changes)
    python 00_all_scripts.py /path/to/content --dry-run
"""

import os
import sys
import time
import argparse
import subprocess
from pathlib import Path
import threading
import signal

class ScriptRunner:
    def __init__(self, target_dir, dry_run=False, auto_yes=False):
        self.target_dir = Path(target_dir).resolve()
        self.dry_run = dry_run
        self.auto_yes = auto_yes
        self.script_dir = Path(__file__).parent
        self.current_step = 0
        self.total_steps = 7
        self._interrupted = False
        
        # Setup signal handler for graceful interruption
        signal.signal(signal.SIGINT, self._signal_handler)
        
        # Define the scripts to run in order
        self.scripts = [
            {
                "name": "01_normalize_filenames.py",
                "title": "Normalize Filenames",
                "description": "Normalize file and folder names (spaces/dashes to underscores)",
                "args": [str(self.target_dir)]
            },
            {
                "name": "02_fix_mdx_frontmatter.py", 
                "title": "Fix MDX Frontmatter",
                "description": "Fix YAML frontmatter syntax issues",
                "args": [str(self.target_dir)]
            },
            {
                "name": "04_generate_all_meta_json.py",
                "title": "Generate All Meta JSON",
                "description": "Generate _meta.json files in all subdirectories",
                "args": [str(self.target_dir)]
            },
            {
                "name": "06_generate_root_meta_json.py",
                "title": "Generate Root Meta JSON", 
                "description": "Generate root-level _meta.json file",
                "args": [str(self.target_dir)]
            },
            {
                "name": "03_generate_index.py",
                "title": "Generate Index",
                "description": "Generate index.mdx from meta structure",
                "args": [str(self.target_dir / "_meta.json")]
            },
            {
                "name": "05_generate_nav_links.py",
                "title": "Generate Navigation Links",
                "description": "Add previous/next navigation links to all files", 
                "args": [str(self.target_dir)]
            },
            {
                "name": "07_validate_meta_json.py",
                "title": "Validate Meta JSON",
                "description": "Validate all _meta.json files against filesystem",
                "args": [str(self.target_dir)]
            }
        ]

    def _signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n\n🛑 Interrupted by user. Stopping after current script completes...")
        self._interrupted = True

    def print_header(self):
        """Print the main header"""
        print("=" * 80)
        print("🚀 MDX Generator - Complete Processing Pipeline")
        print("=" * 80)
        print(f"📁 Target Directory: {self.target_dir}")
        print(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        print(f"⚡ Auto-continue: {'YES' if self.auto_yes else 'NO (7s timeout)'}")
        print("=" * 80)

    def print_step_header(self, step_num, script_info):
        """Print header for each step"""
        print(f"\n{'='*60}")
        print(f"📋 STEP {step_num}/{self.total_steps}: {script_info['title']}")
        print(f"📄 Script: {script_info['name']}")
        print(f"📝 Description: {script_info['description']}")
        print(f"{'='*60}")

    def get_user_confirmation(self, step_num, script_name):
        """Get user confirmation with timeout"""
        if self.auto_yes:
            print(f"✅ Auto-continuing to {script_name}...")
            return True
            
        if self._interrupted:
            return False
            
        print(f"\n🤔 Continue with Step {step_num}: {script_name}?")
        print("   [y] Yes, continue")
        print("   [n] No, stop here") 
        print("   [s] Skip this step")
        print("   (Auto-continue in 7 seconds...)")
        
        # Countdown with interrupt check
        for i in range(7, 0, -1):
            if self._interrupted:
                return False
            print(f"\r⏳ Auto-continuing in {i} seconds... (Press Enter to continue now, 'n' to stop, 's' to skip): ", end="", flush=True)
            
            # Check for user input with timeout
            def get_input():
                try:
                    return input().strip().lower()
                except:
                    return ""
                    
            # Use threading to implement timeout
            user_input = [None]
            def input_thread():
                user_input[0] = get_input()
                
            input_thread = threading.Thread(target=input_thread, daemon=True)
            input_thread.start()
            input_thread.join(timeout=1)
            
            if user_input[0] is not None:
                response = user_input[0]
                if response == 'n':
                    print(f"\n🛑 Stopping at user request.")
                    return False
                elif response == 's':
                    print(f"\n⏭️ Skipping {script_name}")
                    return 'skip'
                else:
                    print(f"\n✅ Continuing with {script_name}...")
                    return True
                    
        print(f"\n⏰ Auto-continuing with {script_name}...")
        return True

    def run_script(self, script_info):
        """Run a single script with proper arguments"""
        script_path = self.script_dir / script_info["name"]
        
        if not script_path.exists():
            print(f"⛔ Error: Script not found: {script_path}")
            return False
            
        # Build command arguments
        cmd = [sys.executable, str(script_path)]
        cmd.extend(script_info["args"])
        
        # Add common flags
        if self.dry_run:
            cmd.append("--dry-run")
        else:
            cmd.append("--yes")  # Skip individual script confirmations
            
        print(f"🔧 Running: {' '.join(cmd)}")
        print("-" * 60)
        
        try:
            # Run the script and capture output in real-time
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )
            
            # Print output in real-time
            for line in process.stdout:
                if self._interrupted:
                    process.terminate()
                    return False
                print(line.rstrip())
                
            process.wait()
            
            if process.returncode == 0:
                print(f"\n✅ {script_info['title']} completed successfully!")
                return True
            else:
                print(f"\n❌ {script_info['title']} failed with return code {process.returncode}")
                return False
                
        except Exception as e:
            print(f"⛔ Error running {script_info['name']}: {e}")
            return False

    def run_all(self):
        """Run all scripts in sequence"""
        if not self.target_dir.exists():
            print(f"⛔ Error: Target directory does not exist: {self.target_dir}")
            return False
            
        self.print_header()
        
        # Pre-flight check
        print(f"\n🔍 Pre-flight check...")
        print(f"📁 Target directory exists: ✅")
        print(f"📝 Found {len([f for f in self.target_dir.rglob('*.md')])} .md files")
        print(f"📝 Found {len([f for f in self.target_dir.rglob('*.mdx')])} .mdx files")
        
        successful_steps = 0
        skipped_steps = 0
        
        for i, script_info in enumerate(self.scripts, 1):
            if self._interrupted:
                print(f"\n🛑 Processing interrupted by user.")
                break
                
            self.current_step = i
            self.print_step_header(i, script_info)
            
            # Get user confirmation
            confirmation = self.get_user_confirmation(i, script_info['title'])
            
            if confirmation is False:
                print(f"🛑 Stopping pipeline at Step {i}")
                break
            elif confirmation == 'skip':
                print(f"⏭️ Skipping Step {i}: {script_info['title']}")
                skipped_steps += 1
                continue
                
            # Run the script
            success = self.run_script(script_info)
            
            if success:
                successful_steps += 1
                print(f"✅ Step {i}/{self.total_steps} completed successfully")
            else:
                print(f"❌ Step {i}/{self.total_steps} failed")
                
                # Ask if user wants to continue despite failure
                if not self.auto_yes and not self._interrupted:
                    cont = input(f"\n⚠️ Step {i} failed. Continue anyway? [y/N]: ").strip().lower()
                    if cont not in ('y', 'yes'):
                        print("🛑 Stopping pipeline due to failure")
                        break
                else:
                    print("⚠️ Continuing despite failure (auto-mode)")
                    
            # Brief pause between steps
            if i < len(self.scripts) and not self._interrupted:
                time.sleep(1)
                
        # Final summary
        self.print_final_summary(successful_steps, skipped_steps)
        return successful_steps > 0

    def print_final_summary(self, successful_steps, skipped_steps):
        """Print final summary"""
        print(f"\n{'='*80}")
        print(f"🎉 PIPELINE COMPLETE")
        print(f"{'='*80}")
        print(f"📊 Total steps: {self.total_steps}")
        print(f"✅ Successful: {successful_steps}")
        print(f"⏭️ Skipped: {skipped_steps}")
        print(f"❌ Failed: {self.total_steps - successful_steps - skipped_steps}")
        print(f"📁 Target directory: {self.target_dir}")
        print(f"🔧 Mode: {'DRY RUN' if self.dry_run else 'LIVE RUN'}")
        
        if successful_steps == self.total_steps:
            print(f"\n🎊 All steps completed successfully!")
        elif successful_steps > 0:
            print(f"\n⚠️ Pipeline completed with some issues.")
        else:
            print(f"\n💥 Pipeline failed - no steps completed successfully.")
            
        print(f"{'='*80}")

def main():
    parser = argparse.ArgumentParser(
        description="Run all MDX processing scripts in sequence",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        'target_dir',
        nargs='?',
        default='.',
        help='Target directory to process (default: current directory)'
    )
    parser.add_argument(
        "--dry-run", "-d",
        action="store_true", 
        help="Run in dry-run mode (no actual changes)"
    )
    parser.add_argument(
        "--yes", "-y",
        action="store_true",
        help="Auto-continue without confirmations"
    )
    
    args = parser.parse_args()
    
    try:
        runner = ScriptRunner(
            target_dir=args.target_dir,
            dry_run=args.dry_run, 
            auto_yes=args.yes
        )
        success = runner.run_all()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print(f"\n\n🛑 Interrupted by user. Exiting...")
        sys.exit(1)
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()