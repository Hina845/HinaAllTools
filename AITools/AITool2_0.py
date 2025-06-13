import tkinter as tk
import requests
import ctypes
import os
from PIL import Image, ImageGrab, ImageTk
import io
import base64

user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)

root = tk.Tk()
root.title("HinaAITool")
root.attributes('-topmost', True)
root.overrideredirect(True) 

hwnd = ctypes.windll.user32.FindWindowW(None, "HinaAITool")

HWND_TOPMOST = -1
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOACTIVATE = 0x0010

width, height = 400, 300
root.geometry(f'{width}x{height}+{screen_width - width - 10}+{screen_height - height - 50}')

_offset_x = 0
_offset_y = 0

def on_mouse_press(event):
    global _offset_x, _offset_y
    _offset_x = event.x
    _offset_y = event.y

def on_mouse_motion(event):
    global _offset_x, _offset_y
    x = root.winfo_pointerx() - _offset_x
    y = root.winfo_pointery() - _offset_y
    root.geometry(f'+{x}+{y}')

root.bind('<ButtonPress-1>', on_mouse_press)
root.bind('<B1-Motion>', on_mouse_motion)

root.attributes('-alpha', 0.05)

frame = tk.Frame(root, bg="black")
frame.pack(expand=True, fill='both')

def on_enter(event):
    root.attributes('-alpha', 0.5)

def on_leave(event):
    root.attributes('-alpha', 0.05z)

chat_frame = tk.Frame(frame, bg="black")
chat_frame.pack(fill="both", expand=True, padx=5, pady=(5, 2))

scrollbar = tk.Scrollbar(chat_frame)
scrollbar.pack(side="right", fill="y")

chat_area = tk.Text(chat_frame, bg="#343541", fg="white", height=3, 
                    yscrollcommand=scrollbar.set, state="disabled", wrap="word",
                    font=("Arial", 8))
chat_area.pack(side="left", fill="both", expand=True)
scrollbar.config(command=chat_area.yview)

# User input area
input_frame = tk.Frame(frame, bg="black")
input_frame.pack(fill="x", side="bottom", padx=5, pady=(2, 5))

user_input = tk.Entry(input_frame, bg="#40414f", fg="white", insertbackground="white",
                    font=("Arial", 8))
user_input.pack(side="left", fill="x", expand=True)

def get_response(prompt):
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, "key.txt")
    with open(key_file_path, "r") as key_file:
        api_key = key_file.read().strip()
    params = {
        "key": api_key
    }
    payload = {
        "contents": [{"parts": [{"text": prompt}]}]
    }
    try:
        response = requests.post(url, params=params, json=payload)
        
        response.raise_for_status()
        
        data = response.json()
        result = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received.")
    except requests.exceptions.RequestException as e:
        result = f"Error: {str(e)}"

    return result

def send_message():
    global screenshot
    message = user_input.get()
    root.attributes('-alpha', 0.05)
    
    if message or screenshot:
        chat_area.config(state="normal")
        chat_area.insert(tk.END, "You: ")
        if message:
            chat_area.insert(tk.END, f"{message}")
        if screenshot:
            chat_area.insert(tk.END, " [Image attached]")
        chat_area.insert(tk.END, "\n\n")
        
        # Get response with image if present
        response = get_response_with_image(message)
        chat_area.insert(tk.END, f"{response}\n\n")
        chat_area.see(tk.END)
        chat_area.config(state="disabled")
        
        # Clear inputs
        user_input.delete(0, tk.END)
        screenshot = None
        for widget in input_frame.winfo_children():
            if isinstance(widget, tk.Label) and hasattr(widget, 'image'):
                widget.destroy()

