"""
Tabbed GUI Manager for the collaboration client.
Reorganizes functionality into separate tabs while preserving all existing features.
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, scrolledtext
import threading
import logging
import time
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from client.stable_video_system import stability_manager
from client.ultra_stable_gui import ultra_stable_manager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ModuleFrame(ttk.Frame):
    """Base class for module frames in the dashboard."""
    
    def __init__(self, parent, title: str):
        super().__init__(parent, relief='ridge', borderwidth=2)
        self.title = title
        self.enabled = False
        
        # Create title label
        self.title_label = ttk.Label(self, text=title, font=('Arial', 12, 'bold'))
        self.title_label.pack(pady=5)
        
        # Status indicator
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill='x', padx=5)
        
        self.status_indicator = tk.Canvas(self.status_frame, width=12, height=12)
        self.status_indicator.pack(side='left')
        
        self.status_label = ttk.Label(self.status_frame, text="Inactive")
        self.status_label.pack(side='left', padx=(5, 0))
        
        self._update_status_indicator()
    
    def set_enabled(self, enabled: bool):
        """Set module enabled state."""
        self.enabled = enabled
        self._update_status_indicator()
    
    def _update_status_indicator(self):
        """Update the visual status indicator."""
        self.status_indicator.delete("all")
        color = "green" if self.enabled else "red"
        self.status_indicator.create_oval(2, 2, 10, 10, fill=color, outline=color)
        
        status_text = "Active" if self.enabled else "Inactive"
        self.status_label.config(text=status_text)


class VideoFrame(ModuleFrame):
    """Video conferencing module frame with large grid layout."""
    
    def __init__(self, parent):
        super().__init__(parent, "Video Conference")
        
        # Add video controls to the existing status frame (same row as Inactive/Active)
        self.video_button = ttk.Button(
            self.status_frame, 
            text="Enable Video", 
            command=self._toggle_video
        )
        self.video_button.pack(side='left', padx=(10, 2))
        
        # Video quality indicator on the right side of status frame
        self.quality_label = ttk.Label(self.status_frame, text="Quality: Auto")
        self.quality_label.pack(side='right', padx=5)
        
        # Large video display area with grid layout
        self.video_display = tk.Frame(self, bg='#2c2c2c')
        self.video_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure grid for consistent video layout - ensure equal slot sizes
        for i in range(2):  # 2x2 grid for up to 4 participants
            self.video_display.rowconfigure(i, weight=1, uniform="video_row")
            self.video_display.columnconfigure(i, weight=1, uniform="video_col")
        
        # Create video slots
        self.video_slots = {}
        self._create_video_slots()
        
        # Callbacks
        self.video_callback: Optional[Callable[[bool], None]] = None
        self.participant_videos = {}  # Track participant video states
        
        # Ultra-fast frame rate for LAN - no limiting for immediate display
        self.last_frame_time = {}  # Track last update time per client
        self.frame_rate_limit = 1.0 / 120  # Ultra-fast: 120 FPS limit for immediate updates
        self.pending_updates = {}  # Track pending updates to prevent queuing
    
    def set_video_callback(self, callback: Callable[[bool], None]):
        """Set callback for video toggle events."""
        self.video_callback = callback
    
    def _toggle_video(self):
        """Toggle video on/off."""
        self.enabled = not self.enabled
        self._update_status_indicator()
        
        button_text = "Disable Video" if self.enabled else "Enable Video"
        self.video_button.config(text=button_text)
        
        # IMMEDIATELY clear local video slot when disabling video
        if not self.enabled:
            self._clear_local_video_slot()
            # Force immediate GUI update to show black screen
            if hasattr(self, 'video_display'):
                self.video_display.update_idletasks()
                self.video_display.update()
        
        if self.video_callback:
            self.video_callback(self.enabled)
    
    def _clear_local_video_slot(self):
        """Clear the local video slot and show blank placeholder when video is disabled."""
        try:
            if 0 in self.video_slots:
                slot = self.video_slots[0]
                if self._widget_exists(slot['frame']):
                    # IMMEDIATELY destroy ALL widgets to remove last frame
                    children_to_destroy = list(slot['frame'].winfo_children())
                    for child in children_to_destroy:
                        # Aggressively clear any image references
                        if isinstance(child, tk.Label) and hasattr(child, 'image'):
                            child.image = None
                            child.configure(image='', text='')
                        # Immediately destroy the widget
                        child.destroy()
                    
                    # Force immediate update to clear the display
                    slot['frame'].update_idletasks()
                    slot['frame'].update()
                    
                    # Create blank black screen placeholder IMMEDIATELY
                    placeholder_label = tk.Label(
                        slot['frame'], 
                        text="",  # No text - completely blank
                        fg='black', 
                        bg='black',  # Pure black background
                        font=('Arial', 1),  # Minimal font
                        bd=0,
                        highlightthickness=0,
                        relief='flat'
                    )
                    placeholder_label.pack(fill='both', expand=True, padx=0, pady=0)
                    
                    # Force immediate display update
                    placeholder_label.update_idletasks()
                    placeholder_label.update()
                    
                    # Update slot references
                    slot['label'] = placeholder_label
                    slot['participant_id'] = 'local'
                    slot['active'] = False
                    
                    logger.info("Local video slot IMMEDIATELY cleared - showing blank black screen")
        except Exception as e:
            logger.error(f"Error clearing local video slot: {e}")
    
    def clear_remote_video_slot(self, client_id: str):
        """Clear a remote video slot and show blank when video is disabled."""
        try:
            # Find the slot for this client
            for slot_id, slot in self.video_slots.items():
                if slot.get('participant_id') == client_id:
                    if self._widget_exists(slot['frame']):
                        # IMMEDIATELY destroy ALL widgets to remove last frame
                        children_to_destroy = list(slot['frame'].winfo_children())
                        for child in children_to_destroy:
                            # Aggressively clear any image references
                            if isinstance(child, tk.Label) and hasattr(child, 'image'):
                                child.image = None
                                child.configure(image='', text='')
                            # Immediately destroy the widget
                            child.destroy()
                        
                        # Force immediate update to clear the display
                        slot['frame'].update_idletasks()
                        slot['frame'].update()
                        
                        # Create blank black screen placeholder IMMEDIATELY
                        placeholder_label = tk.Label(
                            slot['frame'], 
                            text="",  # No text - completely blank
                            fg='black', 
                            bg='black',  # Pure black background
                            font=('Arial', 1),  # Minimal font
                            bd=0,
                            highlightthickness=0,
                            relief='flat'
                        )
                        placeholder_label.pack(fill='both', expand=True, padx=0, pady=0)
                        
                        # Force immediate display update
                        placeholder_label.update_idletasks()
                        placeholder_label.update()
                        
                        # Update slot references
                        slot['label'] = placeholder_label
                        slot['participant_id'] = None
                        slot['active'] = False
                        
                        logger.info(f"Remote video slot IMMEDIATELY cleared for {client_id} - showing blank black screen")
                    break
        except Exception as e:
            logger.error(f"Error clearing remote video slot for {client_id}: {e}")
    
    def _create_video_slots(self):
        """Create video slots in a 2x2 grid with consistent sizing."""
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i, (row, col) in enumerate(positions):
            # Create slot frame with consistent sizing
            slot_frame = tk.Frame(self.video_display, bg='black', relief='solid', borderwidth=1)
            slot_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=2)
            
            # Ensure slot frame expands to fill grid cell
            slot_frame.grid_propagate(False)  # Prevent frame from shrinking
            
            # Placeholder content - blank for all slots to match your video style
            placeholder_label = tk.Label(
                slot_frame, 
                text="", 
                fg='white', 
                bg='black',
                font=('Arial', 10),
                bd=0,
                highlightthickness=0
            )
            placeholder_label.pack(fill='both', expand=True, padx=0, pady=0)
            
            self.video_slots[i] = {
                'frame': slot_frame,
                'label': placeholder_label,
                'participant_id': 'local' if i == 0 else None,
                'active': False
            }
    
    # Include all the existing video methods from the original file
    def update_video_feeds(self, participants: Dict[str, Any]):
        """Update video feed display with participant information."""
        # Update participant info for username display
        for participant_id, participant_info in participants.items():
            username = participant_info.get('username', '')
            video_enabled = participant_info.get('video_enabled', False)
            self.update_participant_info(participant_id, username, video_enabled)
        
        # Get participants with video enabled
        active_participants = [p for p in participants.values() 
                             if p.get('video_enabled', False)]
        
        # Clear all remote slots first to prevent duplicates
        for slot_id, slot in self.video_slots.items():
            if slot_id > 0:  # Don't clear slot 0 (local video)
                if self._widget_exists(slot['frame']):
                    # Clear all widgets from the slot to show blank
                    for child in slot['frame'].winfo_children():
                        child.destroy()
                    
                    # Create blank placeholder
                    placeholder_label = tk.Label(
                        slot['frame'], 
                        text="",  # No text - completely blank
                        fg='white', 
                        bg='black',
                        font=('Arial', 10),
                        bd=0,
                        highlightthickness=0
                    )
                    placeholder_label.pack(fill='both', expand=True, padx=0, pady=0)
                    
                    slot['label'] = placeholder_label
                    slot['participant_id'] = None
                    slot['active'] = False
        
        # Assign participants to available slots (skip slot 0 for local video)
        assigned_participants = set()  # Track assigned participants to prevent duplicates
        slot_index = 1  # Start from slot 1 (slot 0 is for local video)
        
        for participant in active_participants:
            participant_id = participant.get('client_id')
            participant_name = participant.get('username', 'Unknown')
            
            # Skip if already assigned or if no more slots available
            if participant_id in assigned_participants or slot_index >= len(self.video_slots):
                continue
            
            # Assign to next available slot
            if slot_index in self.video_slots:
                slot = self.video_slots[slot_index]
                
                # Update slot with participant info
                if self._widget_exists(slot['frame']):
                    # Clear existing widgets
                    for child in slot['frame'].winfo_children():
                        child.destroy()
                    
                    # Create blank placeholder (no text, just black background like local video)
                    placeholder_label = tk.Label(
                        slot['frame'], 
                        text="",  # No text - completely blank like local video
                        fg='white', 
                        bg='black',
                        font=('Arial', 10),
                        bd=0,
                        highlightthickness=0
                    )
                    placeholder_label.pack(fill='both', expand=True, padx=0, pady=0)
                    slot['label'] = placeholder_label
                    
                    # Create username label at top-left corner (similar to local video)
                    name_label = tk.Label(
                        slot['frame'],
                        text=participant_name,
                        fg='lightblue',
                        bg='black',
                        font=('Arial', 8, 'bold')
                    )
                    # Position at top-left with small padding
                    name_label.place(x=5, y=5)
                
                slot['participant_id'] = participant_id
                slot['active'] = True
                
                assigned_participants.add(participant_id)
                slot_index += 1
    
    def update_local_video(self, frame):
        """Update local video display with proper frame sequencing."""
        try:
            # CRITICAL: Do not update video if video is disabled
            if not self.enabled:
                logger.debug("Video is disabled - ignoring frame update")
                return
            
            # Use direct stable video display for proper frame sequencing
            self._update_local_video_safe_stable(frame)
            
        except Exception as e:
            logger.error(f"Local video display error: {e}")
            # Fallback to ultra-stable system if needed (only if video is enabled)
            if self.enabled:
                try:
                    client_id = 'local'
                    if 0 in self.video_slots:
                        ultra_stable_manager.register_video_slot(client_id, self.video_slots[0])
                        ultra_stable_manager.update_video_frame(client_id, frame)
                except Exception as fallback_error:
                    logger.error(f"Fallback local video error: {fallback_error}")
    
    def _widget_exists(self, widget):
        """Check if a tkinter widget still exists and is valid."""
        try:
            if widget is None:
                return False
            return widget.winfo_exists()
        except (tk.TclError, AttributeError):
            return False
        except Exception:
            return False
    
    def _update_local_video_safe_stable(self, frame):
        """Safe stable update for local video."""
        try:
            if 0 in self.video_slots:
                slot = self.video_slots[0]
                if self._widget_exists(slot['frame']):
                    # Create or update video display safely
                    self._create_stable_video_display(slot['frame'], frame, 'local')
        except Exception as e:
            logger.error(f"Safe local video update error: {e}")
    
    def _create_stable_video_display(self, parent_frame, frame, client_id: str):
        """Create stable video display that fills the entire slot without blank spaces."""
        try:
            import cv2
            from PIL import Image, ImageTk
            
            # Convert frame for display
            if frame is not None and frame.size > 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                
                # Get the actual slot dimensions to fill the entire slot
                parent_frame.update_idletasks()
                slot_width = parent_frame.winfo_width()
                slot_height = parent_frame.winfo_height()
                
                # Use fallback dimensions if slot is not properly initialized
                if slot_width <= 1 or slot_height <= 1:
                    # Get parent video display dimensions as fallback
                    video_display = parent_frame.master
                    if hasattr(video_display, 'winfo_width'):
                        video_display.update_idletasks()
                        display_width = video_display.winfo_width()
                        display_height = video_display.winfo_height()
                        # Calculate slot size (accounting for grid padding and borders)
                        slot_width = max((display_width - 6) // 2, 200)  # 2 columns, minus padding
                        slot_height = max((display_height - 6) // 2, 150)  # 2 rows, minus padding
                    else:
                        slot_width = 400
                        slot_height = 300
                
                # Calculate display size to fill the entire slot
                # No need to reserve space for name label since it's positioned absolutely
                available_height = max(slot_height - 4, 100)  # Small padding only
                available_width = max(slot_width - 4, 150)  # Small padding only
                
                # Resize image to fill the entire slot while maintaining aspect ratio
                img_width, img_height = pil_image.size
                if img_width > 0 and img_height > 0:
                    # Calculate scale factors
                    scale_w = available_width / img_width
                    scale_h = available_height / img_height
                    
                    # Use the larger scale to fill the slot completely
                    scale = max(scale_w, scale_h)
                    
                    # Calculate new dimensions
                    new_width = int(img_width * scale)
                    new_height = int(img_height * scale)
                    
                    # Ensure minimum size
                    new_width = max(new_width, available_width)
                    new_height = max(new_height, available_height)
                    
                    # Resize image to fill the slot
                    pil_image = pil_image.resize((new_width, new_height), Image.LANCZOS)
                
                photo = ImageTk.PhotoImage(pil_image)
                
                # Find existing video widget or create new one
                video_widgets = [child for child in parent_frame.winfo_children() 
                               if isinstance(child, tk.Label) and hasattr(child, 'image') and child.image is not None]
                
                if video_widgets:
                    # Update existing widget
                    video_widget = video_widgets[0]
                    video_widget.configure(image=photo)
                    video_widget.image = photo
                else:
                    # Create new widget only if necessary
                    # Clear placeholder labels and any stale video widgets without valid images
                    for child in parent_frame.winfo_children():
                        if isinstance(child, tk.Label):
                            # Remove placeholder labels
                            if not hasattr(child, 'image') or child.image is None:
                                if ('Video Slot' in child.cget('text') or 
                                    'Enable video' in child.cget('text') or 
                                    child.cget('text') == ''):  # Blank placeholders
                                    child.destroy()
                            # Remove stale video widgets with cleared images
                            elif hasattr(child, 'image') and child.image is None:
                                child.destroy()
                    
                    # Create video widget that fills the entire slot with no padding
                    video_widget = tk.Label(parent_frame, image=photo, bg='black', bd=0, highlightthickness=0)
                    video_widget.pack(fill='both', expand=True, padx=0, pady=0)
                    video_widget.image = photo
                    
                    # Create name label at top-left corner with proper username
                    name_text = self._get_display_name(client_id)
                    name_label = tk.Label(
                        parent_frame,
                        text=name_text,
                        fg='lightgreen' if client_id == 'local' else 'lightblue',
                        bg='black',
                        font=('Arial', 8, 'bold')
                    )
                    # Position at top-left with small padding
                    name_label.place(x=5, y=5)
                    
        except Exception as e:
            logger.error(f"Error creating stable video display for {client_id}: {e}")
    
    def _get_display_name(self, client_id: str) -> str:
        """Get display name for a client, showing username if available."""
        try:
            if client_id == 'local':
                # Get the actual username from connection manager if available
                if hasattr(self, 'participant_videos') and 'local' in self.participant_videos:
                    participant_info = self.participant_videos['local']
                    username = participant_info.get('username', '')
                    if username:
                        return username
                return "You"  # Simple "You" instead of "You (Local)"
            
            # Try to get username from participants
            if hasattr(self, 'participant_videos') and client_id in self.participant_videos:
                participant_info = self.participant_videos[client_id]
                username = participant_info.get('username', '')
                if username and username != client_id:
                    return username
            
            # Fallback to showing last 8 characters of client ID
            if len(client_id) > 8:
                return f"User {client_id[-8:]}"
            else:
                return f"User {client_id}"
        except Exception as e:
            logger.error(f"Error getting display name for {client_id}: {e}")
            if len(client_id) > 8:
                return f"User {client_id[-8:]}"
            else:
                return f"User {client_id}"
    
    def update_remote_video(self, client_id: str, frame):
        """Update remote video display with enhanced error handling."""
        try:
            logger.debug(f"Updating remote video for client {client_id}")
            
            # CRITICAL: Check if this participant's video is enabled
            if hasattr(self, 'participant_videos') and client_id in self.participant_videos:
                video_enabled = self.participant_videos[client_id].get('video_enabled', True)
                if not video_enabled:
                    logger.debug(f"Video disabled for {client_id} - ignoring frame update")
                    return
            
            # Get or assign video slot
            slot_id = self._get_video_slot_stable(client_id)
            
            if slot_id is not None and slot_id in self.video_slots:
                # Assign slot to this client
                self.video_slots[slot_id]['participant_id'] = client_id
                self.video_slots[slot_id]['active'] = True
                
                # Create video display
                self._create_stable_video_display(
                    self.video_slots[slot_id]['frame'], frame, client_id
                )
                
                logger.debug(f"Remote video updated for {client_id} in slot {slot_id}")
            else:
                logger.warning(f"No available video slot for remote client {client_id}")
                
        except Exception as e:
            logger.error(f"Error updating remote video for {client_id}: {e}")
    
    def update_participant_info(self, client_id: str, username: str = None, video_enabled: bool = None):
        """Update participant information for username display."""
        try:
            if not hasattr(self, 'participant_videos'):
                self.participant_videos = {}
            
            if client_id not in self.participant_videos:
                self.participant_videos[client_id] = {}
            
            if username is not None:
                self.participant_videos[client_id]['username'] = username
            if video_enabled is not None:
                self.participant_videos[client_id]['video_enabled'] = video_enabled
                
            logger.debug(f"Updated participant info for {client_id}: username={username}, video={video_enabled}")
        except Exception as e:
            logger.error(f"Error updating participant info for {client_id}: {e}")
    
    def _get_video_slot_stable(self, client_id: str) -> Optional[int]:
        """Get video slot with enhanced positioning - remote video goes to top-right."""
        try:
            # Check existing assignment
            for slot_id, slot in self.video_slots.items():
                if slot.get('participant_id') == client_id:
                    return slot_id
            
            # For remote clients, prioritize top-right corner (slot 1)
            if client_id != 'local':
                # Preferred order for remote clients: top-right (1), bottom-right (3), bottom-left (2)
                preferred_slots = [1, 3, 2]  # Skip slot 0 (local video)
                
                for slot_id in preferred_slots:
                    if slot_id in self.video_slots:
                        slot = self.video_slots[slot_id]
                        if not slot.get('active', False) or slot.get('participant_id') is None:
                            logger.info(f"Assigning remote client {client_id} to slot {slot_id} (position priority)")
                            return slot_id
            
            # Fallback: find any available slot (skip slot 0 for local)
            for slot_id in range(1, len(self.video_slots)):
                slot = self.video_slots[slot_id]
                if not slot.get('active', False):
                    return slot_id
            
            return None
        except Exception as e:
            logger.error(f"Error getting video slot for {client_id}: {e}")
            return None
    
    def clear_video_slot(self, client_id: str):
        """Clear video slot for a disconnected client with ultra-stability and black screen."""
        try:
            # Remove from ultra-stable manager
            ultra_stable_manager.unregister_video_slot(client_id)
            
            # Also remove from stability manager
            stability_manager.remove_video_slot(client_id)
            
            for slot_id, slot in self.video_slots.items():
                if slot.get('participant_id') == client_id:
                    logger.info(f"Clearing ultra-stable video slot {slot_id} for client {client_id}")
                    
                    # COMPLETELY CLEAR THE SLOT - destroy ALL child widgets to show black screen
                    if self._widget_exists(slot['frame']):
                        for child in slot['frame'].winfo_children():
                            child.destroy()
                        
                        # Create blank screen placeholder (no text, just black background)
                        black_label = tk.Label(
                            slot['frame'], 
                            text="", 
                            bg='black', 
                            fg='white',
                            font=('Arial', 10),
                            bd=0,
                            highlightthickness=0
                        )
                        black_label.pack(fill='both', expand=True, padx=0, pady=0)
                        
                        # Update slot references
                        slot['video_widget'] = black_label
                        slot['name_label'] = None
                        slot['participant_id'] = 'local' if slot_id == 0 else None
                        slot['active'] = False
                    break
                    
        except Exception as e:
            logger.error(f"Error clearing ultra-stable video slot for {client_id}: {e}")


class AudioFrame:
    """Compact audio controls for integration into status row."""
    
    def __init__(self, parent):
        self.parent = parent
        self.enabled = False
        self.muted = False
        
        # Create compact audio controls in the parent frame (status row)
        self.audio_button = ttk.Button(
            parent, 
            text="Enable Audio", 
            command=self._toggle_audio
        )
        self.audio_button.pack(side='left', padx=(10, 2))
        
        self.mute_button = ttk.Button(
            parent, 
            text="Mute", 
            command=self._toggle_mute,
            state='disabled'
        )
        self.mute_button.pack(side='left', padx=2)
        
        # Compact audio level indicator
        ttk.Label(parent, text="Level:").pack(side='left', padx=(10, 2))
        
        self.level_bar = ttk.Progressbar(
            parent, 
            length=60,  # Compact size
            mode='determinate'
        )
        self.level_bar.pack(side='left', padx=2)
        
        # Callbacks
        self.audio_callback: Optional[Callable[[bool], None]] = None
        self.mute_callback: Optional[Callable[[bool], None]] = None
    
    def set_audio_callback(self, callback: Callable[[bool], None]):
        """Set callback for audio toggle events."""
        self.audio_callback = callback
    
    def set_mute_callback(self, callback: Callable[[bool], None]):
        """Set callback for mute toggle events."""
        self.mute_callback = callback
    
    def _toggle_audio(self):
        """Toggle audio on/off."""
        self.enabled = not self.enabled
        
        button_text = "Disable Audio" if self.enabled else "Enable Audio"
        self.audio_button.config(text=button_text)
        
        # Enable/disable mute button
        mute_state = 'normal' if self.enabled else 'disabled'
        self.mute_button.config(state=mute_state)
        
        if self.audio_callback:
            self.audio_callback(self.enabled and not self.muted)
    
    def _toggle_mute(self):
        """Toggle mute on/off."""
        self.muted = not self.muted
        
        button_text = "Unmute" if self.muted else "Mute"
        self.mute_button.config(text=button_text)
        
        # Call separate mute callback if available
        if self.mute_callback:
            self.mute_callback(self.muted)
        
        # Also call audio callback for overall state
        if self.audio_callback:
            self.audio_callback(self.enabled and not self.muted)
    
    def update_audio_level(self, level: float):
        """Update audio level indicator (0.0 to 1.0)."""
        self.level_bar['value'] = level * 100


class ScreenShareFrame(ModuleFrame):
    """Screen sharing module frame with presenter controls and display."""
    
    def __init__(self, parent):
        super().__init__(parent, "Screen Share")
        
        # Screen sharing state
        self.is_sharing = False
        self.current_presenter_name = None
        
        # Screen share controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        # Direct screen share button
        self.share_button = ttk.Button(
            self.controls_frame, 
            text="Start Screen Share", 
            command=self._toggle_screen_share
        )
        self.share_button.pack(side='left', padx=2)
        
        # Screen sharing status
        self.status_frame = ttk.Frame(self)
        self.status_frame.pack(fill='x', padx=5, pady=2)
        
        self.sharing_status = ttk.Label(self.status_frame, text="Ready to share")
        self.sharing_status.pack(side='left')
        
        # Screen display area (maximum size for dedicated tab)
        self.screen_display = tk.Frame(self, bg='black', height=700)
        self.screen_display.pack(fill='both', expand=True, padx=1, pady=1)
        self.screen_display.pack_propagate(False)  # Maintain minimum height
        
        self.screen_label = ttk.Label(self.screen_display, text="No screen sharing active", 
                                    background='black', foreground='white')
        self.screen_label.pack(expand=True)
        
        # Screen frame display (for actual screen content) with improved initialization
        self.screen_canvas = tk.Canvas(self.screen_display, bg='black', highlightthickness=0)
        self.screen_canvas.pack(fill='both', expand=True)
        self.screen_canvas.pack_forget()  # Initially hidden
        
        # Canvas state tracking for automatic rescaling
        self.last_canvas_size = (0, 0)
        self.current_frame_data = None
        self.current_presenter = None
        
        # Bind canvas resize event for automatic rescaling
        self.screen_canvas.bind('<Configure>', self._on_canvas_resize)
        
        # Initialize canvas with proper size detection
        self._initialize_canvas()
        
        # Callbacks
        self.screen_share_callback: Optional[Callable[[bool], None]] = None

    def _safe_button_update(self, button, **kwargs):
        """Safely update button properties with validation."""
        try:
            if button and button.winfo_exists():
                button.config(**kwargs)
            else:
                logger.warning("Attempted to update non-existent button")
        except tk.TclError as e:
            logger.error(f"Tkinter error updating button: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating button: {e}")
    
    def _safe_label_update(self, label, **kwargs):
        """Safely update label properties with validation."""
        try:
            if label and label.winfo_exists():
                label.config(**kwargs)
            else:
                logger.warning("Attempted to update non-existent label")
        except tk.TclError as e:
            logger.error(f"Tkinter error updating label: {e}")
        except Exception as e:
            logger.error(f"Unexpected error updating label: {e}")

    def set_screen_share_callback(self, callback: Callable[[bool], None]):
        """Set callback for screen sharing toggle events."""
        self.screen_share_callback = callback
    
    def _toggle_screen_share(self):
        """Toggle screen sharing on/off or request presenter role with loading states."""
        try:
            logger.info(f"Screen share button clicked. Current sharing: {self.is_sharing}")
            
            # Safely get button text with validation
            try:
                if not self.share_button.winfo_exists():
                    logger.error("Share button no longer exists")
                    return
                button_text = self.share_button.cget('text')
            except tk.TclError as e:
                logger.error(f"Error getting button text: {e}")
                return
            
            if button_text == "Request Presenter Role":
                # Add loading states during presenter role requests
                self._safe_button_update(self.share_button, state='disabled', text="Requesting...")
                self._safe_label_update(self.sharing_status, text="Requesting presenter role...", foreground='orange')
                
                # Request presenter role
                if self.screen_share_callback:
                    logger.info("Requesting presenter role")
                    self.screen_share_callback(True)  # This will trigger presenter role request
                    
                    # Set timeout to reset button if no response
                    self.after(10000, self._reset_presenter_request_timeout)
            elif button_text.startswith("Start"):
                # Start screen sharing (already presenter)
                self._safe_button_update(self.share_button, state='disabled', text="Starting...")
                self._safe_label_update(self.sharing_status, text="Starting screen share...", foreground='orange')
                
                if self.screen_share_callback:
                    logger.info("Starting screen sharing")
                    self.screen_share_callback(True)
            elif button_text.startswith("Stop"):
                # Stop screen sharing
                if self.screen_share_callback:
                    logger.info("Stopping screen sharing")
                    self.screen_share_callback(False)
            else:
                logger.warning(f"Unknown button state: {button_text}")
        
        except Exception as e:
            logger.error(f"Error in screen share toggle: {e}")
            # Reset button state on error
            try:
                self._safe_button_update(self.share_button, state='normal', text="Request Presenter Role")
                self._safe_label_update(self.sharing_status, text="Error - try again", foreground='red')
            except:
                pass
    
    def _reset_presenter_request_timeout(self):
        """Reset presenter request button after timeout."""
        if self.share_button.cget('text') == "Requesting...":
            self._safe_button_update(self.share_button, state='normal', text="Request Presenter Role")
            self._safe_label_update(self.sharing_status, text="Request timed out - try again", foreground='red')
            # Reset to normal after delay
            self.after(3000, lambda: self._safe_label_update(self.sharing_status, text="Ready to request presenter role", foreground='black'))
    
    def update_presenter(self, presenter_name: str = None):
        """Update presenter display (for showing who is currently presenting)."""
        self.current_presenter_name = presenter_name
        
        # Update button state based on who is sharing
        if presenter_name and not self.is_sharing:
            # Someone else is sharing - disable our button
            self._safe_button_update(self.share_button, state='disabled', text=f"{presenter_name} is sharing")
            # Display "[Username] is sharing" when receiving remote screen
            self._safe_label_update(self.sharing_status, text=f"{presenter_name} is sharing", foreground='blue')
            # Show their screen area
            if not self.screen_canvas.winfo_viewable():
                self.screen_label.pack_forget()
                self.screen_canvas.pack(fill='both', expand=True)
        elif not presenter_name and not self.is_sharing:
            # No one is sharing - enable our button
            self._safe_button_update(self.share_button, state='normal', text="Start Screen Share")
            # Reset status to "Ready to share" when screen sharing stops
            self._safe_label_update(self.sharing_status, text="Ready to share", foreground='black')
            # Hide screen area
            self.screen_canvas.pack_forget()
            self.screen_label.pack(expand=True)
        
        # Update display based on sharing status
        if not self.is_sharing:
            if presenter_name:
                self._safe_label_update(self.screen_label, text=f"Waiting for {presenter_name} to share")
            else:
                self._safe_label_update(self.screen_label, text="No screen sharing active")
    
    def set_sharing_status(self, is_sharing: bool):
        """Update screen sharing status with proper status messages."""
        self.is_sharing = is_sharing
        self.enabled = is_sharing
        self._update_status_indicator()
        
        if is_sharing:
            self._safe_button_update(self.share_button, text="Stop Screen Share", state='normal')
            # Show "You are sharing" when local screen sharing is active
            self._safe_label_update(self.sharing_status, text="You are sharing", foreground='green')
            self.screen_label.pack_forget()
            self.screen_canvas.pack(fill='both', expand=True)
            
            # Show preview message for local screen sharing
            self._show_local_sharing_preview()
        else:
            self._safe_button_update(self.share_button, text="Start Screen Share", state='normal')
            # Reset status to "Ready to share" when screen sharing stops
            self._safe_label_update(self.sharing_status, text="Ready to share", foreground='black')
            self.screen_canvas.pack_forget()
            self.screen_label.pack(expand=True)
            
            # Clear cached values when stopping screen sharing to prevent issues
            self._reset_screen_cache()
            
            if self.current_presenter_name:
                self._safe_label_update(self.screen_label, text=f"{self.current_presenter_name} is sharing")
            else:
                self._safe_label_update(self.screen_label, text="No screen sharing active")
    
    def _reset_screen_cache(self):
        """Reset cached screen display values to prevent flickering issues."""
        try:
            # Reset all cached values
            self._cached_canvas_size = None
            self._cached_scale = None
            self._cached_scale_key = None
            self._cached_dimensions = None
            self._last_image_id = None
            
            # Reset local preview cache
            self._cached_local_canvas_size = None
            self._cached_local_scale = None
            self._cached_local_scale_key = None
            self._cached_local_dimensions = None
            self._local_image_id = None
            
            # Clear canvas completely
            if hasattr(self, 'screen_canvas') and self.screen_canvas:
                self.screen_canvas.delete("all")
            
            logger.debug("Screen display cache reset")
            
        except Exception as e:
            logger.error(f"Error resetting screen cache: {e}")

    def display_screen_frame(self, frame_data, presenter_name: str):
        """Display a screen frame from the presenter with anti-flickering optimizations."""
        try:
            # Handle None frame data (black screen when presenter stops)
            if frame_data is None:
                self._show_black_screen()
                return
                
            import io
            from PIL import Image, ImageTk
            
            # Store current frame data for rescaling when canvas size changes
            self._store_current_frame(frame_data, presenter_name)
            
            # Update presenter info only when changed (reduce unnecessary updates)
            if self.current_presenter_name != presenter_name:
                self.update_presenter(presenter_name)
                logger.debug(f"Now receiving screen from {presenter_name}")  # Changed to debug
            
            # Convert frame data to PIL Image
            image = Image.open(io.BytesIO(frame_data))
            
            # Show canvas first to ensure it's visible (only if not already visible)
            if not self.screen_canvas.winfo_viewable():
                self.screen_label.pack_forget()
                self.screen_canvas.pack(fill='both', expand=True)
                # Only update canvas size when first showing
                self.screen_canvas.update_idletasks()
            
            # Get canvas dimensions with caching to avoid repeated calls
            if not hasattr(self, '_cached_canvas_size') or self._cached_canvas_size is None:
                canvas_width = self.screen_canvas.winfo_width()
                canvas_height = self.screen_canvas.winfo_height()
                
                # Use fallback dimensions if canvas is not properly initialized
                if canvas_width <= 10 or canvas_height <= 10:
                    canvas_width = max(canvas_width, 1000)  # Maximum fallback for full screen effect
                    canvas_height = max(canvas_height, 650)  # Maximum height for better display
                    logger.debug(f"Using fallback canvas dimensions: {canvas_width}x{canvas_height}")
                
                self._cached_canvas_size = (canvas_width, canvas_height)
            else:
                canvas_width, canvas_height = self._cached_canvas_size
            
            # Calculate proper aspect ratio scaling to prevent distortion
            img_width, img_height = image.size
            if img_width <= 0 or img_height <= 0:
                logger.error("Invalid image dimensions")
                return
            
            # Cache scaling calculations to avoid repeated computation
            scale_key = f"{img_width}x{img_height}_{canvas_width}x{canvas_height}"
            if not hasattr(self, '_cached_scale') or self._cached_scale_key != scale_key:
                # Calculate scale factors for both dimensions
                scale_w = canvas_width / img_width
                scale_h = canvas_height / img_height
                
                # Use the smaller scale to fit within canvas while maintaining aspect ratio
                scale = min(scale_w, scale_h) * 0.99  # Use 99% to maximize space usage for full screen effect
                
                # Apply minimum scale factor to prevent tiny images
                scale = max(scale, 0.3)
                
                # Calculate new dimensions
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Ensure minimum visible size
                new_width = max(new_width, 200)
                new_height = max(new_height, 150)
                
                # Cache the calculations
                self._cached_scale = scale
                self._cached_scale_key = scale_key
                self._cached_dimensions = (new_width, new_height)
                
                logger.debug(f"Calculated scaling: {img_width}x{img_height} -> {new_width}x{new_height} (scale: {scale:.2f})")
            else:
                new_width, new_height = self._cached_dimensions
            
            # Resize image with high quality resampling (since we reduced frame rate, we can afford better quality)
            image = image.resize((new_width, new_height), Image.LANCZOS)  # Better quality for screen sharing
            
            # Convert to PhotoImage for tkinter
            photo = ImageTk.PhotoImage(image)
            
            # Optimized canvas update - only clear and redraw if necessary
            if not hasattr(self, '_last_image_id') or self._last_image_id is None:
                # First image - clear canvas
                self.screen_canvas.delete("all")
                
                # Center the image in the canvas
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                x = max(0, x)
                y = max(0, y)
                
                # Create image on canvas at centered position
                self._last_image_id = self.screen_canvas.create_image(x, y, anchor='nw', image=photo)
            else:
                # Update existing image instead of clearing and recreating
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                x = max(0, x)
                y = max(0, y)
                
                # Update the existing image item
                self.screen_canvas.coords(self._last_image_id, x, y)
                self.screen_canvas.itemconfig(self._last_image_id, image=photo)
            
            # Keep a reference to prevent garbage collection
            self.screen_canvas.image = photo
            
        except Exception as e:
            logger.error(f"Error displaying screen frame: {e}")
            # Reset cached values on error
            self._cached_canvas_size = None
            self._cached_scale = None
            self._last_image_id = None
            
            # Show error message to user
            if hasattr(self, 'screen_label'):
                self._safe_label_update(self.screen_label, text=f"Error displaying screen from {presenter_name}")
                if not self.screen_label.winfo_viewable():
                    self.screen_canvas.pack_forget()
                    self.screen_label.pack(expand=True)
    
    def _initialize_canvas(self):
        """Initialize canvas with proper size detection and fallback values."""
        try:
            # Force initial update to get proper dimensions
            self.screen_canvas.update_idletasks()
            
            # Get initial canvas size
            width = self.screen_canvas.winfo_width()
            height = self.screen_canvas.winfo_height()
            
            # Set fallback dimensions if canvas is not properly initialized
            if width <= 1 or height <= 1:
                # Use parent frame dimensions as fallback
                parent_width = self.screen_display.winfo_width()
                parent_height = self.screen_display.winfo_height()
                
                if parent_width > 1 and parent_height > 1:
                    width = max(parent_width - 10, 400)  # Account for padding
                    height = max(parent_height - 10, 300)
                else:
                    # Ultimate fallback dimensions
                    width = 400
                    height = 300
                
                logger.info(f"Canvas initialized with fallback dimensions: {width}x{height}")
            else:
                logger.info(f"Canvas initialized with actual dimensions: {width}x{height}")
            
            # Store initial size
            self.last_canvas_size = (width, height)
            
        except Exception as e:
            logger.error(f"Error initializing canvas: {e}")
            # Set safe fallback dimensions
            self.last_canvas_size = (400, 300)
    
    def _on_canvas_resize(self, event):
        """Handle canvas resize events for automatic rescaling."""
        try:
            # Only handle resize events for the canvas itself, not child widgets
            if event.widget != self.screen_canvas:
                return
            
            new_width = event.width
            new_height = event.height
            
            # Check if size actually changed significantly (avoid minor fluctuations)
            old_width, old_height = self.last_canvas_size
            width_change = abs(new_width - old_width)
            height_change = abs(new_height - old_height)
            
            if width_change > 5 or height_change > 5:  # Only rescale for significant changes
                logger.info(f"Canvas resized from {old_width}x{old_height} to {new_width}x{new_height}")
                
                # Update stored size
                self.last_canvas_size = (new_width, new_height)
                
                # If we have current frame data, rescale it
                if self.current_frame_data and self.current_presenter:
                    logger.info("Rescaling current frame for new canvas size")
                    self.display_screen_frame(self.current_frame_data, self.current_presenter)
                
        except Exception as e:
            logger.error(f"Error handling canvas resize: {e}")

    def reset_screen_sharing_button(self):
        """Reset screen sharing button to initial state."""
        try:
            self._safe_button_update(self.share_button, state='normal', text="Request Presenter Role")
            self._safe_label_update(self.sharing_status, text="Ready to request presenter role", foreground='black')
            self.is_sharing = False
            logger.info("Screen sharing button reset to initial state")
        except Exception as e:
            logger.error(f"Error resetting screen sharing button: {e}")

    def _show_black_screen(self):
        """Show black screen when presenter stops sharing."""
        try:
            # Clear canvas and show black screen
            self.screen_canvas.delete("all")
            self.screen_canvas.config(bg='black')
            
            # Show "No screen sharing" message
            self.screen_canvas.create_text(
                self.screen_canvas.winfo_width() // 2,
                self.screen_canvas.winfo_height() // 2,
                text="No screen sharing active",
                fill="white",
                font=("Arial", 12)
            )
            
            # Update status
            self._safe_label_update(self.screen_label, text="No screen sharing active")
            self.current_presenter_name = None
            
            logger.info("Displaying black screen - screen sharing stopped")
            
        except Exception as e:
            logger.error(f"Error showing black screen: {e}")

    def cleanup_gui_elements(self):
        """Safely cleanup GUI elements to prevent tkinter errors."""
        try:
            # Reset button state safely
            if hasattr(self, 'share_button') and self.share_button:
                try:
                    if self.share_button.winfo_exists():
                        self.share_button.config(state='disabled')
                except tk.TclError:
                    pass  # Button already destroyed
            
            # Reset status label safely
            if hasattr(self, 'sharing_status') and self.sharing_status:
                try:
                    if self.sharing_status.winfo_exists():
                        self.sharing_status.config(text="Disconnected", foreground='red')
                except tk.TclError:
                    pass  # Label already destroyed
            
            # Clear canvas safely
            if hasattr(self, 'screen_canvas') and self.screen_canvas:
                try:
                    if self.screen_canvas.winfo_exists():
                        self.screen_canvas.delete("all")
                except tk.TclError:
                    pass  # Canvas already destroyed
            
            logger.info("GUI elements cleaned up safely")
        
        except Exception as e:
            logger.error(f"Error during GUI cleanup: {e}")

    def _store_current_frame(self, frame_data, presenter_name: str):
        """Store current frame data for rescaling when canvas size changes."""
        self.current_frame_data = frame_data
        self.current_presenter = presenter_name
    
    def _show_local_sharing_preview(self):
        """Show preview message when you are sharing your screen."""
        try:
            # Clear canvas and show preview message
            self.screen_canvas.delete("all")
            self.screen_canvas.config(bg='#1a1a1a')  # Dark gray background
            
            # Get canvas dimensions
            canvas_width = self.screen_canvas.winfo_width()
            canvas_height = self.screen_canvas.winfo_height()
            
            # Use fallback dimensions if canvas is not ready
            if canvas_width <= 10 or canvas_height <= 10:
                canvas_width = 600
                canvas_height = 400
            
            # Show "You are sharing" message in center
            center_x = canvas_width // 2
            center_y = canvas_height // 2
            
            # Main message
            self.screen_canvas.create_text(
                center_x, center_y - 40,
                text="🖥️ You are sharing your screen",
                fill="#00ff00",  # Green color
                font=("Arial", 16, "bold"),
                anchor="center"
            )
            
            # Subtitle
            self.screen_canvas.create_text(
                center_x, center_y + 10,
                text="Other participants can see your screen",
                fill="#ffffff",  # White color
                font=("Arial", 12),
                anchor="center"
            )
            
            # Status indicator
            self.screen_canvas.create_text(
                center_x, center_y + 40,
                text="● LIVE",
                fill="#ff4444",  # Red color for live indicator
                font=("Arial", 10, "bold"),
                anchor="center"
            )
            
            logger.info("Displaying local screen sharing preview")
            
        except Exception as e:
            logger.error(f"Error showing local sharing preview: {e}")
    
    def display_local_screen_preview(self, frame_data):
        """Display a preview of your own screen when sharing with anti-flickering optimizations."""
        try:
            if not self.is_sharing:
                return  # Only show preview when actively sharing
                
            import io
            from PIL import Image, ImageTk
            
            # Convert frame data to PIL Image
            image = Image.open(io.BytesIO(frame_data))
            
            # Ensure canvas is visible (only if not already visible)
            if not self.screen_canvas.winfo_viewable():
                self.screen_label.pack_forget()
                self.screen_canvas.pack(fill='both', expand=True)
                # Only update canvas size when first showing
                self.screen_canvas.update_idletasks()
            
            # Get canvas dimensions with caching for local preview
            if not hasattr(self, '_cached_local_canvas_size') or self._cached_local_canvas_size is None:
                canvas_width = self.screen_canvas.winfo_width()
                canvas_height = self.screen_canvas.winfo_height()
                
                if canvas_width <= 10 or canvas_height <= 10:
                    canvas_width = 1000
                    canvas_height = 650
                
                self._cached_local_canvas_size = (canvas_width, canvas_height)
            else:
                canvas_width, canvas_height = self._cached_local_canvas_size
            
            # Calculate scaling to fit canvas while maintaining aspect ratio
            img_width, img_height = image.size
            if img_width <= 0 or img_height <= 0:
                return
            
            # Cache scaling calculations for local preview
            local_scale_key = f"local_{img_width}x{img_height}_{canvas_width}x{canvas_height}"
            if not hasattr(self, '_cached_local_scale') or self._cached_local_scale_key != local_scale_key:
                scale_w = canvas_width / img_width
                scale_h = canvas_height / img_height
                scale = min(scale_w, scale_h) * 0.99  # Use 99% to maximize space usage for full screen effect
                
                # Calculate new dimensions
                new_width = int(img_width * scale)
                new_height = int(img_height * scale)
                
                # Cache the calculations
                self._cached_local_scale = scale
                self._cached_local_scale_key = local_scale_key
                self._cached_local_dimensions = (new_width, new_height)
            else:
                new_width, new_height = self._cached_local_dimensions
            
            # Resize image with good quality resampling for preview
            image = image.resize((new_width, new_height), Image.LANCZOS)
            
            # Convert to PhotoImage
            photo = ImageTk.PhotoImage(image)
            
            # Optimized canvas update for local preview
            if not hasattr(self, '_local_image_id') or self._local_image_id is None:
                # First local image - clear canvas
                self.screen_canvas.delete("all")
                
                # Center the image
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                
                # Create image on canvas
                self._local_image_id = self.screen_canvas.create_image(x, y, anchor='nw', image=photo)
                
                # Add "SHARING" overlay (create once)
                self._sharing_overlay_rect = self.screen_canvas.create_rectangle(
                    canvas_width - 120, 10, canvas_width - 10, 40,
                    fill="#ff4444", outline="#ff4444"
                )
                self._sharing_overlay_text = self.screen_canvas.create_text(
                    canvas_width - 65, 25,
                    text="● SHARING",
                    fill="white",
                    font=("Arial", 10, "bold"),
                    anchor="center"
                )
            else:
                # Update existing image instead of clearing and recreating
                x = (canvas_width - new_width) // 2
                y = (canvas_height - new_height) // 2
                
                # Update the existing image item
                self.screen_canvas.coords(self._local_image_id, x, y)
                self.screen_canvas.itemconfig(self._local_image_id, image=photo)
            
            # Keep reference to prevent garbage collection
            self.screen_canvas.image = photo
            
        except Exception as e:
            logger.error(f"Error displaying local screen preview: {e}")
            # Reset cached values on error
            self._cached_local_canvas_size = None
            self._cached_local_scale = None
            self._local_image_id = None
            
            # Fallback to preview message
            self._show_local_sharing_preview()
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted with enhanced feedback."""
        self.set_presenter_status(True)
        # Show visual indicators for active screen sharing state
        self._safe_label_update(self.sharing_status, text="You are the presenter - ready to share", foreground='blue')
        messagebox.showinfo("Screen Share", "You are now the presenter! You can start screen sharing.")
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied with detailed feedback."""
        # Display presenter role denial reasons to users
        message = "Presenter request denied"
        if reason:
            message += f": {reason}"
        else:
            message += ". Another user may already be presenting."
        
        # Show visual feedback in status
        self._safe_label_update(self.sharing_status, text="Presenter request denied", foreground='red')
        
        # Reset status after a delay
        self.after(3000, lambda: self._safe_label_update(self.sharing_status, text="Ready to share", foreground='black'))
        
        messagebox.showwarning("Screen Share", message)
    
    def handle_screen_share_started(self, presenter_name: str):
        """Handle screen sharing being started by presenter."""
        if presenter_name != "You":
            self.update_presenter(presenter_name)
            self._safe_label_update(self.screen_label, text=f"{presenter_name} is sharing their screen")
    
    def handle_screen_share_stopped(self):
        """Handle screen sharing being stopped."""
        # Clear current presenter when screen sharing stops
        self.current_presenter_name = None
        self.set_sharing_status(False)
        # Clear presenter status since server clears presenter role when screen sharing stops
        self.set_presenter_status(False)
        # Reset status to "Ready to request presenter role" when screen sharing stops
        self._safe_label_update(self.sharing_status, text="Ready to request presenter role", foreground='black')
    
    def set_presenter_status(self, is_presenter: bool, presenter_name: str = None):
        """Set presenter status for screen sharing with visual indicators."""
        if is_presenter:
            self._safe_button_update(self.share_button, state='normal', text="Start Screen Share")
            # Show visual indicators for active screen sharing state
            self._safe_label_update(self.sharing_status, text="You are the presenter", foreground='blue')
        else:
            if presenter_name:
                self._safe_button_update(self.share_button, state='disabled', text=f"{presenter_name} is presenter")
                self._safe_label_update(self.sharing_status, text=f"{presenter_name} is the presenter", foreground='black')
            else:
                self._safe_button_update(self.share_button, state='normal', text="Request Presenter Role")
                self._safe_label_update(self.sharing_status, text="Ready to request presenter role", foreground='black')


# Import the remaining classes from the original file
# (ChatFrame, FileTransferFrame, ParticipantListFrame remain the same)

class ChatFrame(ModuleFrame):
    """Group chat module frame with chronological message ordering and history."""
    
    def __init__(self, parent):
        super().__init__(parent, "Group Chat")
        self.set_enabled(True)  # Chat is always enabled
        
        # Chat history storage for session duration
        self.chat_history: List[Dict[str, Any]] = []
        self.max_history_size = 500  # Limit history to prevent memory issues
        
        # Chat display area with improved formatting
        self.chat_display = scrolledtext.ScrolledText(
            self, 
            height=20, 
            state='disabled',
            wrap='word',
            font=('Consolas', 10),
            bg='#f8f9fa',
            fg='#212529'
        )
        self.chat_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure text tags for different message types
        self._configure_message_tags()
        
        # Message input area
        self.input_frame = ttk.Frame(self)
        self.input_frame.pack(fill='x', padx=5, pady=5)
        
        # Character counter
        self.char_counter = ttk.Label(self.input_frame, text="0/1000", font=('Arial', 8))
        self.char_counter.pack(side='right', padx=(5, 0))
        
        self.send_button = ttk.Button(
            self.input_frame, 
            text="Send", 
            command=self._send_message
        )
        self.send_button.pack(side='right', padx=(5, 0))
        
        self.message_entry = ttk.Entry(self.input_frame)
        self.message_entry.pack(side='left', fill='x', expand=True)
        self.message_entry.bind('<Return>', self._send_message)
        self.message_entry.bind('<KeyRelease>', self._update_char_counter)
        
        # Chat controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=(0, 5))
        
        self.clear_button = ttk.Button(
            self.controls_frame, 
            text="Clear History", 
            command=self._clear_chat_history
        )
        self.clear_button.pack(side='left')
        
        self.export_button = ttk.Button(
            self.controls_frame, 
            text="Export Chat", 
            command=self._export_chat_history
        )
        self.export_button.pack(side='left', padx=(5, 0))
        
        # Status label
        self.status_label = ttk.Label(self.controls_frame, text="Ready", font=('Arial', 8))
        self.status_label.pack(side='right')
        
        # Callbacks
        self.message_callback: Optional[Callable[[str], None]] = None
    
    def _configure_message_tags(self):
        """Configure text tags for different message types and formatting."""
        self.chat_display.tag_configure('timestamp', foreground='#6c757d', font=('Consolas', 8))
        self.chat_display.tag_configure('username', foreground='#0d6efd', font=('Consolas', 10, 'bold'))
        self.chat_display.tag_configure('message', foreground='#212529', font=('Consolas', 10))
        self.chat_display.tag_configure('system', foreground='#198754', font=('Consolas', 9, 'italic'))
        self.chat_display.tag_configure('error', foreground='#dc3545', font=('Consolas', 9, 'italic'))
        self.chat_display.tag_configure('own_message', foreground='#6f42c1', font=('Consolas', 10))
    
    def set_message_callback(self, callback: Callable[[str], None]):
        """Set callback for sending messages."""
        self.message_callback = callback
    
    def _send_message(self, event=None):
        """Send a chat message with validation."""
        message_text = self.message_entry.get().strip()
        
        if not message_text:
            self._show_status("Cannot send empty message", is_error=True)
            return
        
        if len(message_text) > 1000:
            self._show_status("Message too long (max 1000 characters)", is_error=True)
            return
        
        if self.message_callback:
            try:
                self.message_callback(message_text)
                self.message_entry.delete(0, tk.END)
                self._update_char_counter()
                self._show_status("Message sent")
            except Exception as e:
                self._show_status(f"Failed to send message: {e}", is_error=True)
        else:
            self._show_status("Not connected", is_error=True)
    
    def _update_char_counter(self, event=None):
        """Update character counter display."""
        current_length = len(self.message_entry.get())
        self.char_counter.config(text=f"{current_length}/1000")
        
        # Change color based on length
        if current_length > 900:
            self.char_counter.config(foreground='red')
        elif current_length > 800:
            self.char_counter.config(foreground='orange')
        else:
            self.char_counter.config(foreground='black')
    
    def _show_status(self, message: str, is_error: bool = False):
        """Show status message with auto-clear."""
        color = 'red' if is_error else 'green'
        self.status_label.config(text=message, foreground=color)
        
        # Clear status after 3 seconds
        self.after(3000, lambda: self.status_label.config(text="Ready", foreground='black'))
    
    def add_message(self, username: str, message: str, timestamp: Optional[datetime] = None, 
                   is_own_message: bool = False, message_type: str = 'chat'):
        """Add a message to the chat display with chronological ordering and sender information."""
        if timestamp is None:
            timestamp = datetime.now()
        
        # Add to chat history for session duration
        message_entry = {
            'username': username,
            'message': message,
            'timestamp': timestamp,
            'is_own_message': is_own_message,
            'message_type': message_type
        }
        
        self.chat_history.append(message_entry)
        
        # Limit history size
        if len(self.chat_history) > self.max_history_size:
            self.chat_history = self.chat_history[-self.max_history_size:]
        
        # Format and display message
        self._display_message(message_entry)
    
    def _display_message(self, message_entry: Dict[str, Any]):
        """Display a message in the chat area with proper formatting."""
        username = message_entry['username']
        message = message_entry['message']
        timestamp = message_entry['timestamp']
        is_own_message = message_entry.get('is_own_message', False)
        message_type = message_entry.get('message_type', 'chat')
        
        # Format timestamp
        time_str = timestamp.strftime("%H:%M:%S")
        
        # Enable editing
        self.chat_display.config(state='normal')
        
        # Insert timestamp
        self.chat_display.insert(tk.END, f"[{time_str}] ", 'timestamp')
        
        if message_type == 'system':
            # System message (join/leave notifications)
            self.chat_display.insert(tk.END, f"* {message}\n", 'system')
        elif message_type == 'error':
            # Error message
            self.chat_display.insert(tk.END, f"! {message}\n", 'error')
        else:
            # Regular chat message
            username_tag = 'own_message' if is_own_message else 'username'
            message_tag = 'own_message' if is_own_message else 'message'
            
            self.chat_display.insert(tk.END, f"{username}: ", username_tag)
            self.chat_display.insert(tk.END, f"{message}\n", message_tag)
        
        # Disable editing and scroll to bottom
        self.chat_display.config(state='disabled')
        self.chat_display.see(tk.END)
    
    def add_system_message(self, message: str, timestamp: Optional[datetime] = None):
        """Add a system message (e.g., user joined/left)."""
        self.add_message("System", message, timestamp, False, 'system')
    
    def add_error_message(self, message: str, timestamp: Optional[datetime] = None):
        """Add an error message."""
        self.add_message("Error", message, timestamp, False, 'error')
    
    def _clear_chat_history(self):
        """Clear chat history and display."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the chat history?"):
            self.chat_history.clear()
            self.chat_display.config(state='normal')
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state='disabled')
            self._show_status("Chat history cleared")
    
    def _export_chat_history(self):
        """Export chat history to a text file."""
        if not self.chat_history:
            self._show_status("No chat history to export", is_error=True)
            return
        
        try:
            from tkinter import filedialog
            filename = filedialog.asksaveasfilename(
                defaultextension=".txt",
                filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
                title="Export Chat History"
            )
            
            if filename:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("LAN Collaboration Suite - Chat History\n")
                    f.write("=" * 50 + "\n\n")
                    
                    for entry in self.chat_history:
                        timestamp = entry['timestamp'].strftime("%Y-%m-%d %H:%M:%S")
                        username = entry['username']
                        message = entry['message']
                        message_type = entry.get('message_type', 'chat')
                        
                        if message_type == 'system':
                            f.write(f"[{timestamp}] * {message}\n")
                        elif message_type == 'error':
                            f.write(f"[{timestamp}] ! {message}\n")
                        else:
                            f.write(f"[{timestamp}] {username}: {message}\n")
                
                self._show_status(f"Chat exported to {filename}")
        
        except Exception as e:
            self._show_status(f"Export failed: {e}", is_error=True)
    
    def get_chat_history(self) -> List[Dict[str, Any]]:
        """Get the current chat history for the session."""
        return self.chat_history.copy()
    
    def load_chat_history(self, history: List[Dict[str, Any]]):
        """Load chat history (e.g., when reconnecting to session)."""
        # Clear current display
        self.chat_display.config(state='normal')
        self.chat_display.delete(1.0, tk.END)
        self.chat_display.config(state='disabled')
        
        # Clear current history
        self.chat_history.clear()
        
        # Sort messages by timestamp to ensure chronological order
        sorted_history = sorted(history, key=lambda x: x.get('timestamp', datetime.min))
        
        # Display each message
        for message_entry in sorted_history:
            self._display_message(message_entry)
            self.chat_history.append(message_entry)
        
        self._show_status(f"Loaded {len(history)} messages from history")


