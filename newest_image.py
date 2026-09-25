import re
from pathlib import Path


def latest_image(folder_path):
    """Return the color_<number> image having the greatest number."""
    folder_path = Path(folder_path)
    if not folder_path.is_dir():
        return None
    image_extensions = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".tiff", ".webp"}
    pattern = re.compile(r"^color_(\d+)$")
    max_num = -1
    last_image = None
    for file_path in folder_path.iterdir():
        if not file_path.is_file() or file_path.suffix.lower() not in image_extensions:
            continue
        match = pattern.match(file_path.stem)
        if match:
            number = int(match.group(1))
            if number > max_num:
                max_num = number
                last_image = file_path.name
    return last_image


if __name__ == "__main__":
    folder = Path(__file__).resolve().parent / "photo"
    image = latest_image(folder)
    print(folder / image if image else "No matching image found")
