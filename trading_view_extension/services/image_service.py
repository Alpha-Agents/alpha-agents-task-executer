from config import IMGBB_API_KEY, IMAGE_DETAIL, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET, CLOUDINARY_CLOUD_NAME
import requests

import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url

# Cloudinary Configuration
cloudinary.config(
    cloud_name=CLOUDINARY_CLOUD_NAME,
    api_key=CLOUDINARY_API_KEY,
    api_secret=CLOUDINARY_API_SECRET,
    secure=True
)

def upload_to_cloudinary(image_path: str, public_id: str = None) -> str:
    """
    Upload a single image to Cloudinary and return the secure URL.

    Args:
        image_path (str): Path to the image file.
        public_id (str): Optional public ID for the image on Cloudinary.

    Returns:
        str: Secure URL of the uploaded image.
    """
    try:
        upload_result = cloudinary.uploader.upload(
            image_path,
            public_id=public_id,
            resource_type="image"
        )
        return upload_result["secure_url"]
    except Exception as e:
        raise RuntimeError(f"Failed to upload image to Cloudinary: {e}")


def upload_to_imgbb(image_path: str) -> str:
    """Upload a single image to ImgBB and return the public URL."""
    try:
        with open(image_path, "rb") as image_file:
            response = requests.post(
                "https://api.imgbb.com/1/upload",
                params={"key": IMGBB_API_KEY},
                files={"image": image_file}
            )
            response.raise_for_status()
            return response.json()["data"]["url"]
    except Exception as e:
        raise RuntimeError(f"Failed to upload image: {e}")

def upload_images(image_paths: list[str]) -> list[str]:
    """Upload multiple images to ImgBB and return a list of URLs."""
    urls = []
    for path in image_paths:
        url = upload_to_imgbb(path)
        urls.append(url)
    return urls


def upload_images(image_paths: list[str], platform: str = "imgbb", cloudinary_public_ids: list[str] = None) -> list[str]:
    """
    Upload multiple images to the specified platform and return a list of URLs.

    Args:
        image_paths (list[str]): List of image file paths.
        platform (str): Target platform for uploads ("imgbb" or "cloudinary").
        cloudinary_public_ids (list[str]): List of public IDs for Cloudinary uploads (optional).

    Returns:
        list[str]: List of URLs of the uploaded images.
    """
    urls = []
    for i, path in enumerate(image_paths):
        try:
            if platform == "imgbb":
                url = upload_to_imgbb(path)
            elif platform == "cloudinary":
                public_id = cloudinary_public_ids[i] if cloudinary_public_ids else None
                url = upload_to_cloudinary(path, public_id=public_id)
            else:
                raise ValueError("Invalid platform. Choose 'imgbb' or 'cloudinary'.")
            urls.append(url)
        except RuntimeError as e:
            print(f"Error uploading {path}: {e}")
    return urls