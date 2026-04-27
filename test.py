import requests
import os
import mimetypes
from dotenv import load_dotenv

load_dotenv()

cloudflare_acctid=os.environ["CLOUDFLARE_ACCOUNTID"]
cloudflare_api_key=os.environ["CLOUDFLARE_API_TOKEN"]

def upload_to_cloudflare(file):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_acctid}/images/v1"

    headers = {
        "Authorization": f"Bearer {cloudflare_api_key}"
    }

    if hasattr(file, "filename"):
        files = {
            "file": (file.filename, file.stream, file.mimetype)
        }

    # Case 2: Normal Python file
    else:
        filename = getattr(file, "name", "upload.jpg")
        mimetype = mimetypes.guess_type(filename)[0] or "image/jpeg"

        files = {
            "file": (filename, file, mimetype)
        }

    response = requests.post(url, headers=headers, files=files)
    data = response.json()

    if not data.get("success"):
        print("Upload failed:", data)
        return None


    return {
        "id": data["result"]["id"],
        "url": data["result"]["variants"][0]
    }

def delete_from_cloudflare(image_id):
    url = f"https://api.cloudflare.com/client/v4/accounts/{cloudflare_acctid}/images/v1/{image_id}"

    headers = {
        "Authorization": f"Bearer {cloudflare_api_key}"
    }

    response = requests.delete(url, headers=headers)
    return response.json()
with open("static/images/default-avatar.png", "rb") as f:
    file=upload_to_cloudflare(f)
print(file)
