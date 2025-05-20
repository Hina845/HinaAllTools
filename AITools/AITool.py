import tkinter as tk
import requests
import ctypes
import os

user32 = ctypes.windll.user32
screen_width = user32.GetSystemMetrics(0)
screen_height = user32.GetSystemMetrics(1)

root = tk.Tk()
root.title("Bottom Right Overlay")
root.attributes('-topmost', True)
root.overrideredirect(True) 

width, height = 400, 300
root.geometry(f'{width}x{height}+{screen_width - width - 10}+{screen_height - height - 50}')

root.attributes('-alpha', 0.05)

frame = tk.Frame(root, bg="black")
frame.pack(expand=True, fill='both')

def on_enter(event):
    root.attributes('-alpha', 0.5)

def on_leave(event):
    root.attributes('-alpha', 0.05)

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
    message = user_input.get()
    root.attributes('-alpha', 0.05)
    if message:
        chat_area.config(state="normal")
        chat_area.insert(tk.END, f"You: {message}\n\n")
        response = get_response(message)
        chat_area.insert(tk.END, f"{response}'\n\n")
        chat_area.see(tk.END)
        chat_area.config(state="disabled")
        user_input.delete(0, tk.END)

send_button = tk.Button(input_frame, text="Send", bg="#4CAF50", fg="white", 
                        command=send_message, font=("Arial", 8))
send_button.pack(side="right", padx=(5, 0))

user_input.bind("<Return>", lambda event: send_message())
frame.bind("<Enter>", on_enter)
frame.bind("<Leave>", on_leave)

exit_button = tk.Button(frame, text="X", bg="red", fg="white", 
                       command=root.destroy, bd=0, padx=5, pady=0)
exit_button.place(relx=1.0, rely=0, anchor="ne")

root.update_idletasks()
root.mainloop()