def get_response_with_image(prompt):
    global screenshot
    url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent"
    script_dir = os.path.dirname(os.path.abspath(__file__))
    key_file_path = os.path.join(script_dir, "key.txt")
    
    with open(key_file_path, "r") as key_file:
        api_key = key_file.read().strip()
    
    # Construct parts for the payload
    api_parts = []

    # Add text part if prompt is provided
    if prompt:
        api_parts.append({"text": prompt})

    # Add image part if screenshot is available
    if screenshot:
        img_byte_arr = io.BytesIO()
        screenshot.save(img_byte_arr, format='PNG')
        img_base64 = base64.b64encode(img_byte_arr.getvalue()).decode('utf-8')
        api_parts.append({
            "inline_data": {
                "mime_type": "image/png",
                "data": img_base64
            }
        })
        # If there's an image but no user prompt, add a default text prompt.
        # Gemini API typically expects text alongside an image.
        if not prompt:
            api_parts.insert(0, {"text": "Chọn đáp án đúng nhất ở câu hỏi trong ảnh."}) # Insert at the beginning

    # If api_parts is empty (e.g., no prompt and no screenshot), 
    # this indicates an issue, as the API expects content.
    if not api_parts:
        return "Error: No content (prompt or image) to send to API."
            
    payload = {
        "contents": [{"parts": api_parts}]
    }
    
    try:
        response = requests.post(url, params={"key": api_key}, json=payload)
        response.raise_for_status()
        data = response.json()
        result = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "No response received.")
    except requests.exceptions.RequestException as e:
        result = f"Error: {str(e)}"
    
    return result

send_button = tk.Button(input_frame, text="Send", bg="#4CAF50", fg="white", 
                        command=send_message, font=("Arial", 8))
send_button.pack(side="right", padx=(5, 0))

screenshot = None

# Function to capture screenshot
def capture_screenshot():
    global screenshot
    # Hide window temporarily
    root.withdraw()
    root.after(100, start_snipping)

def start_snipping():
    snip_window = tk.Toplevel(root)
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
        root.after(100, lambda: take_screenshot(start_x, start_y, end_x, end_y))
    
    canvas.bind("<ButtonPress-1>", on_press)
    canvas.bind("<B1-Motion>", on_motion)
    canvas.bind("<ButtonRelease-1>", on_release)
    snip_window.bind("<Escape>", lambda e: (snip_window.destroy(), root.deiconify()))
    
def take_screenshot(x1, y1, x2, y2):
    global screenshot
    # Ensure valid coordinates
    x1, x2 = min(x1, x2), max(x1, x2)
    y1, y2 = min(y1, y2), max(y1, y2)
    
    # Capture screenshot
    if x1 != x2 and y1 != y2:
        screenshot = ImageGrab.grab(bbox=(x1, y1, x2, y2))
        display_screenshot()
    root.deiconify()

def display_screenshot():
    global screenshot
    if screenshot:
        # Create thumbnail
        thumb_width = 50
        ratio = thumb_width / float(screenshot.width)
        thumb_height = int(float(screenshot.height) * ratio)
        thumbnail = screenshot.resize((thumb_width, thumb_height), Image.LANCZOS)
        
        # Display thumbnail
        img_tk = ImageTk.PhotoImage(thumbnail)
        img_label = tk.Label(input_frame, image=img_tk, bg="#40414f")
        img_label.image = img_tk
        img_label.pack(side="left")

snap_button = tk.Button(input_frame, text="📷", bg="#2196F3", fg="white", 
                       command=capture_screenshot, font=("Arial", 8))
snap_button.pack(side="right", padx=(5, 0))

def clear_screenshots():
    global screenshot
    screenshot = None
    # Remove any thumbnail images in the input frame
    for widget in input_frame.winfo_children():
        if isinstance(widget, tk.Label) and hasattr(widget, 'image'):
            widget.destroy()

clear_button = tk.Button(input_frame, text="🗑️", bg="#FF5722", fg="white", 
                        command=clear_screenshots, font=("Arial", 8))
clear_button.pack(side="right", padx=(5, 0))

user_input.bind("<Return>", lambda event: send_message())
frame.bind("<Enter>", on_enter)
frame.bind("<Leave>", on_leave)

exit_button = tk.Button(frame, text="X", bg="red", fg="white", 
                       command=root.destroy, bd=0, padx=5, pady=0)
exit_button.place(relx=1.0, rely=0, anchor="ne")

root.update_idletasks()
root.mainloop()