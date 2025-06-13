import requests

url = "http://34.27.143.218:5678/webhook/fb35697c-dbb0-4897-b4a4-e0c10bc2c58f"

def send_image_multipart():
    with open('image.png', 'rb') as image_file:
        files = {
            'image': ('image.png', image_file, 'image/png')
        }
        data = {
            'chatInput': 'Trả lời các câu hỏi trong ảnh này'
        }
        response = requests.post(url, files=files, data=data)
        return response

def send_text():
    data = {
        'chatInput': 'flex flex flex' # text input
    } 
    response = requests.post(url, json=data)
    return response

response_img = send_image_multipart() # image handler
response_text = send_text() # text handler

data = response_img.json() # change mode
print(f"{data.get('response')}\n{data.get('output')}")