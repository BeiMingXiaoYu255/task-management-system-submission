"""Create wide crops used as thumbnails on contribution slides."""
from pathlib import Path
from PIL import Image

assets = Path(r"C:\\Users\\q1506\\Desktop\\SoftwareDevelopment\\task-management-system") / "deliverables" / "assets"
target_ratio = 2.8
pairs = [
    ("ui-dashboard.png", "thumb-dashboard.png"),
    ("ui-collaboration-center.png", "thumb-collaboration.png"),
    ("runtime-packaging.png", "thumb-runtime.png"),
    ("ai-assignment.png", "thumb-ai.png"),
]
for source_name, target_name in pairs:
    image = Image.open(assets / source_name)
    width, height = image.size
    ratio = width / height
    if ratio > target_ratio:
        new_width = int(height * target_ratio)
        left = (width - new_width) // 2
        cropped = image.crop((left, 0, left + new_width, height))
    else:
        new_height = int(width / target_ratio)
        top = (height - new_height) // 2
        cropped = image.crop((0, top, width, top + new_height))
    cropped = cropped.convert("RGB")
    cropped.save(assets / target_name, "PNG")
    print(target_name, cropped.size)
