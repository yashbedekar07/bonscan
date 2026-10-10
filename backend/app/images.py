"""Checks uploaded receipt images.

We don't trust the file name or the browser's content type: Pillow opens the
bytes to find out what the file really is.

HEIC (iPhone's photo format) is not accepted. iPhones convert photos to JPEG
automatically when a website only accepts JPG/PNG/WEBP, which the upload
form tells them.
"""

from dataclasses import dataclass
from io import BytesIO

from PIL import Image, UnidentifiedImageError

MAX_IMAGE_BYTES = 10 * 1024 * 1024  # 10 MB

# Pillow format name → (mime type, file extension).
# "MPO" is what some phone cameras produce; it's a normal JPEG for our purposes.
_ALLOWED_FORMATS: dict[str, tuple[str, str]] = {
    "JPEG": ("image/jpeg", "jpg"),
    "MPO": ("image/jpeg", "jpg"),
    "PNG": ("image/png", "png"),
    "WEBP": ("image/webp", "webp"),
}


class ImageError(Exception):
    """A user-facing problem with the uploaded file (wrong type, too big, broken)."""

    def __init__(self, status_code: int, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.message = message


@dataclass
class PreparedImage:
    data: bytes
    mime_type: str
    extension: str


def prepare_image(data: bytes) -> PreparedImage:
    """Validate an uploaded image. Raises ImageError with a friendly message if it can't be used."""
    if not data:
        raise ImageError(400, "The uploaded file is empty.")
    if len(data) > MAX_IMAGE_BYTES:
        raise ImageError(413, "The image is larger than 10 MB. Please use a smaller photo.")
    if _looks_like_heic(data):
        raise ImageError(415, "HEIC photos aren't supported. Please use JPG, PNG or WEBP.")

    try:
        with Image.open(BytesIO(data)) as image:
            image_format = image.format
            image.verify()  # checks the file isn't truncated/corrupt
    except (UnidentifiedImageError, OSError, SyntaxError, ValueError):
        raise ImageError(400, "This file doesn't look like a valid image.")

    if image_format not in _ALLOWED_FORMATS:
        raise ImageError(415, "Please upload a JPG, PNG or WEBP image.")

    mime_type, extension = _ALLOWED_FORMATS[image_format]
    return PreparedImage(data=data, mime_type=mime_type, extension=extension)


def _looks_like_heic(data: bytes) -> bool:
    """HEIC/HEIF files start with an "ftyp" box naming a HEIF brand."""
    return data[4:8] == b"ftyp" and data[8:12] in {b"heic", b"heix", b"hevc", b"heim", b"heis", b"mif1", b"msf1"}
