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
        
        # Video controls at top
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.video_button = ttk.Button(
            self.controls_frame, 
            text="Enable Video", 
            command=self._toggle_video
        )
        self.video_button.pack(side='left', padx=2)
        
        # Video quality indicator
        self.quality_label = ttk.Label(self.controls_frame, text="Quality: Auto")
        self.quality_label.pack(side='right', padx=5)
        
        # Large video display area with grid layout
        self.video_display = tk.Frame(self, bg='#2c2c2c')
        self.video_display.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Configure grid for responsive video layout
        for i in range(2):  # 2x2 grid for up to 4 participants
            self.video_display.rowconfigure(i, weight=1)
            self.video_display.columnconfigure(i, weight=1)
        
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
        
        if self.video_callback:
            self.video_callback(self.enabled)
    
    def _create_video_slots(self):
        """Create video slots in a 2x2 grid."""
        positions = [(0, 0), (0, 1), (1, 0), (1, 1)]
        
        for i, (row, col) in enumerate(positions):
            slot_frame = tk.Frame(self.video_display, bg='black', relief='solid', borderwidth=1)
            slot_frame.grid(row=row, column=col, sticky='nsew', padx=2, pady=2)
            
            # Placeholder content
            slot_text = "Your Video\n(Enable video)" if i == 0 else f"Video Slot {i+1}\nNo participant"
            placeholder_label = tk.Label(
                slot_frame, 
                text=slot_text, 
                fg='lightgreen' if i == 0 else 'white', 
                bg='black',
                font=('Arial', 10)
            )
            placeholder_label.pack(expand=True)
            
            self.video_slots[i] = {
                'frame': slot_frame,
                'label': placeholder_label,
                'participant_id': 'local' if i == 0 else None,
                'active': False
            }
    
    # Include all the existing video methods from the original file
    def update_video_feeds(self, participants: Dict[str, Any]):
        """Update video feed display with participant information."""
        # Get participants with video enabled
        active_participants = [p for p in participants.values() 
                             if p.get('video_enabled', False)]
        
        # Clear all slots first to prevent duplicates
        for slot_id, slot in self.video_slots.items():
            if slot_id > 0:  # Don't clear slot 0 (local video)
                if self._widget_exists(slot['label']):
                    slot['label'].config(
                        text=f"Video Slot {slot_id+1}\nNo participant",
                        fg='white'
                    )
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
                if self._widget_exists(slot['label']):
                    slot['label'].config(
                        text=f"{participant_name}\n{'🎥 Video Active' if participant.get('video_enabled') else '📷 Video Off'}",
                        fg='lightgreen' if participant.get('video_enabled') else 'lightgray'
                    )
                slot['participant_id'] = participant_id
                slot['active'] = True
                
                assigned_participants.add(participant_id)
                slot_index += 1
    
    def update_local_video(self, frame):
        """Update local video display with proper frame sequencing."""
        try:
            # Use direct stable video display for proper frame sequencing
            self._update_local_video_safe_stable(frame)
            
        except Exception as e:
            logger.error(f"Local video display error: {e}")
            # Fallback to ultra-stable system if needed
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
        """Create stable video display without destroying widgets unnecessarily."""
        try:
            import cv2
            from PIL import Image, ImageTk
            
            # Convert frame for display
            if frame is not None and frame.size > 0:
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                pil_image = Image.fromarray(rgb_frame)
                display_size = (320, 240)  # 80% slot coverage
                pil_image = pil_image.resize(display_size, Image.LANCZOS)
                photo = ImageTk.PhotoImage(pil_image)
                
                # Find existing video widget or create new one
                video_widgets = [child for child in parent_frame.winfo_children() 
                               if isinstance(child, tk.Label) and hasattr(child, 'image')]
                
                if video_widgets:
                    # Update existing widget
                    video_widget = video_widgets[0]
                    video_widget.configure(image=photo)
                    video_widget.image = photo
                else:
                    # Create new widget only if necessary
                    # Clear only placeholder labels, not video widgets
                    for child in parent_frame.winfo_children():
                        if isinstance(child, tk.Label) and not hasattr(child, 'image'):
                            if 'Video Slot' in child.cget('text') or 'Enable video' in child.cget('text'):
                                child.destroy()
                    
                    # Create video widget
                    video_widget = tk.Label(parent_frame, image=photo, bg='black')
                    video_widget.pack(fill='both', expand=True)
                    video_widget.image = photo
                    
                    # Create name label
                    name_text = "You (Local)" if client_id == 'local' else f"Client {client_id[:8]}"
                    name_label = tk.Label(
                        parent_frame,
                        text=name_text,
                        fg='lightgreen' if client_id == 'local' else 'lightblue',
                        bg='black',
                        font=('Arial', 8)
                    )
                    name_label.pack(side='bottom')
                    
        except Exception as e:
            logger.error(f"Error creating stable video display for {client_id}: {e}")
    
    def update_remote_video(self, client_id: str, frame):
        """Update remote video display with enhanced error handling."""
        try:
            logger.debug(f"Updating remote video for client {client_id}")
            
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
                        
                        # Create black screen placeholder
                        black_label = tk.Label(
                            slot['frame'], 
                            text="No Video", 
                            bg='black', 
                            fg='white',
                            font=('Arial', 10)
                        )
                        black_label.pack(fill='both', expand=True)
                        
                        # Update slot references
                        slot['video_widget'] = black_label
                        slot['name_label'] = None
                        slot['participant_id'] = 'local' if slot_id == 0 else None
                        slot['active'] = False
                    break
                    
        except Exception as e:
            logger.error(f"Error clearing ultra-stable video slot for {client_id}: {e}")


