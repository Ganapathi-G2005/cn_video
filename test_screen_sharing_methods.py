#!/usr/bin/env python3
"""
Test script to verify all screen sharing methods are available.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_screen_sharing_methods():
    """Test that TabbedGUIManager has all screen sharing methods."""
    try:
        from client.gui_manager import TabbedGUIManager
        
        # Create GUI manager instance
        gui = TabbedGUIManager()
        
        # List of screen sharing methods that screen_manager.py calls
        screen_sharing_methods = [
            'set_screen_sharing_status',  # Called by screen_manager.py
            'set_presenter_status',       # Called by screen_manager.py
            'reset_screen_sharing_button', # Called by screen_manager.py
            'cleanup_gui_elements',       # Called by screen_manager.py
            'display_screen_frame',       # Called by main_client.py
            'update_presenter',           # Called by main_client.py
            'handle_presenter_granted',   # Called by main_client.py
            'handle_presenter_denied',    # Called by main_client.py
            'handle_screen_share_started', # Called by main_client.py
            'handle_screen_share_stopped', # Called by main_client.py
        ]
        
        print("🔍 Testing Screen Sharing Methods...")
        print("=" * 60)
        
        missing_methods = []
        available_methods = []
        
        for method in screen_sharing_methods:
            if hasattr(gui, method):
                available_methods.append(method)
                print(f"✅ {method}")
            else:
                missing_methods.append(method)
                print(f"❌ {method}")
        
        print("=" * 60)
        print(f"📊 Screen Sharing Methods:")
        print(f"✅ Available: {len(available_methods)}/{len(screen_sharing_methods)}")
        print(f"❌ Missing: {len(missing_methods)}")
        
        if missing_methods:
            print(f"\n🚨 Missing methods that screen_manager.py needs:")
            for method in missing_methods:
                print(f"  - {method}")
            return False
        else:
            print(f"\n🎉 All screen sharing methods are available!")
            print(f"✅ screen_manager.py should work correctly now")
            return True
            
    except Exception as e:
        print(f"❌ Error during screen sharing methods test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_screen_sharing_methods()
    
    if success:
        print(f"\n🚀 Screen sharing should work now!")
        print(f"The error 'TabbedGUIManager' object has no attribute 'set_screen_sharing_status' should be fixed.")
        print(f"\n📋 Test Steps:")
        print(f"1. Start server: python start_server.py")
        print(f"2. Start client: python start_client.py")
        print(f"3. Go to 🎥 Media & Screen Share tab")
        print(f"4. Click 'Start Screen Share' button")
        print(f"5. Screen sharing should work without errors")
    else:
        print(f"\n⚠️  Some screen sharing methods are still missing.")
    
    sys.exit(0 if success else 1)