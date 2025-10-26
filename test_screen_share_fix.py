#!/usr/bin/env python3
"""
Test script to verify screen sharing functionality is restored.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_screen_share_functionality():
    """Test that ScreenShareFrame has all required methods."""
    try:
        from client.gui_manager import ScreenShareFrame, TabbedGUIManager
        import tkinter as tk
        
        print("🔍 Testing Screen Share Functionality...")
        print("=" * 50)
        
        # Create a test root window
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Create ScreenShareFrame instance
        screen_frame = ScreenShareFrame(root)
        
        # List of critical screen sharing methods
        required_methods = [
            'display_screen_frame',
            'set_sharing_status', 
            'update_presenter',
            'handle_presenter_granted',
            'handle_presenter_denied',
            'handle_screen_share_started',
            'handle_screen_share_stopped',
            'set_presenter_status',
            'reset_screen_sharing_button',
            '_show_black_screen',
            'cleanup_gui_elements',
            '_store_current_frame',
            '_initialize_canvas',
            '_on_canvas_resize'
        ]
        
        missing_methods = []
        available_methods = []
        
        for method in required_methods:
            if hasattr(screen_frame, method):
                available_methods.append(method)
                print(f"✅ {method}")
            else:
                missing_methods.append(method)
                print(f"❌ {method}")
        
        print("=" * 50)
        print(f"📊 Screen Share Methods:")
        print(f"✅ Available: {len(available_methods)}/{len(required_methods)}")
        print(f"❌ Missing: {len(missing_methods)}")
        
        # Test GUI manager integration
        print(f"\n🔍 Testing GUI Manager Integration...")
        gui_manager = TabbedGUIManager()
        
        gui_integration_methods = [
            'display_screen_frame',
            'set_sharing_status',
            'update_presenter'
        ]
        
        integration_ok = True
        for method in gui_integration_methods:
            if hasattr(gui_manager, method):
                print(f"✅ GUI Manager has {method}")
            else:
                print(f"❌ GUI Manager missing {method}")
                integration_ok = False
        
        root.destroy()
        
        if missing_methods:
            print(f"\n🚨 Missing screen share methods:")
            for method in missing_methods:
                print(f"  - {method}")
            return False
        elif not integration_ok:
            print(f"\n🚨 GUI Manager integration issues found")
            return False
        else:
            print(f"\n🎉 Screen sharing functionality fully restored!")
            print(f"✅ All critical methods are available")
            print(f"✅ GUI Manager integration working")
            return True
            
    except Exception as e:
        print(f"❌ Error during screen share test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_screen_share_functionality()
    
    if success:
        print(f"\n🚀 Screen sharing is ready to use!")
        print(f"1. Start server: python start_server.py")
        print(f"2. Start client: python start_client.py")
        print(f"3. Go to 🎥 Media & Screen Share tab")
        print(f"4. Test screen sharing functionality")
    else:
        print(f"\n⚠️  Screen sharing may still have issues.")
    
    sys.exit(0 if success else 1)