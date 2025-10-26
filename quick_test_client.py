#!/usr/bin/env python3
"""
Quick test to verify the client starts without errors.
"""

try:
    print("Testing client imports...")
    
    # Test GUI manager import
    from client.gui_manager import TabbedGUIManager
    print("✓ TabbedGUIManager imported successfully")
    
    # Test main client import
    from client.main_client import CollaborationClient
    print("✓ CollaborationClient imported successfully")
    
    print("\n🎉 All imports successful! Client should start without errors.")
    print("\nTo run the full client:")
    print("python start_client.py")
    
except Exception as e:
    print(f"✗ Error: {e}")
    import traceback
    traceback.print_exc()