class FileTransferFrame(ModuleFrame):
    """File transfer module frame with enhanced UI."""
    
    def __init__(self, parent):
        super().__init__(parent, "File Transfer")
        self.set_enabled(True)  # File transfer is always enabled
        
        # Upload controls
        self.upload_frame = ttk.Frame(self)
        self.upload_frame.pack(fill='x', padx=5, pady=5)
        
        self.upload_button = ttk.Button(
            self.upload_frame, 
            text="Share File", 
            command=self._select_file
        )
        self.upload_button.pack(fill='x')
        
        # File list with better sizing
        ttk.Label(self, text="Shared Files:", font=('Arial', 10, 'bold')).pack(anchor='w', padx=5, pady=(10, 5))
        
        # File list frame with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.file_listbox = tk.Listbox(list_frame, height=10, font=('Arial', 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_listbox.yview)
        self.file_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.file_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.file_listbox.bind('<Double-Button-1>', self._download_file)
        
        # Download controls
        download_frame = ttk.Frame(self)
        download_frame.pack(fill='x', padx=5, pady=5)
        
        self.download_button = ttk.Button(
            download_frame, 
            text="Download Selected", 
            command=self._download_file
        )
        self.download_button.pack(fill='x')
        
        # Progress display
        self.progress_label = ttk.Label(self, text="", font=('Arial', 9))
        self.progress_label.pack(padx=5, pady=(10, 5))
        
        self.progress_bar = ttk.Progressbar(self, mode='determinate')
        # Progress bar will be packed only when needed
        
        # Cancel button for downloads
        self.cancel_button = ttk.Button(
            self, 
            text="Cancel Download", 
            command=self._cancel_download,
            state='disabled'
        )
        # Cancel button will be packed only when needed
        
        # File data
        self.shared_files: Dict[str, Dict[str, Any]] = {}
        
        # Callbacks
        self.file_upload_callback: Optional[Callable[[str], None]] = None
        self.file_download_callback: Optional[Callable[[str], None]] = None
        self.cancel_download_callback: Optional[Callable[[], None]] = None
        
        # Track current download
        self.current_download_file_id: Optional[str] = None
    
    def set_file_callbacks(self, upload_callback: Callable[[str], None], 
                          download_callback: Callable[[str], None],
                          cancel_download_callback: Optional[Callable[[], None]] = None):
        """Set callbacks for file operations."""
        self.file_upload_callback = upload_callback
        self.file_download_callback = download_callback
        self.cancel_download_callback = cancel_download_callback
    
    def _select_file(self):
        """Open file dialog to select file for sharing."""
        file_path = filedialog.askopenfilename(
            title="Select file to share",
            filetypes=[("All files", "*.*")]
        )
        
        if file_path and self.file_upload_callback:
            self.file_upload_callback(file_path)
    
    def _download_file(self, event=None):
        """Download selected file with validation and user feedback."""
        selection = self.file_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a file to download.")
            return
        
        if not self.file_download_callback:
            messagebox.showerror("Error", "Download functionality not available.")
            return
        
        try:
            file_index = selection[0]
            file_items = list(self.shared_files.items())
            
            if file_index >= len(file_items):
                messagebox.showerror("Error", "Invalid file selection.")
                return
            
            file_id, file_info = file_items[file_index]
            filename = file_info['filename']
            filesize = file_info['filesize']
            
            # Confirm download with user
            size_mb = filesize / (1024 * 1024)
            if size_mb > 10:  # Warn for files larger than 10MB
                result = messagebox.askyesno(
                    "Large File Download", 
                    f"Download '{filename}' ({size_mb:.1f} MB)?\n\nThis may take some time."
                )
                if not result:
                    return
            
            # Start download
            self.file_download_callback(file_id)
            
        except Exception as e:
            messagebox.showerror("Download Error", f"Failed to start download: {e}")
    
    def _cancel_download(self):
        """Cancel current download."""
        if self.cancel_download_callback:
            self.cancel_download_callback()
        else:
            messagebox.showwarning("Cancel Download", "No download to cancel.")
    
    def add_shared_file(self, file_id: str, filename: str, filesize: int, uploader: str):
        """Add a file to the shared files list."""
        self.shared_files[file_id] = {
            'filename': filename,
            'filesize': filesize,
            'uploader': uploader
        }
        
        # Update listbox
        self._update_file_list()
    
    def _update_file_list(self):
        """Update the file list display."""
        self.file_listbox.delete(0, tk.END)
        
        for file_id, file_info in self.shared_files.items():
            filename = file_info['filename']
            filesize = file_info['filesize']
            uploader = file_info['uploader']
            
            # Format file size
            if filesize < 1024:
                size_str = f"{filesize} B"
            elif filesize < 1024 * 1024:
                size_str = f"{filesize / 1024:.1f} KB"
            else:
                size_str = f"{filesize / (1024 * 1024):.1f} MB"
            
            display_text = f"{filename} ({size_str}) - {uploader}"
            self.file_listbox.insert(tk.END, display_text)
    
    def show_transfer_progress(self, filename: str, progress: float, transfer_type: str = "Downloading"):
        """Show file transfer progress with enhanced display."""
        # Update progress label with more detailed information
        progress_percent = int(progress * 100)
        self.progress_label.config(text=f"{transfer_type}: {filename} ({progress_percent}%)")
        
        # Update progress bar
        self.progress_bar['value'] = progress * 100
        self.progress_bar.pack(fill='x', padx=5, pady=(5, 0))
        
        # Show and enable cancel button during download
        if progress < 1.0 and transfer_type == "Downloading":
            self.cancel_button.pack(fill='x', padx=5, pady=(5, 0))
            self.cancel_button.config(state='normal')
        else:
            self.cancel_button.config(state='disabled')
    
    def hide_transfer_progress(self):
        """Hide file transfer progress."""
        self.progress_label.config(text="")
        self.progress_bar.pack_forget()
        self.cancel_button.pack_forget()
        self.cancel_button.config(state='disabled')
        self.current_download_file_id = None


