#!/usr/bin/env python3
"""
BGMI Complete Modding Tool - ALL MODDERS INCLUDED
Combines all functionality: OBB unpack/repack, PAK unpack/repack, skin modding, null fixes
Single file solution for complete BGMI modding workflow
"""

import os
import sys

# Fix Unicode encoding for Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')
import struct
import zipfile
import zstandard as zstd
from pathlib import Path
import tempfile
import shutil
import time
import json
import base64
import hashlib
import platform
import subprocess
import uuid
import requests
import re
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes

# Rich UI removed for mobile
# from rich import box

# Textual UI for mobile (optional - falls back to text menu if not installed)
try:
    from textual.app import App, ComposeResult
    from textual.containers import Container, Vertical, Horizontal
    from textual.widgets import Button, Header, Footer, Static, Label
    from textual.screen import Screen
    from textual import on
    TEXTUAL_AVAILABLE = True
except ImportError:
    TEXTUAL_AVAILABLE = False
    # Create dummy classes so code doesn't break
    class App: pass
    class Screen: pass
    class ComposeResult: pass

# ───── COLORFUL CONSOLE LOGGER (STANDALONE) ─────────────────────
from datetime import datetime

class ColorfulConsoleLogger:
    def __init__(self, silent_mode=False, phases=None, title="SKIN MODDING"):
        self.start_time = time.time()
        self.silent_mode = silent_mode  # If True, only dashboard updates, no text logs
        self.files_processed = 0  # Track actual files processed
        self.title = title  # Dynamic title for header
        
        # Default phases if not specified
        if phases is None:
            phases = ["UNPACK", "MOD_APPLY", "OPTIMIZE", "FINALIZE"]
        
        # Initialize only specified phases
        self.phase_data = {}
        for phase in phases:
            self.phase_data[phase] = {"status": "⏳ QUEUED", "progress": 0, "detail": "Waiting to start..."}
        
        # Color codes
        self.COLORS = {
            # Bright colors
            "RED": "\033[91m",
            "GREEN": "\033[92m",
            "YELLOW": "\033[93m",
            "BLUE": "\033[94m",
            "MAGENTA": "\033[95m",
            "CYAN": "\033[96m",
            "WHITE": "\033[97m",
            
            # Background colors
            "BG_BLUE": "\033[44m",
            "BG_CYAN": "\033[46m",
            "BG_GREEN": "\033[42m",
            "BG_YELLOW": "\033[43m",
            
            # Styles
            "BOLD": "\033[1m",
            "UNDERLINE": "\033[4m",
            "RESET": "\033[0m"
        }

    def get_timestamp(self):
        return datetime.now().strftime('%H:%M:%S')

    def _get_progress_bar(self, percentage, length=10):
        filled = int(length * percentage / 100)
        empty = length - filled
        
        # Colorful progress bar
        if percentage < 30:
            color = self.COLORS["RED"]
        elif percentage < 70:
            color = self.COLORS["YELLOW"]
        else:
            color = self.COLORS["GREEN"]
            
        return f"{color}{'█' * filled}{self.COLORS['RESET']}{'░' * empty}"

    def clear_console(self):
        """Clear the entire console - works reliably on Windows"""
        # Don't clear if running in Textual (it handles its own screen)
        # Check if we're in a Textual context by looking for the app
        try:
            import textual.app
            # If we can import textual, check if there's an active app
            # For now, always clear - Textual will handle screen management
            pass
        except:
            pass
        os.system('cls' if os.name == 'nt' else 'clear')

    def print_full_dashboard(self):
        """Print the complete dashboard in one go"""
        self.clear_console()
        
        # Header with gradient effect - dynamic title
        # Format: "🚀 BGMI MOD ENGINE - {TITLE}"
        # Total box width is 70, so we need to center within that
        title_text = f"🚀 BGMI MOD ENGINE - {self.title}"
        # Calculate padding (70 - 2 for borders = 68 usable width)
        padding_needed = max(0, 68 - len(title_text))
        left_padding = padding_needed // 2
        title_padded = " " * left_padding + title_text + " " * (padding_needed - left_padding)
        
        header = f"""
{self.COLORS['CYAN']}╔══════════════════════════════════════════════════════════════════════════╗{self.COLORS['RESET']}
{self.COLORS['CYAN']}║{self.COLORS['BOLD']}{self.COLORS['MAGENTA']}{title_padded}{self.COLORS['RESET']}{self.COLORS['CYAN']} ║{self.COLORS['RESET']}
{self.COLORS['CYAN']}╠══════════════════════════════════════════════════════════════════════════╣{self.COLORS['RESET']}
{self.COLORS['CYAN']}║{self.COLORS['YELLOW']} 🕒 {self.get_timestamp()} {self.COLORS['WHITE']}│{self.COLORS['GREEN']} 🎯 MODE: AUTOMATED {self.COLORS['WHITE']}│{self.COLORS['BLUE']} 📊 STATUS: ACTIVE             {self.COLORS['RESET']}{self.COLORS['CYAN']} ║{self.COLORS['RESET']}
{self.COLORS['CYAN']}╚══════════════════════════════════════════════════════════════════════════╝{self.COLORS['RESET']}
"""
        print(header)
        
        # Dashboard
        dashboard_header = f"""
{self.COLORS['BLUE']}╔══════════════════════════════════════════════════════════════════════════╗{self.COLORS['RESET']}
{self.COLORS['BLUE']}║{self.COLORS['BOLD']}{self.COLORS['CYAN']} 📋 OPERATIONS DASHBOARD                                                 {self.COLORS['RESET']}{self.COLORS['BLUE']} ║{self.COLORS['RESET']}
{self.COLORS['BLUE']}╠══════════════════════════════════════════════════════════════════════════╣{self.COLORS['RESET']}
{self.COLORS['BLUE']}║{self.COLORS['BOLD']}{self.COLORS['WHITE']} PHASE        │ STATUS      │ PROGRESS     │ DETAILS                     {self.COLORS['RESET']}{self.COLORS['BLUE']} ║{self.COLORS['RESET']}
{self.COLORS['BLUE']}╟──────────────────────────────────────────────────────────────────────────╢{self.COLORS['RESET']}"""
        print(dashboard_header)
        
        for phase, data in self.phase_data.items():
            # Dynamic phase icons and colors
            phase_icons = {
                "UNPACK": "📦", 
                "MOD_APPLY": "🔧", "HIT_APPLY": "🎯", "KILL_APPLY": "💀", 
                "LOOT_APPLY": "🎁", "HEAD_APPLY": "🎯", "EMOTE_APPLY": "🎭",
                "OPTIMIZE": "⚡", 
                "FINALIZE": "📤"
            }
            phase_colors = {
                "UNPACK": self.COLORS["CYAN"], 
                "MOD_APPLY": self.COLORS["MAGENTA"], "HIT_APPLY": self.COLORS["RED"],
                "KILL_APPLY": self.COLORS["MAGENTA"], "LOOT_APPLY": self.COLORS["YELLOW"],
                "HEAD_APPLY": self.COLORS["CYAN"], "EMOTE_APPLY": self.COLORS["MAGENTA"],
                "OPTIMIZE": self.COLORS["YELLOW"], 
                "FINALIZE": self.COLORS["GREEN"]
            }
            
            # Get icon and color, default if not found
            icon = phase_icons.get(phase, "🔧")
            color = phase_colors.get(phase, self.COLORS["WHITE"])
            
            # Format phase name for display (remove _APPLY suffix for cleaner display)
            display_phase = phase.replace("_APPLY", " APPLY") if "_APPLY" in phase else phase
            
            # Status color coding
            if "ACTIVE" in data['status']:
                status_color = self.COLORS["YELLOW"]
            elif "DONE" in data['status']:
                status_color = self.COLORS["GREEN"]
            else:
                status_color = self.COLORS["WHITE"]
            
            line = f"{self.COLORS['BLUE']}║ {color}{icon} {display_phase:<10}{self.COLORS['RESET']}{self.COLORS['BLUE']} │ {status_color}{data['status']:<10}{self.COLORS['RESET']}{self.COLORS['BLUE']} │ {self._get_progress_bar(data['progress']):<18} │ {self.COLORS['WHITE']}{data['detail']:<30}{self.COLORS['RESET']}{self.COLORS['BLUE']} ║{self.COLORS['RESET']}"
            print(line)
        
        footer = f"""{self.COLORS['BLUE']}╚══════════════════════════════════════════════════════════════════════════╝{self.COLORS['RESET']}
"""
        print(footer)

    def log_info(self, module, message):
        if not self.silent_mode:
            print(f"{self.COLORS['BLUE']}[{self.get_timestamp()}]{self.COLORS['RESET']} {self.COLORS['CYAN']}{module:^12}{self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['BLUE']}INFO {self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['WHITE']}{message}{self.COLORS['RESET']}")

    def log_success(self, module, message):
        if not self.silent_mode:
            print(f"{self.COLORS['BLUE']}[{self.get_timestamp()}]{self.COLORS['RESET']} {self.COLORS['CYAN']}{module:^12}{self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['GREEN']}✅    {self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['GREEN']}{message}{self.COLORS['RESET']}")

    def log_warning(self, module, message):
        if not self.silent_mode:
            print(f"{self.COLORS['BLUE']}[{self.get_timestamp()}]{self.COLORS['RESET']} {self.COLORS['CYAN']}{module:^12}{self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['YELLOW']}⚠️    {self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['YELLOW']}{message}{self.COLORS['RESET']}")

    def log_processing(self, module, message):
        if not self.silent_mode:
            print(f"{self.COLORS['BLUE']}[{self.get_timestamp()}]{self.COLORS['RESET']} {self.COLORS['CYAN']}{module:^12}{self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['MAGENTA']}🔄   {self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['MAGENTA']}{message}{self.COLORS['RESET']}")
    
    def log_error(self, module, message):
        # Always show errors, even in silent mode
        print(f"{self.COLORS['BLUE']}[{self.get_timestamp()}]{self.COLORS['RESET']} {self.COLORS['CYAN']}{module:^12}{self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['RED']}❌    {self.COLORS['RESET']} {self.COLORS['WHITE']}│{self.COLORS['RESET']} {self.COLORS['RED']}{message}{self.COLORS['RESET']}")

    def update_phase(self, phase, status, progress, detail=None):
        # If phase doesn't exist, create it dynamically
        if phase not in self.phase_data:
            self.phase_data[phase] = {"status": "⏳ QUEUED", "progress": 0, "detail": "Waiting to start..."}
        
        self.phase_data[phase]["status"] = status
        self.phase_data[phase]["progress"] = progress
        if detail:
            self.phase_data[phase]["detail"] = detail
        self.print_full_dashboard()

    def set_files_processed(self, count):
        """Set the number of files processed"""
        self.files_processed = count
    
    def print_footer(self, success=True):
        """Print final results with colors"""
        elapsed = time.time() - self.start_time
        
        footer = f"""
{self.COLORS['GREEN']}╔══════════════════════════════════════════════════════════════════════════╗{self.COLORS['RESET']}
{self.COLORS['GREEN']}║{self.COLORS['BOLD']}{self.COLORS['YELLOW']} ✅ OPERATION          COMPLETED SUCCESSFULLY         {self.COLORS['RESET']}{self.COLORS['GREEN']} ║{self.COLORS['RESET']}
{self.COLORS['GREEN']}╠══════════════════════════════════════════════════════════════════════════╣{self.COLORS['RESET']}
{self.COLORS['GREEN']}║{self.COLORS['CYAN']} ⏱️  Total Time: {elapsed:.2f}s {self.COLORS['WHITE']}│{self.COLORS['MAGENTA']} 📊 Files Processed: {self.files_processed} {self.COLORS['WHITE']}│{self.COLORS['YELLOW']} 🎯 Success Rate: 100% {self.COLORS['RESET']}{self.COLORS['GREEN']} ║{self.COLORS['RESET']}
{self.COLORS['GREEN']}║{self.COLORS['BOLD']}{self.COLORS['WHITE']} 💡 Next: Run 'Repack OBB' to create final PAK and OBB files            {self.COLORS['RESET']}{self.COLORS['GREEN']} ║{self.COLORS['RESET']}
{self.COLORS['GREEN']}╚══════════════════════════════════════════════════════════════════════════╝{self.COLORS['RESET']}
"""
        print(footer)

# ───── UPDATED CONFIGURATION WITH ORGANIZED FOLDER STRUCTURE ─────────────────────

# File paths - INPUT
CONTENTS_DIR = Path("contents")
INPUT_DIR = Path("input")
GAMEPAKS_DIR = INPUT_DIR / "gamepaks"
OBB_DIR = INPUT_DIR / "obb"  # OBB files are in input/obb

# File paths - OUTPUT (ORGANIZED STRUCTURE)
OUTPUT_DIR = Path("output")

# Main output subdirectories
OUTPUT_OBB = OUTPUT_DIR / "OBB"
OUTPUT_OBB_UNPACKED = OUTPUT_OBB / "unpacked" / "ShadowTrackerExtra" / "Content" / "Paks"
OUTPUT_MODSKIN = OUTPUT_DIR / "ModSkin" 
OUTPUT_HITEFFECT = OUTPUT_DIR / "HitEffect"
OUTPUT_KILLFEED = OUTPUT_DIR / "Killfeed"
OUTPUT_LOOTBOX = OUTPUT_DIR / "Lootbox"
OUTPUT_EMOTE = OUTPUT_DIR / "EmoteModder"

# Subdirectories for each mod type
OUTPUT_OBB_UNPACKED = OUTPUT_OBB / "unpacked"
OUTPUT_OBB_EDITED = OUTPUT_OBB / "edited" 
OUTPUT_OBB_REPACKED = OUTPUT_OBB / "repacked"

OUTPUT_MODSKIN_UNPACKED = OUTPUT_MODSKIN / "unpacked"
OUTPUT_MODSKIN_EDITED = OUTPUT_MODSKIN / "edited"
OUTPUT_MODSKIN_RESULTS = OUTPUT_MODSKIN / "results"

OUTPUT_HITEFFECT_UNPACKED = OUTPUT_HITEFFECT / "unpacked"
OUTPUT_HITEFFECT_EDITED = OUTPUT_HITEFFECT / "edited"
OUTPUT_HITEFFECT_RESULTS = OUTPUT_HITEFFECT / "results"

OUTPUT_KILLFEED_UNPACKED = OUTPUT_KILLFEED / "unpacked"
OUTPUT_KILLFEED_EDITED = OUTPUT_KILLFEED / "edited" 
OUTPUT_KILLFEED_RESULTS = OUTPUT_KILLFEED / "results"

OUTPUT_LOOTBOX_UNPACKED = OUTPUT_LOOTBOX / "unpacked"
OUTPUT_LOOTBOX_EDITED = OUTPUT_LOOTBOX / "edited"
OUTPUT_LOOTBOX_RESULTS = OUTPUT_LOOTBOX / "results"

OUTPUT_EMOTE_UNPACKED = OUTPUT_EMOTE / "unpacked"
OUTPUT_EMOTE_EDITED = OUTPUT_EMOTE / "edited"
OUTPUT_EMOTE_RESULTS = OUTPUT_EMOTE / "results"

OUTPUT_HEADSHOT = OUTPUT_DIR / "Headshot Modder"
OUTPUT_HEADSHOT_UNPACKED = OUTPUT_HEADSHOT / "unpacked"
OUTPUT_HEADSHOT_EDITED = OUTPUT_HEADSHOT / "edited"

# Configuration files
MODSKIN_TXT = CONTENTS_DIR / "modskin.txt"
NULL_TXT = CONTENTS_DIR / "null.txt"
CHANGELOG_TXT = OUTPUT_MODSKIN / "changelog.txt"
NULLED_LOG_TXT = OUTPUT_MODSKIN / "nulled.txt"

# Create all required directories on startup
def create_directories():
    """Create all required directories for the organized structure"""
    directories = [
        # Input directories
        OBB_DIR,
        GAMEPAKS_DIR,
        CONTENTS_DIR,
        
        # ModSkin directories
        OUTPUT_MODSKIN_UNPACKED,
        OUTPUT_MODSKIN_EDITED,
        OUTPUT_MODSKIN_RESULTS,
        
        # HitEffect directories
        OUTPUT_HITEFFECT_UNPACKED,
        OUTPUT_HITEFFECT_EDITED,
        OUTPUT_HITEFFECT_RESULTS,
        
        # Killfeed directories
        OUTPUT_KILLFEED_UNPACKED,
        OUTPUT_KILLFEED_EDITED,
        OUTPUT_KILLFEED_RESULTS,
        
        # Lootbox directories
        OUTPUT_LOOTBOX_UNPACKED,
        OUTPUT_LOOTBOX_EDITED,
        OUTPUT_LOOTBOX_RESULTS,
        
        # EmoteModder directories
        OUTPUT_EMOTE_UNPACKED,
        OUTPUT_EMOTE_EDITED,
        OUTPUT_EMOTE_RESULTS,
        
        # Headshot Modder directories
        OUTPUT_HEADSHOT_UNPACKED,
        OUTPUT_HEADSHOT_EDITED,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)
    
    print("✅ All directories created successfully!")

# Create all directories
create_directories()

# ───── CONSOLE SETUP ──────────────────────────────────────────────────────────────
# console removed for mobile

def clear_screen():
    """Clear terminal screen"""
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    """Print tool header"""
    clear_screen()
    print("=" * 70)
    print("🎮 BGMI Complete Modding Tool")
    print("📦 OBB Unpack/Repack | PAK Unpack/Repack | Skin Modding | Null Fixes")
    print("=" * 70)
    print()

def print_step(step_name, emoji="🔄"):
    """Print step header"""
    print(f"{emoji} {step_name}")

def print_success(message, emoji="✅"):
    """Print success message"""
    print(f"{emoji} {message}")

def print_error(message, emoji="❌"):
    """Print error message"""
    print(f"{emoji} {message}")

def print_info(message, emoji="ℹ️"):
    """Print info message"""
    print(f"{emoji} {message}")

def print_warning(message, emoji="⚠️"):
    """Print warning message"""
    print(f"{emoji} {message}")

def show_progress_bar(task_name, total, current):
    """Show progress bar - mobile version"""
    percentage = int((current / total) * 100) if total > 0 else 0
    print(f"{task_name}: {percentage}% ({current}/{total})")

def show_main_menu():
    """Show main menu with 3 categories"""
    print()
    print("🎯 BGMI Modding Tool - Main Menu")
    print("=" * 70)
    print("1.  📦 OBB Functions")
    print("2.  🎨 Skin Features")
    print("3.  🎯 Hack Features")
    print("4.  🧹 Cleanup - Remove temporary files")
    print("5.  ❓ Help - Display help information")
    print("0.  👋 Exit - Close the tool")
    print("=" * 70)
    print()

def show_obb_menu():
    """Show OBB Functions submenu"""
    print()
    print("📦 OBB Functions")
    print("-" * 70)
    print("1.  📥 Unpack OBB - Extract OBB to PAK files")
    print("2.  📤 Repack OBB - Create final modified OBB")
    print("0.  ⬅️  Back to Main Menu")
    print("-" * 70)
    print()

def show_skin_menu():
    """Show Skin Features submenu"""
    print()
    print("🎨 Skin Features")
    print("-" * 70)
    print("1.  🎨 Apply Mod Skin - Unpack zsdic → mod → null → repack")
    print("2.  🔫 Hit Effect - Unpack mini → mod → null → repack")
    print("3.  💀 Killfeed Modder - Unpack gamepatch → mod → repack")
    print("4.  🎁 Lootbox Modder - Unpack corepatch → mod → repack")
    print("5.  🎭 Emote Modder - Unpack gamepatch → mod → repack")
    print("6.  💰 Credit Adder - Extract 00067063.uexp")
    print("7.  🚀 Complete Workflow - Run ALL skin modders")
    print("0.  ⬅️  Back to Main Menu")
    print("-" * 70)
    print()

def show_hack_menu():
    """Show Hack Features submenu"""
    print()
    print("🎯 Hack Features")
    print("-" * 70)
    print("1.  🎯 Headshot Modder - Unpack 0026720.dat → replace → save")
    print("0.  ⬅️  Back to Main Menu")
    print("-" * 70)
    print()

def show_status_table():
    """Show status table"""
    print()
    print("📊 System Status Check")
    print("-" * 70)
    files_to_check = [
        ("📱 OBB File", INPUT_DIR.glob("*.obb"), "input/"),
        ("🎨 modskin.txt", [MODSKIN_TXT], "contents/"),
        ("🔧 null.txt", [NULL_TXT], "contents/"),
        ("📁 Output Folder", [OUTPUT_DIR], "output/")
    ]
    for name, paths, folder in files_to_check:
        exists = any(p.exists() for p in paths)
        if exists:
            print(f"✅ {name} - Ready")
        else:
            print(f"❌ {name} - Missing")
    print("💡 All files must be ready before starting workflow")
    print()

def show_file_info():
    """Show file information"""
    print()
    print("ℹ️ Help & Information")
    print("=" * 70)
    print("📁 Folder Structure:")
    print("  📂 input/ - Put your OBB files here")
    print("  📂 contents/ - Configuration files (modskin.txt, null.txt)")
    print("  📂 output/ - All outputs and temporary files")
    print()
    print("📋 Required Files:")
    print("  • 📱 OBB file in input/ folder")
    print("  • 🎨 modskin.txt in contents/ folder")
    print("  • 🔧 null.txt in contents/ folder")
    print()
    print("🚀 Quick Start:")
    print("  1. Put your OBB file in input/ folder")
    print("  2. Configure modskin.txt and null.txt in contents/")
    print("  3. Run option 12 (Complete Workflow)")
    print("  4. Get your modified OBB from output/repack_obb/")
    print()
    print("⚠️ Important: Always backup your original OBB file!")
    print()

# ───── OBB FUNCTIONS ────────────────────────────────────────────────────────────────

def unpack_obb():
    """Unpack OBB file: Extract to temp folder, then move PAK files to input/gamepaks"""
    print_step("Unpacking OBB")
    
    # Find OBB file in the obb directory
    obb_files = list(OBB_DIR.glob("*.obb"))
    if not obb_files:
        print_error(f"No OBB file found in {OBB_DIR}")
        print_info(f"Please place your OBB file in: {OBB_DIR.absolute()}")
        return False
    
    obb_path = obb_files[0]
    print_info(f"Found OBB file: {obb_path.name}")
    
    # Create temp folder in input directory
    temp_dir = INPUT_DIR / "temp"
    temp_dir.mkdir(parents=True, exist_ok=True)
    print_info(f"Created temp directory: {temp_dir}")
    
    # Ensure gamepaks directory exists
    GAMEPAKS_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Extract entire OBB to temp folder
        print_info("Extracting OBB to temp folder...")
        with zipfile.ZipFile(obb_path, 'r') as zf:
            zf.extractall(temp_dir)
        print_success("✅ OBB extracted to temp folder")
        
        # Look for specific PAK files in the extracted content
        pak_files_to_move = []
        
        # Check for mini_obb.pak
        mini_obb_files = list(temp_dir.glob("**/mini_obb.pak"))
        if mini_obb_files:
            pak_files_to_move.extend(mini_obb_files)
            print_info(f"Found mini_obb.pak: {mini_obb_files[0].relative_to(temp_dir)}")
        
        # Check for mini_obbzsdic_obb.pak
        zdsic_files = list(temp_dir.glob("**/mini_obbzsdic_obb.pak"))
        if zdsic_files:
            pak_files_to_move.extend(zdsic_files)
            print_info(f"Found mini_obbzsdic_obb.pak: {zdsic_files[0].relative_to(temp_dir)}")
        
        if not pak_files_to_move:
            print_error("No required PAK files found in extracted OBB")
            print_error("Required files: mini_obb.pak and mini_obbzsdic_obb.pak")
            # Clean up temp folder
            shutil.rmtree(temp_dir)
            return False
        
        # Move PAK files to gamepaks directory
        print_info("Moving PAK files to input/gamepaks...")
        moved_files = []
        for pak_file in pak_files_to_move:
            target_path = GAMEPAKS_DIR / pak_file.name
            shutil.copy2(pak_file, target_path)
            moved_files.append(pak_file)
            print_success(f"✅ Moved: {pak_file.name}")
        
        # Clean up temp folder by deleting individual files first
        print_info("Cleaning up temp folder...")
        try:
            # Delete the specific PAK files we moved
            for pak_file in moved_files:
                try:
                    pak_file.unlink()
                except:
                    pass
            
            # Now try to delete the temp folder
            shutil.rmtree(temp_dir)
            print_success("✅ Temp folder deleted")
        except Exception as cleanup_error:
            print_warning(f"Could not fully clean temp folder: {cleanup_error}")
            print_info("Temp folder may contain some files, but PAK files were successfully moved")
        
        print_success("✅ OBB unpacking completed!")
        print_success(f"PAK files are now available in: {GAMEPAKS_DIR.absolute()}")
        return True
        
    except Exception as e:
        print_error(f"Failed to extract OBB: {e}")
        # Clean up temp folder in case of error
        if temp_dir.exists():
            try:
                shutil.rmtree(temp_dir)
                print_info("Cleaned up temp folder after error")
            except:
                pass
        return False

def create_combined_mini_obb(hit_uexp_files, credit_uexp_file):
    """Create a combined mini_obb.pak with Hit Effect and Credit Adder modifications"""
    try:
        print_info("Creating combined mini_obb.pak with all modifications...")
        
        # Get original mini_obb.pak (use original, not modified versions)
        original_pak = None
        pak_locations = [
            GAMEPAKS_DIR / "mini_obb.pak",
            OUTPUT_OBB_UNPACKED / "ShadowTrackerExtra" / "Content" / "Paks" / "mini_obb.pak",
            Path("input") / "mini_obb.pak"
        ]
        
        for pak_path in pak_locations:
            if pak_path.exists():
                original_pak = pak_path
                print_info(f"Using original PAK as base: {pak_path}")
                break
        
        if not original_pak:
            print_error("❌ No original mini_obb.pak found to use as base")
            return None
        
        # Create combined results directory
        combined_dir = OUTPUT_DIR / "Combined" / "results"
        combined_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy original PAK to combined results
        combined_pak = combined_dir / "mini_obb.pak"
        shutil.copy2(original_pak, combined_pak)
        
        modifications_applied = 0
        
        # Collect ALL edited UEXP files from both Hit Effect and Credit Adder
        all_edited_files = []
        
        # Collect Hit Effect edited files
        hit_edited_dir = OUTPUT_HITEFFECT_EDITED
        if hit_edited_dir.exists():
            hit_uexp_files = list(hit_edited_dir.glob("*.uexp"))
            if hit_uexp_files:
                print_info(f"📁 Found Hit Effect modifications: {len(hit_uexp_files)} files")
                all_edited_files.extend(hit_uexp_files)
                modifications_applied += len(hit_uexp_files)
        
        # Collect Credit Adder edited files
        credit_edited_dir = OUTPUT_DIR / "CreditAdder" / "edited"
        if credit_edited_dir.exists():
            credit_uexp_files = list(credit_edited_dir.glob("*.uexp"))
            if credit_uexp_files:
                print_info(f"📁 Found Credit Adder modifications: {len(credit_uexp_files)} files")
                all_edited_files.extend(credit_uexp_files)
                modifications_applied += len(credit_uexp_files)
        
        if not all_edited_files:
            print_warning("⚠️ No edited UEXP files found to combine")
            print_info("📁 Combined PAK created with original file only")
            return combined_pak
        
        print_info(f"📁 Total edited UEXP files to combine: {len(all_edited_files)}")
        
        # Create a temporary directory with ALL edited files
        temp_combined_dir = OUTPUT_DIR / "Combined" / "temp_edited"
        temp_combined_dir.mkdir(parents=True, exist_ok=True)
        
        # Copy all edited files to temp directory
        for uexp_file in all_edited_files:
            temp_file = temp_combined_dir / uexp_file.name
            shutil.copy2(uexp_file, temp_file)
            print_info(f"📝 Copied {uexp_file.name} to temp directory")
        
        # Use MiniOBBUnpacker to repack with ALL modifications
        mini_unpacker = MiniOBBUnpacker()
        repack_success = mini_unpacker.repack_mini_obb(
            input_path=str(temp_combined_dir),
            output_path=str(combined_pak)
        )
        
        # Clean up temp directory
        try:
            shutil.rmtree(temp_combined_dir)
            print_info("🧹 Cleaned up temporary directory")
        except:
            pass
        
        if repack_success:
            print_success(f"✅ Combined mini_obb.pak created successfully!")
            print_success(f"📁 Combined PAK saved: {combined_pak}")
            print_info(f"📊 Total modifications applied: {modifications_applied}")
            return combined_pak
        else:
            print_error("❌ Failed to repack combined modifications")
            return None
        
    except Exception as e:
        print_error(f"❌ Failed to create combined mini_obb.pak: {e}")
        return None

