#!/usr/bin/env python3
"""
Test script to verify GUI compatibility with main_client.py
Checks that all required methods are available in TabbedGUIManager.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_gui_compatibility():
    """Test that TabbedGUIManager has all required methods."""
    try:
        from client.gui_manager import TabbedGUIManager
        
        # Create GUI manager instance
        gui = TabbedGUIManager()
        
        # List of required methods for compatibility with main_client.py
        required_methods = [
            # File transfer methods
            'show_file_transfer_progress',
            'hide_file_transfer_progress',
            'add_shared_file',
            
            # Participant methods
            'update_participants',
            
            # Video methods
            'update_local_video',
            'update_remote_video',
            'clear_video_slot',
            
            # Audio methods
            'update_audio_level',
            
            # Chat methods
            'add_chat_message',
            'add_system_message',
            
            # Screen sharing methods
            'update_presenter',
            'set_sharing_status',
            'display_screen_frame',
            'handle_presenter_granted',
            'handle_presenter_denied',
            'handle_screen_share_started',
            'handle_screen_share_stopped',
            'set_presenter_status',
            
            # Connection methods
            'update_connection_status',
            'show_error',
            'show_info',
            'set_connection_callbacks',
            'set_module_callbacks',
            
            # GUI lifecycle
            'run'
        ]
        
        print("🔍 Testing GUI Compatibility...")
        print("=" * 50)
        
        missing_methods = []
        available_methods = []
        
        for method in required_methods:
            if hasattr(gui, method):
                available_methods.append(method)
                print(f"✅ {method}")
            else:
                missing_methods.append(method)
                print(f"❌ {method}")
        
        print("=" * 50)
        print(f"📊 Results:")
        print(f"✅ Available: {len(available_methods)}/{len(required_methods)}")
        print(f"❌ Missing: {len(missing_methods)}")
        
        if missing_methods:
            print(f"\n🚨 Missing methods:")
            for method in missing_methods:
                print(f"  - {method}")
            return False
        else:
            print(f"\n🎉 All required methods are available!")
            print(f"✅ TabbedGUIManager is fully compatible with main_client.py")
            return True
            
    except Exception as e:
        print(f"❌ Error during compatibility test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_gui_compatibility()
    
    if success:
        print(f"\n🚀 Ready to test file transfer!")
        print(f"1. Start server: python start_server.py")
        print(f"2. Start client: python start_client.py")
        print(f"3. Go to 📁 File Sharing tab and test file upload/download")
    else:
        print(f"\n⚠️  Some methods are missing. File transfer may not work correctly.")
    
    sys.exit(0 if success else 1)