class ParticipantListFrame(ttk.Frame):
    """Enhanced participant list display frame."""
    
    def __init__(self, parent):
        super().__init__(parent, relief='ridge', borderwidth=1)
        
        # Title
        title_label = ttk.Label(self, text="Participants", font=('Arial', 12, 'bold'))
        title_label.pack(pady=5)
        
        # Participant list with scrollbar
        list_frame = ttk.Frame(self)
        list_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.participant_listbox = tk.Listbox(list_frame, height=8, font=('Arial', 9))
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.participant_listbox.yview)
        self.participant_listbox.configure(yscrollcommand=scrollbar.set)
        
        self.participant_listbox.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Connection info
        self.connection_info = ttk.Label(self, text="Not connected", font=('Arial', 9))
        self.connection_info.pack(pady=5)
    
    def update_participants(self, participants: Dict[str, Dict[str, Any]], current_client_id: str):
        """Update the participant list display."""
        self.participant_listbox.delete(0, tk.END)
        
        for client_id, participant in participants.items():
            username = participant.get('username', 'Unknown')
            video_status = "📹" if participant.get('video_enabled', False) else "📹❌"
            audio_status = "🎤" if participant.get('audio_enabled', False) else "🎤❌"
            
            if client_id == current_client_id:
                username += " (You)"
            
            display_text = f"{username} {video_status} {audio_status}"
            self.participant_listbox.insert(tk.END, display_text)
    
    def update_connection_info(self, status: str, participant_count: int):
        """Update connection information display."""
        info_text = f"Status: {status} | Participants: {participant_count}"
        self.connection_info.config(text=info_text)


