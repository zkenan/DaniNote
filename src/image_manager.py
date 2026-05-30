"""Image management for the sticky notes application."""

import os
import shutil
import uuid
from typing import List, Set


class ImageManager:
    """Manages image files for notes - insert, copy, cleanup."""

    def __init__(self, data_dir: str):
        self.images_dir = os.path.join(data_dir, "images")
        os.makedirs(self.images_dir, exist_ok=True)

    def copy_image(self, source_path: str) -> str:
        """
        Copy an image to the images directory and return the relative path.
        Args:
            source_path: Absolute path to the source image.
        Returns:
            Relative path to the copied image (e.g., 'images/abc123.png').
        """
        ext = os.path.splitext(source_path)[1].lower()
        if ext not in (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"):
            ext = ".png"

        filename = f"{uuid.uuid4().hex}{ext}"
        dest_path = os.path.join(self.images_dir, filename)

        shutil.copy2(source_path, dest_path)
        return f"images/{filename}"

    def get_absolute_path(self, relative_path: str) -> str:
        """Convert a relative image path to an absolute path."""
        return os.path.join(os.path.dirname(self.images_dir), relative_path)

    def delete_image(self, relative_path: str):
        """Delete an image file."""
        abs_path = self.get_absolute_path(relative_path)
        if os.path.exists(abs_path):
            os.remove(abs_path)

    def cleanup_unused(self, used_images: Set[str]):
        """
        Remove images that are no longer referenced by any note.
        Args:
            used_images: Set of image filenames that are still in use.
        """
        for filename in os.listdir(self.images_dir):
            if filename not in used_images:
                os.remove(os.path.join(self.images_dir, filename))

    def get_all_images(self) -> List[str]:
        """Get list of all image filenames in the images directory."""
        return os.listdir(self.images_dir)