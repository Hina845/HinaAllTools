import tkinter as tk
import asyncio
import threading
import requests
import ctypes
import os
from PIL import Image, ImageGrab, ImageTk
import io
import base64
from typing import Optional

class GeminiClient:
    """Handles communication with Gemini API"""
    
    def __init__(self):
        script_dir = os.path.dirname(os.path.abspath(__file__))
        key_file_path = os.path.join(script_dir, "key.txt")
        with open(key_file_path, "r") as key_file:
            self.api_key = key_file.read().strip()
        self.base_url = "http://34.27.143.218:5678/webhook/fb35697c-dbb0-4897-b4a4-e0c10bc2c58f"
    
    async def get_response(self, prompt: str, image: Optional[Image.Image] = None) -> str:
        api_parts = []

        # Add text part if prompt is provided

        data = {}
        files = {}

        if prompt:
            data = {"chatInput": prompt}

        if image:
            img_byte_arr = io.BytesIO()
            image.save(img_byte_arr, format='PNG')
            img_byte_arr.seek(0)  # Reset the stream position to the beginning
            files = {
                'image': ('image.png', img_byte_arr, 'image/png')
            }

            if not prompt:
                data = {"chatInput": "Trả lời các câu hỏi trong ảnh này"}
        
        if not data and not files:
            return "No input provided. Please enter a message or attach an image."
        
        # Run the API call in a separate thread to avoid blocking the event loop
        try:
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                lambda: self._make_api_call(data, files)
            )
            return result
        except Exception as e:
            raise e
            return f"Error: {str(e)}"
    
    def _make_api_call(self, data, files):
        try:
            if not files:
                response = requests.post(
                    self.base_url, 
                    json = data,
                )
            else:
                response = requests.post(
                    self.base_url,
                    files=files,
                    data=data
                )
            response.raise_for_status()
            data = response.json()
            return f'{data["response"]}\n{data["output"]}'
        except requests.exceptions.RequestException as e:
            return f"Error: {str(e)}"


class ScreenshotManager:
    """Manages screenshot capture and display"""
    
    def __init__(self, root, callback=None):
        self.root = root
        self.screenshot = None
        self.callback = callback
    
    def capture_screenshot(self):
        """Start the screenshot capture process"""
        self.root.withdraw()  # Hide main window
        self.root.after(100, self.start_snipping)
    
    def start_snipping(self):
        """Create the snipping overlay window"""
        snip_window = tk.Toplevel(self.root)
        snip_window.attributes('-fullscreen', True)
        snip_window.attributes('-alpha', 0.3)
        snip_window.configure(bg="black")
        
        start_x, start_y, end_x, end_y = 0, 0, 0, 0
        drawing = False
        rect_id = None
        
        canvas = tk.Canvas(snip_window, cursor="cross", bg="grey", highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)
        
        def on_press(event):
            nonlocal drawing, rect_id, start_x, start_y
            drawing = True
            start_x, start_y = event.x, event.y
            rect_id = canvas.create_rectangle(start_x, start_y, start_x, start_y, outline="red", width=2)
        
        def on_motion(event):
            nonlocal rect_id
            if drawing:
                canvas.coords(rect_id, start_x, start_y, event.x, event.y)
        
        def on_release(event):
            nonlocal drawing, end_x, end_y
            drawing = False
            end_x, end_y = event.x, event.y
            snip_window.destroy()
            self.root.after(100, lambda: self.take_screenshot(start_x, start_y, end_x, end_y))
        
        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_motion)
        canvas.bind("<ButtonRelease-1>", on_release)
        snip_window.bind("<Escape>", lambda e: (snip_window.destroy(), self.root.deiconify()))
    
    def take_screenshot(self, x1, y1, x2, y2):
        """Capture the selected region as a screenshot"""
        # Ensure valid coordinates
        x1, x2 = min(x1, x2), max(x1, x2)
        y1, y2 = min(y1, y2), max(y1, y2)
        
        # Capture screenshot if area is valid
        if x1 != x2 and y1 != y2:
            self.screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
            if self.callback:
                self.callback(self.screenshot)
        
        self.root.deiconify()  # Show main window again
    
    def clear(self):
        """Clear the current screenshot"""
        self.screenshot = None
        return self.screenshot