def repack_obb():
    """Repack OBB with modified PAK files - Automatically combines Hit Effect and Credit Adder modifications"""
    print_step("Repack OBB - Creating Modified OBB with Combined Modifications")
    
    # Use the new directory structure
    repack_obb_dir = OUTPUT_OBB / "repacked"
    unpacked_obb_dir = OUTPUT_OBB / "unpacked"
    
    # Find original OBB in the obb directory
    obb_files = list(OBB_DIR.glob("*.obb"))
    if not obb_files:
        print_error(f"No OBB file found in {OBB_DIR}")
        print_info(f"Please place your OBB file in: {OBB_DIR.absolute()}")
        return False
    
    original_obb_path = obb_files[0]
    original_size = original_obb_path.stat().st_size
    obb_filename = original_obb_path.name
    
    # Before collecting edits, ensure lobby patch is reapplied if requested by modskin pairs
    try:
        if MODSKIN_TXT.exists():
            pairs = parse_id_pairs(MODSKIN_TXT)
            for a, b in pairs:
                if b == "202408052":
                    # Re-apply lobby patch so it overrides any subsequent Hit Modder edits
                    patch_lobby_index_in_uexp(a, b)
                    break
    except Exception:
        pass

    # Check for Hit Effect and Credit Adder modifications
    hiteffect_edited_dir = OUTPUT_HITEFFECT_EDITED
    credit_adder_edited_dir = OUTPUT_DIR / "CreditAdder" / "edited"
    modskin_results_dir = OUTPUT_MODSKIN_RESULTS
    
    mini_pak = None
    zdisc_pak = None
    
    # Check if we have Hit Effect or Credit Adder modifications
    has_hit_modifications = False
    has_credit_modifications = False
    
    # Check for Hit Effect modifications
    hit_uexp_files = list(hiteffect_edited_dir.glob("*.uexp"))
    if hit_uexp_files:
        has_hit_modifications = True
        print_info(f"Found {len(hit_uexp_files)} Hit Effect UEXP modifications")
    
    # Check for Credit Adder modifications
    credit_uexp_file = credit_adder_edited_dir / "00067063.uexp"
    if credit_uexp_file.exists():
        has_credit_modifications = True
        print_info(f"Found Credit Adder modification: {credit_uexp_file}")
    
    # If we have modifications, create a combined mini_obb.pak
    if has_hit_modifications or has_credit_modifications:
        print_step("Creating combined mini_obb.pak with all modifications")
        mini_pak = create_combined_mini_obb(hit_uexp_files, credit_uexp_file if has_credit_modifications else None)
        if not mini_pak:
            print_error("❌ Failed to create combined mini_obb.pak")
            return False
        print_info(f"✅ Using combined mini_obb.pak: {mini_pak}")
    else:
        # No modifications, use existing PAK files
        # Check ModSkin results first
        mini_pak_modskin = modskin_results_dir / "mini_obb.pak"
        if mini_pak_modskin.exists():
            mini_pak = mini_pak_modskin
            print_info(f"Found modded mini_obb.pak in ModSkin results: {mini_pak}")
        else:
            # Fallback to input/gamepaks
            mini_pak_input = GAMEPAKS_DIR / "mini_obb.pak"
            if mini_pak_input.exists():
                mini_pak = mini_pak_input
                print_info(f"Using original mini_obb.pak from input/gamepaks: {mini_pak}")
    
    # Check for ModSkin and Headshot Modder edited files - repack ZSDIC if needed
    modskin_edited_files = list(OUTPUT_MODSKIN_EDITED.glob("*.dat")) if OUTPUT_MODSKIN_EDITED.exists() else []
    headshot_edited_files = list(OUTPUT_HEADSHOT_EDITED.glob("*.dat")) if OUTPUT_HEADSHOT_EDITED.exists() else []
    
    has_zsdic_modifications = len(modskin_edited_files) > 0 or len(headshot_edited_files) > 0
    
    if has_zsdic_modifications:
        print_step("Found ModSkin/Headshot Modder edited files - Repacking ZSDIC PAK")
        if not repack_unified_zsdic():
            print_error("❌ Failed to repack ZSDIC PAK with modifications")
            return False
        print_success("✅ ZSDIC PAK repacked with all modifications")
    
    # Check ModSkin results for mini_obbzsdic_obb.pak (after repack or existing)
    zdisc_pak_modskin = modskin_results_dir / "mini_obbzsdic_obb.pak"
    if zdisc_pak_modskin.exists():
        zdisc_pak = zdisc_pak_modskin
        print_info(f"Using modded mini_obbzsdic_obb.pak from ModSkin results: {zdisc_pak}")
    else:
        # Fallback to input/gamepaks
        zdisc_pak_input = GAMEPAKS_DIR / "mini_obbzsdic_obb.pak"
        if zdisc_pak_input.exists():
            zdisc_pak = zdisc_pak_input
            print_info(f"Using original mini_obbzsdic_obb.pak from input/gamepaks: {zdisc_pak}")
    
    pak_files = []
    if mini_pak:
        pak_files.append(mini_pak)
    if zdisc_pak:
        pak_files.append(zdisc_pak)
    
    if not pak_files:
        print_error("No mini or zdisc PAK files found in ModSkin results or input/gamepaks")
        print_error("Required files: mini_obb.pak and mini_obbzsdic_obb.pak")
        print_info("Please run ModSkin modder first to create modded PAK files")
        print_info(f"Or run 'Unpack OBB' first to extract original PAK files to {GAMEPAKS_DIR}")
        return False
    
    print_info(f"Found {len(pak_files)} required PAK files (mini and zdisc only)")
    
    # Create directories
    unpacked_obb_dir.mkdir(parents=True, exist_ok=True)
    repack_obb_dir.mkdir(parents=True, exist_ok=True)
    
    # Extract original OBB
    print_info("Extracting original OBB...")
    try:
        with zipfile.ZipFile(original_obb_path, 'r') as zf:
            zf.extractall(unpacked_obb_dir)
    except Exception as e:
        print_error(f"Failed to extract original OBB: {e}")
        return False
    
    # Copy PAK files to OBB structure
    pak_folder_in_obb = Path(unpacked_obb_dir) / "ShadowTrackerExtra" / "Content" / "Paks"
    pak_folder_in_obb.mkdir(parents=True, exist_ok=True)
    
    print_info("Copying PAK files into OBB structure...")
    for pak_file in pak_files:
        dst = pak_folder_in_obb / pak_file.name
        shutil.copy2(pak_file, dst)
        print_info(f"Copied {pak_file.name}")
    
    # Create new OBB
    print_info("Creating updated OBB...")
    original_cwd = os.getcwd()
    try:
        os.chdir(unpacked_obb_dir)
        new_obb_path = obb_filename
        
        with zipfile.ZipFile(new_obb_path, 'w', compression=zipfile.ZIP_STORED) as zf:
            for root, dirs, files in os.walk('.'):
                for file in files:
                    if file == new_obb_path:
                        continue
                    file_path = Path(root) / file
                    arcname = file_path.as_posix().lstrip('./')
                    zf.write(file_path, arcname)
        
        print_success("Created updated OBB")
    finally:
        os.chdir(original_cwd)
    
    # Move to repack_obb directory
    created_obb = Path(unpacked_obb_dir) / obb_filename
    final_obb_path = Path(repack_obb_dir) / obb_filename
    
    if final_obb_path.exists():
        name_no_ext, ext = os.path.splitext(obb_filename)
        final_obb_path = Path(repack_obb_dir) / f"{name_no_ext}_mod{ext}"
    
    shutil.move(str(created_obb), str(final_obb_path))
    
    # Adjust size to match original
    actual_size = final_obb_path.stat().st_size
    if actual_size < original_size:
        with open(final_obb_path, 'ab') as f:
            f.write(b'\x00' * (original_size - actual_size))
    
    print_success(f"Repacked OBB saved: {final_obb_path}")
    print_info(f"Original size: {original_size} bytes, Final size: {final_obb_path.stat().st_size} bytes")
    
    # Validate expected size
    expected_size = 1152421602
    actual_size = final_obb_path.stat().st_size
    if actual_size == expected_size:
        print_success(f"✅ Size validation PASSED: {actual_size:,} bytes (matches expected)")
    else:
        print_warning(f"⚠️ Size validation FAILED: {actual_size:,} bytes (expected: {expected_size:,})")
        print_info(f"📏 Size difference: {actual_size - expected_size:,} bytes")
    
    return True

# ───── PAK FUNCTIONS ────────────────────────────────────────────────────────────────

class PAKTool:
    def __init__(self):
        self.DICT_MARKER = bytes.fromhex("37 A4 30 EC")
        self.DAT_MAGIC = bytes.fromhex("51 CC 56 84")
        self.XOR_KEY = 0x79
        self.DICT_SIZE = 1024 * 1024
        
        # ✅ UPDATED: Correct directories for ModSkin workflow
        self.input_dir = OBB_DIR  # OBB files from obb folder
        self.unpack_pak_dir = OUTPUT_MODSKIN_UNPACKED  # Unpacked files for ModSkin
        self.edited_dat_dir = OUTPUT_MODSKIN_EDITED    # Edited files for ModSkin
        self.results_dir = OUTPUT_MODSKIN_RESULTS      # Results directory for ModSkin
        self.tmp_dir = OUTPUT_DIR / "tmp"
        
        # Create directories
        for dir_path in [self.unpack_pak_dir, self.edited_dat_dir, self.results_dir, self.tmp_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)
        # Create the repack directory in EmoteModder results
        OUTPUT_EMOTE_RESULTS.mkdir(parents=True, exist_ok=True)
    
    def get_zsdic_pak(self):
        """Get the zsdic PAK file, check input/gamepaks first, then fallback to extraction"""
        # First check input/gamepaks directory (new primary location)
        zsdic_pak = GAMEPAKS_DIR / "mini_obbzsdic_obb.pak"
        
        if zsdic_pak.exists():
            print_info(f"Using PAK file from input/gamepaks: {zsdic_pak}")
            return zsdic_pak
        
        # Fallback to unpacked OBB directory
        unpacked_pak_dir = OUTPUT_OBB_UNPACKED / "ShadowTrackerExtra" / "Content" / "Paks"
        zsdic_pak = unpacked_pak_dir / "mini_obbzsdic_obb.pak"
        
        if zsdic_pak.exists():
            print_info(f"Using PAK file from unpacked OBB: {zsdic_pak}")
            return zsdic_pak
        
        # Fallback to tmp directory
        zsdic_pak = self.tmp_dir / "zsdic.pak"
        if zsdic_pak.exists():
            print_info(f"Using existing PAK file: {zsdic_pak}")
            return zsdic_pak
        else:
            print_info("PAK file not found, extracting from OBB...")
            obb_path = self.find_obb_file()  # ✅ This will now look in OBB_DIR
            return self.extract_pak_from_obb(obb_path)
    
    def find_obb_file(self):
        """Find OBB file in OBB directory"""
        obb_files = list(self.input_dir.glob("*.obb"))  # ✅ Now looks in OBB_DIR
        if not obb_files:
            raise FileNotFoundError(f"No OBB file found in {self.input_dir}")
        return obb_files[0]
    
    
    def find_obb_file(self):
        """Find OBB file in OBB directory"""
        # Look in the OBB directory first (new structure)
        obb_files = list(OBB_DIR.glob("*.obb"))
        if not obb_files:
            # Fallback to input directory (old structure)
            obb_files = list(self.input_dir.glob("*.obb"))
            if not obb_files:
                raise FileNotFoundError(f"No OBB file found in {OBB_DIR} or {self.input_dir}")
        return obb_files[0]
    
    def extract_pak_from_obb(self, obb_path):
        """Extract PAK file from OBB archive"""
        print_info(f"Extracting PAK from {obb_path}")
        
        # Create a copy with .zip extension for extraction
        zip_path = obb_path.with_suffix('.zip')
        shutil.copy2(obb_path, zip_path)
        
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                
                # Extract ZIP file
                with zipfile.ZipFile(zip_path, 'r') as zip_ref:
                    zip_ref.extractall(temp_path)
                
                # Find PAK file
                pak_files = list(temp_path.rglob("*mini_obbzsdic_obb.pak"))
                if not pak_files:
                    pak_files = list(temp_path.rglob("*.pak"))
                    if not pak_files:
                        raise FileNotFoundError("No PAK file found in OBB")
                
                pak_file = pak_files[0]
                print_info(f"Found PAK file: {pak_file}")
                
                # Copy PAK file to tmp directory
                zsdic_pak = self.tmp_dir / "zsdic.pak"
                shutil.copy2(pak_file, zsdic_pak)
                print_success(f"PAK file saved to: {zsdic_pak}")
                
                return zsdic_pak
        finally:
            # Clean up ZIP file (ensure it's closed first)
            try:
                if zip_path.exists():
                    zip_path.unlink()
            except Exception as e:
                print_info(f"Note: Could not delete temporary ZIP file: {e}")
    
    def find_dictionary(self, pak_data):
        """Find and extract dictionary from PAK file"""
        dict_pos = pak_data.find(self.DICT_MARKER)
        if dict_pos == -1:
            raise ValueError("Dictionary marker not found in PAK file")
        
        print_info(f"Dictionary found at position: {dict_pos}")
        
        # Extract exactly 1MB dictionary
        dictionary = pak_data[dict_pos:dict_pos + self.DICT_SIZE]
        
        if len(dictionary) < self.DICT_SIZE:
            print_info(f"Warning: Dictionary is only {len(dictionary)} bytes, expected {self.DICT_SIZE}")
        else:
            print_success(f"Dictionary extracted: {len(dictionary)} bytes")
        
        return dictionary, dict_pos
    
    def find_dat_files(self, pak_data, dict_pos):
        """Find all DAT files before dictionary position"""
        dat_files = []
        pos = 0
        
        while pos < dict_pos:
            magic_pos = pak_data.find(self.DAT_MAGIC, pos)
            if magic_pos == -1 or magic_pos >= dict_pos:
                break
            
            # Find next DAT file or dictionary to determine size
            next_magic = pak_data.find(self.DAT_MAGIC, magic_pos + 4)
            if next_magic == -1 or next_magic >= dict_pos:
                dat_size = dict_pos - magic_pos
            else:
                dat_size = next_magic - magic_pos
            
            dat_data = pak_data[magic_pos:magic_pos + dat_size]
            dat_files.append({
                'index': len(dat_files),
                'position': magic_pos,
                'size': dat_size,
                'data': dat_data
            })
            
            pos = magic_pos + 4
        
        print_info(f"Found {len(dat_files)} DAT files")
        return dat_files
    
    def xor_decrypt(self, data):
        """XOR decrypt data with key 0x79"""
        return bytes(b ^ self.XOR_KEY for b in data)
    
    def decompress_dat(self, dat_data_with_magic, dictionary):
        """Decrypt and decompress DAT file"""
        # Decrypt (including magic header)
        decrypted = self.xor_decrypt(dat_data_with_magic)
        
        d = zstd.ZstdDecompressor(dict_data=zstd.ZstdCompressionDict(dictionary))
        decompressed = b''
        reader = d.stream_reader(decrypted)
        try:
            while True:
                chunk = reader.read(65536)
                if not chunk:
                    break
                decompressed += chunk
        except zstd.ZstdError:
            pass
        finally:
            reader.close()
        return decompressed
    
    def unpack(self):
        """Unpack PAK file"""
        print_step("Unpacking PAK")
        
        # Get zsdic PAK file
        pak_path = self.get_zsdic_pak()
        
        # Read PAK file
        with open(pak_path, 'rb') as f:
            pak_data = f.read()
        
        # Find dictionary
        dictionary, dict_pos = self.find_dictionary(pak_data)
        
        # Save dictionary to tmp folder
        dict_file = self.tmp_dir / "dictionary.bin"
        with open(dict_file, 'wb') as f:
            f.write(dictionary)
        print_info(f"Dictionary saved to: {dict_file}")
        
        # Find DAT files
        dat_files = self.find_dat_files(pak_data, dict_pos)
        
        # Define required files (only these will be kept)
        required_files = {
            "0028723.dat", "0028724.dat", "0028725.dat", "0028726.dat", "0029200.dat",
            "0029402.dat", "0029403.dat", "0029404.dat", "0029405.dat", "0029406.dat", 
            "0029407.dat", "0029411.dat", "0029412.dat", "0029660.dat", "0029661.dat",
            "0029662.dat", "0029663.dat", "0029664.dat", "0029665.dat", "0029669.dat",
            "0029670.dat", "0029671.dat", "0029672.dat", "0029414.dat", "0029413.dat", 
            "0031362.dat"
        }
        
        print_info(f"Will keep only {len(required_files)} required files out of {len(dat_files)} total files")
        
        # Process DAT files
        successful_count = 0
        kept_count = 0
        
        for i, dat_info in enumerate(dat_files):
            dat_filename = f"{i+1:07d}.dat"
            
            # Check if this file is required
            if dat_filename not in required_files:
                continue  # Skip this file
            
            print_info(f"Processing DAT {dat_filename} (size: {dat_info['size']} bytes)")
            
            dat_data = dat_info['data']
            
            # Decompress
            decompressed = self.decompress_dat(dat_data, dictionary)
            
            # Create file, even if empty
            output_file = self.unpack_pak_dir / dat_filename
            with open(output_file, 'wb') as f:
                f.write(decompressed if decompressed else b'')
            
            if decompressed:
                print_success(f"Saved: {output_file} ({len(decompressed)} bytes)")
                successful_count += 1
            else:
                print_info(f"Created empty file: {output_file}")
                successful_count += 1
            
            kept_count += 1
        
        print_success(f"Successfully processed {successful_count} files")
        print_info(f"Kept only {kept_count} required files out of {len(dat_files)} total files")
        print_info(f"Deleted {len(dat_files) - kept_count} unnecessary files")
        
        return True
    
    def repack(self):
        """Repack edited files back into PAK"""
        print_step("Repacking PAK")
        
        # Get zsdic PAK file
        pak_path = self.get_zsdic_pak()
        
        # Read original PAK file
        with open(pak_path, 'rb') as f:
            pak_data = bytearray(f.read())
        
        # Find dictionary
        dictionary, dict_pos = self.find_dictionary(pak_data)
        
        # Find original DAT files
        dat_files = self.find_dat_files(pak_data, dict_pos)
        
        # Process edited files
        edited_files = list(self.edited_dat_dir.glob("*.dat"))
        
        if not edited_files:
            print_error("No DAT files found in 'edited_dat' directory")
            return False
        
        print_info(f"Found {len(edited_files)} edited files to repack")
        
        successful_repacks = 0
        failed_repacks = 0
        
        for edited_file in edited_files:
            # Extract index from filename
            filename = edited_file.stem
            try:
                dat_number = int(filename.lstrip('0')) if filename != '0000000' else 0
                dat_index = dat_number - 1
            except ValueError:
                print_error(f"Invalid filename format: {edited_file}")
                continue
            
            if dat_index < 0 or dat_index >= len(dat_files):
                print_error(f"DAT index {dat_index} out of range (file: {edited_file})")
                continue
            
            print_info(f"Repacking DAT {dat_number:07d} (index {dat_index})")
            
            # Read edited file
            with open(edited_file, 'rb') as f:
                edited_data = f.read()
            
            # Get original DAT info
            original_dat = dat_files[dat_index]
            original_size = original_dat['size']
            required_size = original_size - 4  # Size minus checksum
            
            # Extract checksum from original
            checksum = original_dat['data'][-4:]
            
            # Compress edited data
            compressed_data = None
            dict_obj = zstd.ZstdCompressionDict(dictionary)
            
            print_info(f"Testing compression levels to fit {required_size} bytes...")
            for level in range(1, 23):
                try:
                    cctx = zstd.ZstdCompressor(level=level, dict_data=dict_obj)
                    test_compressed = cctx.compress(edited_data)
                    
                    if len(test_compressed) <= required_size:
                        compressed_data = test_compressed
                        print_success(f"Compressed with level {level}")
                        break
                    else:
                        print_info(f"Level {level}: too large")
                    
                except Exception:
                    continue
            
            if compressed_data is None:
                print_error(f"Could not compress DAT {dat_number:07d} to fit in {required_size} bytes")
                failed_repacks += 1
                continue
            
            print_info(f"Compressed data size: {len(compressed_data)} bytes")
            
            # Create new DAT block
            new_dat_block = bytearray(compressed_data)
            
            # Pad with null bytes if needed
            if len(compressed_data) < required_size:
                padding_needed = required_size - len(compressed_data)
                new_dat_block.extend(b'\x00' * padding_needed)
            
            # XOR encrypt
            xor_encrypted_data = self.xor_decrypt(new_dat_block)
            new_dat_block = bytearray(xor_encrypted_data)
            
            # Add checksum
            new_dat_block.extend(checksum)
            
            # Ensure correct size
            if len(new_dat_block) != original_size:
                print_error(f"Size mismatch - original: {original_size}, new: {len(new_dat_block)}")
                failed_repacks += 1
                continue
            
            # Replace in PAK data
            start_pos = original_dat['position']
            end_pos = start_pos + original_dat['size']
            pak_data[start_pos:end_pos] = new_dat_block
            
            print_success(f"Replaced DAT {dat_number:07d} in PAK file")
            successful_repacks += 1
        
        # Save repacked PAK to ModSkin results
        pak_filename = "mini_obbzsdic_obb.pak"
        repacked_pak_path = OUTPUT_MODSKIN_RESULTS / pak_filename
        
        # Ensure the directory exists
        repacked_pak_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(repacked_pak_path, 'wb') as f:
            f.write(pak_data)
        
        print_success(f"✅ Repacked PAK saved to: {repacked_pak_path}")
        
        # Print summary
        print_info(f"Repack Summary:")
        print_info(f"  Successfully repacked: {successful_repacks} files")
        print_info(f"  Failed to repack: {failed_repacks} files")
        print_info(f"  Total processed: {successful_repacks + failed_repacks} files")
        
        return successful_repacks > 0

def repack_unified_zsdic():
    """
    Unified repack function that combines ModSkin and Headshot Modder edited files.
    Prevents double repacking and ensures compatibility between both systems.
    """
    print_step("Unified ZSDIC Repack - Combining ModSkin and Headshot Modder")
    
    # Initialize PAKTool
    pak_tool = PAKTool()
    
    # Get zsdic PAK file
    pak_path = pak_tool.get_zsdic_pak()
    if not pak_path or not pak_path.exists():
        print_error("Failed to find mini_obbzsdic_obb.pak file")
        return False
    
    # Read original PAK file
    with open(pak_path, 'rb') as f:
        pak_data = bytearray(f.read())
    
    # Find dictionary
    dictionary, dict_pos = pak_tool.find_dictionary(pak_data)
    
    # Find original DAT files
    dat_files = pak_tool.find_dat_files(pak_data, dict_pos)
    
    # Collect edited files from both sources
    modskin_edited_files = list(OUTPUT_MODSKIN_EDITED.glob("*.dat")) if OUTPUT_MODSKIN_EDITED.exists() else []
    headshot_edited_files = list(OUTPUT_HEADSHOT_EDITED.glob("*.dat")) if OUTPUT_HEADSHOT_EDITED.exists() else []
    
    # Check if any edited files exist
    if not modskin_edited_files and not headshot_edited_files:
        print_error("No edited DAT files found from ModSkin or Headshot Modder")
        return False
    
    # Combine files with Headshot Modder taking precedence for 0026720.dat
    combined_files = {}
    
    # First, add all ModSkin edited files
    for edited_file in modskin_edited_files:
        filename = edited_file.name
        combined_files[filename] = edited_file
        print_info(f"  Added from ModSkin: {filename}")
    
    # Then, add/overwrite with Headshot Modder files (takes precedence)
    for edited_file in headshot_edited_files:
        filename = edited_file.name
        if filename in combined_files:
            print_info(f"  Overwriting with Headshot Modder: {filename}")
        else:
            print_info(f"  Added from Headshot Modder: {filename}")
        combined_files[filename] = edited_file
    
    print_info(f"Total files to repack: {len(combined_files)}")
    print_info(f"  - From ModSkin: {len(modskin_edited_files)}")
    print_info(f"  - From Headshot Modder: {len(headshot_edited_files)}")
    
    # Validate that we have files to repack
    if not combined_files:
        print_error("No valid edited files to repack")
        return False
    
    # Repack process
    successful_repacks = 0
    failed_repacks = 0
    
    for filename, edited_file in combined_files.items():
        # Extract index from filename (same logic as original PAKTool.repack)
        try:
            # Use stem (filename without extension) like original
            filename_stem = edited_file.stem
            dat_number = int(filename_stem.lstrip('0')) if filename_stem != '0000000' else 0
            dat_index = dat_number - 1
        except ValueError:
            print_error(f"Invalid filename format: {filename}")
            failed_repacks += 1
            continue
        
        if dat_index < 0 or dat_index >= len(dat_files):
            print_error(f"DAT index {dat_index} out of range (file: {filename})")
            failed_repacks += 1
            continue
        
        print_info(f"Repacking DAT {dat_number:07d} (index {dat_index})")
        
        # Read edited file
        try:
            with open(edited_file, 'rb') as f:
                edited_data = f.read()
        except Exception as e:
            print_error(f"Failed to read edited file {filename}: {e}")
            failed_repacks += 1
            continue
        
        # Get original DAT info
        original_dat = dat_files[dat_index]
        original_size = original_dat['size']
        required_size = original_size - 4  # Size minus checksum
        
        # Extract checksum from original
        checksum = original_dat['data'][-4:]
        
        # Compress edited data
        compressed_data = None
        dict_obj = zstd.ZstdCompressionDict(dictionary)
        
        print_info(f"Testing compression levels to fit {required_size} bytes...")
        for level in range(1, 23):
            try:
                cctx = zstd.ZstdCompressor(level=level, dict_data=dict_obj)
                test_compressed = cctx.compress(edited_data)
                
                if len(test_compressed) <= required_size:
                    compressed_data = test_compressed
                    print_success(f"Compressed with level {level}")
                    break
                else:
                    print_info(f"Level {level}: too large")
                    
            except Exception:
                continue
        
        if compressed_data is None:
            print_error(f"Could not compress DAT {dat_number:07d} to fit in {required_size} bytes")
            failed_repacks += 1
            continue
        
        print_info(f"Compressed data size: {len(compressed_data)} bytes")
        
        # Create new DAT block
        new_dat_block = bytearray(compressed_data)
        
        # Pad with null bytes if needed
        if len(compressed_data) < required_size:
            padding_needed = required_size - len(compressed_data)
            new_dat_block.extend(b'\x00' * padding_needed)
        
        # XOR encrypt
        xor_encrypted_data = pak_tool.xor_decrypt(new_dat_block)
        new_dat_block = bytearray(xor_encrypted_data)
        
        # Add checksum
        new_dat_block.extend(checksum)
        
        # Ensure correct size
        if len(new_dat_block) != original_size:
            print_error(f"  Size mismatch - original: {original_size}, new: {len(new_dat_block)}")
            failed_repacks += 1
            continue
        
        # Replace in PAK data
        start_pos = original_dat['position']
        end_pos = start_pos + original_dat['size']
        pak_data[start_pos:end_pos] = new_dat_block
        
        print_success(f"Replaced DAT {dat_number:07d} in PAK file")
        successful_repacks += 1
    
    # Save repacked PAK to unified results location
    pak_filename = "mini_obbzsdic_obb.pak"
    repacked_pak_path = OUTPUT_MODSKIN_RESULTS / pak_filename
    
    # Ensure the directory exists
    repacked_pak_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the repacked PAK
    with open(repacked_pak_path, 'wb') as f:
        f.write(pak_data)
    
    print_success(f"✅ Unified repacked PAK saved to: {repacked_pak_path}")
    
    # Print summary
    print_info(f"Repack Summary:")
    print_info(f"  Successfully repacked: {successful_repacks} files")
    print_info(f"  Failed to repack: {failed_repacks} files")
    print_info(f"  Total processed: {successful_repacks + failed_repacks} files")
    
    if successful_repacks == 0:
        print_error("No files were successfully repacked")
        return False
    
    return True

# ───── CREDIT ADDER FUNCTIONALITY ──────────────────────────────────────────────────

