from flask import Flask, request, jsonify
import os
import base64
import requests
from PIL import Image
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
UPLOAD_FOLDER = "profile_uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Shopify credentials
SHOP_NAME = "sq1q6i-jm"
ADMIN_API_TOKEN = os.getenv("SHOPIFY_ADMIN_API_TOKEN")
API_VERSION = "2024-01"
HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": ADMIN_API_TOKEN,
}

def assign_profile_image_to_customer(customer_id, image_path):
    try:
        with open(image_path, "rb") as f:
            files = {
                'file': (os.path.basename(image_path), f, 'image/webp')
            }
            headers = {
                "X-Shopify-Access-Token": ADMIN_API_TOKEN,
            }
            upload_response = requests.post(
                f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/files.json",
                headers=headers,
                files=files
            )
        upload_response.raise_for_status()
        uploaded_url = upload_response.json()["file"]["url"]

        metafield_payload = {
            "metafield": {
                "namespace": "custom",
                "key": "profile_image",
                "type": "single_line_text_field",
                "value": uploaded_url
            }
        }

        metafield_response = requests.post(
            f"https://{SHOP_NAME}.myshopify.com/admin/api/{API_VERSION}/customers/{customer_id}/metafields.json",
            headers={
                "Content-Type": "application/json",
                "X-Shopify-Access-Token": ADMIN_API_TOKEN,
            },
            json=metafield_payload
        )
        metafield_response.raise_for_status()
        app.logger.info(f"✅ Profile image assigned to customer {customer_id}")
        return uploaded_url

    except Exception as e:
        app.logger.error(f"❌ Failed to assign image: {e}")
        raise e

@app.route('/')
def index():
    return jsonify({"message": "FlipXDeals Profile Upload Service is running."}), 200

@app.route('/profile-upload', methods=['POST'])
def profile_upload():
    try:
        file = request.files.get('file')
        customer_id = request.form.get('customer_id')

        if not file or not customer_id:
            return jsonify({"success": False, "error": "Missing file or customer_id"}), 400

        allowed_types = ['image/jpeg', 'image/png', 'image/webp']
        if file.content_type not in allowed_types:
            return jsonify({
                "success": False,
                "error": f"Invalid file type: {file.content_type}. Only JPG, PNG, and WebP are allowed."
            }), 400

        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        if file_size > 5 * 1024 * 1024:
            return jsonify({
                "success": False,
                "error": "File too large. Maximum allowed size is 5MB."
            }), 400

        filename = f"user_{customer_id}.webp"
        filepath = os.path.join(UPLOAD_FOLDER, filename)

        # Resize and convert to 500x500 webp
        img = Image.open(file.stream)
        img = img.convert("RGB")
        img = img.resize((500, 500), Image.LANCZOS)
        img.save(filepath, "WEBP", quality=90)

        url = assign_profile_image_to_customer(customer_id, filepath)
        return jsonify({"success": True, "url": url})

    except Exception as e:
        app.logger.error(f"Error in profile_upload: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
