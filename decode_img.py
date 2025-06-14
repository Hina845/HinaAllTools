import base64
import os, time

with open('screenshot.txt', 'r') as image_file:
    images = image_file.readlines()

    output_dir = './pic'
    os.makedirs(output_dir, exist_ok=True)

    start = time.time()

    for i, image_data in enumerate(images):
        image_data = image_data.strip()
        try:
            image_bytes = base64.b64decode(image_data)
            output_path = os.path.join(output_dir, f'{i + 1}.png')
            with open(output_path, 'wb') as output_file:
                output_file.write(image_bytes)
        except Exception as e:
            print(f"Failed to decode image {i + 1}: {e}")
    
    print(time.time() - start)