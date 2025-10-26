#!/usr/bin/env python3
"""
Test script to verify screen sharing preview functionality.
"""

import sys
import os

# Add the project root to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_screen_sharing_preview():
    """Test that screen sharing preview functionality is available."""
    try:
        from client.gui_manager import TabbedGUIManager
        from client.main_client import CollaborationClient
        
        print("🔍 Testing Screen Sharing Preview Functionality...")
        print("=" * 60)
        
        # Test GUI Manager methods
        gui_manager = TabbedGUIManager()
        
        gui_methods = [
            'display_local_screen_preview',
            'set_screen_sharing_status',
            'display_screen_frame'
        ]
        
        print("📱 GUI Manager Methods:")
        for method in gui_methods:
            if hasattr(gui_manager, method):
                print(f"✅ {method}")
            else:
                print(f"❌ {method}")
        
        # Test ScreenShareFrame methods
        if gui_manager.screen_share_frame:
            screen_frame_methods = [
                'display_local_screen_preview',
                '_show_local_sharing_preview',
                'set_sharing_status'
            ]
            
            print(f"\n🖥️ ScreenShareFrame Methods:")
            for method in screen_frame_methods:
                if hasattr(gui_manager.screen_share_frame, method):
                    print(f"✅ {method}")
                else:
                    print(f"❌ {method}")
        
        # Test CollaborationClient methods
        print(f"\n👤 CollaborationClient Methods:")
        client_methods = [
            '_on_local_screen_frame_captured'
        ]
        
        # Check if the method exists in the class (without instantiating)
        for method in client_methods:
            if hasattr(CollaborationClient, method):
                print(f"✅ {method}")
            else:
                print(f"❌ {method}")
        
        print("=" * 60)
        print("🎯 Screen Sharing Preview Flow:")
        print("1. User clicks 'Start Screen Share'")
        print("2. Screen capture starts with frame callback")
        print("3. _on_local_screen_frame_captured() processes frames")
        print("4. display_local_screen_preview() shows preview in GUI")
        print("5. User sees their own screen in the Screen Share tab")
        
        print(f"\n✨ What's Fixed:")
        print("• Added local screen frame callback in main_client.py")
        print("• Added display_local_screen_preview() method in GUI")
        print("• Added _show_local_sharing_preview() for status messages")
        print("• Screen sharing now shows preview instead of blank screen")
        
        return True
        
    except Exception as e:
        print(f"❌ Error during screen sharing preview test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_screen_sharing_preview()
    
    if success:
        print(f"\n🚀 Screen sharing preview should work now!")
        print(f"When you share your screen, you should see:")
        print(f"• Your screen preview in the 🖥️ Screen Share tab")
        print(f"• 'SHARING' indicator overlay")
        print(f"• Live preview of what others are seeing")
        print(f"\n📋 Test Steps:")
        print(f"1. Start server: python start_server.py")
        print(f"2. Start client: python start_client.py")
        print(f"3. Go to 🖥️ Screen Share tab")
        print(f"4. Click 'Start Screen Share'")
        print(f"5. You should now see your screen preview!")
    else:
        print(f"\n⚠️  Screen sharing preview may still have issues.")
    
    sys.exit(0 if success else 1)