class HinaAITool:
    """Main application class for AI tool"""
    
    def __init__(self):
        # Initialize system settings
        user32 = ctypes.windll.user32
        self.screen_width = user32.GetSystemMetrics(0)
        self.screen_height = user32.GetSystemMetrics(1)
        
        # Create components
        self.api_client = GeminiClient()
        self.event_loop = None
        
        # Create main window
        self.root = tk.Tk()
        self.root.title("HinaAITool")
        self.root.attributes('-topmost', True)
        self.root.overrideredirect(True)
        
        # Window dimensions
        self.width, self.height = 400, 300
        self.root.geometry(f'{self.width}x{self.height}+{self.screen_width - self.width - 10}+{self.screen_height - self.height - 50}')
        
        # Window dragging
        self._offset_x = 0
        self._offset_y = 0
        
        # Initialize sub-components
        self.screenshot_manager = ScreenshotManager(self.root, self.display_screenshot)
        
        # Set up the UI
        self.setup_ui()
        
        # Start asyncio event loop in a separate thread
        self.setup_asyncio_thread()
    
    def setup_asyncio_thread(self):
        """Set up a separate thread for the asyncio event loop"""
        def run_event_loop():
            self.event_loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self.event_loop)
            self.event_loop.run_forever()
            
        self.asyncio_thread = threading.Thread(target=run_event_loop, daemon=True)
        self.asyncio_thread.start()
    
    def setup_ui(self):
        """Set up the application UI"""
        # Main frame
        self.frame = tk.Frame(self.root, bg="black")
        self.frame.pack(expand=True, fill='both')
        
        # Chat area
        self.chat_frame = tk.Frame(self.frame, bg="black")
        self.chat_frame.pack(fill="both", expand=True, padx=5, pady=(5, 2))
        
        self.scrollbar = tk.Scrollbar(self.chat_frame)
        self.scrollbar.pack(side="right", fill="y")
        
        self.chat_area = tk.Text(
            self.chat_frame, bg="#343541", fg="white", height=3,
            yscrollcommand=self.scrollbar.set, state="disabled", wrap="word",
            font=("Arial", 8)
        )
        self.chat_area.pack(side="left", fill="both", expand=True)
        self.scrollbar.config(command=self.chat_area.yview)
        
        # Input area
        self.input_frame = tk.Frame(self.frame, bg="black")
        self.input_frame.pack(fill="x", side="bottom", padx=5, pady=(2, 5))
        
        self.user_input = tk.Entry(
            self.input_frame, bg="#40414f", fg="white", 
            insertbackground="white", font=("Arial", 8)
        )
        self.user_input.pack(side="left", fill="x", expand=True)
        
        # Buttons
        self.send_button = tk.Button(
            self.input_frame, text="Send", bg="#4CAF50", fg="white", 
            command=self.send_message, font=("Arial", 8)
        )
        self.send_button.pack(side="right", padx=(5, 0))
        
        self.snap_button = tk.Button(
            self.input_frame, text="📷", bg="#2196F3", fg="white", 
            command=self.screenshot_manager.capture_screenshot, font=("Arial", 8)
        )
        self.snap_button.pack(side="right", padx=(5, 0))
        
        self.clear_button = tk.Button(
            self.input_frame, text="🗑️", bg="#FF5722", fg="white", 
            command=self.clear_screenshots, font=("Arial", 8)
        )
        self.clear_button.pack(side="right", padx=(5, 0))
        
        # Exit button
        self.exit_button = tk.Button(
            self.frame, text="X", bg="red", fg="white", 
            command=self.root.destroy, bd=0, padx=5, pady=0
        )
        self.exit_button.place(relx=1.0, rely=0, anchor="ne")
        
        # Window transparency and event bindings
        self.root.attributes('-alpha', 0.01)
        self.bind_events()
    
    def bind_events(self):
        """Bind UI events"""
        self.root.bind('<ButtonPress-1>', self.on_mouse_press)
        self.root.bind('<B1-Motion>', self.on_mouse_motion)
        self.frame.bind("<Enter>", self.on_enter)
        self.frame.bind("<Leave>", self.on_leave)
        self.user_input.bind("<Return>", lambda event: self.send_message())
    
    def on_mouse_press(self, event):
        """Handle mouse press for window dragging"""
        self._offset_x = event.x
        self._offset_y = event.y
    
    def on_mouse_motion(self, event):
        """Handle mouse motion for window dragging"""
        x = self.root.winfo_pointerx() - self._offset_x
        y = self.root.winfo_pointery() - self._offset_y
        self.root.geometry(f'+{x}+{y}')
    
    def on_enter(self, event):
        """Handle mouse enter - make window more visible"""
        self.root.attributes('-alpha', 0.5)
    
    def on_leave(self, event):
        """Handle mouse leave - make window more transparent"""
        self.root.attributes('-alpha', 0.01)
    
    def send_message(self):
        """Send message to API and display response"""
        message = self.user_input.get()
        screenshot = self.screenshot_manager.screenshot
        
        if not message and not screenshot:
            return
        
        self.root.attributes('-alpha', 0.05)
        
        # Add user message to chat
        self.add_to_chat("You: ", end="")
        if message:
            self.add_to_chat(f"{message}")
        if screenshot:
            self.add_to_chat(" [Image attached]")
        self.add_to_chat("\n\n")
        
        # Get response asynchronously
        if self.event_loop:
            asyncio.run_coroutine_threadsafe(
                self.get_and_display_response(message, screenshot),
                self.event_loop
            )
        
        # Clear inputs
        self.user_input.delete(0, tk.END)
        self.clear_screenshots()
    
    async def get_and_display_response(self, message, image):
        """Get response from API and display it"""
        response = await self.api_client.get_response(message, image)
        
        # Use after to update UI from main thread
        self.root.after(0, lambda: self.add_to_chat(f"{response}\n\n"))
    
    def add_to_chat(self, message, end=None):
        """Add text to chat area"""
        self.chat_area.config(state="normal")
        self.chat_area.insert(tk.END, message)
        if end:
            self.chat_area.insert(tk.END, end)
        self.chat_area.see(tk.END)
        self.chat_area.config(state="disabled")
    
    def display_screenshot(self, screenshot):
        """Display a thumbnail of the screenshot"""
        if screenshot:
            # Create thumbnail
            thumb_width = 50
            ratio = thumb_width / float(screenshot.width)
            thumb_height = int(float(screenshot.height) * ratio)
            thumbnail = screenshot.resize((thumb_width, thumb_height), Image.LANCZOS)
            
            # Display thumbnail
            img_tk = ImageTk.PhotoImage(thumbnail)
            img_label = tk.Label(self.input_frame, image=img_tk, bg="#40414f")
            img_label.image = img_tk  # Keep a reference
            img_label.pack(side="left")
    
    def clear_screenshots(self):
        """Clear all screenshots"""
        self.screenshot_manager.clear()
        for widget in self.input_frame.winfo_children():
            if isinstance(widget, tk.Label) and hasattr(widget, 'image'):
                widget.destroy()
    
    def run(self):
        """Run the application"""
        self.root.mainloop()
        
        # Cleanup asyncio loop when app exits
        if self.event_loop:
            self.event_loop.call_soon_threadsafe(self.event_loop.stop)


if __name__ == "__main__":
    app = HinaAITool()
    app.run()