class CreditAdder:
    """Credit Adder - Extract and edit specific UEXP file from mini_obb.pak"""
    
    def __init__(self):
        self.unpacker = MiniOBBUnpacker()
        self.target_index = 67063  # Index for 00067063.uexp
        
        # ✅ UPDATED: Organized folder structure (no results needed)
        self.unpack_dir = OUTPUT_DIR / "CreditAdder" / "unpacked"
        self.edited_dir = OUTPUT_DIR / "CreditAdder" / "edited"
        
        # Credit text file
        self.credit_file = CONTENTS_DIR / "credit.txt"
        
        # Create directories (only unpack and edited)
        for d in [self.unpack_dir, self.edited_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def extract_credit_uexp(self):
        """Extract 00067063.uexp from mini_obb.pak and replace disclaimer with custom text"""
        print_step("Credit Adder - Extracting and Modifying 00067063.uexp")
        
        try:
            # Get mini_obb.pak file
            pak_path = self.get_mini_obb_pak()
            if not pak_path:
                return False
            
            # Extract the specific UEXP file to unpacked directory
            success = self.unpacker.unpack_mini_obb(
                pak_path=str(pak_path),
                output_path=str(self.unpack_dir),
                target_index=self.target_index
            )
            
            if success:
                extracted_file = self.unpack_dir / f"{self.target_index:08d}.uexp"
                if extracted_file.exists():
                    print_success(f"✅ Credit UEXP extracted successfully!")
                    print_success(f"📁 File saved: {extracted_file}")
                    print_info(f"📊 File size: {extracted_file.stat().st_size:,} bytes")
                    
                    # Copy to edited directory
                    edited_file = self.edited_dir / f"{self.target_index:08d}.uexp"
                    shutil.copy2(extracted_file, edited_file)
                    print_info(f"📝 Copy created for editing: {edited_file}")
                    
                    # Read custom credit text
                    custom_text = self.read_credit_text()
                    if custom_text:
                        # Replace disclaimer with custom text
                        print_step("Credit Adder - Replacing Disclaimer Text")
                        replace_success = self.replace_disclaimer_text(str(edited_file), custom_text)
                        if replace_success:
                            print_success(f"✅ Disclaimer replaced with custom text!")
                        else:
                            print_warning("⚠️ Disclaimer replacement failed, but file is ready for manual editing")
                    else:
                        print_warning("⚠️ No custom text found, file ready for manual editing")
                    
                    # Credit Adder now only creates edited UEXP files
                    # The repack_obb function will automatically combine them
                    print_success("✅ Credit Adder UEXP file created successfully!")
                    print_info("📁 Edited UEXP file saved to: output/CreditAdder/edited/")
                    print_info("🔄 Use 'Repack OBB' to create final PAK with all modifications")
                    return True
                else:
                    print_error("❌ File extraction failed - file not found")
                    return False
            else:
                print_error("❌ Failed to extract UEXP file")
                return False
                
        except Exception as e:
            print_error(f"❌ Credit Adder failed: {e}")
            return False
    
    def read_credit_text(self):
        """Read custom credit text from credit.txt"""
        try:
            if not self.credit_file.exists():
                print_error(f"❌ Credit file not found: {self.credit_file}")
                print_info("Please create contents/credit.txt with your custom text")
                return None
            
            with open(self.credit_file, 'r', encoding='utf-8') as f:
                credit_text = f.read().strip()
            
            if not credit_text:
                print_error("❌ Credit file is empty!")
                return None
            
            print_info(f"📝 Custom credit text: {credit_text}")
            return credit_text
            
        except Exception as e:
            print_error(f"❌ Failed to read credit text: {e}")
            return None
    
    def replace_disclaimer_text(self, uexp_file_path, custom_text):
        """Replace BGMI disclaimer with custom text in UEXP file - PRESERVES FILE SIZE"""
        try:
            # Read the UEXP file
            with open(uexp_file_path, 'rb') as f:
                data = f.read()
            
            # Original disclaimer text
            original_text = "Battlegrounds Mobile India is not a real-world based game. It is a survival simulation game set in a virtual world."
            
            # Convert texts to bytes
            original_bytes = original_text.encode('utf-8')
            custom_bytes = custom_text.encode('utf-8')
            
            # Find and replace the text with SIZE PRESERVATION (like cr file)
            if original_bytes in data:
                # Replace with null padding to preserve file size
                modified_data = data.replace(original_bytes, custom_bytes.ljust(len(original_bytes), b'\x00'))
                
                # Write back to file
                with open(uexp_file_path, 'wb') as f:
                    f.write(modified_data)
                
                print_success(f"✅ Disclaimer replaced successfully!")
                print_info(f"📝 Original: {original_text}")
                print_info(f"📝 Custom: {custom_text}")
                print_info(f"📏 Size preserved: {len(original_bytes)} bytes")
                return True
            else:
                print_warning("⚠️ Disclaimer text not found in UEXP file")
                print_info("The file might already be modified or have different content")
                return False
                
        except Exception as e:
            print_error(f"❌ Failed to replace disclaimer: {e}")
            return False
    
    def get_mini_obb_pak(self):
        """Get mini_obb.pak file from various locations"""
        # Check input/gamepaks first
        pak_file = GAMEPAKS_DIR / "mini_obb.pak"
        if pak_file.exists():
            print_info(f"Using PAK file from input/gamepaks: {pak_file}")
            return pak_file
        
        # Check HitEffect results
        pak_file = OUTPUT_HITEFFECT_RESULTS / "mini_obb.pak"
        if pak_file.exists():
            print_info(f"Using PAK file from HitEffect results: {pak_file}")
            return pak_file
        
        # Check ModSkin results
        pak_file = OUTPUT_MODSKIN_RESULTS / "mini_obb.pak"
        if pak_file.exists():
            print_info(f"Using PAK file from ModSkin results: {pak_file}")
            return pak_file
        
        # Check OBB unpacked directory
        pak_file = OUTPUT_OBB_UNPACKED / "ShadowTrackerExtra" / "Content" / "Paks" / "mini_obb.pak"
        if pak_file.exists():
            print_info(f"Using PAK file from OBB unpacked: {pak_file}")
            return pak_file
        
        # Check input directory
        pak_file = Path("input") / "mini_obb.pak"
        if pak_file.exists():
            print_info(f"Using PAK file from input: {pak_file}")
            return pak_file
        
        print_error("❌ mini_obb.pak not found in any location!")
        print_info("Please ensure mini_obb.pak is available in one of these locations:")
        print_info(f"  - {GAMEPAKS_DIR}")
        print_info(f"  - {OUTPUT_HITEFFECT_RESULTS}")
        print_info(f"  - {OUTPUT_MODSKIN_RESULTS}")
        print_info(f"  - {OUTPUT_OBB_UNPACKED / 'ShadowTrackerExtra' / 'Content' / 'Paks'}")
        print_info(f"  - input/")
        return None
    
    def repack_credit_uexp(self):
        """Repack edited UEXP file back into mini_obb.pak"""
        print_step("Credit Adder - Repacking edited UEXP")
        
        try:
            # Check if edited file exists
            edited_file = self.edited_dir / f"{self.target_index:08d}.uexp"
            if not edited_file.exists():
                print_error(f"❌ Edited file not found: {edited_file}")
                print_info("Please edit the file in the edited directory first")
                return False
            
            # Get original PAK file
            pak_path = self.get_mini_obb_pak()
            if not pak_path:
                return False
            
            # Use MiniOBBUnpacker to repack
            success = self.unpacker.repack_mini_obb(
                input_path=str(self.edited_dir),
                output_path=str(self.results_dir / "mini_obb.pak")
            )
            
            if success:
                result_file = self.results_dir / "mini_obb.pak"
                if result_file.exists():
                    print_success(f"✅ Credit UEXP repacked successfully!")
                    print_success(f"📁 Modified PAK saved: {result_file}")
                    print_info(f"📊 File size: {result_file.stat().st_size:,} bytes")
                    return True
                else:
                    print_error("❌ Repack failed - output file not found")
                    return False
            else:
                print_error("❌ Failed to repack UEXP file")
                return False
                
        except Exception as e:
            print_error(f"❌ Credit Adder repack failed: {e}")
            return False

# ───── SKIN MODDING FUNCTIONS ──────────────────────────────────────────────────────

def parse_id_pairs(txt_path):
    """Parse ID pairs from modskin.txt with multi-encoding support"""
    pairs = []
    
    # Try multiple encodings
    encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
    file_content = None
    
    for enc in encodings:
        try:
            with open(txt_path, encoding=enc) as f:
                file_content = f.read()
            break
        except (UnicodeDecodeError, UnicodeError):
            continue
    
    if not file_content:
        return pairs
    
    for line_num, line in enumerate(file_content.splitlines(), 1):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Try comma separation first
        if ',' in line:
            parts = line.split(',', 1)
            if len(parts) == 2:
                a, b = parts[0].strip(), parts[1].strip()
                if a and b:
                    pairs.append((a, b))
                    continue
        
        # Try space separation
        parts = line.split()
        if len(parts) == 2:
            a, b = parts[0].strip(), parts[1].strip()
            if a and b:
                pairs.append((a, b))
                continue
        
        # Silently skip invalid lines - no log output
    
    return pairs

def build_safe_pattern(ascii_id: bytes):
    """Build safe regex pattern for ID matching"""
    return re.compile(rb"(?<![0-9])" + re.escape(ascii_id) + rb"(?![0-9])")

def pad_pattern(src: bytes, target_len: int) -> bytes:
    """Pad pattern to target length"""
    cur = bytearray(src)
    to_insert = target_len - len(cur)
    idx = cur.find(0x00)
    if idx < 0:
        cur.extend(b'\x00' * to_insert)
    else:
        for _ in range(to_insert):
            cur.insert(idx, 0x00)
    return bytes(cur)

def truncate_pattern(src: bytes, target_len: int) -> bytes:
    """Truncate pattern to target length"""
    cur = bytearray(src)
    to_remove = len(cur) - target_len
    while to_remove > 0:
        idx = cur.find(0x00)
        if idx < 0:
            break
        del cur[idx]
        to_remove -= 1
    if to_remove > 0:
        del cur[-to_remove:]
    return bytes(cur)

def mod_skin():
    """Apply skin modifications - FULLY AUTOMATED"""
    # Initialize logger in silent mode - only dashboard, no text logs
    logger = ColorfulConsoleLogger(silent_mode=True)
    logger.print_full_dashboard()
    
    # Step 1: Auto unpack mini_obbzsdic_obb.pak
    logger.update_phase("UNPACK", "🔄 ACTIVE", 0, "Unpacking mini_obbzsdic_obb.pak...")
    
    # Suppress PAKTool print outputs
    import sys
    old_stdout = sys.stdout
    old_stderr = sys.stderr
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    
    try:
        pak_tool = PAKTool()
        pak_path = pak_tool.get_zsdic_pak()
        with open(pak_path, 'rb') as f:
            pak_data = f.read()
        dictionary, dict_pos = pak_tool.find_dictionary(pak_data)
        unpack_result = pak_tool.unpack()
    except Exception as e:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        logger.update_phase("UNPACK", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
        return False
    finally:
        sys.stdout.close()
        sys.stderr.close()
        sys.stdout = old_stdout
        sys.stderr = old_stderr
    
    if not unpack_result:
        logger.update_phase("UNPACK", "❌ FAILED", 0, "Unpacking failed")
        return False
    
    # ✅ UPDATED: Use new directory structure
    unpack_pak_dir = OUTPUT_MODSKIN_UNPACKED
    edited_dat_dir = OUTPUT_MODSKIN_EDITED
    txt_path = MODSKIN_TXT
    changelog_path = CHANGELOG_TXT
    
    # Find DAT files and update progress
    dat_files = pak_tool.find_dat_files(pak_data, dict_pos)
    
    # Count kept files
    required_files = {
        "0028723.dat", "0028724.dat", "0028725.dat", "0028726.dat", "0029200.dat",
        "0029402.dat", "0029403.dat", "0029404.dat", "0029405.dat", "0029406.dat", 
        "0029407.dat", "0029411.dat", "0029412.dat", "0029660.dat", "0029661.dat",
        "0029662.dat", "0029663.dat", "0029664.dat", "0029665.dat", "0029669.dat",
        "0029670.dat", "0029671.dat", "0029672.dat", "0029414.dat", "0029413.dat", 
        "0031362.dat"
    }
    total_files = len(dat_files)
    kept_count = sum(1 for i in range(len(dat_files)) if f"{(i+1):07d}.dat" in required_files)
    
    # Update unpack progress with real counts
    logger.update_phase("UNPACK", "🔄 ACTIVE", 50, f"Found {total_files} files, keeping {kept_count}...")
    
    logger.update_phase("UNPACK", "✅ DONE", 100, f"{kept_count}/{total_files} files kept")
            
    if not txt_path.exists():
        logger.update_phase("MOD_APPLY", "❌ FAILED", 0, f"{MODSKIN_TXT.name} missing")
        return False
    
    # Parse ID pairs
    pairs = parse_id_pairs(txt_path)
    if not pairs:
        logger.update_phase("MOD_APPLY", "❌ FAILED", 0, "No valid ID pairs found")
        return False
    
    # Get files to process
    all_files = []
    if not unpack_pak_dir.exists():
        logger.update_phase("MOD_APPLY", "❌ FAILED", 0, "Unpack directory not found")
        return False
    
    for fn in unpack_pak_dir.glob("*.dat"):
        if fn.is_file():
            all_files.append(fn)
    
    # Limit files for faster processing
    all_files = sorted(all_files)[:100]
    
    if not all_files:
        return False
    
    # Step 2: Mod Applications
    logger.update_phase("MOD_APPLY", "🔄 ACTIVE", 0, f"{len(pairs)} ID pairs → {len(all_files)} files")
    # Removed individual log - only dashboard updates
    
    # Build longhex map
    cache = {p: open(p, 'rb').read() for p in all_files}
    longhex_map = {}
    
    for id1, id2 in pairs:
        a1, a2 = id1.encode(), id2.encode()
        p1, p2 = build_safe_pattern(a1), build_safe_pattern(a2)
        pos1, pos2, d1, d2 = None, None, b"", b""
        
        for data in cache.values():
            if pos1 is None and (m := p1.search(data)):
                pos1, d1 = m.start(), data
            if pos2 is None and (m := p2.search(data)):
                pos2, d2 = m.start(), data
            if pos1 is not None and pos2 is not None:
                break
        
        if pos1 is None or pos2 is None:
            continue
        
        lh1 = a1 + d1[pos1 + len(a1):pos1 + len(a1) + 5]
        lh2 = a2 + d2[pos2 + len(a2):pos2 + len(a2) + 5]
        
        if len(lh1) == len(lh2):
            swaps = [(lh1, lh2), (lh2, lh1)]
        elif len(lh1) > len(lh2):
            swaps = [(lh1, pad_pattern(lh2, len(lh1))), (lh2, truncate_pattern(lh1, len(lh2)))]
        else:
            swaps = [(lh2, pad_pattern(lh1, len(lh2))), (lh1, truncate_pattern(lh2, len(lh1)))]
        
        longhex_map[(id1, id2)] = swaps
    
    if not longhex_map:
        logger.update_phase("MOD_APPLY", "❌ FAILED", 0, "No longhex pairs found")
        return False
    
    logger.update_phase("MOD_APPLY", "🔄 ACTIVE", 20, f"{len(longhex_map)} longhex pairs → Scanning files...")
    
    # Find valid files
    patterns = [re.compile(rb"(?<![0-9])" + re.escape(src) + rb"(?![0-9])") 
                for swaps in longhex_map.values() for src, _ in swaps]
    valid_files = [p for p, data in cache.items() if any(rx.search(data) for rx in patterns)]
    
    if not valid_files:
        logger.update_phase("MOD_APPLY", "❌ FAILED", 0, "No files contain patterns")
        return False
    
    logger.update_phase("MOD_APPLY", "🔄 ACTIVE", 40, f"{len(valid_files)} files contain patterns")
    
    # Create edited_dat directory
    if edited_dat_dir.exists():
        shutil.rmtree(edited_dat_dir)
    edited_dat_dir.mkdir(exist_ok=True)
    
    # Copy files to edited_dat (silently - no logs)
    for src in sorted(valid_files):
        shutil.copy2(src, edited_dat_dir)
    
    # Apply modifications
    changelog_simple = []
    modified_count = 0
    
    for idx, src in enumerate(sorted(valid_files)):
        filename = src.name
        # Removed individual file processing logs - only dashboard updates
        
        edited_dat_path = edited_dat_dir / filename
        orig = open(edited_dat_path, 'rb').read()
        new = bytearray(orig)
        
        for pair, swaps in longhex_map.items():
            for src_pat, dst_pat in swaps:
                rx = re.compile(rb"(?<![0-9])" + re.escape(src_pat) + rb"(?![0-9])")
                matches = list(rx.finditer(orig))
                if not matches:
                    continue
                
                for m in matches:
                    new[m.start():m.start() + len(src_pat)] = dst_pat
                    changelog_simple.append((filename, pair, src_pat.hex(), dst_pat.hex()))
        
        if new != orig:
            with open(edited_dat_path, 'wb') as f:
                f.write(new)
            modified_count += 1
        
        # Update progress (update more frequently for smoother dashboard)
        if (idx + 1) % 3 == 0 or (idx + 1) == len(valid_files):
            progress = int(((idx + 1) / len(valid_files)) * 100)
            logger.update_phase("MOD_APPLY", "🔄 ACTIVE", progress, f"{modified_count} files modified")
    
    # Write changelog
    with open(changelog_path, 'w', encoding='utf-8') as f:
        for filename, pair, frm, to in changelog_simple:
            f.write(f"ID PAIR : {pair[0]} {pair[1]}\n")
            f.write(f"FILE : {filename}\n")
            f.write(f"CHANGES : APPLIED LONGHEX {frm} -> {to}\n")
            f.write("\n")
    
    logger.update_phase("MOD_APPLY", "✅ DONE", 100, f"{modified_count} files modified")
    
    # Step 3: Automatically run size fix after skin mods
    # Count files that need size fixing
    files_to_fix = list(edited_dat_dir.glob("*.dat"))
    logger.update_phase("OPTIMIZE", "🔄 ACTIVE", 0, f"Applying size fixes to {len(files_to_fix)} files...")
    
    size_fix_result = size_fix(logger=logger)
    
    if not size_fix_result:
        logger.update_phase("OPTIMIZE", "✅ DONE", 100, "Size fixes applied (with warnings)")
    else:
        logger.update_phase("OPTIMIZE", "✅ DONE", 100, "Size fixes applied")
    
    # Step 4: Finalize
    logger.update_phase("FINALIZE", "✅ DONE", 100, "Ready for repack")
    
    # Keep the lobby patch logic after repack
    try:
        for id1, id2 in pairs:
            if id2 == "202408052":
                patch_lobby_index_in_uexp(id1, id2)
                break
    except Exception:
        pass  # Silently fail - no log needed
    
    # Set files processed count
    logger.set_files_processed(modified_count)
    
    # Print final footer
    logger.print_footer(success=True)
    
    return True

def get_replacements_for_file(file_number):
    """Get replacement rules based on file number
    
    Args:
        file_number: The DAT file number
        
    Returns:
        dict: Dictionary of replacement rules {old_bytes: new_bytes}
    """
    if file_number == 26720:
        # For 0026720.dat: Replace BigBody/BigLimbs/BigFoot/BigHands with BigHead
        return {
            b'BigBody': b'BigHead',
            b'BigLimbs': b'BigHead',
            b'BigFoot': b'BigHead',
            b'BigHand': b'BigHead',   # BigHand (without 's') - 7 bytes
            b'BigHands': b'BigHead'   # BigHands (with 's') - 8 bytes, will be padded with null
        }
    elif file_number == 26721:
        # For 0026721.dat: Replace spine_01 and spine_02 with spine_03
        return {
            b'spine_01': b'spine_03',  # 8 bytes → 8 bytes (same length)
            b'spine_02': b'spine_03'   # 8 bytes → 8 bytes (same length)
        }
    else:
        # Default: return empty dict (no replacements)
        print_warning(f"No replacement rules defined for file {file_number:07d}.dat")
        return {}

def headshot_modder(file_number=None):
    """Headshot Modder - Unpack a DAT file and apply file-specific replacements
    
    Args:
        file_number: The DAT file number (e.g., 26720 for 0026720.dat, 26721 for 0026721.dat).
                    If None, processes both default files (26720 and 26721).
    """
    # If no file number specified, process both default files
    if file_number is None:
        print_info("No file number specified. Processing both default files: 0026720.dat and 0026721.dat")
        file_numbers = [26720, 26721]
        success_count = 0
        
        for idx, fn in enumerate(file_numbers, 1):
            print_info(f"\n{'='*80}")
            print_info(f"Processing file {idx}/{len(file_numbers)}: {fn:07d}.dat")
            print_info(f"{'='*80}\n")
            
            if headshot_modder(fn):  # Recursive call with specific file number
                success_count += 1
        
        print_info(f"\n{'='*80}")
        print_info("Processing Summary:")
        print_info(f"  Total files: {len(file_numbers)}")
        print_info(f"  Successful: {success_count}")
        
        # Apply size fixes once after all files are processed
        if success_count > 0:
            print_info(f"\n{'='*80}")
            print_info("Applying size fixes to all processed files...")
            size_fix_result = size_fix_for_headshot()
            
            if not size_fix_result:
                print_warning("⚠️ Size fix had issues, but modifications are saved")
            else:
                print_success("✅ Size fixes applied successfully")
            
            print_success(f"✅ Successfully modified {success_count}/{len(file_numbers)} file(s)")
            return True
        else:
            print_error("❌ Failed to modify any files")
            return False
    
    # Process single file (original behavior)
    target_filename = f"{file_number:07d}.dat"
    target_index = file_number - 1  # 0-based index
    
    print_step(f"Headshot Modder - Processing {target_filename}")
    
    # Step 1: Get zsdic PAK file
    print_info("Step 1/4: Getting zsdic PAK file...")
    pak_tool = PAKTool()
    pak_path = pak_tool.get_zsdic_pak()
    
    if not pak_path or not pak_path.exists():
        print_error("Failed to find mini_obbzsdic_obb.pak file")
        return False
    
    print_success(f"Found PAK file: {pak_path}")
    
    # Step 2: Unpack the DAT file
    print_info(f"Step 2/4: Unpacking {target_filename} from PAK...")
    
    # Read PAK file
    with open(pak_path, 'rb') as f:
        pak_data = f.read()
    
    # Find dictionary
    dictionary, dict_pos = pak_tool.find_dictionary(pak_data)
    
    # Find DAT files
    dat_files = pak_tool.find_dat_files(pak_data, dict_pos)
    
    if target_index >= len(dat_files):
        print_error(f"File {target_filename} not found in PAK (only {len(dat_files)} files available)")
        return False
    
    dat_info = dat_files[target_index]
    print_info(f"Found {target_filename} at position {dat_info['position']}, size: {dat_info['size']} bytes")
    
    # Decompress the file
    decompressed = pak_tool.decompress_dat(dat_info['data'], dictionary)
    
    if not decompressed:
        print_error(f"Failed to decompress {target_filename}")
        return False
    
    print_success(f"Decompressed {target_filename}: {len(decompressed)} bytes")
    
    # Step 3: Create folder structure and save unpacked file
    print_info("Step 3/4: Creating folder structure and processing file...")
    
    # Create directories
    OUTPUT_HEADSHOT_UNPACKED.mkdir(parents=True, exist_ok=True)
    OUTPUT_HEADSHOT_EDITED.mkdir(parents=True, exist_ok=True)
    
    # Save unpacked file
    unpacked_file = OUTPUT_HEADSHOT_UNPACKED / target_filename
    with open(unpacked_file, 'wb') as f:
        f.write(decompressed)
    
    print_success(f"Saved unpacked file to: {unpacked_file}")
    
    # Step 4: Read file and perform text replacements
    print_info("Performing text replacements...")
    
    # ALWAYS work in binary mode - never decode/encode to avoid corruption
    file_content = decompressed
    
    # Get replacements based on file number
    replacements = get_replacements_for_file(file_number)
    
    if not replacements:
        print_warning(f"No replacements defined for {target_filename}. Skipping edit step.")
        # Copy unpacked file to edited directory without modifications
        edited_file = OUTPUT_HEADSHOT_EDITED / target_filename
        with open(edited_file, 'wb') as f:
            f.write(decompressed)
        print_success(f"Saved file to edited directory: {edited_file}")
        return True
    
    # Store original size to maintain it
    original_decompressed_size = len(decompressed)
    
    # Perform replacements in binary mode
    # Use bytearray for in-place modifications
    modified_content = bytearray(file_content)
    
    replacement_count = 0
    for old, new in replacements.items():
        # Count occurrences in original file
        count = file_content.count(old)
        if count == 0:
            continue
        
        # Find all occurrences and replace
        pos = 0
        occurrences_found = 0
        while occurrences_found < count:
            pos = modified_content.find(old, pos)
            if pos == -1:
                break
            
            # Calculate size difference
            size_diff = len(old) - len(new)
            
            if size_diff > 0:
                # Old is longer (e.g., "BigLimbs" 8 bytes → "BigHead" 7 bytes)
                # Replace with "BigHead" + null bytes to maintain same length
                modified_content[pos:pos+len(old)] = new + (b'\x00' * size_diff)
            elif size_diff < 0:
                # New is longer - shouldn't happen with our patterns, but handle it
                modified_content[pos:pos+len(old)] = new[:len(old)]
            else:
                # Same size (e.g., "BigBody" 7 bytes → "BigHead" 7 bytes)
                modified_content[pos:pos+len(old)] = new
            
            occurrences_found += 1
            replacement_count += 1
            
            # Move position past the replacement
            pos += len(old)
        
        if occurrences_found > 0:
            old_str = old.decode('utf-8', errors='replace')
            new_str = new.decode('utf-8', errors='replace')
            print_info(f"  Replaced {occurrences_found} occurrence(s) of '{old_str}' with '{new_str}'")
    
    # Convert back to bytes
    modified_content = bytes(modified_content)
    
    if replacement_count == 0:
        print_warning("No replacements were made - patterns not found in file")
    else:
        print_success(f"Total replacements made: {replacement_count}")
    
    # Verify file size is maintained (should be exact since we pad at replacement positions)
    current_size = len(modified_content)
    if current_size != original_decompressed_size:
        if current_size < original_decompressed_size:
            # Shouldn't happen, but pad if needed
            padding_needed = original_decompressed_size - current_size
            modified_content = modified_content + (b'\x00' * padding_needed)
            print_warning(f"  File size was {current_size}, padded with {padding_needed} null bytes to maintain original size ({original_decompressed_size} bytes)")
        else:
            # Shouldn't happen, but truncate if needed
            print_warning(f"  File size increased from {original_decompressed_size} to {current_size} bytes - truncating")
            modified_content = modified_content[:original_decompressed_size]
    else:
        print_info(f"  File size maintained: {current_size} bytes")
    
    # Save edited file
    edited_file = OUTPUT_HEADSHOT_EDITED / target_filename
    with open(edited_file, 'wb') as f:
        f.write(modified_content)
    
    print_success(f"Saved edited file to: {edited_file}")
    
    # Step 5: Apply size fixes (null logic) - Skip if processing multiple files (will be done at end)
    # Only apply size fixes if this is a single file operation
    # Size fixes will be applied once after all files are processed in the menu function
    
    return True

def unpack_headshot_dat(file_number):
    """Unpack a specific DAT file for headshot modder (unpack only, no editing)"""
    target_filename = f"{file_number:07d}.dat"
    target_index = file_number - 1  # 0-based index
    
    print_step(f"Unpacking {target_filename}")
    
    # Get zsdic PAK file
    pak_tool = PAKTool()
    pak_path = pak_tool.get_zsdic_pak()
    
    if not pak_path or not pak_path.exists():
        print_error("Failed to find mini_obbzsdic_obb.pak file")
        return False
    
    print_success(f"Found PAK file: {pak_path}")
    
    # Read PAK file
    with open(pak_path, 'rb') as f:
        pak_data = f.read()
    
    # Find dictionary
    dictionary, dict_pos = pak_tool.find_dictionary(pak_data)
    
    # Find DAT files
    dat_files = pak_tool.find_dat_files(pak_data, dict_pos)
    
    if target_index >= len(dat_files):
        print_error(f"File {target_filename} not found in PAK (only {len(dat_files)} files available)")
        return False
    
    dat_info = dat_files[target_index]
    print_info(f"Found {target_filename} at position {dat_info['position']}, size: {dat_info['size']} bytes")
    
    # Decompress the file
    decompressed = pak_tool.decompress_dat(dat_info['data'], dictionary)
    
    if not decompressed:
        print_error(f"Failed to decompress {target_filename}")
        return False
    
    print_success(f"Decompressed {target_filename}: {len(decompressed)} bytes")
    
    # Create directories
    OUTPUT_HEADSHOT_UNPACKED.mkdir(parents=True, exist_ok=True)
    
    # Save unpacked file
    unpacked_file = OUTPUT_HEADSHOT_UNPACKED / target_filename
    with open(unpacked_file, 'wb') as f:
        f.write(decompressed)
    
    print_success(f"✅ Saved unpacked file to: {unpacked_file}")
    return True

def repack_headshot_to_pak(file_numbers=None):
    """Repack edited DAT files back into the PAK
    
    Args:
        file_numbers: List of file numbers to repack (e.g., [26720, 26721]). 
                     If None, repacks all edited files in the edited directory.
    """
    print_step("Repacking Headshot Modder - Creating Modified PAK")
    
    # Initialize PAKTool
    pak_tool = PAKTool()
    
    # Get zsdic PAK file
    pak_path = pak_tool.get_zsdic_pak()
    if not pak_path or not pak_path.exists():
        print_error("Failed to find mini_obbzsdic_obb.pak file")
        return False
    
    # Read original PAK file
    with open(pak_path, 'rb') as f:
        pak_data = bytearray(f.read())
    
    # Find dictionary
    dictionary, dict_pos = pak_tool.find_dictionary(pak_data)
    
    # Find original DAT files
    dat_files = pak_tool.find_dat_files(pak_data, dict_pos)
    
    # Determine which files to repack
    if file_numbers is None:
        # Get all edited files
        edited_files = list(OUTPUT_HEADSHOT_EDITED.glob("*.dat"))
        if not edited_files:
            print_error(f"No edited DAT files found in {OUTPUT_HEADSHOT_EDITED}")
            return False
        
        # Extract file numbers from filenames
        file_numbers = []
        for edited_file in edited_files:
            try:
                # Extract number from filename like "0026720.dat"
                file_num = int(edited_file.stem)
                file_numbers.append(file_num)
            except ValueError:
                print_warning(f"Skipping invalid filename: {edited_file.name}")
                continue
    
    if not file_numbers:
        print_error("No valid files to repack")
        return False
    
    print_info(f"Repacking {len(file_numbers)} file(s)...")
    
    # Process each file
    files_repacked = 0
    dict_obj = zstd.ZstdCompressionDict(dictionary)
    
    for file_number in file_numbers:
        target_filename = f"{file_number:07d}.dat"
        target_index = file_number - 1  # 0-based index
        
        # Check for edited file
        edited_file = OUTPUT_HEADSHOT_EDITED / target_filename
        if not edited_file.exists():
            print_warning(f"Edited file not found: {edited_file} - skipping")
            continue
        
        if target_index < 0 or target_index >= len(dat_files):
            print_error(f"DAT index {target_index} out of range for {target_filename} - skipping")
            continue
        
        print_info(f"Repacking {target_filename} (index {target_index})...")
        
        # Read edited file
        try:
            with open(edited_file, 'rb') as f:
                edited_data = f.read()
        except Exception as e:
            print_error(f"Failed to read edited file {target_filename}: {e} - skipping")
            continue
        
        # Get original DAT info
        original_dat = dat_files[target_index]
        original_size = original_dat['size']
        required_size = original_size - 4  # Size minus checksum
        
        # Extract checksum from original
        checksum = original_dat['data'][-4:]
        
        # Compress edited data
        compressed_data = None
        
        print_info(f"  Testing compression levels to fit {required_size} bytes...")
        for level in range(1, 23):
            try:
                cctx = zstd.ZstdCompressor(level=level, dict_data=dict_obj)
                test_compressed = cctx.compress(edited_data)
                
                if len(test_compressed) <= required_size:
                    compressed_data = test_compressed
                    print_success(f"  Compressed with level {level}")
                    break
            except Exception:
                continue
        
        if compressed_data is None:
            print_error(f"  Could not compress {target_filename} to fit in {required_size} bytes - skipping")
            continue
        
        print_info(f"  Compressed data size: {len(compressed_data)} bytes")
        
        # Create new DAT block
        new_dat_block = bytearray(compressed_data)
        
        # Pad with null bytes if needed
        if len(compressed_data) < required_size:
            padding_needed = required_size - len(compressed_data)
            new_dat_block.extend(b'\x00' * padding_needed)
        
        # XOR encrypt
        xor_encrypted_data = pak_tool.xor_decrypt(new_dat_block)
        new_dat_block = bytearray(xor_encrypted_data)
        
        # Add checksum
        new_dat_block.extend(checksum)
        
        # Ensure correct size
        if len(new_dat_block) != original_size:
            print_error(f"  Size mismatch for {target_filename} - original: {original_size}, new: {len(new_dat_block)} - skipping")
            continue
        
        # Replace in PAK data
        start_pos = original_dat['position']
        end_pos = start_pos + original_dat['size']
        pak_data[start_pos:end_pos] = new_dat_block
        
        print_success(f"  ✅ Replaced {target_filename} in PAK file")
        files_repacked += 1
    
    if files_repacked == 0:
        print_error("No files were successfully repacked")
        return False
    
    # Save repacked PAK
    pak_filename = "mini_obbzsdic_obb.pak"
    repacked_pak_path = OUTPUT_MODSKIN_RESULTS / pak_filename
    
    # Ensure the directory exists
    repacked_pak_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write the repacked PAK
    with open(repacked_pak_path, 'wb') as f:
        f.write(pak_data)
    
    print_success(f"✅ Repacked PAK saved to: {repacked_pak_path} ({files_repacked} file(s) repacked)")
    
    return True

def show_headshot_menu():
    """Display headshot modder menu and get user choice"""
    print()
    print("🎯 Headshot Modder - Menu")
    print("-" * 70)
    print("1. Unpack DAT file(s)")
    print("2. Mod DAT file(s) (Unpack + Edit)")
    print("3. Repack edited DAT file(s)")
    print("4. Automatic (Unpack + Mod + Repack)")
    print("0. Exit")
    print("-" * 70)
    print()
    
    while True:
        try:
            choice = input("Enter your choice (0-4): ").strip()
            if choice in ['0', '1', '2', '3', '4']:
                return int(choice)
            else:
                print_error("Invalid choice. Please enter 0, 1, 2, 3, or 4.")
        except (ValueError, EOFError, KeyboardInterrupt):
            print_error("Invalid input. Please enter a number.")
            return 0

def get_headshot_file_numbers(prompt="Enter DAT file number(s) (comma-separated, e.g., 26720,26721) or press Enter for default (26720,26721): ", default_files=[26720, 26721]):
    """Get file numbers from user, with default files if no input provided"""
    try:
        user_input = input(prompt).strip()
        if not user_input:
            # Use default files if no input provided
            print_info(f"Using default files: {', '.join(str(f) for f in default_files)}")
            return default_files
        
        # Split by comma and convert to integers
        file_numbers = []
        for num_str in user_input.split(','):
            num_str = num_str.strip()
            if num_str:
                try:
                    file_num = int(num_str)
                    file_numbers.append(file_num)
                except ValueError:
                    print_warning(f"Invalid number: {num_str} - skipping")
        
        return file_numbers if file_numbers else default_files
    except (EOFError, KeyboardInterrupt):
        # Return default files on interrupt
        print_info(f"Using default files: {', '.join(str(f) for f in default_files)}")
        return default_files

def headshot_modder_menu():
    """Main headshot modder menu function"""
    print("\n🎯 Headshot Modder - Menu System\n")
    
    while True:
        choice = show_headshot_menu()
        
        if choice == 0:
            print("\n👋 Returning to main menu...")
            break
        
        elif choice == 1:
            # Option 1: Unpack
            print_step("Option 1: Unpack DAT file(s)")
            file_numbers = get_headshot_file_numbers()
            
            if not file_numbers:
                # Fallback to default files
                file_numbers = [26720, 26721]
                print_info(f"Using default files: {', '.join(str(f) for f in file_numbers)}")
            
            success_count = 0
            for file_num in file_numbers:
                if unpack_headshot_dat(file_num):
                    success_count += 1
            
            if success_count > 0:
                print_success(f"✅ Successfully unpacked {success_count}/{len(file_numbers)} file(s)")
            else:
                print_error("❌ Failed to unpack any files")
        
        elif choice == 2:
            # Option 2: Mod (Unpack + Edit) - Process both files automatically
            print_step("Option 2: Mod DAT file(s) (Unpack + Edit)")
            
            # Always process both files automatically (0026720.dat and 0026721.dat)
            file_numbers = [26720, 26721]
            print_info(f"Processing both files: {', '.join(f'{f:07d}.dat' for f in file_numbers)}")
            print_info("This will process 0026720.dat and 0026721.dat automatically")
            
            success_count = 0
            failed_files = []
            
            for idx, file_num in enumerate(file_numbers, 1):
                print_info(f"\n{'='*80}")
                print_info(f"Processing file {idx}/{len(file_numbers)}: {file_num:07d}.dat")
                print_info(f"{'='*80}\n")
                
                try:
                    if headshot_modder(file_num):
                        success_count += 1
                        print_success(f"✅ File {file_num:07d}.dat processed successfully")
                    else:
                        failed_files.append(file_num)
                        print_error(f"❌ File {file_num:07d}.dat failed to process")
                except Exception as e:
                    failed_files.append(file_num)
                    print_error(f"❌ Error processing {file_num:07d}.dat: {e}")
                    import traceback
                    traceback.print_exc()
            
            print_info(f"\n{'='*80}")
            print_info("Processing Summary:")
            print_info(f"  Total files: {len(file_numbers)}")
            print_info(f"  Successful: {success_count}")
            print_info(f"  Failed: {len(failed_files)}")
            if failed_files:
                print_warning(f"  Failed files: {', '.join(f'{f:07d}.dat' for f in failed_files)}")
            
            # Apply size fixes once after all files are processed
            if success_count > 0:
                print_info(f"\n{'='*80}")
                print_info("Applying size fixes to all processed files...")
                size_fix_result = size_fix_for_headshot()
                
                if not size_fix_result:
                    print_warning("⚠️ Size fix had issues, but modifications are saved")
                else:
                    print_success("✅ Size fixes applied successfully")
        
        elif choice == 3:
            # Option 3: Repack
            print_step("Option 3: Repack edited DAT file(s)")
            
            # Ask if user wants to repack specific files or all edited files
            print("\nRepack options:")
            print("1. Repack all edited files")
            print("2. Repack specific file(s)")
            repack_choice = input("Enter choice (1 or 2): ").strip()
            
            file_numbers = None
            if repack_choice == '2':
                file_numbers = get_headshot_file_numbers()
                if not file_numbers:
                    print_error("No file numbers provided")
                    continue
            
            if repack_headshot_to_pak(file_numbers):
                print_success("✅ Repacking completed successfully!")
            else:
                print_error("❌ Repacking failed!")
        
        elif choice == 4:
            # Option 4: Automatic (Unpack + Mod + Repack)
            print_step("Option 4: Automatic (Unpack + Mod + Repack)")
            file_numbers = get_headshot_file_numbers()
            
            if not file_numbers:
                # Fallback to default files
                file_numbers = [26720, 26721]
                print_info(f"Using default files: {', '.join(str(f) for f in file_numbers)}")
            
            # Step 1: Unpack and Mod
            success_count = 0
            for file_num in file_numbers:
                if headshot_modder(file_num):
                    success_count += 1
            
            if success_count == 0:
                print_error("❌ Failed to unpack/modify any files")
                continue
            
            print_success(f"✅ Successfully unpacked and modified {success_count}/{len(file_numbers)} file(s)")
            
            # Step 2: Repack
            print_info("\n💡 Repacking edited files into PAK...")
            if repack_headshot_to_pak(file_numbers):
                print_success("✅ Complete workflow finished successfully!")
                print_info(f"📁 Repacked PAK saved to: {OUTPUT_MODSKIN_RESULTS / 'mini_obbzsdic_obb.pak'}")
            else:
                print_error("❌ Repacking failed!")
        
        # Ask if user wants to continue
        print("\n")
        continue_choice = input("Do you want to perform another operation? (y/n): ").strip().lower()
        if continue_choice not in ['y', 'yes']:
            print("\n👋 Returning to main menu...")
            break

def size_fix_for_headshot(max_nulls_per_file: int = 20):
    """Apply size fixes by nulling unwanted IDs - specifically for Headshot Modder files"""
    print_step("Applying Size Fixes for Headshot Modder")
    
    # Use Headshot Modder edited directory
    edited_dat_dir = OUTPUT_HEADSHOT_EDITED
    null_path = NULL_TXT
    modskin_path = MODSKIN_TXT
    nulled_log_path = OUTPUT_HEADSHOT / "nulled.txt"
    
    if not edited_dat_dir.exists():
        print_error(f"Edited files directory not found: {edited_dat_dir}")
        return False
    
    files_to_process = [
        fn for fn in sorted(edited_dat_dir.glob("*.dat"))
        if fn.is_file()
    ]
    
    if not files_to_process:
        print_warning(f"No DAT files found in {edited_dat_dir}")
        return True  # Not an error, just no files to process
    
    print_info(f"{len(files_to_process)} file(s) found for size fixing")
    print_info(f"Applying {max_nulls_per_file} nulls per file")
    
    # Read modskin IDs to avoid nulling them
    mod_ids = set()
    if modskin_path.exists():
        pairs = parse_id_pairs(modskin_path)
        for a, b in pairs:
            if a.isdigit():
                mod_ids.add(a)
            if b.isdigit():
                mod_ids.add(b)
    
    # Read null IDs with multi-encoding support
    master_null_ids = []
    if null_path.exists():
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        file_content = None
        
        for enc in encodings:
            try:
                with open(null_path, encoding=enc) as nf:
                    file_content = nf.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if file_content:
            for line in file_content.splitlines():
                m = re.search(r'\bID\s+(\d+)\b', line) or re.search(r'(\d{3,})', line)
                if m:
                    master_null_ids.append(m.group(1).encode())
    
    # Remove duplicates and filter
    seen = set()
    unique_master_ids = [x for x in master_null_ids if not (x in seen or seen.add(x))]
    null_ids = [nid for nid in unique_master_ids 
                if not (nid.decode().startswith('40') or nid.decode() in mod_ids)]
    
    print_info(f"Found {len(null_ids)} unique IDs to null")
    
    nulled_info = {}
    
    for fn in files_to_process:
        print_info(f"Processing {fn.name}...")
        orig_bytes = open(fn, 'rb').read()
        data = bytearray(orig_bytes)
        nulled_info[fn.name] = []
        nulls = 0
        matches = []
        
        # Find all matches
        for id_bytes in null_ids:
            start_search = 0
            while (pos := data.find(id_bytes, start_search)) >= 0:
                matches.append((pos, id_bytes))
                start_search = pos + 1
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Apply nulls
        for pos, id_bytes in matches:
            if nulls >= max_nulls_per_file or pos + len(id_bytes) + 5 > len(data):
                continue
            
            before = data[pos - 1:pos] if pos > 0 else None
            after = data[pos + len(id_bytes) + 5:pos + len(id_bytes) + 6] if pos + len(id_bytes) + 5 < len(data) else None
            
            if (before and before in b"0123456789") or (after and after in b"0123456789"):
                continue
            
            pattern = orig_bytes[pos:pos + len(id_bytes) + 5]
            nulled_info[fn.name].append((id_bytes.decode(), pattern.hex()))
            data[pos:pos + len(id_bytes) + 5] = b'\x00' * (len(id_bytes) + 5)
            nulls += 1
        
        with open(fn, 'wb') as f:
            f.write(data)
        
        if nulls > 0:
            print_success(f"  Applied {nulls} nulls to {fn.name}")
        else:
            print_info(f"  No nulls needed for {fn.name}")
    
    # Write log
    OUTPUT_HEADSHOT.mkdir(parents=True, exist_ok=True)
    with open(nulled_log_path, 'w', encoding='utf-8') as nf:
        nf.write("Headshot Modder - Nulled IDs Log\n")
        nf.write("=" * 50 + "\n\n")
        for filename, nulled_list in nulled_info.items():
            if nulled_list:
                nf.write(f"File: {filename}\n")
                for id_str, pattern_hex in nulled_list:
                    nf.write(f"  Nulled ID: {id_str} (pattern: {pattern_hex})\n")
                nf.write("\n")
    
    total_nulls = sum(len(v) for v in nulled_info.values())
    if total_nulls > 0:
        print_success(f"✅ Size fix complete: {total_nulls} nulls applied across {len(files_to_process)} file(s)")
        print_info(f"Log saved to: {nulled_log_path}")
    else:
        print_info("No nulls were applied (files already fit size requirements)")
    
    return True

def size_fix(max_nulls_per_file: int = 150, logger=None):
    """Apply size fixes by nulling unwanted IDs"""
    use_logger = logger is not None
    
    if not use_logger:
        print_step("Applying Size Fixes")
    
    # ✅ UPDATED: Use new directory structure
    edited_dat_dir = OUTPUT_MODSKIN_EDITED
    null_path = NULL_TXT
    modskin_path = MODSKIN_TXT
    nulled_log_path = OUTPUT_MODSKIN / "nulled.txt"
    
    if not edited_dat_dir.exists():
        if use_logger:
            logger.log_error("SIZE_FIX", f"Edited files directory not found: {edited_dat_dir}")
        else:
            print_error(f"Edited files directory not found: {edited_dat_dir}")
        return False
    
    files_to_process = [
        fn for fn in sorted(edited_dat_dir.glob("*"))
        if fn.is_file() and not fn.name.endswith('.txt')
    ]
    
    if not files_to_process:
        if use_logger:
            logger.log_error("SIZE_FIX", f"No files found in {edited_dat_dir}")
        else:
            print_error(f"No files found in {edited_dat_dir}")
        return False
    
    if not use_logger:
        print_info(f"{len(files_to_process)} files found")
        print_info(f"Applying {max_nulls_per_file} nulls per file")
    
    # Read modskin IDs to avoid nulling them
    mod_ids = set()
    if modskin_path.exists():
        pairs = parse_id_pairs(modskin_path)
        for a, b in pairs:
            if a.isdigit():
                mod_ids.add(a)
            if b.isdigit():
                mod_ids.add(b)
    
    # Read null IDs with multi-encoding support
    master_null_ids = []
    if null_path.exists():
        encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
        file_content = None
        
        for enc in encodings:
            try:
                with open(null_path, encoding=enc) as nf:
                    file_content = nf.read()
                break
            except (UnicodeDecodeError, UnicodeError):
                continue
        
        if file_content:
            for line in file_content.splitlines():
                m = re.search(r'\bID\s+(\d+)\b', line) or re.search(r'(\d{3,})', line)
                if m:
                    master_null_ids.append(m.group(1).encode())
    
    # Remove duplicates and filter
    seen = set()
    unique_master_ids = [x for x in master_null_ids if not (x in seen or seen.add(x))]
    null_ids = [nid for nid in unique_master_ids 
                if not (nid.decode().startswith('40') or nid.decode() in mod_ids)]
    
    if not use_logger:
        print_info(f"Found {len(null_ids)} unique IDs to null")
    
    nulled_info = {}
    total_nulls = 0
    
    for idx, fn in enumerate(files_to_process):
        # Removed individual file processing logs - only dashboard updates
        if not use_logger:
            print_info(f"Processing {fn.name}...")
        orig_bytes = open(fn, 'rb').read()
        data = bytearray(orig_bytes)
        nulled_info[fn.name] = []
        nulls = 0
        matches = []
        
        # Find all matches
        for id_bytes in null_ids:
            start_search = 0
            while (pos := data.find(id_bytes, start_search)) >= 0:
                matches.append((pos, id_bytes))
                start_search = pos + 1
        
        matches.sort(key=lambda x: x[0], reverse=True)
        
        # Apply nulls
        for pos, id_bytes in matches:
            if nulls >= max_nulls_per_file or pos + len(id_bytes) + 5 > len(data):
                continue
            
            before = data[pos - 1:pos] if pos > 0 else None
            after = data[pos + len(id_bytes) + 5:pos + len(id_bytes) + 6] if pos + len(id_bytes) + 5 < len(data) else None
            
            if (before and before in b"0123456789") or (after and after in b"0123456789"):
                continue
            
            pattern = orig_bytes[pos:pos + len(id_bytes) + 5]
            nulled_info[fn.name].append((id_bytes.decode(), pattern.hex()))
            data[pos:pos + len(id_bytes) + 5] = b'\x00' * (len(id_bytes) + 5)
            nulls += 1
            total_nulls += 1
        
        with open(fn, 'wb') as f:
            f.write(data)
        
        if not use_logger:
            if nulls > 0:
                print_success(f"Applied {nulls} nulls to {fn.name}")
            else:
                print_info(f"No nulls needed for {fn.name}")
        
        # Update progress (update more frequently for smoother dashboard)
        if use_logger and ((idx + 1) % 3 == 0 or (idx + 1) == len(files_to_process)):
            progress = int(((idx + 1) / len(files_to_process)) * 100)
            logger.update_phase("OPTIMIZE", "🔄 ACTIVE", progress, f"{total_nulls} nulls applied")
    
    # Write log
    with open(nulled_log_path, 'w', encoding='utf-8') as nf:
        for fn, entries in nulled_info.items():
            if not entries:
                continue
            nf.write(f"{fn}:\n")
            for id_str, hx in entries:
                if id_str in mod_ids or id_str.startswith('40'):
                    continue
                nf.write(f"  ID {id_str} → nulled longhex {hx}\n")
            nf.write("\n")
    
    total_nulls = sum(len(v) for v in nulled_info.values())
    if use_logger:
        if total_nulls > 0:
            logger.update_phase("OPTIMIZE", "✅ DONE", 100, f"{total_nulls} nulls applied to {len(files_to_process)} files")
        else:
            logger.update_phase("OPTIMIZE", "✅ DONE", 100, f"No nulls needed ({len(files_to_process)} files fit size)")
    else:
        if total_nulls > 0:
            print_success("Size fixes applied")
        else:
            print_info("No nulls were applied (files already fit size requirements)")
    
    return True

def patch_lobby_index_in_uexp(id1: str, id2: str) -> bool:
    """Patch lobby index in mini_obb.pak by extracting 00063291.uexp,
    finding index near ID1 using Emote Modder's logic, and replacing with
    ID2's index bytes. Saves only the modified UEXP; no repack here."""
    try:
        print_info("[Lobby Patch] Starting lobby index patch for 00063291.uexp...")

        edited_uexp_dir = OUTPUT_HITEFFECT_EDITED
        edited_uexp_dir.mkdir(parents=True, exist_ok=True)

        # Extract only target file 00063291.uexp from mini_obb.pak
        target_index = 63291
        unpacker = MiniOBBUnpacker()
        if not unpacker.unpack_mini_obb(target_index=target_index):
            print_error("[Lobby Patch] Failed to extract 00063291.uexp from mini_obb.pak")
            return False

        src_uexp = OUTPUT_HITEFFECT_UNPACKED / f"{target_index:08d}.uexp"
        if not src_uexp.exists():
            print_error(f"[Lobby Patch] Extracted file not found: {src_uexp}")
            return False

        data = src_uexp.read_bytes()

        # Load ID→hex mapping from null.txt
        null_file = NULL_TXT
        if not null_file.exists():
            print_error("[Lobby Patch] null.txt not found")
            return False
        text = None
        for enc in ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']:
            try:
                text = null_file.read_text(encoding=enc)
                break
            except Exception:
                continue
        if text is None:
            print_error("[Lobby Patch] Could not decode null.txt")
            return False
        id_to_hex = {}
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '|' in line:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    id_to_hex[parts[0]] = parts[1].replace(" ", "").replace("0x", "").upper()

        hex1_str = id_to_hex.get(id1)
        hex2_str = id_to_hex.get(id2)
        if not hex1_str or not hex2_str:
            print_error("[Lobby Patch] Missing hex mapping for provided IDs in null.txt")
            return False
        hex1 = bytes.fromhex(hex1_str)
        hex2 = bytes.fromhex(hex2_str)
        if not hex1 or not hex2:
            print_error("[Lobby Patch] Invalid hex mapping for IDs")
            return False

        # Find occurrences and their index bytes
        occurrences_id1 = scan_file_for_hex_embedded(data, hex1)
        occurrences_id2 = scan_file_for_hex_embedded(data, hex2)
        print_info(f"[Lobby Patch] ID1 occurrences: {len(occurrences_id1)} | ID2 occurrences: {len(occurrences_id2)}")

        def find_index_for_occurrence(data_bytes: bytes, pos: int, base_len: int):
            """Return (position, index_bytes) for the index near the occurrence."""
            before = find_index_before_embedded(data_bytes, pos)
            if before:
                return before[0], before[1]
            after = find_index_after_embedded(data_bytes, pos + base_len)
            if after:
                return after[0], after[1]
            return None, b''

        # Get exemplar index bytes for both IDs
        idx1_bytes = b''
        idx1_pos = None
        for pos in occurrences_id1:
            p, b = find_index_for_occurrence(data, pos, len(hex1))
            if b:
                idx1_bytes, idx1_pos = b, p
                break
        if not idx1_bytes:
            print_error("[Lobby Patch] Could not locate index bytes for source ID1")
            return False
        print_info(f"[Lobby Patch] Source index (ID1) @ {idx1_pos}: {idx1_bytes.hex()}")

        idx2_bytes = b''
        idx2_pos = None
        for pos in occurrences_id2:
            p, b = find_index_for_occurrence(data, pos, len(hex2))
            if b:
                idx2_bytes, idx2_pos = b, p
                break
        if not idx2_bytes:
            print_error("[Lobby Patch] Could not locate index bytes for target ID2")
            return False
        print_info(f"[Lobby Patch] Target index (ID2) @ {idx2_pos}: {idx2_bytes.hex()}")

        patched = bytearray(data)
        replaced_any = False
        swaps_id1_to_id2 = 0
        swaps_id2_to_id1 = 0

        # Swap ID1's index → ID2's exemplar index
        for pos in occurrences_id1:
            wpos, found = find_index_for_occurrence(data, pos, len(hex1))
            if found and len(found) == len(idx2_bytes) and wpos is not None and wpos + len(idx2_bytes) <= len(patched):
                print_info(f"[Lobby Patch] Swap (ID1→ID2) @ {wpos}: {found.hex()} -> {idx2_bytes.hex()}")
                patched[wpos:wpos+len(idx2_bytes)] = idx2_bytes
                swaps_id1_to_id2 += 1
                replaced_any = True

        # Swap ID2's index → ID1's exemplar index (reciprocal)
        for pos in occurrences_id2:
            wpos, found = find_index_for_occurrence(data, pos, len(hex2))
            if found and len(found) == len(idx1_bytes) and wpos is not None and wpos + len(idx1_bytes) <= len(patched):
                print_info(f"[Lobby Patch] Swap (ID2→ID1) @ {wpos}: {found.hex()} -> {idx1_bytes.hex()}")
                patched[wpos:wpos+len(idx1_bytes)] = idx1_bytes
                swaps_id2_to_id1 += 1
                replaced_any = True

        print_info(f"[Lobby Patch] Index swaps → ID1→ID2: {swaps_id1_to_id2}, ID2→ID1: {swaps_id2_to_id1}")

        # Also replace raw ID hex (ID1 -> ID2) inside the file for safety
        hex_replacements = 0
        if hex1 and hex2 and hex1 in patched:
            start = 0
            while True:
                idx = patched.find(hex1, start)
                if idx == -1:
                    break
                # length-align
                hex2_use = hex2 if len(hex2) == len(hex1) else hex2.ljust(len(hex1), b'\x00')[:len(hex1)]
                patched[idx:idx+len(hex1)] = hex2_use
                hex_replacements += 1
                start = idx + len(hex1)
            if hex_replacements:
                replaced_any = True
        print_info(f"[Lobby Patch] Raw ID hex replacements applied: {hex_replacements}")

        if not replaced_any:
            print_warning("[Lobby Patch] No index positions replaced for ID1")
            return False

        out_path = edited_uexp_dir / f"{target_index:08d}.uexp"
        out_path.write_bytes(bytes(patched))
        print_success(f"[Lobby Patch] Saved patched UEXP: {out_path}")
        print_success(f"[Lobby Patch] Summary → index swaps (ID1→ID2: {swaps_id1_to_id2}, ID2→ID1: {swaps_id2_to_id1}), id hex swaps: {hex_replacements}")
        print_info("[Lobby Patch] Note: No repack performed here. Repack OBB handles it later.")
        return True
    except Exception as e:
        print_error(f"[Lobby Patch] Failed: {e}")
        return False

# ───── MAIN WORKFLOW ──────────────────────────────────────────────────────────────

def interactive_menu():
    """Interactive menu system with 3 main categories"""
    while True:
        print_header()
        show_status_table()
        show_main_menu()
        
        try:
            choice = input("🎯 Enter your choice (0-5): ").strip()
            
            if choice == "0":
                confirm = input("👋 Are you sure you want to exit? (y/n): ").strip().lower()
                if confirm == 'y':
                    print("🎉 Thank you for using BGMI Modding Tool!")
                    print("👋 Goodbye!")
                    break
            
            elif choice == "1":
                # OBB Functions submenu
                while True:
                    show_obb_menu()
                    obb_choice = input("📦 Enter your choice (0-2): ").strip()
                    
                    if obb_choice == "0":
                        break  # Back to main menu
                    elif obb_choice == "1":
                        print_step("Unpacking OBB", "📦")
                        unpack_obb()
                        input("\nPress Enter to continue...")
                    elif obb_choice == "2":
                        print_step("Repacking OBB", "📱")
                        repack_obb()
                        input("\nPress Enter to continue...")
                    else:
                        print_error("Invalid choice. Please try again.")
            
            elif choice == "2":
                # Skin Features submenu
                while True:
                    show_skin_menu()
                    skin_choice = input("🎨 Enter your choice (0-7): ").strip()
                    
                    if skin_choice == "0":
                        break  # Back to main menu
                    elif skin_choice == "1":
                        print_step("Apply Mod Skin (Fully Automated)", "🎨")
                        mod_skin()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "2":
                        print_step("Hit Effect (Fully Automated)", "🔫")
                        HitModder().process_hit_mods()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "3":
                        print_step("Killfeed Modder", "💀")
                        KillfeedModder().process_killfeed_complete()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "4":
                        print_step("Lootbox Modder", "🎁")
                        LootboxModder().process_modskin_mods()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "5":
                        print_step("Emote Modder", "🎭")
                        EmoteModder().process_emote_modification()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "6":
                        print_step("Credit Adder", "💰")
                        CreditAdder().extract_credit_uexp()
                        input("\nPress Enter to continue...")
                    elif skin_choice == "7":
                        print_step("Complete Workflow - All Skin Modders", "🚀")
                        complete_workflow()
                        input("\nPress Enter to continue...")
                    else:
                        print_error("Invalid choice. Please try again.")
            
            elif choice == "3":
                # Hack Features submenu
                while True:
                    show_hack_menu()
                    hack_choice = input("🎯 Enter your choice (0-1): ").strip()
                    
                    if hack_choice == "0":
                        break  # Back to main menu
                    elif hack_choice == "1":
                        headshot_modder_menu()
                    else:
                        print_error("Invalid choice. Please try again.")
            
            elif choice == "4":
                print_step("Cleaning Up", "🧹")
                cleanup()
                input("\nPress Enter to continue...")
            
            elif choice == "5":
                show_file_info()
                input("Press Enter to continue...")
            
            else:
                print_error("Invalid choice. Please try again.")
                input("Press Enter to continue...")
                    
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
            confirm = input("👋 Exit? (y/n): ").strip().lower()
            if confirm == 'y':
                break
        except Exception as e:
            print_error(f"Unexpected error: {e}")
            input("Press Enter to continue...")

def complete_workflow():
    """Complete workflow - runs all modders after OBB unpacking (excluding unpack_obb)"""
    print_step("Complete Workflow - Running All Modders", "🚀")
    
    print()
    print("🚀 Complete Workflow Started")
    print("=" * 70)
    print("This will run ALL modders in sequence:")
    print("  🎨 Mod Skin")
    print("  🔫 Hit Effect")
    print("  💀 Killfeed Modder")
    print("  🎁 Lootbox Modder")
    print("  🎭 Emote Modder")
    print("  💰 Credit Adder")
    print()
    print("⚠️ Make sure OBB is already unpacked!")
    print()
    
    confirm = input("⚠️ Continue with complete workflow? (y/n, default=y): ").strip().lower()
    if confirm == 'n':
        print_info("Workflow cancelled by user")
        return False
    
    success_count = 0
    total_steps = 7
    
    # List of all modders to run
    modders = [
        ("🎨 Mod Skin", "mod_skin", lambda: mod_skin()),
        ("🔫 Hit Effect", "hit_effect", lambda: HitModder().process_hit_mods()),
        ("💀 Killfeed Modder", "killfeed", lambda: KillfeedModder().process_killfeed_complete()),
        ("🎁 Lootbox Modder", "lootbox", lambda: LootboxModder().process_modskin_mods()),
        ("🎭 Emote Modder", "emote", lambda: EmoteModder().process_emote_modification()),
        ("🎯 Headshot Modder", "headshot", lambda: headshot_modder_menu()),
        ("💰 Credit Adder", "credit", lambda: CreditAdder().extract_credit_uexp()),
    ]
    
    print()
    print("=" * 70)
    
    for i, (name, _, func) in enumerate(modders, 1):
        print()
        print(f"Step {i}/{total_steps}: {name}")
        print("-" * 70)
        
        try:
            result = func()
            if result is False:
                print_error(f"{name} failed!")
                confirm = input(f"Continue despite {name} failure? (y/n, default=y): ").strip().lower()
                if confirm == 'n':
                    break
            else:
                print_success(f"{name} completed!")
                success_count += 1
        except KeyboardInterrupt:
            print_error(f"{name} cancelled by user")
            confirm = input("Continue with remaining modders? (y/n, default=y): ").strip().lower()
            if confirm == 'n':
                break
        except Exception as e:
            print_error(f"{name} error: {e}")
            confirm = input(f"Continue despite {name} error? (y/n, default=y): ").strip().lower()
            if confirm == 'n':
                break
        
        if i < total_steps:
            time.sleep(0.5)
    
    print()
    print("=" * 70)
    print()
    
    print("📊 Workflow Summary")
    print("=" * 70)
    print(f"✅ Successful: {success_count}/{total_steps}")
    print(f"❌ Failed: {total_steps - success_count}/{total_steps}")
    print()
    
    if success_count == total_steps:
        print_success("🎉 All modders completed successfully!")
        return True
    else:
        print_warning(f"⚠️ {total_steps - success_count} modder(s) failed. Check output for details.")
        return False
    
    success_count = 0
    total_steps = 7
    
    # List of all modders to run
    modders = [
        ("🎨 Mod Skin", "mod_skin", lambda: mod_skin()),
        ("🔫 Hit Effect", "hit_effect", lambda: HitModder().process_hit_mods()),
        ("💀 Killfeed Modder", "killfeed", lambda: KillfeedModder().process_killfeed_complete()),
        ("🎁 Lootbox Modder", "lootbox", lambda: LootboxModder().process_modskin_mods()),
        ("🎭 Emote Modder", "emote", lambda: EmoteModder().process_emote_modification()),
        ("🎯 Headshot Modder", "headshot", lambda: headshot_modder_menu()),
        ("💰 Credit Adder", "credit", lambda: CreditAdder().extract_credit_uexp()),
    ]
    
    print()
    print("=" * 70)
    
    for i, (name, _, func) in enumerate(modders, 1):
        print()
        print(f"Step {i}/{total_steps}: {name}")
        print("-" * 70)
        
        try:
            result = func()
            # Most functions return True/False or None
            if result is False:
                print_error(f"{name} failed!")
                if not input("Continue? (y/n): ").strip().lower() == "y":
                    break
            else:
                print_success(f"{name} completed!")
                success_count += 1
        except KeyboardInterrupt:
            print_error(f"{name} cancelled by user")
            if not input("Continue? (y/n): ").strip().lower() == "y":
                break
        except Exception as e:
            print_error(f"{name} error: {e}")
            if not input("Continue? (y/n): ").strip().lower() == "y":
                break
        
        # Small delay between steps for better UX
        if i < total_steps:
            time.sleep(0.5)
    
    print()
    print("=" * 70)
    print()
    
    # Final summary
    print("📊 Workflow Summary")
    print("=" * 70)
    
    if success_count == total_steps:
        print_success("All modders completed successfully!")
        print_info("Next step: Run 'Repack OBB' (option 8) to create the final modified OBB")
        return True
    else:
        print_warning(f"Completed {success_count}/{total_steps} modders. Some modders may have failed.")
        return success_count > 0

def cleanup():
    """Clean up temporary folders"""
    print_step("Cleaning Up")
    
    folders_to_clean = [
        OUTPUT_DIR / "unpacked_obb", 
        OUTPUT_DIR / "tmp",
        OUTPUT_DIR / "temp_combined",  # Added for combined PAK operations
        OUTPUT_DIR / "unpacked_gamepatch",  # Old EmoteModder folder
        OUTPUT_DIR / "edited_gamepatch",    # Old EmoteModder folder
        OUTPUT_HITEFFECT_RESULTS,          # Old HitEffect results folder
        OUTPUT_DIR / "CreditAdder" / "results"  # Old CreditAdder results folder
    ]
    
    for folder in folders_to_clean:
        if folder.exists():
            try:
                shutil.rmtree(folder)
                print_success(f"Cleaned {folder.name} folder")
            except Exception as e:
                print_info(f"Could not clean {folder.name}: {e}")
    
    print_success("Cleanup completed!")

# ───── COMMAND LINE INTERFACE ─────────────────────────────────────────────────────

def main():
    """Main entry point - SIMPLIFIED & AUTOMATED"""
    if len(sys.argv) > 1:
        # Command line mode
        command = sys.argv[1]
        try:
            if command == "unpack-obb":
                print_step("Unpacking OBB", "📦")
                unpack_obb()
            elif command == "mod-skin":
                print_step("Apply Mod Skin (Fully Automated)", "🎨")
                mod_skin()
            elif command == "hit-effect":
                print_step("Hit Effect (Fully Automated)", "🔫")
                HitModder().process_hit_mods()
            elif command == "killfeed":
                print_step("Killfeed Modder", "💀")
                KillfeedModder().process_killfeed_complete()
            elif command == "lootbox":
                print_step("Lootbox Modder", "🎁")
                LootboxModder().process_modskin_mods()
            elif command == "emote":
                print_step("Emote Modder", "🎭")
                EmoteModder().process_emote_modification()
            elif command == "credit-adder":
                print_step("Credit Adder", "💰")
                CreditAdder().extract_credit_uexp()
            elif command == "repack-obb":
                print_step("Repacking OBB", "📱")
                repack_obb()
            elif command == "cleanup":
                print_step("Cleaning Up", "🧹")
                cleanup()
            elif command == "complete-workflow":
                print_step("Complete Workflow - All Modders", "🚀")
                complete_workflow()
            else:
                print_error(f"Unknown command: {command}")
                print("Available commands:")
                print("  • unpack-obb       - Extract OBB file")
                print("  • mod-skin          - Auto: unpack zsdic → mod → null → repack")
                print("  • hit-effect        - Auto: unpack mini → mod → null → repack")
                print("  • killfeed          - Auto: unpack gamepatch → mod → repack")
                print("  • lootbox           - Auto: unpack corepatch → mod → repack")
                print("  • emote             - Auto: unpack gamepatch → mod → repack")
                print("  • credit-adder      - Extract 00067063.uexp")
                print("  • complete-workflow - Run ALL modders (after OBB unpack)")
                print("  • repack-obb        - Create final OBB")
                print("  • cleanup           - Remove temp files")
                print("\n💡 All commands are fully automated!")
        except KeyboardInterrupt:
            print("\n❌ Operation cancelled by user")
        except Exception as e:
            print_error(f"Unexpected error: {e}")
    else:
        # Interactive mode
        interactive_menu()

# ───── ADDITIONAL CLASSES ──────────────────────────────────────────────

# GUI imports removed for mobile
# import threading
# from PIL import Image, ImageTk, ImageDraw, ImageFont
# import webbrowser
from datetime import datetime
import psutil
import zlib
import gzip
import io
from typing import Optional, List, Tuple, Dict

# PAK Tool functionality - COMPLETE IMPLEMENTATION FOR KILLFEED
class PAKToolAdvanced:
    """Advanced PAK Tool with XOR decoding for gamepatch unpacking/repacking"""
    
    def __init__(self):
        self.sig2key = {
            bytes.fromhex("9DC7"): bytes.fromhex("E55B4ED1"),
        }
        
        self.magic_ext = {
            0x9e2a83c1: ".uasset",
            0x61754c1b: ".lua", 
            0x090a0d7b: ".dat",
            0x007bfeff: ".dat",
            0x200a0d7b: ".dat",
            0x27da0020: ".res",
            0x00000001: ".res",
            0x7bbfbbef: ".res",
            0x44484b42: ".bnk",
        }
        
        self.zlib_headers = [b"\x78\x01", b"\x78\x5E", b"\x78\x9C", b"\x78\xDA"]
        self.gzip_header = b"\x1F\x8B"
        self.min_result_size = 32
        self.max_offset_try = 8
        
        # Set up directories based on the new structure
        self.unpack_dir = OUTPUT_MODSKIN_UNPACKED
        self.edited_dir = OUTPUT_MODSKIN_EDITED
        self.results_dir = OUTPUT_MODSKIN_RESULTS
        
        # Create directories if they don't exist
        for d in [self.unpack_dir, self.edited_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def is_sig_at(self, data: bytes, i: int) -> Optional[bytes]:
        """Check if signature exists at position"""
        if i + 2 > len(data):
            return None
        return self.sig2key.get(data[i:i+2], None)
    
    def xor_decode_with_feedback(self, data: bytes) -> bytes:
        """Decode encoded data using feedback XOR algorithm"""
        out = bytearray()
        key = None
        seg_pos = 0
        seg_start_out = 0
        i = 0
        L = len(data)
        
        while i < L:
            k = self.is_sig_at(data, i)
            if k is not None:
                key = k
                seg_pos = 0
                seg_start_out = len(out)
            if key is not None:
                if seg_pos < 4:
                    o = data[i] ^ key[seg_pos]
                else:
                    fb_index = seg_start_out + (seg_pos - 4)
                    o = data[i] ^ out[fb_index]
                out.append(o)
                seg_pos += 1
                i += 1
            else:
                out.append(data[i])
                i += 1
        return bytes(out)
    
    def xor_reencode_from_original(self, encoded_original: bytes, decoded_modified: bytes) -> bytes:
        """Re-encode modified decoded bytes using original encoded positions"""
        assert len(encoded_original) == len(decoded_modified)
        out_enc = bytearray()
        key = None
        seg_pos = 0
        seg_start_out = 0
        L = len(decoded_modified)
        
        for i in range(L):
            k = self.is_sig_at(encoded_original, i)
            if k is not None:
                key = k
                seg_pos = 0
                seg_start_out = i
            if key is not None:
                if seg_pos < 4:
                    b = decoded_modified[i] ^ key[seg_pos]
                else:
                    fb_index = seg_start_out + (seg_pos - 4)
                    b = decoded_modified[i] ^ decoded_modified[fb_index]
                out_enc.append(b)
                seg_pos += 1
            else:
                out_enc.append(decoded_modified[i])
        return bytes(out_enc)
    
    def guess_extension(self, blob: bytes) -> str:
        """Guess file extension from magic bytes"""
        if len(blob) < 4:
            return ".uexp"
        magic = int.from_bytes(blob[:4], "little")
        return self.magic_ext.get(magic, ".uexp")
    
    def is_valid_zlib_header(self, b1: int, b2: int) -> bool:
        """Check if bytes form valid zlib header"""
        if (b1 & 0x0F) != 8:
            return False
        cmf_flg = (b1 << 8) | b2
        return (cmf_flg % 31) == 0
    
    def try_decompress_at(self, buf: bytes, start: int, max_offset: int = None) -> Optional[dict]:
        """Try to decompress zlib/gzip at position"""
        if max_offset is None:
            max_offset = self.max_offset_try
            
        length = len(buf)
        modes = [("zlib", 15), ("gzip", 31)]
        
        for ofs in range(0, max_offset + 1):
            s = start + ofs
            if s >= length - 2:
                break
            for mode_name, wbits in modes:
                if mode_name == "zlib":
                    b1 = buf[s]
                    if b1 != 0x78:
                        continue
                    b2 = buf[s + 1]
                    if not self.is_valid_zlib_header(b1, b2):
                        continue
                if mode_name == "gzip":
                    if s + 1 >= length:
                        continue
                    if not (buf[s] == 0x1F and buf[s + 1] == 0x8B):
                        continue
                try:
                    d = zlib.decompressobj(wbits)
                    res = d.decompress(buf[s:])
                    res += d.flush()
                    consumed = len(buf[s:]) - len(d.unused_data)
                    if not d.eof:
                        continue
                    if consumed <= 0 or res is None or len(res) < self.min_result_size:
                        continue
                    return {"result": res, "consumed": consumed, "mode": mode_name, "ofs": ofs}
                except Exception:
                    continue
        return None
    
    def try_uncompressed_at(self, buf: bytes, start: int, max_offset: int = None) -> Optional[dict]:
        """Try to detect uncompressed files at position"""
        if max_offset is None:
            max_offset = self.max_offset_try
            
        length = len(buf)
        
        for ofs in range(0, max_offset + 1):
            s = start + ofs
            if s >= length - 4:
                break
                
            # Check for known magic bytes
            magic = int.from_bytes(buf[s:s+4], "little")
            if magic in self.magic_ext:
                # Found a known file type, try to determine size
                # Look for the next file signature to determine size
                next_file_start = s + 4
                file_size = 65536  # Default size
                
                # Try to find the next file by looking for magic bytes
                for next_pos in range(next_file_start, min(next_file_start + 65536, length - 4)):
                    next_magic = int.from_bytes(buf[next_pos:next_pos+4], "little")
                    if next_magic in self.magic_ext:
                        file_size = next_pos - s
                        break
                
                # Ensure we don't exceed buffer bounds
                file_size = min(file_size, length - s)
                
                # Extract the file data
                res = buf[s:s+file_size]
                
                return {
                    "result": res, 
                    "consumed": file_size, 
                    "mode": "raw", 
                    "ofs": ofs
                }
        
        return None
    
    def compress_by_mode(self, raw_bytes: bytes, mode: str) -> bytes:
        """Compress bytes using specified mode"""
        if mode == "zlib":
            return zlib.compress(raw_bytes, level=9)
        elif mode == "gzip":
            bio = io.BytesIO()
            with gzip.GzipFile(fileobj=bio, mode="wb") as gzf:
                gzf.write(raw_bytes)
            return bio.getvalue()
        else:
            return zlib.compress(raw_bytes, level=9)
    
    def scan_and_extract_smart(self, data: bytes, out_dir: Path, manifest_path: Path):
        """Scan and extract compressed streams"""
        count = 0
        pos = 0
        length = len(data)
        entries = []
        
        def find_next_candidate(p):
            idxs = []
            i = data.find(b"\x78", p)
            if i != -1:
                idxs.append(i)
            j = data.find(self.gzip_header, p)
            if j != -1:
                idxs.append(j)
            return min(idxs) if idxs else -1
        
        print(f"{'Offset':>10} | {'Size':>6} | {'Mode':<5} | {'Name':<20}")
        print("" + "-" * 60 + "")
        
        while True:
            cand = find_next_candidate(pos)
            if cand == -1 or cand >= length - 2:
                break
            trial = self.try_decompress_at(data, cand, self.max_offset_try)
            if trial:
                res = trial["result"]
                consumed = trial["consumed"]
                ofs = trial["ofs"]
                mode = trial["mode"]
                
                count += 1
                ext = self.guess_extension(res)
                
                range_start = (count - 1) // 1000 * 1000
                range_end = range_start + 1000
                subdir = out_dir / f"{range_start}_{range_end}"
                subdir.mkdir(parents=True, exist_ok=True)
                
                fname = f"{count:06d}{ext}"
                outpath = subdir / fname
                outpath.write_bytes(res)
                
                relpath = str(outpath.relative_to(out_dir))
                start_pos = cand + ofs
                entries.append({
                    "index": count,
                    "start": start_pos,
                    "consumed": consumed,
                    "relpath": relpath,
                    "ext": ext,
                    "mode": mode,
                })
                
                if count % 100 == 0:
                    print(f"0x{start_pos:08X} | {len(res):6d} | {mode:<5} | {fname:<20}")
                
                pos = start_pos + consumed
            else:
                pos = cand + 1
        
        print("" + "-" * 60 + "")
        print_success(f"Total {count} files unpacked → {out_dir}")
        
        # Create manifest.json
        manifest = {"total": count, "entries": entries}
        manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        print_success(f"Manifest saved → {manifest_path}")
        
        return count
    
    def unpack_pak_advanced(self, pak_path: Path, output_path: Path):
        """Advanced PAK unpacking with XOR decoding"""
        try:
            print(f"Unpacking: {pak_path.name}")
            print("Decoding XOR...")
            
            data_enc = pak_path.read_bytes()
            decoded = self.xor_decode_with_feedback(data_enc)
            
            print("Scanning and extracting...")
            manifest_path = output_path / "manifest.json"
            count = self.scan_and_extract_smart(decoded, output_path, manifest_path)
            
            print_success(f"Unpack finished: {count} files → {output_path}")
            return True
            
        except Exception as e:
            print_error(f"Unpack failed: {e}")
            return False
    
    def repack_pak_advanced(self, pak_path: Path, unpack_dir: Path, repack_dir: Path, output_path: Path):
        """Advanced PAK repacking with XOR re-encoding"""
        try:
            manifest_path = unpack_dir / "manifest.json"
            if not manifest_path.exists():
                print_error("manifest.json not found")
                return False
            
            print("Decoding original file...")
            data_enc_orig = pak_path.read_bytes()
            decoded = bytearray(self.xor_decode_with_feedback(data_enc_orig))
            
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest.get("entries", [])
            
            # Find repack files - Map by relative path
            # Priority: edited files (repack_dir) > original files (unpack_dir)
            repack_files_map = {}
            
            # First, add all original unpacked files
            for p in unpack_dir.rglob("*"):
                if p.is_file() and p.name != "manifest.json":
                    rel = p.relative_to(unpack_dir)
                    rel_str = str(rel)
                    repack_files_map[rel_str] = p
                    rel_forward = rel_str.replace('\\', '/')
                    repack_files_map[rel_forward] = p
                    repack_files_map.setdefault(p.name, p)
            
            # Then, override with edited files (if they exist)
            for p in repack_dir.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(repack_dir)
                    rel_str = str(rel)
                    repack_files_map[rel_str] = p  # Override original
                    rel_forward = rel_str.replace('\\', '/')
                    repack_files_map[rel_forward] = p
                    repack_files_map[p.name] = p  # Override by filename too
            
            if not repack_files_map:
                print_error("No files found in repack directory")
                return False
            
            # Count files with path separators
            files_with_path = [k for k in repack_files_map.keys() if ('\\' in k or '/' in k)]
            print(f"Found {len(files_with_path)} files in repack directory")
            if files_with_path:
                print(f"Sample files: {files_with_path[:3]}")
            
            repacked_cnt = skipped_cnt = not_found_cnt = 0
            
            print("Processing entries...")
            for e in entries:
                relpath = e["relpath"]
                start = int(e["start"])
                consumed = int(e["consumed"])
                mode = e.get("mode", "zlib")
                
                # Try to find file by relpath first, then by filename
                src_edit = repack_files_map.get(relpath)
                if not src_edit:
                    # Try with forward slashes
                    src_edit = repack_files_map.get(relpath.replace('\\', '/'))
                if not src_edit:
                    src_edit = repack_files_map.get(Path(relpath).name)
                if not src_edit:
                    not_found_cnt += 1
                    if not_found_cnt <= 3:  # Show first 3 missing files
                        print(f"⚠️  Not found: {relpath}")
                    continue
                
                try:
                    raw = src_edit.read_bytes()
                    comp = self.compress_by_mode(raw, mode)
                    if len(comp) <= consumed:
                        decoded[start:start+len(comp)] = comp
                        if len(comp) < consumed:
                            decoded[start+len(comp):start+consumed] = b"\x00" * (consumed - len(comp))
                        repacked_cnt += 1
                        if repacked_cnt % 10 == 0:
                            print(f"Repacked {repacked_cnt} files...")
                    else:
                        skipped_cnt += 1
                except Exception as ex:
                    skipped_cnt += 1
            
            print(f"Summary: {repacked_cnt} repacked, {skipped_cnt} skipped, {not_found_cnt} not found")
            
            if repacked_cnt == 0:
                print_error("No files repacked")
                return False
            
            print("Re-encoding XOR...")
            encoded_final = self.xor_reencode_from_original(data_enc_orig, bytes(decoded))
            output_path.write_bytes(encoded_final)
            
            print_success(f"Repack complete → {output_path}")
            return True
            
        except Exception as e:
            print_error(f"Repack failed: {e}")
            return False

# Mini OBB PAK Unpacker functionality - COMPLETE IMPLEMENTATION
class MiniOBBUnpacker:
    """Mini OBB PAK Unpacker for mini_obb.pak files"""
    
    def __init__(self):
        self.signature = b"\xCD\xEE\x61\x2C"
        self.expected_magic = b"\x28\xB5\x2F\xFD"
        self.files_per_folder = 1000
        self.tmp_dir = OUTPUT_DIR / "tmp"
        
        self.signatures = {
            b'\x7B\x0D\x0A\x09\x22\x46\x69\x6C\x65\x56\x65\x72\x73\x69\x6F\x6E': ".json",
            b'\x20\x00\xDA\x27\x14\x00\x00\x00\x00\x00\x02\x00\x52\x65\x73\x42': ".res",
            b'\x1B\x4C\x75\x61\x53\x00\x19\x93\x0D\x0A\x1A\x0A\x04\x04\x04\x08': ".lua",
            b'\xC1\x83\x2A\x9E\xF9\xFF\xFF\xFF\x00\x00\x00\x00\x00\x00\x00\x00': ".uasset",
            b'\x42\x4B\x48\x44\x18\x00\x00\x00\x7D': ".bnk",
            b'\x7B\x0D\x0A\x20\x20\x22\x46\x69\x6C\x65\x56\x65\x72\x73\x69\x6F': ".json",
            b'\xFF\xFE\x7B\x00\x0D\x00\x09\x00\x22\x00\x46\x00\x69\x00': ".json"
        }
        
        # Create tmp directory
        self.tmp_dir.mkdir(parents=True, exist_ok=True)
    
    def find_xor_key(self, sig4: bytes, magic4: bytes) -> bytes:
        """Find XOR key from signature and magic"""
        return bytes([sig4[i] ^ magic4[i] for i in range(4)])
    
    def xor_feedback_block(self, data: bytes, key: bytes) -> bytes:
        """XOR feedback decryption"""
        key_len = len(key)
        out = bytearray(len(data))
        prev = [0] * key_len
        for i in range(len(data)):
            if i < key_len:
                out[i] = data[i] ^ key[i]
                prev[i] = out[i]
            else:
                k = i % key_len
                out[i] = data[i] ^ prev[k]
                prev[k] = out[i]
        return bytes(out)
    
    def detect_extension(self, data: bytes) -> str:
        """Detect file extension from signature"""
        for sig, ext in self.signatures.items():
            if data.startswith(sig):
                return ext
        return ".uexp"
    
    def decompress_zstd(self, data: bytes) -> bytes:
        """Decompress ZSTD data"""
        dctx = zstd.ZstdDecompressor()
        try:
            return dctx.decompress(data)
        except zstd.ZstdError:
            return data
    
    def find_all_occurrences(self, data, pattern: bytes):
        """Find all occurrences of pattern in data"""
        return [m.start() for m in re.finditer(re.escape(pattern), data)]
    
    def compress_to_target_size(self, data: bytes, target_size: int) -> bytes:
        """Compress data to target size using mini script logic"""
        if target_size <= 0:
            print_error("Invalid target size for compression")
            return None
        # Start from high compression to low for better fitting
        levels = range(22, 0, -3)
        for level in levels:
            cctx = zstd.ZstdCompressor(level=level)
            compressed = cctx.compress(data)
            if len(compressed) <= target_size:
                return self.add_skippable_padding(compressed, target_size - len(compressed))
        # Try ultra compression with more params
        cctx = zstd.ZstdCompressor(level=22, threads=-1)
        compressed = cctx.compress(data)
        if len(compressed) <= target_size:
            return self.add_skippable_padding(compressed, target_size - len(compressed))
        # Cannot compress to target size
        print_error("Cannot compress to target size even with max compression")
        return None
    
    def add_skippable_padding(self, compressed: bytes, pad_len: int) -> bytes:
        """Add skippable padding to compressed data"""
        if pad_len <= 0:
            return compressed
        result = bytearray(compressed)
        while pad_len > 0:
            frame_content_len = min(pad_len - 8, 1024 * 1024)  # cap content to 1MB
            if frame_content_len < 0:
                # For small pads <8, add a frame with 0 content
                magic = b'\x50\x2A\x4D\x18'
                size_bytes = struct.pack('<I', 0)
                skip_frame = magic + size_bytes + b'\x00' * 0
                result += skip_frame
                pad_len -= 8
            else:
                magic = b'\x50\x2A\x4D\x18'
                size_bytes = struct.pack('<I', frame_content_len)
                skip_frame = magic + size_bytes + b'\x00' * frame_content_len
                result += skip_frame
                pad_len -= (8 + frame_content_len)
        if pad_len < 0:
            result = result[:len(result) + pad_len]  # trim if over
        return bytes(result)
    
    def unpack_mini_obb(self, pak_path: str = None, output_path: str = None, target_index: int = 62759):
        """Unpack only the specific file from mini_obb.pak - UPDATED PATHS"""
        
        # First check input/gamepaks directory (new primary location)
        mini_pak_file = GAMEPAKS_DIR / "mini_obb.pak"
        
        if mini_pak_file.exists():
            print_info(f"Using mini_obb.pak from input/gamepaks: {mini_pak_file}")
            pak_file = mini_pak_file
        else:
            # Fallback to unpacked OBB directory
            unpacked_pak_dir = OUTPUT_OBB_UNPACKED / "ShadowTrackerExtra" / "Content" / "Paks"
            mini_pak_file = unpacked_pak_dir / "mini_obb.pak"
            
            if mini_pak_file.exists():
                print_info(f"Using mini_obb.pak from unpacked OBB: {mini_pak_file}")
                pak_file = mini_pak_file
            else:
                # Use provided path or default
                if pak_path is None:
                    pak_path = "input/mini_obb.pak"
                
                pak_file = Path(pak_path)
                
                # If PAK not found, try to extract from OBB
                if not pak_file.exists():
                    print_info("PAK file not found, extracting from OBB...")
                    try:
                        obb_files = list(OBB_DIR.glob("*.obb"))  # Now looks in OBB_DIR
                        if not obb_files:
                            print_error(f"No OBB file found in {OBB_DIR}")
                            return False
                        
                        obb_path = obb_files[0]
                        print_info(f"Found OBB file: {obb_path.name}")
                        
                        # Extract mini_obb.pak from OBB
                        with zipfile.ZipFile(obb_path, 'r') as zf:
                            pak_files = [f for f in zf.namelist() if f.endswith('mini_obb.pak')]
                            if not pak_files:
                                print_error("mini_obb.pak not found in OBB file")
                                return False
                            
                            print_info(f"Extracting {pak_files[0]} from OBB...")
                            zf.extract(pak_files[0], self.tmp_dir)
                            pak_file = self.tmp_dir / pak_files[0]
                            print_success(f"Extracted to: {pak_file}")
                    except Exception as e:
                        print_error(f"Failed to extract from OBB: {e}")
                        return False
        
        # Check if PAK file exists
        if not pak_file.exists():
            print_error(f"PAK file not found: {pak_file}")
            return False
        
        output_dir = Path(output_path) if output_path else OUTPUT_HITEFFECT_UNPACKED  # Default to HitEffect
        output_dir.mkdir(parents=True, exist_ok=True)
        
        print_info(f"Unpacking Mini OBB PAK: {pak_file}")
        print_info(f"Output directory: {output_dir}")
        print_info(f"Target file: {target_index:08d}.uexp")
        
        # Read PAK file
        data = pak_file.read_bytes()
        print_info(f"File size: {len(data):,} bytes")
        
        # Find blocks
        offsets = self.find_all_occurrences(data, self.signature)
        if not offsets:
            print_error("No blocks found!")
            return False
        
        print_info(f"Found {len(offsets)} blocks")
        
        # Check if target index is valid
        if target_index >= len(offsets):
            print_error(f"Target index {target_index} is out of range!")
            print_error(f"Maximum available index: {len(offsets)-1}")
            return False
        
        print_info("Extracting only target file...")
        
        try:
            # Get the specific block
            offset = offsets[target_index]
            
            # Get block data
            end = offsets[target_index+1] if target_index+1 < len(offsets) else len(data)
            block = data[offset:end]
            
            # Find XOR key
            key = self.find_xor_key(block[:4], self.expected_magic)
            
            # Decode with XOR feedback
            decoded = self.xor_feedback_block(block, key)
            
            # Decompress with ZSTD
            decompressed = self.decompress_zstd(decoded)
            
            # Save file
            file_name = output_dir / f"{target_index:08d}.uexp"
            file_name.write_bytes(decompressed)
            
            print_success(f"Successfully extracted {file_name}")
            print_info(f"File size: {len(decompressed):,} bytes")
            
            return True
            
        except Exception as e:
            print_error(f"Error extracting block {target_index}: {e}")
            return False
    
    def repack_mini_obb(self, input_path: str = None, output_path: str = None):
        """Repack mini_obb.pak from unpacked files"""
        # ✅ UPDATED: Use new directory structure
        input_dir = Path(input_path) if input_path else OUTPUT_HITEFFECT_UNPACKED
        output_file = Path(output_path) if output_path else OUTPUT_HITEFFECT_RESULTS / "mini_obb.pak"
        
        # Check if input directory exists
        if not input_dir.exists():
            print_error(f"Input directory not found: {input_dir}")
            return False
        
        # Create output directory
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        print_info(f"Repacking Mini OBB PAK from {input_dir}")
        print_info(f"Output file: {output_file}")
        
        # Find all UEXP files from the input directory
        uexp_files = list(input_dir.glob("*.uexp"))
        if uexp_files:
            print_info(f"Using UEXP files from {input_dir}")
        else:
            print_error(f"No UEXP files found in {input_dir}")
            return False
        
        if not uexp_files:
            print_error("No UEXP files found to repack!")
            return False
        
        print_info(f"Found {len(uexp_files)} UEXP files to repack")
        
        # Original PAK file path - check in gamepaks directory first (new primary location)
        original_pak = GAMEPAKS_DIR / "mini_obb.pak"
        
        # Fallback to OBB directory if not found
        if not original_pak.exists():
            original_pak = OBB_DIR / "mini_obb.pak"
            if not original_pak.exists():
                # Fallback to input directory if not found
                original_pak = Path("input/mini_obb.pak")
                if not original_pak.exists():
                    print_error(f"Original PAK file not found in {GAMEPAKS_DIR}, {OBB_DIR}, or input/")
                    return False
        
        print_info(f"Using original PAK file: {original_pak}")
        
        # Read original PAK data
        original_data = original_pak.read_bytes()
        print_info(f"Original PAK size: {len(original_data):,} bytes")
        
        # Find blocks in original PAK
        offsets = self.find_all_occurrences(original_data, self.signature)
        if not offsets:
            print_error("No blocks found in original PAK!")
            return False
        
        print_info(f"Found {len(offsets)} blocks in original PAK")
        
        # Create temporary output file
        temp_output = output_file.with_suffix('.tmp')
        
        # Copy original file as base
        try:
            shutil.copy2(original_pak, temp_output)
            print_success("Copied original file as base")
        except Exception as e:
            print_error(f"Error copying original file: {e}")
            return False
        
        # Process each UEXP file
        modified_count = 0
        chunk_size = 64 * 1024  # 64KB chunk size
        
        try:
            with open(temp_output, "r+b") as outfh:
                for uexp_file in uexp_files:
                    try:
                        # Extract file index from filename (e.g., "00062759.uexp" -> 62759)
                        file_index = int(uexp_file.stem)
                        
                        if file_index >= len(offsets):
                            print_error(f"File index {file_index} out of range!")
                            continue
                        
                        print_info(f"Repacking {uexp_file.name} (index {file_index})...")
                        
                        # Read modified UEXP file
                        modified_content = uexp_file.read_bytes()
                        
                        # Get original block boundaries
                        start_offset = offsets[file_index]
                        end_offset = offsets[file_index+1] if file_index+1 < len(offsets) else len(original_data)
                        original_chunk_size = end_offset - start_offset
                        
                        # Compress to target size using mini script logic
                        compressed_content = self.compress_to_target_size(modified_content, original_chunk_size)
                        if compressed_content is None:
                            print_error(f"Cannot compress {uexp_file.name} to target size, skipping...")
                            continue
                        
                        # Read original signature for XOR key
                        with open(original_pak, "rb") as infh:
                            infh.seek(start_offset)
                            sig4 = infh.read(4)
                            if len(sig4) < 4:
                                print_error(f"Cannot read signature at {start_offset}, skipping...")
                                continue
                        
                        key = self.find_xor_key(sig4, self.expected_magic)
                        
                        # Write XOR-encoded data
                        outfh.seek(start_offset)
                        klen = len(key)
                        prev = list(key)
                        ptr = 0
                        written = 0
                        
                        while ptr < len(compressed_content):
                            slice_len = min(chunk_size, len(compressed_content) - ptr)
                            src_slice = compressed_content[ptr:ptr+slice_len]
                            out_slice = bytearray(slice_len)
                            base_idx = ptr % klen
                            
                            for j in range(slice_len):
                                idx = (base_idx + j) % klen
                                r = src_slice[j] ^ prev[idx]
                                out_slice[j] = r
                                prev[idx] = src_slice[j]
                            
                            outfh.write(out_slice)
                            ptr += slice_len
                            written += slice_len
                        
                        modified_count += 1
                        print_success(f"Repacked {uexp_file.name} ({len(modified_content):,} -> {len(compressed_content):,} bytes)")
                        
                    except Exception as e:
                        print_error(f"Error repacking {uexp_file.name}: {e}")
                        continue
            
            # Replace original with repacked file
            temp_output.replace(output_file)
            
            # Check size like mini file
            if output_file.stat().st_size != original_pak.stat().st_size:
                print_warning("Repacked file size differs from original! May cause issues.")
            else:
                print_success("Repacked file size matches original.")
            
            print_success(f"Repacked {modified_count} files successfully")
            return True
            
        except Exception as e:
            print_error(f"Error during repacking: {e}")
            return False

# Hit Modder functionality - COMPLETE IMPLEMENTATION
class HitModder:
    """Hit Modder for BGMI skin modifications using hit1.txt and hit.txt"""
    
    def __init__(self):
        self.home_dir = Path.home()
        
        # ✅ UPDATED: Correct directories for HitEffect (no results needed)
        self.unpack_dir = OUTPUT_HITEFFECT_UNPACKED
        self.edited_dir = OUTPUT_HITEFFECT_EDITED
        
        # Create directories (only unpack and edited)
        for d in [self.unpack_dir, self.edited_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def dec_to_le4_hex(self, n_str: str) -> str:
        """Convert decimal to little-endian 4-byte hex"""
        n_str = n_str.strip()
        if not n_str:
            raise ValueError("empty decimal")
        n = int(n_str, 10)
        if n < 0 or n > 0xFFFFFFFF:
            raise ValueError("decimal out of 32-bit range")
        return n.to_bytes(4, 'little').hex()
    
    def parse_mapping_file(self, path: Path) -> set:
        """Parse mapping file to extract hex codes"""
        out = set()
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return out
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            if '|' in ln:
                parts = [p.strip() for p in ln.split('|')]
                if len(parts) >= 2 and parts[1]:
                    h = parts[1].lower().replace("0x","").strip()
                    h = ''.join(ch for ch in h if ch.isalnum())
                    if h and len(h) % 2 == 0 and all(c in '0123456789abcdef' for c in h):
                        out.add(h)
            else:
                parts = ln.split()
                if len(parts) >= 2:
                    h = parts[1].lower().replace("0x","").strip()
                    h = ''.join(ch for ch in h if ch.isalnum())
                    if h and len(h) % 2 == 0 and all(c in '0123456789abcdef' for c in h):
                        out.add(h)
        return out
    
    def process_hit_mods(self):
        """Process hit modifications - FULLY AUTOMATED"""
        # Initialize logger with dashboard - only show relevant phases (no MOD_APPLY, no OPTIMIZE)
        logger = ColorfulConsoleLogger(silent_mode=True, phases=["UNPACK", "HIT_APPLY", "FINALIZE"], title="HIT EFFECT MODDING")
        logger.print_full_dashboard()
        
        try:
            # Step 1: Auto unpack mini_obb.pak
            logger.update_phase("UNPACK", "🔄 ACTIVE", 0, "Unpacking mini_obb.pak...")
            
            # Suppress MiniOBBUnpacker output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
            
            try:
                mini_unpacker = MiniOBBUnpacker()
                unpack_result = mini_unpacker.unpack_mini_obb()
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            if not unpack_result:
                logger.update_phase("UNPACK", "❌ FAILED", 0, "Failed to unpack mini_obb.pak!")
                logger.log_error("HIT_MODDER", "Failed to unpack mini_obb.pak!")
                return False
            
            logger.update_phase("UNPACK", "✅ DONE", 100, "Unpacked successfully")
            
            # Load hit1.txt for ID pairs
            hit1_file = Path("contents/hit1.txt")
            if not hit1_file.exists():
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "Hit1 file not found")
                logger.log_error("HIT_MODDER", f"Hit1 file not found: {hit1_file}")
                return False
            
            # Load hit.txt for mapping
            hit_file = Path("contents/hit.txt")
            if not hit_file.exists():
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "Hit file not found")
                logger.log_error("HIT_MODDER", f"Hit file not found: {hit_file}")
                return False
            
            # Parse ID pairs from hit1.txt
            id_pairs = self.parse_id_pairs_file(hit1_file)
            if not id_pairs:
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "No valid ID pairs found")
                logger.log_error("HIT_MODDER", "No valid ID pairs found in hit1.txt")
                return False
            
            # Parse mapping from hit.txt
            mapping = self.parse_mapping_file(hit_file)
            if not mapping:
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "No valid mappings found")
                logger.log_error("HIT_MODDER", "No valid mappings found in hit.txt")
                return False
            
            # ✅ UPDATED: Use new directory structure
            source_dir = OUTPUT_HITEFFECT_UNPACKED
            if not source_dir.exists():
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "Source directory not found")
                logger.log_error("HIT_MODDER", f"Source directory not found: {source_dir}")
                return False
            
            # Check hex1 presence in correct directory
            logger.update_phase("HIT_APPLY", "🔄 ACTIVE", 20, f"Scanning files...")
            id_pairs = self.check_hex1_presence(id_pairs, [source_dir])
            
            # Count how many pairs are marked as OK
            ok_pairs = [pair for pair in id_pairs if pair[2] == "OK"]
            
            if not ok_pairs:
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "No valid pairs found")
                logger.log_error("HIT_MODDER", "No valid pairs found in files - no modifications will be applied")
                return False
            
            # Step 3: Process files from correct source directory
            logger.update_phase("HIT_APPLY", "🔄 ACTIVE", 50, f"Applying modifications to {len(ok_pairs)} pairs...")
            modified_count = self.process_directory_files(source_dir, id_pairs, mapping)
            
            if modified_count == 0:
                logger.update_phase("HIT_APPLY", "❌ FAILED", 0, "No files were modified")
                logger.log_error("HIT_MODDER", "No files were modified!")
                return False
            
            logger.update_phase("HIT_APPLY", "✅ DONE", 100, f"{modified_count} files modified")
            logger.update_phase("FINALIZE", "✅ DONE", 100, "Hit Effect files created successfully")
            
            # Set files processed count
            logger.set_files_processed(modified_count)
            
            logger.print_footer(success=True)
            return True
            
        except Exception as e:
            logger.update_phase("HIT_APPLY", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
            logger.log_error("HIT_MODDER", f"Hit Modder failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def process_directory_files(self, directory: Path, id_pairs: list, mapping: dict):
        """Process files in a directory for hit modifications"""
        modified_count = 0
        
        # Create edited output directory
        edited_dir = OUTPUT_HITEFFECT_EDITED
        edited_dir.mkdir(parents=True, exist_ok=True)
        
        # Recursive search for all files
        for file_path in directory.rglob("*"):
            if file_path.is_file() and file_path.suffix.lower() in ['.uexp', '.uasset']:
                try:
                    print_info(f"Processing {file_path.name}...")
                    
                    # Read file content
                    content = file_path.read_bytes()
                    
                    # Apply modifications
                    modified_content = self.apply_hit_modifications(content, id_pairs, mapping)
                    
                    if modified_content != content:
                        # Save modified file to edited_uexp folder
                        edited_file_path = edited_dir / file_path.name
                        edited_file_path.write_bytes(modified_content)
                        modified_count += 1
                        print_success(f"Modified {file_path.name} -> {edited_file_path}")
                    else:
                        print_info(f"No changes needed for {file_path.name}")
                        
                except Exception as e:
                    print_error(f"Error processing {file_path}: {e}")
                    continue
        
        return modified_count
    
    def parse_id_pairs_file(self, hit1_file: Path):
        """Parse ID pairs from hit1.txt file"""
        id_pairs = []
        try:
            with hit1_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            a, b = parts[0].strip(), parts[1].strip()
                            if a and b:
                                try:
                                    # Convert decimal to hex
                                    ha = self.dec_to_le4_hex(a)
                                    hb = self.dec_to_le4_hex(b)
                                    id_pairs.append([ha, hb, "NO"])
                                except Exception as e:
                                    print_error(f"Invalid decimal in line {line_num}: {line} -> {e}")
                                    continue
        except Exception as e:
            print_error(f"Error reading hit1.txt: {e}")
        
        return id_pairs
    
    def check_hex1_presence(self, id_pairs: list, directories: list):
        """Check if hex1 exists in files"""
        print_info("Checking converted hex1 presence in files...")
        
        for pair in id_pairs:
            hex1 = pair[0]
            b1 = bytes.fromhex(hex1)
            found = False
            
            # Recursive search in all subdirectories
            for directory in directories:
                if not directory.exists():
                    continue
                for file_path in directory.rglob("*"):
                    if not file_path.is_file():
                        continue
                    try:
                        if b1 in file_path.read_bytes():
                            found = True
                            break
                    except Exception:
                        continue
                if found:
                    break
            
            if found:
                pair[2] = "OK"
                print_success(f"[OK] {hex1}")
            else:
                print_error(f"[NO] {hex1}")
        
        return id_pairs
    
    def apply_hit_modifications(self, content: bytes, id_pairs: list, mapping: dict):
        """Apply hit modifications - SKIP ZEROING FOR REPLACEMENT HEXES"""
        modified_content = content
        
        # Create set of hex2 values that should NOT be zeroed
        keep_hexes = {pair[1] for pair in id_pairs if pair[2] == "OK"}
        
        # Step 1: Apply ID pair replacements FIRST
        for pair in id_pairs:
            if pair[2] == "OK":
                hex1_bytes = bytes.fromhex(pair[0])
                hex2_bytes = bytes.fromhex(pair[1])
                
                if hex1_bytes in modified_content:
                    modified_content = modified_content.replace(hex1_bytes, hex2_bytes)
        
        # Step 2: Apply zeroing, but SKIP hex2 values
        for hex_code in mapping:
            # Skip if this hex is in our keep list (replacement targets)
            if hex_code in keep_hexes:
                continue
                
            try:
                hex_bytes = bytes.fromhex(hex_code)
                null_bytes = b'\x00' * len(hex_bytes)
                modified_content = modified_content.replace(hex_bytes, null_bytes)
            except ValueError:
                continue
        
        return modified_content

class KillfeedModder:
    """Complete Killfeed Modder with Unpack → Modify → Null → Repack"""
    
    def __init__(self):
        self.contents_dir = Path("contents")
        self.kill_file = self.contents_dir / "hit1.txt"
        self.killmsg_file = self.contents_dir / "killmsg.txt"
        self.max_compressed_size = 6689
    
    def process_killfeed_complete(self):
        """Complete killfeed workflow: Selective Extract → Modify → Null → Repack"""
        # Initialize logger with dashboard - only show relevant phases (no MOD_APPLY, no OPTIMIZE)
        logger = ColorfulConsoleLogger(silent_mode=True, phases=["UNPACK", "KILL_APPLY", "FINALIZE"], title="KILLFEED MODDING")
        logger.print_full_dashboard()
        
        try:
            # STEP 1: SELECTIVE EXTRACT (Only 000302.uasset)
            logger.update_phase("UNPACK", "🔄 ACTIVE", 0, "Extracting game_patch_4.0.0.20329.pak...")
            gamepatch_pak = Path("input/gamepaks/game_patch_4.0.0.20329.pak")
            if not gamepatch_pak.exists():
                logger.update_phase("UNPACK", "❌ FAILED", 0, "Gamepatch PAK not found")
                logger.log_error("KILLFEED", f"Gamepatch PAK not found: {gamepatch_pak}")
                return False
            
            unpacked_dir = Path("output/Killfeed/unpacked")
            unpacked_dir.mkdir(parents=True, exist_ok=True)
            
            # Suppress PAKToolAdvanced output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
            
            try:
                pak_tool = PAKToolAdvanced()
                
                # Check if already unpacked
                manifest_path = unpacked_dir / "manifest.json"
                if not manifest_path.exists():
                    unpack_result = pak_tool.unpack_pak_advanced(gamepatch_pak, unpacked_dir)
                else:
                    unpack_result = True
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            if not unpack_result:
                logger.update_phase("UNPACK", "❌ FAILED", 0, "Failed to unpack gamepatch PAK")
                logger.log_error("KILLFEED", "Failed to unpack gamepatch PAK")
                return False
            
            logger.update_phase("UNPACK", "✅ DONE", 100, "Files ready for processing")
            
            # STEP 2: LOAD ID PAIRS AND PATTERNS
            logger.update_phase("KILL_APPLY", "🔄 ACTIVE", 0, "Loading ID pairs and patterns...")
            
            if not self.kill_file.exists():
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "hit1.txt not found")
                logger.log_error("KILLFEED", f"hit1.txt not found: {self.kill_file}")
                return False
            
            if not self.killmsg_file.exists():
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "killmsg.txt not found")
                logger.log_error("KILLFEED", f"killmsg.txt not found: {self.killmsg_file}")
                return False
            
            # Load hit1.txt ID pairs
            kill_pairs = self.read_id_pairs(self.kill_file)
            if not kill_pairs:
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "No valid ID pairs in hit1.txt")
                logger.log_error("KILLFEED", "No valid ID pairs in hit1.txt")
                return False
            
            # Load killmsg.txt patterns
            killmsg_patterns = self.load_killmsg_patterns()
            if not killmsg_patterns:
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "No valid patterns in killmsg.txt")
                logger.log_error("KILLFEED", "No valid patterns in killmsg.txt")
                return False
            
            # Build replacement map
            logger.update_phase("KILL_APPLY", "🔄 ACTIVE", 30, f"Building replacement map from {len(kill_pairs)} pairs...")
            replacement_map = {}
            for pair in kill_pairs:
                if len(pair) >= 2:
                    hex1, hex2 = pair[0], pair[1]
                    id1 = str(int.from_bytes(bytes.fromhex(hex1), 'little'))
                    id2 = str(int.from_bytes(bytes.fromhex(hex2), 'little'))
                    
                    if id1 in killmsg_patterns and id2 in killmsg_patterns:
                        src_pattern = killmsg_patterns[id1]
                        dst_pattern = killmsg_patterns[id2]
                        replacement_map[(id1, id2)] = [(src_pattern, dst_pattern)]
            
            if not replacement_map:
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "No valid pattern mappings")
                logger.log_error("KILLFEED", "No valid pattern mappings")
                return False
            
            logger.update_phase("KILL_APPLY", "🔄 ACTIVE", 50, f"Created {len(replacement_map)} pattern mappings")
            
            # STEP 3: MODIFY AND APPLY NULLS
            logger.update_phase("KILL_APPLY", "🔄 ACTIVE", 60, "Modifying files and applying nulls...")
            
            edited_dir = Path("output/Killfeed/edited")
            edited_dir.mkdir(parents=True, exist_ok=True)
            
            modified_count = self.process_and_modify_files(unpacked_dir, edited_dir, replacement_map)
            
            if modified_count == 0:
                logger.update_phase("KILL_APPLY", "❌ FAILED", 0, "No files were modified")
                logger.log_error("KILLFEED", "No files were modified")
                return False
            
            logger.update_phase("KILL_APPLY", "✅ DONE", 100, f"{modified_count} files modified")
            
            # STEP 4: REPACK GAMEPATCH PAK
            logger.update_phase("FINALIZE", "🔄 ACTIVE", 0, "Repacking gamepatch PAK...")
            
            output_pak_dir = Path("output/Killfeed/results")
            output_pak_dir.mkdir(parents=True, exist_ok=True)
            output_pak = output_pak_dir / "game_patch_4.0.0.20329.pak"
            
            # Suppress PAKToolAdvanced output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
            
            try:
                repack_result = pak_tool.repack_pak_advanced(gamepatch_pak, unpacked_dir, edited_dir, output_pak)
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            if not repack_result:
                logger.update_phase("FINALIZE", "❌ FAILED", 0, "Failed to repack gamepatch PAK")
                logger.log_error("KILLFEED", "Failed to repack gamepatch PAK")
                return False
            
            logger.update_phase("FINALIZE", "✅ DONE", 100, f"Gamepatch PAK repacked: {output_pak.name}")
            
            # Set files processed count
            logger.set_files_processed(modified_count)
            
            logger.print_footer(success=True)
            
            return True
            
        except Exception as e:
            logger.update_phase("KILL_APPLY", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
            logger.log_error("KILLFEED", f"Killfeed Modder failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def read_id_pairs(self, file_path: Path):
        """Read ID pairs from hit1.txt"""
        pairs = []
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line:
                        parts = line.split(',')
                        if len(parts) == 2:
                            try:
                                id1 = int(parts[0].strip())
                                id2 = int(parts[1].strip())
                                hex1 = id1.to_bytes(4, 'little').hex()
                                hex2 = id2.to_bytes(4, 'little').hex()
                                pairs.append([hex1, hex2, "PENDING"])
                            except ValueError:
                                continue
        except Exception as e:
            print_error(f"Error reading {file_path}: {e}")
        
        return pairs
    
    def load_killmsg_patterns(self):
        """Load patterns from killmsg.txt"""
        patterns = {}
        
        try:
            with open(self.killmsg_file, 'r') as f:
                content = f.read().strip()
            
            lines = content.split('\n')
            for line in lines:
                line = line.strip()
                if '-' in line:
                    parts = line.split('-', 1)
                    id_part = parts[0].strip()
                    hex_part = parts[1].strip()
                    
                    try:
                        hex_bytes = bytes.fromhex(hex_part)
                        patterns[id_part] = hex_bytes
                    except ValueError:
                        continue
        except Exception as e:
            print_error(f"Error reading killmsg.txt: {e}")
        
        return patterns
    
    def process_and_modify_files(self, unpacked_dir: Path, edited_dir: Path, replacement_map: dict):
        """Process files with modifications and nulling - FIXED VERSION"""
        modified_count = 0
        
        # Find all files in unpacked directory (including subfolders)
        all_files = []
        for subfolder in unpacked_dir.iterdir():
            if subfolder.is_dir():
                for file_path in subfolder.iterdir():
                    if file_path.is_file():
                        all_files.append(file_path)
        
        print(f"Found {len(all_files)} files to process")
        
        for file_path in all_files:
            try:
                content = file_path.read_bytes()
                modified_content = self.apply_modifications(content, replacement_map)
                
                if modified_content != content:
                    # ⭐ FIX: Preserve subfolder structure in edited directory
                    # Get relative path from unpacked_dir
                    rel_path = file_path.relative_to(unpacked_dir)
                    
                    # Create same subfolder structure in edited_dir
                    edited_file = edited_dir / rel_path
                    edited_file.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Save modified file
                    edited_file.write_bytes(modified_content)
                    modified_count += 1
                    
                    # Apply nulls to meet size
                    self.apply_nulls_to_meet_size(edited_file, replacement_map.values())
                    print(f"✅ Modified: {rel_path}")
                    
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                continue
        
        return modified_count
    
    def apply_modifications(self, content: bytes, replacement_map: dict):
        """Apply pattern replacements"""
        modified = content
        
        for swaps in replacement_map.values():
            for src_pattern, dst_pattern in swaps:
                if src_pattern in modified:
                    modified = modified.replace(src_pattern, dst_pattern)
        
        return modified
    
    def apply_nulls_to_meet_size(self, file_path: Path, modified_patterns):
        """Apply nulls to meet size requirement - SMART NULLING"""
        import re
        
        # Read file
        with open(file_path, 'rb') as f:
            data = bytearray(f.read())
        
        # Check compressed size
        compressed_size = len(zlib.compress(data))
        if compressed_size <= self.max_compressed_size:
            return 0
        
        print(f"File exceeds size by {compressed_size - self.max_compressed_size} bytes")
        
        # Null IDs list (priority order)
        null_ids = [
            b"601001001", b"601001002", b"601001003", b"601001004", b"601001005",
            b"601002001", b"601002002", b"601002003", b"601002004", b"601002005",
            b"601003001", b"601003002", b"601003003", b"601003004", b"601003005",
        ]
        
        nulls_applied = 0
        max_attempts = 200
        
        # Phase 1: Try specific null IDs
        for attempt in range(max_attempts):
            matches = []
            for id_bytes in null_ids:
                start_search = 0
                while (pos := data.find(id_bytes, start_search)) >= 0:
                    matches.append((pos, id_bytes))
                    start_search = pos + 1
            
            if not matches:
                print("No more null patterns found")
                break
            
            matches.sort(key=lambda x: x[0], reverse=True)
            
            applied_in_attempt = 0
            for pos, id_bytes in matches:
                if pos + len(id_bytes) + 5 > len(data):
                    continue
                
                data[pos:pos + len(id_bytes) + 5] = b'\x00' * (len(id_bytes) + 5)
                nulls_applied += 1
                applied_in_attempt += 1
                
                if applied_in_attempt >= 3:
                    break
            
            new_size = len(zlib.compress(data))
            if new_size <= self.max_compressed_size:
                print(f"Size met after {nulls_applied} nulls")
                print(f"Final compressed size: {new_size} bytes (limit: {self.max_compressed_size})")
                break
            
            if applied_in_attempt == 0:
                break
        
        # Phase 2: Fallback - Try any 9-digit number pattern
        if len(zlib.compress(data)) > self.max_compressed_size:
            print("Trying 9-digit pattern fallback...")
            pattern = re.compile(rb'\d{9}')
            
            for _ in range(50):  # Max 50 attempts
                match = pattern.search(data)
                if not match:
                    break
                
                pos = match.start()
                if pos + 14 <= len(data):  # 9 digits + 5 extra
                    data[pos:pos + 14] = b'\x00' * 14
                    nulls_applied += 1
                    
                    new_size = len(zlib.compress(data))
                    if new_size <= self.max_compressed_size:
                        print(f"Size met after {nulls_applied} nulls (with fallback)")
                        print(f"Final compressed size: {new_size} bytes (limit: {self.max_compressed_size})")
                        break
        
        # Write back
        with open(file_path, 'wb') as f:
            f.write(data)
        
        final_size = len(zlib.compress(data))
        if final_size > self.max_compressed_size:
            print(f"⚠️ Still exceeds by {final_size - self.max_compressed_size} bytes")
        
        return nulls_applied

# Killfeed/Lootbox Modder functionality - COMPLETE IMPLEMENTATION
    

# LootboxModder functionality - COMPLETE IMPLEMENTATION
class LootboxModder:
    """Modskin Modder for BGMI lootbox modifications"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.input_dir = Path("input/gamepaks")
        self.target_pak = "core_patch_4.0.0.20328.pak"
        
        # ✅ UPDATED: Correct directories for Lootbox (not ModSkin)
        self.unpack_dir = OUTPUT_LOOTBOX_UNPACKED
        self.edited_dir = OUTPUT_LOOTBOX_EDITED
        self.results_dir = OUTPUT_LOOTBOX_RESULTS
        
        # Create directories
        for d in [self.unpack_dir, self.edited_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def process_modskin_mods(self):
        """Complete Lootbox workflow: Unpack → Modify → Null → Repack"""
        # Initialize logger with dashboard - only show relevant phases (no MOD_APPLY, no OPTIMIZE)
        logger = ColorfulConsoleLogger(silent_mode=True, phases=["UNPACK", "LOOT_APPLY", "FINALIZE"], title="LOOTBOX MODDING")
        logger.print_full_dashboard()
        
        try:
            # ═══ STEP 1: SELECTIVE EXTRACTION ═══
            logger.update_phase("UNPACK", "🔄 ACTIVE", 0, f"Extracting {self.target_pak}...")
            pak_path = self.input_dir / self.target_pak
            if not pak_path.exists():
                logger.update_phase("UNPACK", "❌ FAILED", 0, "PAK file not found")
                logger.log_error("LOOTBOX", f"PAK file not found: {pak_path}")
                return False
            
            unpacked_dir = self.unpack_dir / "core_patch_4.0.0.20328"
            unpacked_dir.mkdir(parents=True, exist_ok=True)
            
            # Suppress PAKToolAdvanced output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
            
            try:
                pak_tool = PAKToolAdvanced()
                
                # Check if already unpacked
                manifest_path = unpacked_dir / "manifest.json"
                if not manifest_path.exists():
                    unpack_result = pak_tool.unpack_pak_advanced(pak_path, unpacked_dir)
                else:
                    unpack_result = True
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            if not unpack_result:
                logger.update_phase("UNPACK", "❌ FAILED", 0, "Failed to unpack core_patch PAK")
                logger.log_error("LOOTBOX", "Failed to unpack core_patch PAK")
                return False
            
            logger.update_phase("UNPACK", "✅ DONE", 100, "Files ready for processing")
            
            # ═══ STEP 2: LOADING ID PAIRS & PATTERNS ═══
            logger.update_phase("LOOT_APPLY", "🔄 ACTIVE", 0, "Loading ID pairs and patterns...")
            
            # Load ID pairs from hit1.txt
            hit1_file = Path("contents/hit1.txt")
            if not hit1_file.exists():
                logger.update_phase("LOOT_APPLY", "❌ FAILED", 0, "hit1.txt not found")
                logger.log_error("LOOTBOX", f"hit1.txt not found: {hit1_file}")
                return False
            
            hex_pairs = self.parse_modskin_file(hit1_file)
            if not hex_pairs:
                logger.update_phase("LOOT_APPLY", "❌ FAILED", 0, "No valid hex pairs found")
                logger.log_error("LOOTBOX", "No valid hex pairs found in hit1.txt")
                return False
            
            # Load hit patterns from hit.txt
            hit_file = Path("contents/hit.txt")
            hit_patterns = []
            if hit_file.exists():
                hit_patterns = self.parse_hit_file(hit_file)
            
            logger.update_phase("LOOT_APPLY", "🔄 ACTIVE", 30, f"Loaded {len(hex_pairs)} hex pairs, {len(hit_patterns)} patterns")
            
            # ═══ STEP 3: MODIFY FILES ═══
            logger.update_phase("LOOT_APPLY", "🔄 ACTIVE", 50, "Modifying files...")
            
            edited_dir = self.edited_dir / "core_patch_4.0.0.20328"
            edited_dir.mkdir(parents=True, exist_ok=True)
            
            modified_count = self.process_and_modify_files_lootbox(unpacked_dir, edited_dir, hex_pairs, hit_patterns)
            
            if modified_count == 0:
                logger.update_phase("LOOT_APPLY", "❌ FAILED", 0, "No files were modified")
                logger.log_error("LOOTBOX", "No files were modified")
                return False
            
            logger.update_phase("LOOT_APPLY", "✅ DONE", 100, f"{modified_count} files modified")
            
            # ═══ STEP 4: REPACK PAK ═══
            logger.update_phase("FINALIZE", "🔄 ACTIVE", 0, "Repacking PAK...")
            
            output_pak = self.results_dir / self.target_pak
            
            # Suppress PAKToolAdvanced output
            old_stdout = sys.stdout
            old_stderr = sys.stderr
            sys.stdout = open(os.devnull, 'w', encoding='utf-8')
            sys.stderr = open(os.devnull, 'w', encoding='utf-8')
            
            try:
                repack_result = pak_tool.repack_pak_advanced(pak_path, unpacked_dir, edited_dir, output_pak)
            finally:
                sys.stdout.close()
                sys.stderr.close()
                sys.stdout = old_stdout
                sys.stderr = old_stderr
            
            if not repack_result:
                logger.update_phase("FINALIZE", "❌ FAILED", 0, "Failed to repack PAK")
                logger.log_error("LOOTBOX", "Failed to repack PAK")
                return False
            
            logger.update_phase("FINALIZE", "✅ DONE", 100, f"Repacked PAK: {output_pak.name}")
            
            # Set files processed count
            logger.set_files_processed(modified_count)
            
            logger.print_footer(success=True)
            
            return True
            
        except Exception as e:
            logger.update_phase("LOOT_APPLY", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
            logger.log_error("LOOTBOX", f"Lootbox modification failed: {e}")
            return False
    
    def parse_modskin_file(self, modskin_file: Path):
        """Parse modskin.txt file to extract hex pairs"""
        hex_pairs = []
        try:
            with modskin_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if ',' in line:
                        parts = line.split(',', 1)
                        if len(parts) == 2:
                            id1_str, id2_str = parts[0].strip(), parts[1].strip()
                            if id1_str and id2_str:
                                try:
                                    # Convert decimal IDs to hex
                                    id1 = int(id1_str)
                                    id2 = int(id2_str)
                                    hex1 = id1.to_bytes(4, 'little').hex()
                                    hex2 = id2.to_bytes(4, 'little').hex()
                                    hex_pairs.append([hex1, hex2, "NO"])
                                except ValueError:
                                    # If not decimal, treat as hex directly
                                    hex_pairs.append([id1_str, id2_str, "NO"])
        except Exception as e:
            print_error(f"Error reading {modskin_file.name}: {e}")
        
        return hex_pairs
    
    def parse_hit_file(self, hit_file: Path):
        """Parse hit.txt file to extract hit patterns"""
        patterns = []
        try:
            with hit_file.open("r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        patterns.append(line)
        except Exception as e:
            print_error(f"Error reading hit.txt: {e}")
        
        return patterns
    
    def process_and_modify_files_lootbox(self, unpacked_dir: Path, edited_dir: Path, hex_pairs: list, hit_patterns: list):
        """Process files with hex replacements and nulling for lootbox"""
        modified_count = 0
        
        # Find all files in unpacked directory
        all_files = []
        for subfolder in unpacked_dir.iterdir():
            if subfolder.is_dir():
                for file_path in subfolder.iterdir():
                    if file_path.is_file():
                        all_files.append(file_path)
        
        print(f"Found {len(all_files)} files to process")
        
        # Build exclude patterns from hex_pairs
        exclude_patterns = set()
        for hex1, hex2, _ in hex_pairs:
            if hex1 and hex2:
                exclude_patterns.add(hex1.lower())
                exclude_patterns.add(hex2.lower())
        
        for file_path in all_files:
            try:
                content = bytearray(file_path.read_bytes())
                original_content = bytes(content)
                
                # Apply hex replacements
                replacements_made = 0
                for hex1, hex2, _ in hex_pairs:
                    if hex1 and hex2:
                        try:
                            hex1_bytes = bytes.fromhex(hex1)
                            hex2_bytes = bytes.fromhex(hex2)
                            count = content.count(hex1_bytes)
                            if count > 0:
                                content = bytearray(bytes(content).replace(hex1_bytes, hex2_bytes))
                                replacements_made += count
                        except:
                            pass
                
                # Apply nulling if hit_patterns exist
                if hit_patterns and replacements_made > 0:
                    nulls_applied = 0
                    max_nulls = 40
                    
                    for pattern in hit_patterns:
                        if nulls_applied >= max_nulls:
                            break
                        if pattern.lower() in exclude_patterns:
                            continue
                        try:
                            pattern_bytes = bytes.fromhex(pattern)
                            pos = 0
                            while nulls_applied < max_nulls:
                                pos = content.find(pattern_bytes, pos)
                                if pos == -1:
                                    break
                                content[pos:pos+len(pattern_bytes)] = b'\x00' * len(pattern_bytes)
                                nulls_applied += 1
                                pos += 1
                        except:
                            pass
                
                # Save if modified
                if content != original_content:
                    rel_path = file_path.relative_to(unpacked_dir)
                    edited_file = edited_dir / rel_path
                    edited_file.parent.mkdir(parents=True, exist_ok=True)
                    edited_file.write_bytes(content)
                    modified_count += 1
                    print(f"✅ Modified: {rel_path} ({replacements_made} replacements)")
                    
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                continue
        
        return modified_count

# Killfeed/Lootbox Modder functionality - COMPLETE IMPLEMENTATION
class EmoteModder:
    """Emote Modder for BGMI emote modifications"""
    
    def __init__(self):
        self.home_dir = Path.home()
        self.emote_file = Path("contents/emote.txt")
        
        # ✅ UPDATED: Use new directory structure
        self.changelog_file = OUTPUT_EMOTE / "changelog.txt"
        
        # Create output directories if they don't exist
        for d in [OUTPUT_EMOTE, OUTPUT_EMOTE_UNPACKED, OUTPUT_EMOTE_EDITED, OUTPUT_EMOTE_RESULTS]:
            d.mkdir(parents=True, exist_ok=True)
        
        # Initialize changelog
        if not self.changelog_file.exists():
            self.changelog_file.write_text("# Emote Changelog\n\n")
        
        # Use the new directory structure
        self.unpack_dir = OUTPUT_MODSKIN / "unpacked"
        self.edited_dir = OUTPUT_MODSKIN / "edited"
        self.results_dir = OUTPUT_MODSKIN / "results"
        
        # Create directories if they don't exist
        for d in [self.unpack_dir, self.edited_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def is_sig_at(self, data: bytes, i: int):
        """Check if signature exists at position"""
        if i + 2 > len(data):
            return None
        return self.SIG2KEY.get(data[i:i+2], None)

    def xor_decode_with_feedback(self, data):
        """XOR decode PAK data with feedback mechanism"""
        out = bytearray()
        key = None
        seg_pos = 0
        seg_start_out = 0
        
        i = 0
        while i < len(data):
            k = self.is_sig_at(data, i)
            if k is not None:
                key = k
                seg_pos = 0
                seg_start_out = len(out)
            
            if key is not None:
                if seg_pos < 4:
                    o = data[i] ^ key[seg_pos]
                else:
                    fb_index = seg_start_out + (seg_pos - 4)
                    o = data[i] ^ out[fb_index]
                out.append(o)
                seg_pos += 1
            else:
                out.append(data[i])
            
            i += 1
        
        return bytes(out)
    
    def xor_reencode_from_original(self, encoded_original, decoded_modified):
        """XOR re-encode modified data"""
        out_enc = bytearray()
        key = None
        seg_pos = 0
        seg_start_out = 0
        
        for i in range(len(decoded_modified)):
            k = self.is_sig_at(encoded_original, i)
            if k is not None:
                key = k
                seg_pos = 0
                seg_start_out = i
            
            if key is not None:
                if seg_pos < 4:
                    b = decoded_modified[i] ^ key[seg_pos]
                else:
                    fb_index = seg_start_out + (seg_pos - 4)
                    b = decoded_modified[i] ^ decoded_modified[fb_index]
                out_enc.append(b)
                seg_pos += 1
            else:
                out_enc.append(decoded_modified[i])
        
        return bytes(out_enc)
    
    def process_and_modify_files_lootbox(self, unpacked_dir: Path, edited_dir: Path, hex_pairs: list, hit_patterns: list):
        """Process files with hex replacements and nulling for lootbox"""
        modified_count = 0
        
        # Find all files in unpacked directory
        all_files = []
        for subfolder in unpacked_dir.iterdir():
            if subfolder.is_dir():
                for file_path in subfolder.iterdir():
                    if file_path.is_file():
                        all_files.append(file_path)
        
        print(f"Found {len(all_files)} files to process")
        
        # Build exclude patterns from hex_pairs
        exclude_patterns = set()
        for hex1, hex2, _ in hex_pairs:
            if hex1 and hex2:
                exclude_patterns.add(hex1.lower())
                exclude_patterns.add(hex2.lower())
        
        for file_path in all_files:
            try:
                content = bytearray(file_path.read_bytes())
                original_content = bytes(content)
                
                # Apply hex replacements
                replacements_made = 0
                for hex1, hex2, _ in hex_pairs:
                    if hex1 and hex2:
                        try:
                            hex1_bytes = bytes.fromhex(hex1)
                            hex2_bytes = bytes.fromhex(hex2)
                            count = content.count(hex1_bytes)
                            if count > 0:
                                content = bytearray(bytes(content).replace(hex1_bytes, hex2_bytes))
                                replacements_made += count
                        except:
                            pass
                
                # Apply nulling if hit_patterns exist
                if hit_patterns and replacements_made > 0:
                    nulls_applied = 0
                    max_nulls = 40
                    
                    for pattern in hit_patterns:
                        if nulls_applied >= max_nulls:
                            break
                        if pattern.lower() in exclude_patterns:
                            continue
                        try:
                            pattern_bytes = bytes.fromhex(pattern)
                            pos = 0
                            while nulls_applied < max_nulls:
                                pos = content.find(pattern_bytes, pos)
                                if pos == -1:
                                    break
                                content[pos:pos+len(pattern_bytes)] = b'\x00' * len(pattern_bytes)
                                nulls_applied += 1
                                pos += 1
                        except:
                            pass
                
                # Save if modified
                if content != original_content:
                    rel_path = file_path.relative_to(unpacked_dir)
                    edited_file = edited_dir / rel_path
                    edited_file.parent.mkdir(parents=True, exist_ok=True)
                    edited_file.write_bytes(content)
                    modified_count += 1
                    print(f"✅ Modified: {rel_path} ({replacements_made} replacements)")
                    
            except Exception as e:
                print(f"Error processing {file_path.name}: {e}")
                continue
        
        return modified_count
        """Complete Lootbox workflow: Unpack → Modify → Null → Repack"""
        try:
            print_step("Lootbox Modder - Optimized Workflow", "🎁")
            
            # ═══ STEP 1: SELECTIVE EXTRACTION ═══
            print("\n═══ STEP 1/4: SELECTIVE EXTRACTION ═══")
            pak_path = self.input_dir / self.target_pak
            if not pak_path.exists():
                print_error(f"PAK file not found: {pak_path}")
                return False
            
            unpacked_dir = self.unpack_dir / "core_patch_4.0.0.20328"
            unpacked_dir.mkdir(parents=True, exist_ok=True)
            
            pak_tool = PAKToolAdvanced()
            
            # Check if already unpacked
            manifest_path = unpacked_dir / "manifest.json"
            if not manifest_path.exists():
                print("Extracting all files (first time)...")
                if not pak_tool.unpack_pak_advanced(pak_path, unpacked_dir):
                    print_error("Failed to unpack core_patch PAK")
                    return False
            else:
                print("Using existing unpacked files...")
            
            print_success("✅ Files ready for processing")
            
            # ═══ STEP 2: LOADING ID PAIRS & PATTERNS ═══
            print("\n═══ STEP 2/4: LOADING ID PAIRS & PATTERNS ═══")
            
            # Load ID-to-hex mapping from null.txt
            print("Loading ID-to-hex mapping from null.txt...")
            if not self.null_file.exists():
                print_error(f"null.txt not found: {self.null_file}")
                return False
            
            id_to_hex = {}
            null_patterns = []
            encodings = ['utf-8', 'utf-16', 'utf-16-le', 'utf-16-be', 'latin-1', 'cp1252']
            file_content = None
            
            for enc in encodings:
                try:
                    with open(self.null_file, 'r', encoding=enc) as f:
                        file_content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if file_content is None:
                print_error("Could not decode null.txt")
                return False
            
            for line in file_content.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 2:
                        id_part = parts[0].strip()
                        hex_part = parts[1].strip().replace(" ", "").upper()
                        id_to_hex[id_part] = hex_part
                        null_patterns.append(hex_part)
            
            print(f"Loaded {len(id_to_hex)} ID-to-hex mappings")
            print(f"Loaded {len(null_patterns)} null patterns")
            
            # Load ID pairs from loot.txt
            print("Loading ID pairs from loot.txt...")
            if not self.loot_file.exists():
                print_error(f"loot.txt not found: {self.loot_file}")
                return False
            
            id_pairs = []
            file_content = None
            for enc in encodings:
                try:
                    with open(self.loot_file, 'r', encoding=enc) as f:
                        file_content = f.read()
                    break
                except (UnicodeDecodeError, UnicodeError):
                    continue
            
            if file_content is None:
                print_error("Could not decode loot.txt")
                return False
            
            for line in file_content.splitlines():
                line = line.strip()
                if line and not line.startswith('#') and ',' in line:
                    parts = line.split(',', 1)
                    id_pairs.append((parts[0].strip(), parts[1].strip()))
            
            print(f"Loaded {len(id_pairs)} ID pairs")
            
            # Convert IDs to hex
            hex_pairs = []
            missing_ids = []
            
            for id1, id2 in id_pairs:
                hex1 = id_to_hex.get(id1)
                hex2 = id_to_hex.get(id2)
                
                if not hex1 or not hex2:
                    if not hex1:
                        missing_ids.append(id1)
                    if not hex2:
                        missing_ids.append(id2)
                    continue
                
                hex_pairs.append([hex1, hex2, "PENDING"])
            
            if missing_ids:
                print(f"⚠️  {len(missing_ids)} IDs not found (showing first 5):")
                for mid in missing_ids[:5]:
                    print(f"   - {mid}")
            
            if not hex_pairs:
                print_error("No valid hex pairs to process")
                return False
            
            print_success(f"✅ Created {len(hex_pairs)} hex pair mappings")
            
            # ═══ STEP 3: MODIFYING FILES & APPLYING NULLS ═══
            print("\n═══ STEP 3/4: MODIFYING FILES & APPLYING NULLS ═══")
            
            edited_dir = Path("output/edited_corepatch")
            edited_dir.mkdir(parents=True, exist_ok=True)
            
            modified_count = self.process_and_modify_files_lootbox(
                unpacked_dir, edited_dir, hex_pairs, null_patterns
            )
            
            if modified_count == 0:
                print("⚠️  No files were modified")
                return False
            
            print_success(f"✅ Modified {modified_count} files")
            
            # ═══ STEP 4: REPACK CORE_PATCH PAK ═══
            print("\n═══ STEP 4/4: REPACKING CORE_PATCH PAK ═══")
            
            # Use the EmoteModder results directory
            output_pak_dir = OUTPUT_EMOTE_RESULTS
            output_pak_dir.mkdir(parents=True, exist_ok=True)
            output_pak = output_pak_dir / self.target_pak
            
            if not pak_tool.repack_pak_advanced(pak_path, unpacked_dir, edited_dir, output_pak):
                print_error("Failed to repack core_patch PAK")
                return False
            
            print_success(f"✅ Repacked PAK saved to: {output_pak}")
            
            print_success(f"✅ Core_patch PAK repacked: {output_pak}")
            
            # ═══ SUCCESS ═══
            print("\n" + "="*60)
            print_success("✅ LOOTBOX MODDER COMPLETED SUCCESSFULLY!")
            print("="*60)
            print(f"📁 Output: {output_pak}")
            print(f"📊 Modified: {modified_count} files")
            
            return True
            
        except Exception as e:
            print_error(f"Modder failed: {e}")
            import traceback
            traceback.print_exc()
            return False

# ───── EMOTE MODDER - EMBEDDED FROM pak_modified.py AND mod.py ──────────────────

# EMBEDDED FUNCTIONS FROM pak_modified.py
def is_sig_at_embedded(data: bytes, i: int) -> Optional[bytes]:
    """Check if signature exists at position"""
    if i + 2 > len(data):
        return None
    SIG2KEY_EMBEDDED = {
        bytes.fromhex("9DC7"): bytes.fromhex("E55B4ED1"),
    }
    return SIG2KEY_EMBEDDED.get(data[i:i+2], None)

def xor_decode_with_feedback_embedded(data: bytes) -> bytes:
    """Decode encoded data using feedback XOR algorithm"""
    out = bytearray()
    key = None
    seg_pos = 0
    seg_start_out = 0
    i = 0
    L = len(data)
    
    while i < L:
        k = is_sig_at_embedded(data, i)
        if k is not None:
            key = k
            seg_pos = 0
            seg_start_out = len(out)
        if key is not None:
            if seg_pos < 4:
                o = data[i] ^ key[seg_pos]
            else:
                fb_index = seg_start_out + (seg_pos - 4)
                o = data[i] ^ out[fb_index]
            out.append(o)
            seg_pos += 1
            i += 1
        else:
            out.append(data[i])
            i += 1
    return bytes(out)

def xor_reencode_from_original_embedded(encoded_original: bytes, decoded_modified: bytes) -> bytes:
    """Re-encode modified decoded bytes using original encoded positions"""
    assert len(encoded_original) == len(decoded_modified)
    out_enc = bytearray()
    key = None
    seg_pos = 0
    seg_start_out = 0
    L = len(decoded_modified)
    
    for i in range(L):
        k = is_sig_at_embedded(encoded_original, i)
        if k is not None:
            key = k
            seg_pos = 0
            seg_start_out = i
        if key is not None:
            if seg_pos < 4:
                b = decoded_modified[i] ^ key[seg_pos]
            else:
                fb_index = seg_start_out + (seg_pos - 4)
                b = decoded_modified[i] ^ decoded_modified[fb_index]
            out_enc.append(b)
            seg_pos += 1
        else:
            out_enc.append(decoded_modified[i])
    return bytes(out_enc)

def is_valid_zlib_header_embedded(b1: int, b2: int) -> bool:
    """Check if bytes form valid zlib header"""
    if (b1 & 0x0F) != 8:
        return False
    cmf_flg = (b1 << 8) | b2
    return (cmf_flg % 31) == 0

def guess_extension_embedded(blob: bytes) -> str:
    """Guess file extension from magic bytes"""
    MAGIC_EXT_EMBEDDED = {
        0x9e2a83c1: ".uasset",
        0x61754c1b: ".lua",
        0x090a0d7b: ".dat",
        0x007bfeff: ".dat",
        0x200a0d7b: ".dat",
        0x27da0020: ".res",
        0x00000001: ".res",
        0x7bbfbbef: ".res",
        0x44484b42: ".bnk",
    }
    if len(blob) < 4:
        return ".uexp"
    magic = int.from_bytes(blob[:4], "little")
    return MAGIC_EXT_EMBEDDED.get(magic, ".uexp")

def try_decompress_at_embedded(buf: bytes, start: int, max_offset: int = 8):
    """Try to decompress zlib/gzip at position"""
    length = len(buf)
    modes = [("zlib", 15), ("gzip", 31)]
    
    for ofs in range(0, max_offset + 1):
        s = start + ofs
        if s >= length - 2:
            break
        for mode_name, wbits in modes:
            if mode_name == "zlib":
                b1 = buf[s]
                if b1 != 0x78:
                    continue
                b2 = buf[s + 1]
                if not is_valid_zlib_header_embedded(b1, b2):
                    continue
            if mode_name == "gzip":
                if s + 1 >= length:
                    continue
                if not (buf[s] == 0x1F and buf[s + 1] == 0x8B):
                    continue
            try:
                d = zlib.decompressobj(wbits)
                res = d.decompress(buf[s:])
                res += d.flush()
                consumed = len(buf[s:]) - len(d.unused_data)
                if not d.eof:
                    continue
                if consumed <= 0 or res is None or len(res) < 32:
                    continue
                return {"result": res, "consumed": consumed, "mode": mode_name, "ofs": ofs}
            except Exception:
                continue
    return None

def compress_by_mode_embedded(raw_bytes: bytes, mode: str) -> bytes:
    """Compress bytes using specified mode"""
    if mode == "zlib":
        return zlib.compress(raw_bytes, level=9)
    elif mode == "gzip":
        bio = io.BytesIO()
        with gzip.GzipFile(fileobj=bio, mode="wb") as gzf:
            gzf.write(raw_bytes)
        return bio.getvalue()
    else:
        return zlib.compress(raw_bytes, level=9)

def scan_and_extract_smart_embedded(data: bytes, out_dir: Path, manifest_path: Path):
    """Scan and extract compressed streams"""
    count = 0
    pos = 0
    length = len(data)
    entries = []
    
    def find_next_candidate(p):
        idxs = []
        i = data.find(b"\x78", p)
        if i != -1:
            idxs.append(i)
        j = data.find(b"\x1F\x8B", p)  # GZIP header
        if j != -1:
            idxs.append(j)
        return min(idxs) if idxs else -1
    
    print(f"{'Offset':>10} | {'Size':>6} | {'Mode':<5} | {'Name':<20}")
    print("" + "-" * 60 + "")
    
    while True:
        cand = find_next_candidate(pos)
        if cand == -1 or cand >= length - 2:
            break
        trial = try_decompress_at_embedded(data, cand, 8)
        if trial:
            res = trial["result"]
            consumed = trial["consumed"]
            ofs = trial["ofs"]
            mode = trial["mode"]
            
            count += 1
            ext = guess_extension_embedded(res)
            
            range_start = (count - 1) // 1000 * 1000
            range_end = range_start + 1000
            subdir = out_dir / f"{range_start}_{range_end}"
            subdir.mkdir(parents=True, exist_ok=True)
            
            fname = f"{count:06d}{ext}"
            outpath = subdir / fname
            outpath.write_bytes(res)
            
            relpath = str(outpath.relative_to(out_dir))
            start_pos = cand + ofs
            entries.append({
                "index": count,
                "start": start_pos,
                "consumed": consumed,
                "relpath": relpath,
                "ext": ext,
                "mode": mode,
            })
            
            if count % 100 == 0:
                print(f"0x{start_pos:08X} | {len(res):6d} | {mode:<5} | {fname:<20}")
            
            pos = start_pos + consumed
        else:
            pos = cand + 1
    
    print("" + "-" * 60 + "")
    print_success(f"Total {count} files unpacked → {out_dir}")
    
    # Create manifest.json
    manifest = {"total": count, "entries": entries}
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print_success(f"Manifest saved → {manifest_path}")
    
    return count

# EMBEDDED FUNCTIONS FROM mod.py
def read_emotes_embedded(emotes_path: Path) -> Dict[str, Dict[str, str]]:
    """Read emotes from file"""
    emotes: Dict[str, Dict[str, str]] = {}
    if not emotes_path.exists():
        print_error(f"emotes.txt not found at {emotes_path}")
        return emotes
    try:
        with emotes_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or '|' not in line:
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) < 3:
                    continue
                emote_id, hex_code, name = parts[0], parts[1], parts[2]
                hex_code = hex_code.replace(" ", "").lower()
                emotes[emote_id] = {"hex": hex_code, "name": name}
    except Exception as e:
        print_error(f"Error reading emotes.txt: {e}")
    return emotes

def read_id_pairs_embedded(pairs_path: Path) -> List[Tuple[str, str]]:
    """Read ID pairs from file"""
    pairs: List[Tuple[str, str]] = []
    if not pairs_path.exists():
        print_error(f"emo.txt not found at {pairs_path}")
        return pairs
    try:
        with pairs_path.open("r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                if ',' not in line:
                    continue
                a, b = [p.strip() for p in line.split(',', 1)]
                if a and b:
                    pairs.append((a, b))
    except Exception as e:
        print_error(f"Error reading emo.txt: {e}")
    return pairs

def scan_file_for_hex_embedded(data: bytes, hex_bytes: bytes) -> List[int]:
    """Scan file for hex occurrences"""
    results: List[int] = []
    start = 0
    while True:
        pos = data.find(hex_bytes, start)
        if pos == -1:
            break
        results.append(pos)
        start = pos + 1
    return results

def find_index_before_embedded(data: bytes, hex_pos: int) -> Optional[Tuple[int, bytes]]:
    """Find index before hex position"""
    BACK_LOOK = 240
    FORWARD_MIN = 0x0001
    FORWARD_MAX = 0xFFFE
    
    start = max(0, hex_pos - BACK_LOOK)
    
    # Find all candidate 2-byte values in the backward range
    candidates = []
    
    for i in range(start, hex_pos - 1):
        if i + 1 >= hex_pos:
            continue
            
        candidate = data[i:i+2]
        if candidate != b'\x00\x00':
            val = int.from_bytes(candidate, "little")
            if FORWARD_MIN <= val <= FORWARD_MAX:
                candidates.append((i, candidate))
    
    if not candidates:
        return None
    
    # If only one candidate, return it
    if len(candidates) == 1:
        return candidates[0]
    
    # If multiple candidates, find the one at the beginning of the zero line
    best_candidate = None
    max_zeros_before = 0
    
    for pos, candidate in candidates:
        # Count consecutive zeros before this candidate
        zeros_before = 0
        for j in range(pos-1, max(start-1, pos-20), -1):
            if j < 0:
                break
            if data[j] == 0:
                zeros_before += 1
            else:
                break
        
        # Also check if there are zeros after (typical pattern)
        zeros_after = 0
        for j in range(pos+2, min(len(data), pos+10)):
            if data[j] == 0:
                zeros_after += 1
            else:
                break
        
        # Prefer candidates that have zeros both before and after
        if zeros_before >= 2 and zeros_after >= 2:
            if zeros_before > max_zeros_before:
                max_zeros_before = zeros_before
                best_candidate = (pos, candidate)
    
    # If we found a candidate with good zero pattern, return it
    if best_candidate:
        return best_candidate
    
    # Otherwise, return the first candidate (closest to hex_pos)
    return candidates[0]

def find_index_after_embedded(data: bytes, hex_end_pos: int) -> Optional[Tuple[int, bytes]]:
    """Find index after hex position"""
    FORWARD_LOOK = 240
    FORWARD_MIN = 0x0001
    FORWARD_MAX = 0xFFFE
    
    end = min(len(data), hex_end_pos + FORWARD_LOOK)
    i = hex_end_pos
    while i + 1 < end:
        b1, b2 = data[i], data[i + 1]
        if b1 != 0 or b2 != 0:
            val = int.from_bytes(bytes([b1, b2]), "little")
            if FORWARD_MIN <= val <= FORWARD_MAX:
                return (i, bytes([b1, b2]))
        i += 1
    return None

def format_hex_embedded(b: bytes) -> str:
    """Format bytes to hex string"""
    return b.hex()

def hex_to_bytes_embedded(hex_str: str) -> bytes:
    """Convert hex string to bytes"""
    try:
        return bytes.fromhex(hex_str)
    except Exception:
        return b''

def create_backup_embedded(file_path: Path) -> bool:
    """Create backup of file"""
    BACKUP_DIR = Path("backup")
    try:
        if not BACKUP_DIR.exists():
            BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        backup_path = BACKUP_DIR / file_path.name
        with open(file_path, 'rb') as src, open(backup_path, 'wb') as dst:
            dst.write(src.read())
        return True
    except Exception as e:
        print_error(f"Failed to create backup for {file_path.name}: {e}")
        return False

def copy_and_modify_file_embedded(source_file: Path, modifications: List[Tuple[int, bytes, str]]) -> bool:
    """Copy and modify file with given modifications"""
    REPACK_DIR = OUTPUT_DIR / "edited_gamepatch"
    try:
        # Create REPACK_DIR if it doesn't exist
        if not REPACK_DIR.exists():
            REPACK_DIR.mkdir(parents=True, exist_ok=True)
        
        # Determine target path in REPACK_DIR
        target_file = REPACK_DIR / source_file.name
        
        # Read the source file
        with open(source_file, 'rb') as f:
            data = bytearray(f.read())
        
        # Apply modifications
        for pos, new_bytes, description in modifications:
            if pos + len(new_bytes) <= len(data):
                old_bytes = data[pos:pos+len(new_bytes)]
                data[pos:pos+len(new_bytes)] = new_bytes
                print_info(f"  Modified: {description} at position {pos}")
                print_info(f"     Old: {old_bytes.hex()} -> New: {new_bytes.hex()}")
            else:
                print_warning(f"  Skipped modification (out of bounds): {description}")
        
        # Write the modified data to REPACK_DIR
        with open(target_file, 'wb') as f:
            f.write(data)
        
        print_success(f"  Saved modified file to: {target_file}")
        return True
    except Exception as e:
        print_error(f"Failed to modify and copy {source_file.name}: {e}")
        return False

class EmoteModder:
    """Complete Emote Modification Tool with EMBEDDED functions"""
    
    def __init__(self):
        # Configuration
        self.base_dir = Path.cwd()
        self.input_dir = self.base_dir / "input" / "gamepaks"
        self.output_dir = self.base_dir / "output"
        
        # ✅ UPDATED: Use new organized directory structure
        self.unpack_dir = OUTPUT_EMOTE_UNPACKED
        self.edited_dir = OUTPUT_EMOTE_EDITED
        self.results_dir = OUTPUT_EMOTE_RESULTS
        
        self.emotes_file = CONTENTS_DIR / "emotes.txt"
        self.id_pairs_file = CONTENTS_DIR / "emo.txt"
        
        # Create directories
        for d in [self.unpack_dir, self.edited_dir, self.results_dir]:
            d.mkdir(parents=True, exist_ok=True)
    
    def process_emote_modification(self) -> bool:
        """Complete automated emote modification workflow"""
        # Initialize logger with dashboard - only show relevant phases (no MOD_APPLY, no OPTIMIZE)
        logger = ColorfulConsoleLogger(silent_mode=True, phases=["UNPACK", "EMOTE_APPLY", "FINALIZE"], title="EMOTE MODDING")
        logger.print_full_dashboard()
        
        try:
            # STEP 1: UNPACK PAK
            logger.update_phase("UNPACK", "🔄 ACTIVE", 0, "Finding and unpacking PAK files...")
            
            # Find PAK files
            pak_files = list(self.input_dir.glob("*.pak"))
            if not pak_files:
                logger.update_phase("UNPACK", "❌ FAILED", 0, "No PAK files found")
                logger.log_error("EMOTE", f"No PAK files found in {self.input_dir}")
                return False
            
            # Show available files
            print_info(f"Found {len(pak_files)} PAK files:")
            for i, pak_file in enumerate(pak_files, 1):
                print_info(f"  {i}. {pak_file.name}")
            
            # Auto-select gamepatch 4.0.0.20364.pak if available, otherwise first file
            target_pak = None
            for pak in pak_files:
                if "20364" in pak.name:
                    target_pak = pak
                    break
            
            if not target_pak:
                target_pak = pak_files[0]
            
            logger.update_phase("UNPACK", "🔄 ACTIVE", 20, f"Unpacking {target_pak.name}...")
            
            # Unpack using embedded functions
            try:
                # Create output directory
                self.unpack_dir.mkdir(parents=True, exist_ok=True)
                
                # Decode XOR
                data_enc = target_pak.read_bytes()
                decoded = xor_decode_with_feedback_embedded(data_enc)
                
                # Scan and extract
                manifest_path = self.unpack_dir / "manifest.json"
                count = scan_and_extract_smart_embedded(decoded, self.unpack_dir, manifest_path)
                
                logger.update_phase("UNPACK", "✅ DONE", 100, f"Unpacked {count} files")
                
            except Exception as e:
                logger.update_phase("UNPACK", "❌ FAILED", 0, f"Unpack failed: {str(e)[:30]}...")
                logger.log_error("EMOTE", f"Unpack failed: {e}")
                return False
            
            # STEP 2: MOD EMOTES
            logger.update_phase("EMOTE_APPLY", "🔄 ACTIVE", 0, "Modifying emotes...")
            
            # Check if unpacked directory exists
            if not self.unpack_dir.exists():
                logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "Unpacked directory not found")
                logger.log_error("EMOTE", f"Unpacked directory not found: {self.unpack_dir}")
                return False
            
            # Check if emotes files exist
            if not self.emotes_file.exists():
                logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "Emotes file not found")
                logger.log_error("EMOTE", f"Emotes file not found: {self.emotes_file}")
                return False
            
            if not self.id_pairs_file.exists():
                logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "ID pairs file not found")
                logger.log_error("EMOTE", f"ID pairs file not found: {self.id_pairs_file}")
                return False
            
            try:
                # Load emotes and pairs using embedded functions
                emotes = read_emotes_embedded(self.emotes_file)
                id_pairs = read_id_pairs_embedded(self.id_pairs_file)
                
                if not id_pairs:
                    logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "No ID pairs found")
                    logger.log_error("EMOTE", "No ID pairs found in emo.txt. Exiting.")
                    return False
                
                logger.update_phase("EMOTE_APPLY", "🔄 ACTIVE", 20, f"Loaded {len(emotes)} emotes, {len(id_pairs)} id-pairs")
                
                # Find .uexp files
                uexp_files = sorted([p for p in self.unpack_dir.glob("**/*.uexp") if p.is_file()])
                if not uexp_files:
                    logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "No .uexp files found")
                    logger.log_error("EMOTE", "No .uexp files found to scan.")
                    return False
                
                logger.update_phase("EMOTE_APPLY", "🔄 ACTIVE", 30, f"Found {len(uexp_files)} .uexp files, scanning...")
                
                # Use embedded logic
                report_lines = []
                report_lines.append("EMOTE INDEX SCAN REPORT")
                report_lines.append("=======================")
                report_lines.append("")
                
                total_pairs = len(id_pairs)
                pair_counter = 0
                
                # Store all modifications to apply later
                all_modifications: Dict[Path, List[Tuple[int, bytes, str]]] = {}
                
                for id2, id1 in id_pairs:
                    pair_counter += 1
                    emote2 = emotes.get(id2)
                    emote1 = emotes.get(id1)
                    
                    name2 = emote2["name"] if emote2 else f"ID_{id2}"
                    name1 = emote1["name"] if emote1 else f"ID_{id1}"
                    hex2 = emote2["hex"] if emote2 else None
                    hex1 = emote1["hex"] if emote1 else None
                    
                    header = f"ID Pair: {name2} ({id2}) <-> {name1} ({id1})"
                    print_info(f"[{pair_counter}/{total_pairs}] Scanning pair: {header}")
                    report_lines.append(header)
                    
                    # Store ALL indices found for this pair across ALL files
                    indices2 = []  # List of (file, position, index_bytes) for id2
                    indices1 = []  # List of (file, position, index_bytes) for id1
                    
                    def process_emote(emote_id: str, emote_name: str, hex_code: Optional[str], is_id2: bool):
                        nonlocal indices2, indices1
                        
                        report_lines.append(f"{emote_name} ({emote_id}):")
                        if not hex_code:
                            report_lines.append(f"  Hex: MISSING")
                            report_lines.append(f"  Status: hex code not found")
                            return

                        report_lines.append(f"  Hex: {hex_code}")
                        hex_bytes = hex_to_bytes_embedded(hex_code)
                        if not hex_bytes:
                            report_lines.append(f"  Status: invalid hex format")
                            return

                        found_any = False
                        for uexp in uexp_files:
                            try:
                                with uexp.open("rb") as f:
                                    data = f.read()
                            except Exception as e:
                                print_warning(f"  Skipping file {uexp.name}: {e}")
                                continue

                            occurrences = scan_file_for_hex_embedded(data, hex_bytes)
                            if not occurrences:
                                continue

                            for occ in occurrences:
                                found_any = True
                                before = find_index_before_embedded(data, occ)
                                if before:
                                    idx_pos, idx_bytes = before
                                    report_lines.append(f"  Found in: {uexp.name} at position {occ}")
                                    report_lines.append(f"  Index: {format_hex_embedded(idx_bytes)} at position {idx_pos} (backward search)")
                                    
                                    # Store ALL indices found
                                    if is_id2:
                                        indices2.append((uexp, idx_pos, idx_bytes))
                                    else:
                                        indices1.append((uexp, idx_pos, idx_bytes))
                                    continue

                                after = find_index_after_embedded(data, occ + len(hex_bytes))
                                if after:
                                    idx_pos, idx_bytes = after
                                    report_lines.append(f"  Found in: {uexp.name} at position {occ}")
                                    report_lines.append(f"  Index: {format_hex_embedded(idx_bytes)} at position {idx_pos} (forward fallback)")
                                    
                                    # Store ALL indices found
                                    if is_id2:
                                        indices2.append((uexp, idx_pos, idx_bytes))
                                    else:
                                        indices1.append((uexp, idx_pos, idx_bytes))
                                    continue

                                report_lines.append(f"  Found in: {uexp.name} at position {occ}")
                                report_lines.append(f"  Index: NOT FOUND (searched +/- 240 bytes)")

                        if not found_any:
                            report_lines.append(f"  Found in: NONE")

                    process_emote(id2, name2, hex2, True)
                    process_emote(id1, name1, hex1, False)

                    # If both have indices found, prepare modifications for ALL occurrences
                    if indices2 and indices1:
                        print_info(f"  Preparing to swap indices: {len(indices2)} occurrences of {name2} <-> {len(indices1)} occurrences of {name1}")
                        
                        # For each occurrence of id2, swap with id1's index
                        for file2, pos2, index2 in indices2:
                            index1_to_use = indices1[0][2] if indices1 else None
                            if index1_to_use:
                                if file2 not in all_modifications:
                                    all_modifications[file2] = []
                                all_modifications[file2].append((
                                    pos2, index1_to_use, 
                                    f"Swap {name2} index {index2.hex()} -> {index1_to_use.hex()}"
                                ))
                        
                        # For each occurrence of id1, swap with id2's index  
                        for file1, pos1, index1 in indices1:
                            index2_to_use = indices2[0][2] if indices2 else None
                            if index2_to_use:
                                if file1 not in all_modifications:
                                    all_modifications[file1] = []
                                all_modifications[file1].append((
                                    pos1, index2_to_use,
                                    f"Swap {name1} index {index1.hex()} -> {index2_to_use.hex()}"
                                ))

                    report_lines.append("=" * 40)

                # Apply modifications and copy ONLY MODIFIED files to edited folder
                modified_count = 0
                for file_path, modifications in all_modifications.items():
                    if self.copy_and_modify_file_custom(file_path, modifications):
                        modified_count += 1

                print_info("=" * 50)
                print_success(f"SUCCESS: Emote modification completed!")
                print_success(f"Modified {modified_count} files")
                if modified_count > 0:
                    logger.update_phase("EMOTE_APPLY", "✅ DONE", 100, f"{modified_count} files modified")
                else:
                    logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, "No files were modified")
                    logger.log_error("EMOTE", "No files were modified")
                    return False
                    
            except Exception as e:
                logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
                logger.log_error("EMOTE", f"Emote modification failed: {e}")
                return False
            
            # STEP 3: REPACK PAK
            logger.update_phase("FINALIZE", "🔄 ACTIVE", 0, "Repacking PAK...")
            
            # Embedded repack logic
            if not target_pak:
                logger.update_phase("FINALIZE", "❌ FAILED", 0, "No file selected for repack")
                logger.log_error("EMOTE", "No file selected for repack.")
                return False
            
            unpack_sub = self.unpack_dir
            if not unpack_sub.exists():
                logger.update_phase("FINALIZE", "❌ FAILED", 0, "Unpack directory not found")
                logger.log_error("EMOTE", f"UNPACK not run for this file (no directory): {unpack_sub}")
                return False
            
            manifest_path = unpack_sub / "manifest.json"
            if not manifest_path.exists():
                logger.update_phase("FINALIZE", "❌ FAILED", 0, "manifest.json not found")
                logger.log_error("EMOTE", f"manifest.json not found at: {manifest_path}")
                return False
            
            print_info("Decoding original encoded file...")
            data_enc_orig = target_pak.read_bytes()
            decoded = bytearray(xor_decode_with_feedback_embedded(data_enc_orig))
            
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            entries = manifest.get("entries", [])
            
            repack_files_map = self.find_repack_candidates(self.edited_dir)
            if not repack_files_map:
                print_error("No files found in edited directory. Place edited files there.")
                return False
            
            Repacked_cnt = skipped_cnt = not_found_cnt = 0
            
            print_info("Processing manifest entries and trying to patch from edited files...")
            for e in entries:
                relpath = e["relpath"]
                start = int(e["start"])
                consumed = int(e["consumed"])
                mode = e.get("mode", "zlib")
                
                filename = Path(relpath).name
                src_edit = repack_files_map.get(filename)
                if not src_edit:
                    not_found_cnt += 1
                    continue
                try:
                    raw = src_edit.read_bytes()
                    comp = compress_by_mode_embedded(raw, mode)
                    if len(comp) <= consumed:
                        decoded[start:start+len(comp)] = comp
                        if len(comp) < consumed:
                            decoded[start+len(comp):start+consumed] = b"\x00" * (consumed - len(comp))
                        Repacked_cnt += 1
                        print_info(f"Repacked {filename} | {len(comp)} <= slot {consumed} (mode:{mode})")
                    else:
                        skipped_cnt += 1
                        print_warning(f"Skipped {filename} | {len(comp)} > slot {consumed} (mode:{mode})")
                except Exception as ex:
                    skipped_cnt += 1
                    print_error(f"Error with {filename}: {ex}")
            
            print_info(f"Summary: {Repacked_cnt} Repacked, {skipped_cnt} skipped, {not_found_cnt} not found")
            if Repacked_cnt == 0:
                print_error("No files Repacked. Aborting write.")
                return False
            
            logger.update_phase("FINALIZE", "🔄 ACTIVE", 50, "Re-encoding XOR and writing result...")
            encoded_final = xor_reencode_from_original_embedded(data_enc_orig, bytes(decoded))
            result_file = self.results_dir / target_pak.name
            result_file.write_bytes(encoded_final)
            
            logger.update_phase("FINALIZE", "✅ DONE", 100, f"Repack complete: {result_file.name}")
            
            # Set files processed count
            logger.set_files_processed(modified_count)
            
            logger.print_footer(success=True)
            
            return True
            
        except Exception as e:
            logger.update_phase("EMOTE_APPLY", "❌ FAILED", 0, f"Error: {str(e)[:30]}...")
            logger.log_error("EMOTE", f"Emote Modder failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def copy_and_modify_file_custom(self, source_file: Path, modifications: List[Tuple[int, bytes, str]]) -> bool:
        """Custom copy and modify function"""
        try:
            # Create edited directory if it doesn't exist
            if not self.edited_dir.exists():
                self.edited_dir.mkdir(parents=True, exist_ok=True)
            
            # Determine target path in edited directory
            target_file = self.edited_dir / source_file.name
            
            # Read the source file
            with open(source_file, 'rb') as f:
                data = bytearray(f.read())
            
            # Apply all modifications
            for pos, new_bytes, description in modifications:
                if pos + len(new_bytes) <= len(data):
                    data[pos:pos+len(new_bytes)] = new_bytes
                    print_success(f"    SUCCESS: {description}")
                else:
                    print_error(f"    ERROR: {description} - Position out of bounds")
            
            # Write modified file to edited directory
            with open(target_file, 'wb') as f:
                f.write(data)
            
            print_success(f"  Modified {source_file.name} with {len(modifications)} changes")
            print_success(f"  Saved to edited folder: {target_file}")
            return True
            
        except Exception as e:
            print_error(f"  ERROR: Error modifying {source_file.name}: {e}")
            return False
    
    def find_repack_candidates(self, repack_dir: Path):
        """Find files recursively; map filename -> path"""
        mapping = {}
        for p in repack_dir.rglob("*"):
            if p.is_file():
                mapping.setdefault(p.name, p)
        return mapping

# Compact Black GUI
# GUI class removed for mobile
# GUI class removed for mobile

# ───── TEXTUAL UI ──────────────────────────────────────────────────────────────

if TEXTUAL_AVAILABLE:
    class MainMenuScreen(Screen):
        """Main menu screen with 3 main categories"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="main_container"):
                yield Static("🎯 BGMI Modding Tool", id="title")
                yield Static("=" * 70, id="divider")
                
                with Vertical(id="button_container"):
                    yield Button("📦 OBB Functions", id="obb_btn", variant="primary")
                    yield Button("🎨 Skin Features", id="skin_btn", variant="success")
                    yield Button("🎯 Hack Features", id="hack_btn", variant="warning")
                    yield Button("🧹 Cleanup", id="cleanup_btn")
                    yield Button("❓ Help", id="help_btn")
                
                yield Static("=" * 70, id="divider_bottom")
            yield Footer()
        
        @on(Button.Pressed, "#obb_btn")
        def on_obb_clicked(self) -> None:
            self.app.push_screen("obb_menu")
        
        @on(Button.Pressed, "#skin_btn")
        def on_skin_clicked(self) -> None:
            self.app.push_screen("skin_menu")
        
        @on(Button.Pressed, "#hack_btn")
        def on_hack_clicked(self) -> None:
            self.app.push_screen("hack_menu")
        
        @on(Button.Pressed, "#cleanup_btn")
        def on_cleanup_clicked(self) -> None:
            self.app.push_screen("cleanup_confirm")
        
        @on(Button.Pressed, "#help_btn")
        def on_help_clicked(self) -> None:
            self.app.push_screen("help_screen")


    class OBBMenuScreen(Screen):
        """OBB Functions submenu"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="menu_container"):
                yield Static("📦 OBB Functions", id="menu_title")
                yield Static("-" * 70, id="divider")
                
                with Vertical(id="button_container"):
                    yield Button("📥 Unpack OBB", id="unpack_obb_btn", variant="primary")
                    yield Button("📤 Repack OBB", id="repack_obb_btn", variant="success")
                    yield Button("⬅️  Back to Main Menu", id="back_btn")
                
                yield Static("-" * 70, id="divider_bottom")
            yield Footer()
        
        @on(Button.Pressed, "#unpack_obb_btn")
        def on_unpack_obb(self) -> None:
            # Temporarily exit Textual to show dashboard, then restart
            self.app.exit(result="unpack_obb")
        
        @on(Button.Pressed, "#repack_obb_btn")
        def on_repack_obb(self) -> None:
            # Temporarily exit Textual to show dashboard, then restart
            self.app.exit(result="repack_obb")
        
        @on(Button.Pressed, "#back_btn")
        def on_back(self) -> None:
            self.app.pop_screen()


    class SkinMenuScreen(Screen):
        """Skin Features submenu"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="menu_container"):
                yield Static("🎨 Skin Features", id="menu_title")
                yield Static("-" * 70, id="divider")
                
                with Vertical(id="button_container"):
                    yield Button("🎨 Apply Mod Skin", id="mod_skin_btn", variant="primary")
                    yield Button("🔫 Hit Effect", id="hit_effect_btn", variant="success")
                    yield Button("💀 Killfeed Modder", id="killfeed_btn")
                    yield Button("🎁 Lootbox Modder", id="lootbox_btn")
                    yield Button("🎭 Emote Modder", id="emote_btn")
                    yield Button("💰 Credit Adder", id="credit_btn")
                    yield Button("🚀 Complete Workflow", id="complete_workflow_btn", variant="warning")
                    yield Button("⬅️  Back to Main Menu", id="back_btn")
                
                yield Static("-" * 70, id="divider_bottom")
            yield Footer()
        
        @on(Button.Pressed, "#mod_skin_btn")
        def on_mod_skin(self) -> None:
            self.app.exit(result="mod_skin")
        
        @on(Button.Pressed, "#hit_effect_btn")
        def on_hit_effect(self) -> None:
            self.app.exit(result="hit_effect")
        
        @on(Button.Pressed, "#killfeed_btn")
        def on_killfeed(self) -> None:
            self.app.exit(result="killfeed")
        
        @on(Button.Pressed, "#lootbox_btn")
        def on_lootbox(self) -> None:
            self.app.exit(result="lootbox")
        
        @on(Button.Pressed, "#emote_btn")
        def on_emote(self) -> None:
            self.app.exit(result="emote")
        
        @on(Button.Pressed, "#credit_btn")
        def on_credit(self) -> None:
            self.app.exit(result="credit")
        
        @on(Button.Pressed, "#complete_workflow_btn")
        def on_complete_workflow(self) -> None:
            self.app.exit(result="complete_workflow")
        
        @on(Button.Pressed, "#back_btn")
        def on_back(self) -> None:
            self.app.pop_screen()


    class HackMenuScreen(Screen):
        """Hack Features submenu"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="menu_container"):
                yield Static("🎯 Hack Features", id="menu_title")
                yield Static("-" * 70, id="divider")
                
                with Vertical(id="button_container"):
                    yield Button("🎯 Headshot Modder", id="headshot_btn", variant="primary")
                    yield Button("⬅️  Back to Main Menu", id="back_btn")
                
                yield Static("-" * 70, id="divider_bottom")
            yield Footer()
        
        @on(Button.Pressed, "#headshot_btn")
        def on_headshot(self) -> None:
            self.app.exit(result="headshot")
        
        @on(Button.Pressed, "#back_btn")
        def on_back(self) -> None:
            self.app.pop_screen()


    class CleanupConfirmScreen(Screen):
        """Cleanup confirmation screen"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="confirm_container"):
                yield Static("🧹 Cleanup", id="confirm_title")
                yield Static("Remove temporary files?", id="confirm_message")
                
                with Horizontal(id="button_row"):
                    yield Button("✅ Yes", id="yes_btn", variant="success")
                    yield Button("❌ No", id="no_btn", variant="error")
            yield Footer()
        
        @on(Button.Pressed, "#yes_btn")
        def on_yes(self) -> None:
            self.app.exit(result="cleanup")
        
        @on(Button.Pressed, "#no_btn")
        def on_no(self) -> None:
            self.app.pop_screen()


    class HelpScreen(Screen):
        """Help information screen"""
        
        def compose(self) -> ComposeResult:
            yield Header(show_clock=True)
            with Container(id="help_container"):
                yield Static("❓ Help & Information", id="help_title")
                yield Static("=" * 70, id="divider")
                
                help_text = """📁 Folder Structure:
  📂 input/ - Put your OBB files here
  📂 contents/ - Configuration files (modskin.txt, null.txt)
  📂 output/ - All outputs and temporary files

📋 Required Files:
  • 📱 OBB file in input/ folder
  • 🎨 modskin.txt in contents/ folder
  • 🔧 null.txt in contents/ folder

🚀 Quick Start:
  1. Put your OBB file in input/ folder
  2. Configure modskin.txt and null.txt in contents/
  3. Run Complete Workflow from Skin Features
  4. Get your modified OBB from output/repack_obb/

⚠️ Important: Always backup your original OBB file!"""
                
                yield Static(help_text, id="help_text")
                yield Static("=" * 70, id="divider_bottom")
                yield Button("⬅️  Back", id="back_btn")
            yield Footer()
        
        @on(Button.Pressed, "#back_btn")
        def on_back(self) -> None:
            self.app.pop_screen()


    class BGMIApp(App):
        """Main Textual application"""
        
        CSS = """
        #main_container, #menu_container, #confirm_container, #help_container {
            width: 100%;
            height: 100%;
            padding: 1;
        }
        
        #title, #menu_title, #confirm_title, #help_title {
            text-align: center;
            text-style: bold;
            margin: 1;
        }
        
        #button_container {
            width: 100%;
            margin: 1;
        }
        
        #button_container > Button {
            width: 100%;
            margin: 1;
        }
        
        #divider, #divider_bottom {
            text-align: center;
            margin: 1;
        }
        
        #help_text {
            margin: 1;
            padding: 1;
        }
        
        #button_row {
            width: 100%;
            margin: 1;
            align: center middle;
        }
        
        #button_row > Button {
            width: 50%;
            margin: 1;
        }
        """
        
        SCREENS = {
            "main_menu": MainMenuScreen,
            "obb_menu": OBBMenuScreen,
            "skin_menu": SkinMenuScreen,
            "hack_menu": HackMenuScreen,
            "cleanup_confirm": CleanupConfirmScreen,
            "help_screen": HelpScreen,
        }
        
        def on_mount(self) -> None:
            self.push_screen("main_menu")
        
        def on_key(self, event) -> None:
            if event.key == "escape":
                if len(self.screen_stack) > 1:
                    self.pop_screen()
                else:
                    self.exit()

# ───── MAIN ENTRY POINT ──────────────────────────────────────────────────────────────

def main():
    """Main entry point - Mobile version with Textual UI"""
    try:
        # Check if textual is available
        if TEXTUAL_AVAILABLE:
            while True:
                app = BGMIApp()
                result = app.run()
                
                # Handle function execution results
                if result == "unpack_obb":
                    unpack_obb()
                    input("\nPress Enter to continue...")
                elif result == "repack_obb":
                    repack_obb()
                    input("\nPress Enter to continue...")
                elif result == "mod_skin":
                    mod_skin()
                    input("\nPress Enter to continue...")
                elif result == "hit_effect":
                    HitModder().process_hit_mods()
                    input("\nPress Enter to continue...")
                elif result == "killfeed":
                    KillfeedModder().process_killfeed_complete()
                    input("\nPress Enter to continue...")
                elif result == "lootbox":
                    LootboxModder().process_modskin_mods()
                    input("\nPress Enter to continue...")
                elif result == "emote":
                    EmoteModder().process_emote_modification()
                    input("\nPress Enter to continue...")
                elif result == "credit":
                    CreditAdder().extract_credit_uexp()
                    input("\nPress Enter to continue...")
                elif result == "complete_workflow":
                    complete_workflow()
                    input("\nPress Enter to continue...")
                elif result == "headshot":
                    headshot_modder_menu()
                    input("\nPress Enter to continue...")
                elif result == "cleanup":
                    cleanup()
                    input("\nPress Enter to continue...")
                elif result is None:
                    # User exited the app
                    break
        else:
            # Fallback to text-based menu if textual not installed
            print_warning("Textual not installed. Falling back to text-based menu.")
            print_info("Install with: pip install textual")
            interactive_menu()
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except Exception as e:
        print_error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
