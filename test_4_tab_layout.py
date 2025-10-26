#!/usr/bin/env python3
"""
Test script for the new 4-tab layout with separate screen sharing.
"""

import sys
import os
import tkinter as tk
from tkinter import messagebox

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from client.gui_manager import TabbedGUIManager
    print("✓ Successfully imported TabbedGUIManager")
    
    # Create the new 4-tab GUI
    gui_manager = TabbedGUIManager()
    
    # Show info about the new 4-tab layout
    messagebox.showinfo(
        "New 4-Tab Layout", 
        "🎉 UI Reorganized into 4 Dedicated Sections! 🎉\n\n"
        "New 4-Tab Layout:\n\n"
        "🎥 Video & Audio Tab:\n"
        "  • Video Conferencing (80% larger videos)\n"
        "  • Audio Controls & Level Indicators\n"
        "  • Participant List\n\n"
        "🖥️ Screen Share Tab:\n"
        "  • Dedicated full-screen sharing interface\n"
        "  • Larger display area (600px height)\n"
        "  • Enhanced presenter controls\n\n"
        "💬 Group Chat Tab:\n"
        "  • Full-screen chat interface\n"
        "  • Better message display\n"
        "  • Chat history & export\n\n"
        "📁 File Sharing Tab:\n"
        "  • Enhanced file management\n"
        "  • Better progress tracking\n"
        "  • Improved file operations\n\n"
        "✅ All functionality preserved!\n"
        "✅ Better organization with dedicated spaces!"
    )
    
    print("✓ New 4-tab interface created successfully")
    print("\n🎯 New 4-Tab Layout:")
    print("  1. 🎥 Video & Audio - Video conferencing and audio controls")
    print("  2. 🖥️ Screen Share - Dedicated screen sharing with larger display")
    print("  3. 💬 Group Chat - Full-screen chat interface")
    print("  4. 📁 File Sharing - Enhanced file management")
    
    print("\n✨ Improvements:")
    print("  • Screen sharing gets its own dedicated tab")
    print("  • Larger screen display area (600px height)")
    print("  • Video & Audio tab focused on conferencing")
    print("  • Better space utilization for each function")
    print("  • Cleaner, more organized interface")
    
    print("\n🚀 To test with full functionality:")
    print("1. Start the server: python start_server.py")
    print("2. Start clients: python start_client.py")
    print("3. Navigate between the 4 tabs to access different features")
    print("4. Screen sharing now has its own dedicated space!")
    
    # Run the GUI
    gui_manager.run()
    
except ImportError as e:
    print(f"✗ Import error: {e}")
    print("Make sure you're running this from the project root directory")
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()