class TabbedGUIManager:
    """
    Tabbed GUI manager for the collaboration client.
    
    Organizes functionality into separate tabs:
    - Media Tab: Video, Audio, and Screen Sharing
    - Chat Tab: Group Chat
    - Files Tab: File Sharing
    """
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("LAN Collaboration Suite")
        
        # Get screen dimensions for responsive sizing
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        # Set window size based on screen size (85% of screen for better visibility)
        window_width = int(screen_width * 0.85)
        window_height = int(screen_height * 0.85)
        
        # Center the window
        x = (screen_width - window_width) // 2
        y = (screen_height - window_height) // 2
        
        self.root.geometry(f"{window_width}x{window_height}+{x}+{y}")
        self.root.minsize(1200, 800)  # Increased minimum size for better layout
        
        # Make window resizable and responsive
        self.root.rowconfigure(1, weight=1)  # Tab content area
        self.root.columnconfigure(0, weight=1)
        
        # Set application styling
        self._setup_styling()
        
        # Connection callbacks
        self.connect_callback: Optional[Callable[[str], None]] = None
        self.disconnect_callback: Optional[Callable[[], None]] = None
        
        # Module frames
        self.video_frame: Optional[VideoFrame] = None
        self.audio_frame: Optional[AudioFrame] = None
        self.chat_frame: Optional[ChatFrame] = None
        self.screen_share_frame: Optional[ScreenShareFrame] = None
        self.file_transfer_frame: Optional[FileTransferFrame] = None
        self.participant_frame: Optional[ParticipantListFrame] = None
        
        # Connection state
        self.connected = False
        
        # Create the interface
        self._create_interface()
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self._on_closing)
    
    def _setup_styling(self):
        """Setup GUI styling and theming."""
        try:
            # Configure ttk styles for better appearance
            style = ttk.Style()
            
            # Try to use a modern theme if available
            available_themes = style.theme_names()
            if 'clam' in available_themes:
                style.theme_use('clam')
            elif 'alt' in available_themes:
                style.theme_use('alt')
            
            # Configure custom styles for progress bars
            style.configure("Complete.Horizontal.TProgressbar", 
                          foreground='green', background='green')
                
        except Exception as e:
            logger.warning(f"Could not setup advanced styling: {e}")
    
    def _on_closing(self):
        """Handle application closing."""
        try:
            if self.connected and self.disconnect_callback:
                # Attempt graceful disconnect
                self.disconnect_callback()
            
            # Close the application
            self.root.quit()
            self.root.destroy()
            
        except Exception as e:
            logger.error(f"Error during application shutdown: {e}")
            # Force close if graceful shutdown fails
            self.root.destroy()
    
    def _create_interface(self):
        """Create the main tabbed interface layout."""
        # Top section: Connection controls (always visible)
        self._create_connection_section()
        
        # Main section: Tabbed interface
        self._create_tabbed_section()
    
    def _create_connection_section(self):
        """Create connection controls section at the top."""
        connection_frame = ttk.LabelFrame(self.root, text="Connection", padding=10)
        connection_frame.pack(fill='x', padx=10, pady=(10, 5))
        
        # Main connection row
        main_row = ttk.Frame(connection_frame)
        main_row.pack(fill='x')
        
        # Server input
        ttk.Label(main_row, text="Server:", font=('Arial', 10)).pack(side='left')
        self.server_entry = ttk.Entry(main_row, width=15, font=('Arial', 10))
        self.server_entry.pack(side='left', padx=(5, 15))
        self.server_entry.insert(0, "localhost")
        
        # Username input
        ttk.Label(main_row, text="Username:", font=('Arial', 10)).pack(side='left')
        self.username_entry = ttk.Entry(main_row, width=15, font=('Arial', 10))
        self.username_entry.pack(side='left', padx=(5, 15))
        self.username_entry.insert(0, "User")
        
        # Connection buttons
        self.connect_button = ttk.Button(
            main_row, 
            text="Connect", 
            command=self._connect_clicked
        )
        self.connect_button.pack(side='left', padx=5)
        
        self.disconnect_button = ttk.Button(
            main_row, 
            text="Disconnect", 
            command=self._disconnect_clicked,
            state='disabled'
        )
        self.disconnect_button.pack(side='left', padx=5)
        
        # Status display
        self.status_label = ttk.Label(main_row, text="Status: Disconnected", font=('Arial', 10, 'bold'))
        self.status_label.pack(side='right', padx=10)
    
    def _create_tabbed_section(self):
        """Create the main tabbed interface."""
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=10, pady=5)
        
        # Tab 1: Video & Audio (Video conferencing and audio controls)
        self._create_media_tab()
        
        # Tab 2: Screen Share (Dedicated screen sharing section)
        self._create_screen_share_tab()
        
        # Tab 3: Chat
        self._create_chat_tab()
        
        # Tab 4: Files
        self._create_files_tab()
    
    def _create_media_tab(self):
        """Create the Video & Audio tab with video conferencing and integrated audio controls."""
        media_frame = ttk.Frame(self.notebook)
        self.notebook.add(media_frame, text="🎥 Video & Audio")
        
        # Configure for full expansion - video frame fills entire tab
        media_frame.rowconfigure(0, weight=1)
        media_frame.columnconfigure(0, weight=1)
        
        # Video frame with integrated audio controls fills the entire tab
        self.video_frame = VideoFrame(media_frame)
        self.video_frame.grid(row=0, column=0, sticky='nsew', padx=5, pady=5)
        
        # Create audio controls directly in the video frame (will be added to status row)
        self.audio_frame = AudioFrame(self.video_frame.status_frame)
        
        # No participants frame - removed as requested
        self.participant_frame = None
    
    def _create_screen_share_tab(self):
        """Create the dedicated Screen Share tab."""
        screen_share_container = ttk.Frame(self.notebook)
        self.notebook.add(screen_share_container, text="🖥️ Screen Share")
        
        # Configure for full expansion
        screen_share_container.rowconfigure(0, weight=1)
        screen_share_container.columnconfigure(0, weight=1)
        
        # Screen share frame takes the full tab with more space
        self.screen_share_frame = ScreenShareFrame(screen_share_container)
        self.screen_share_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
    
    def _create_chat_tab(self):
        """Create the Chat tab."""
        chat_container = ttk.Frame(self.notebook)
        self.notebook.add(chat_container, text="💬 Group Chat")
        
        # Configure for full expansion
        chat_container.rowconfigure(0, weight=1)
        chat_container.columnconfigure(0, weight=1)
        
        # Chat frame takes the full tab
        self.chat_frame = ChatFrame(chat_container)
        self.chat_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
    
    def _create_files_tab(self):
        """Create the Files tab."""
        files_container = ttk.Frame(self.notebook)
        self.notebook.add(files_container, text="📁 File Sharing")
        
        # Configure for full expansion
        files_container.rowconfigure(0, weight=1)
        files_container.columnconfigure(0, weight=1)
        
        # File transfer frame takes the full tab
        self.file_transfer_frame = FileTransferFrame(files_container)
        self.file_transfer_frame.grid(row=0, column=0, sticky='nsew', padx=10, pady=10)
    
    def _connect_clicked(self):
        """Handle connect button click."""
        server = self.server_entry.get().strip()
        username = self.username_entry.get().strip()
        
        if not server or not username:
            messagebox.showerror("Error", "Please enter server address and username")
            return
        
        if self.connect_callback:
            self.connect_callback(username)
    
    def _disconnect_clicked(self):
        """Handle disconnect button click."""
        if self.disconnect_callback:
            self.disconnect_callback()
    
    def set_connection_callbacks(self, connect_callback: Callable[[str], None], 
                               disconnect_callback: Callable[[], None]):
        """Set callbacks for connection events."""
        self.connect_callback = connect_callback
        self.disconnect_callback = disconnect_callback
    
    def set_module_callbacks(self, video_callback: Callable[[bool], None],
                           audio_callback: Callable[[bool], None],
                           message_callback: Callable[[str], None],
                           screen_share_callback: Callable[[bool], None],
                           file_upload_callback: Callable[[str], None],
                           file_download_callback: Callable[[str], None]):
        """Set callbacks for module events."""
        try:
            if self.video_frame:
                self.video_frame.set_video_callback(video_callback)
            
            if self.audio_frame:
                self.audio_frame.set_audio_callback(audio_callback)
            
            if self.chat_frame:
                self.chat_frame.set_message_callback(message_callback)
            
            if self.screen_share_frame:
                self.screen_share_frame.set_screen_share_callback(screen_share_callback)
            
            if self.file_transfer_frame:
                self.file_transfer_frame.set_file_callbacks(file_upload_callback, file_download_callback)
                
        except Exception as e:
            logger.error(f"Error setting module callbacks: {e}")
    
    def update_connection_status(self, status: str):
        """Update connection status display and button states."""
        self.status_label.config(text=f"Status: {status}")
        
        # Update button states based on connection status
        if status.lower() == "connected":
            self.connected = True
            self.connect_button.config(state='disabled')
            self.disconnect_button.config(state='normal')
        else:
            self.connected = False
            self.connect_button.config(state='normal')
            self.disconnect_button.config(state='disabled')
    
    def show_error(self, title: str, message: str):
        """Show error message dialog."""
        messagebox.showerror(title, message)
    
    def show_info(self, title: str, message: str):
        """Show info message dialog."""
        messagebox.showinfo(title, message)
    
    def run(self):
        """Start the GUI main loop."""
        self.root.mainloop()
    
    # Delegate methods to access individual frames
    def get_video_frame(self) -> Optional[VideoFrame]:
        return self.video_frame
    
    def get_audio_frame(self) -> Optional[AudioFrame]:
        return self.audio_frame
    
    def get_chat_frame(self) -> Optional[ChatFrame]:
        return self.chat_frame
    
    def get_screen_share_frame(self) -> Optional[ScreenShareFrame]:
        return self.screen_share_frame
    
    def get_file_transfer_frame(self) -> Optional[FileTransferFrame]:
        return self.file_transfer_frame
    
    def get_participant_frame(self) -> Optional[ParticipantListFrame]:
        return self.participant_frame
    
    # File transfer progress methods (for compatibility with main_client.py)
    def show_file_transfer_progress(self, filename: str, progress: float, transfer_type: str = "Downloading"):
        """Show file transfer progress with enhanced display."""
        if self.file_transfer_frame:
            self.file_transfer_frame.show_transfer_progress(filename, progress, transfer_type)
    
    def hide_file_transfer_progress(self):
        """Hide file transfer progress."""
        if self.file_transfer_frame:
            self.file_transfer_frame.hide_transfer_progress()
    
    # Participant management methods (for compatibility)
    def update_participants(self, participants: Dict[str, Dict[str, Any]], current_client_id: str):
        """Update video feeds (participant list removed)."""
        # Participant frame removed - only update video feeds
        if self.video_frame:
            self.video_frame.update_video_feeds(participants)
    
    def add_shared_file(self, file_id: str, filename: str, filesize: int, uploader: str):
        """Add a file to the shared files list."""
        if self.file_transfer_frame:
            self.file_transfer_frame.add_shared_file(file_id, filename, filesize, uploader)
    
    # Video-related methods (for compatibility)
    def update_local_video(self, frame):
        """Update local video display."""
        if self.video_frame:
            self.video_frame.update_local_video(frame)
    
    def update_remote_video(self, client_id: str, frame):
        """Update remote video display."""
        if self.video_frame:
            self.video_frame.update_remote_video(client_id, frame)
    
    def clear_video_slot(self, client_id: str):
        """Clear video slot for disconnected client."""
        if self.video_frame:
            self.video_frame.clear_video_slot(client_id)
    
    # Audio-related methods (for compatibility)
    def update_audio_level(self, level: float):
        """Update audio level indicator."""
        if self.audio_frame:
            self.audio_frame.update_audio_level(level)
    
    # Chat-related methods (for compatibility)
    def add_chat_message(self, username: str, message: str, timestamp: Optional[datetime] = None, 
                        is_own_message: bool = False, message_type: str = 'chat'):
        """Add a message to the chat display."""
        if self.chat_frame:
            self.chat_frame.add_message(username, message, timestamp, is_own_message, message_type)
    
    def add_system_message(self, message: str, timestamp: Optional[datetime] = None):
        """Add a system message to chat."""
        if self.chat_frame:
            self.chat_frame.add_system_message(message, timestamp)
    
    # Screen sharing methods (for compatibility)
    def update_presenter(self, presenter_name: str = None):
        """Update presenter display."""
        if self.screen_share_frame:
            self.screen_share_frame.update_presenter(presenter_name)
    
    def set_sharing_status(self, is_sharing: bool):
        """Set screen sharing status."""
        if self.screen_share_frame:
            self.screen_share_frame.set_sharing_status(is_sharing)
    
    def display_screen_frame(self, frame_data, presenter_name: str):
        """Display screen frame from presenter."""
        if self.screen_share_frame:
            self.screen_share_frame.display_screen_frame(frame_data, presenter_name)
    
    def handle_presenter_granted(self):
        """Handle presenter role being granted."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_presenter_granted()
    
    def handle_presenter_denied(self, reason: str = ""):
        """Handle presenter role being denied."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_presenter_denied(reason)
    
    def handle_screen_share_started(self, presenter_name: str):
        """Handle screen sharing being started."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_screen_share_started(presenter_name)
    
    def handle_screen_share_stopped(self):
        """Handle screen sharing being stopped."""
        if self.screen_share_frame:
            self.screen_share_frame.handle_screen_share_stopped()
    
    def set_presenter_status(self, is_presenter: bool, presenter_name: str = None):
        """Set presenter status."""
        if self.screen_share_frame:
            self.screen_share_frame.set_presenter_status(is_presenter, presenter_name)
    
    # Screen sharing status methods (for compatibility with screen_manager.py)
    def set_screen_sharing_status(self, is_sharing: bool):
        """Set screen sharing active status."""
        if self.screen_share_frame:
            self.screen_share_frame.set_sharing_status(is_sharing)
    
    def reset_screen_sharing_button(self):
        """Reset screen sharing button to initial state."""
        if self.screen_share_frame:
            self.screen_share_frame.reset_screen_sharing_button()
    
    def cleanup_gui_elements(self):
        """Safely cleanup GUI elements to prevent tkinter errors."""
        if self.screen_share_frame:
            self.screen_share_frame.cleanup_gui_elements()
    
    def display_local_screen_preview(self, frame_data):
        """Display a preview of your own screen when sharing."""
        if self.screen_share_frame:
            self.screen_share_frame.display_local_screen_preview(frame_data)


# For backward compatibility, create an alias
GUIManager = TabbedGUIManager