class AudioFrame(ModuleFrame):
    """Audio conferencing module frame."""
    
    def __init__(self, parent):
        super().__init__(parent, "Audio Conference")
        
        # Audio controls
        self.controls_frame = ttk.Frame(self)
        self.controls_frame.pack(fill='x', padx=5, pady=5)
        
        self.audio_button = ttk.Button(
            self.controls_frame, 
            text="Enable Audio", 
            command=self._toggle_audio
        )
        self.audio_button.pack(side='left', padx=2)
        
        self.mute_button = ttk.Button(
            self.controls_frame, 
            text="Mute", 
            command=self._toggle_mute,
            state='disabled'
        )
        self.mute_button.pack(side='left', padx=2)
        
        # Audio level indicator
        self.level_frame = ttk.Frame(self)
        self.level_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(self.level_frame, text="Audio Level:").pack(side='left')
        
        self.level_bar = ttk.Progressbar(
            self.level_frame, 
            length=100, 
            mode='determinate'
        )
        self.level_bar.pack(side='left', padx=(5, 0), fill='x', expand=True)
        
        # Audio status
        self.audio_status = ttk.Label(self, text="Audio inactive")
        self.audio_status.pack(pady=5)
        
        # State
        self.muted = False
        
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
        self._update_status_indicator()
        
        button_text = "Disable Audio" if self.enabled else "Enable Audio"
        self.audio_button.config(text=button_text)
        
        # Enable/disable mute button
        mute_state = 'normal' if self.enabled else 'disabled'
        self.mute_button.config(state=mute_state)
        
        # Update status
        if self.enabled:
            status_text = "Muted" if self.muted else "Active"
        else:
            status_text = "Inactive"
        self.audio_status.config(text=f"Audio {status_text}")
        
        if self.audio_callback:
            self.audio_callback(self.enabled and not self.muted)
    
    def _toggle_mute(self):
        """Toggle mute on/off."""
        self.muted = not self.muted
        
        button_text = "Unmute" if self.muted else "Mute"
        self.mute_button.config(text=button_text)
        
        status_text = "Muted" if self.muted else "Active"
        self.audio_status.config(text=f"Audio {status_text}")
        
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
        
        # Screen display area (larger for better visibility)
        self.screen_display = tk.Frame(self, bg='black', height=400)
        self.screen_display.pack(fill='both', expand=True, padx=5, pady=5)
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
    
    def _initialize_canvas(self):
        """Initialize canvas with proper size detection."""
        try:
            # Set initial canvas size
            self.last_canvas_size = (400, 300)
        except Exception as e:
            logger.error(f"Error initializing canvas: {e}")
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
        """Set sharing status."""
        self.is_sharing = is_sharing
        self._update_status_indicator()
        
        if is_sharing:
            self._safe_button_update(self.share_button, state='normal', text="Stop Screen Share")
            self._safe_label_update(self.sharing_status, text="Sharing your screen", foreground='green')
        else:
            self._safe_button_update(self.share_button, state='normal', text="Request Presenter Role")
            self._safe_label_update(self.sharing_status, text="Ready to share", foreground='black')
    
    def display_screen_frame(self, frame_data, presenter_name: str):
        """Display screen frame from presenter."""
        try:
            # Store current frame data for rescaling
            self._store_current_frame(frame_data, presenter_name)
            
            # Implementation would go here for displaying the actual screen frame
            # This is a placeholder for the screen sharing display logic
            pass
            
        except Exception as e:
            logger.error(f"Error displaying screen frame: {e}")
    
    def _store_current_frame(self, frame_data, presenter_name: str):
        """Store current frame data for rescaling when canvas size changes."""
        self.current_frame_data = frame_data
        self.current_presenter = presenter_name


# Import the remaining classes from the original file
# (ChatFrame, FileTransferFrame, ParticipantListFrame remain the same)
clas
s ChatFrame(ModuleFrame):
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
        
        # Tab 1: Media (Video, Audio, Screen Sharing)
        self._create_media_tab()
        
        # Tab 2: Chat
        self._create_chat_tab()
        
        # Tab 3: Files
        self._create_files_tab()
    
    def _create_media_tab(self):
        """Create the Media tab with video, audio, and screen sharing."""
        media_frame = ttk.Frame(self.notebook)
        self.notebook.add(media_frame, text="🎥 Media & Screen Share")
        
        # Configure grid weights
        media_frame.rowconfigure(0, weight=1)
        media_frame.columnconfigure(0, weight=2)  # Video gets more space
        media_frame.columnconfigure(1, weight=1)  # Right panel
        
        # Left side: Video conferencing (larger area)
        video_container = ttk.Frame(media_frame)
        video_container.grid(row=0, column=0, sticky='nsew', padx=(0, 5))
        video_container.rowconfigure(0, weight=1)
        video_container.columnconfigure(0, weight=1)
        
        self.video_frame = VideoFrame(video_container)
        self.video_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        # Audio controls below video
        self.audio_frame = AudioFrame(video_container)
        self.audio_frame.grid(row=1, column=0, sticky='ew')
        
        # Right side: Screen sharing and participants
        right_panel = ttk.Frame(media_frame)
        right_panel.grid(row=0, column=1, sticky='nsew', padx=(5, 0))
        right_panel.rowconfigure(0, weight=1)  # Screen share gets most space
        right_panel.columnconfigure(0, weight=1)
        
        # Screen sharing (top of right panel)
        self.screen_share_frame = ScreenShareFrame(right_panel)
        self.screen_share_frame.grid(row=0, column=0, sticky='nsew', pady=(0, 5))
        
        # Participants (bottom of right panel)
        self.participant_frame = ParticipantListFrame(right_panel)
        self.participant_frame.grid(row=1, column=0, sticky='ew')
    
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


# For backward compatibility, create an alias
GUIManager = TabbedGUIManager