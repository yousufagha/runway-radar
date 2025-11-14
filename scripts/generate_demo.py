import os
from datetime import datetime, timedelta
import random

from PIL import Image, ImageDraw, ImageFont
import pandas as pd


def ensure_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path, exist_ok=True)


def make_image(path: str, bg_color: tuple, label: str):
    img = Image.new("RGB", (640, 480), color=bg_color)
    draw = ImageDraw.Draw(img)
    # Try to draw a simple label
    try:
        font = ImageFont.load_default()
    except Exception:
        font = None
    text_color = (255, 255, 255) if sum(bg_color) < 400 else (0, 0, 0)
    draw.text((20, 20), label, font=font, fill=text_color)
    img.save(path)


def generate_images(out_dir: str):
    ensure_dir(out_dir)
    items = [
        ("red_dress_evening.png", (200, 30, 30), "red dress - evening"),
        ("blue_blazer_formal.png", (30, 60, 200), "blue blazer - formal"),
        ("green_jacket_streetwear.png", (20, 150, 80), "green jacket - streetwear"),
        ("beige_trench_classic.png", (210, 190, 150), "beige trench - classic"),
        ("black_boots_edgy.png", (20, 20, 20), "black boots - edgy"),
        ("white_shirt_minimal.png", (235, 235, 235), "white shirt - minimal"),
    ]
    for fname, color, label in items:
        make_image(os.path.join(out_dir, fname), color, label)


def generate_texts_csv(path: str):
    now = datetime.utcnow()
    def d(days):
        return (now - timedelta(days=days)).isoformat()

    rows = [
        {"text": "Loving the red dress trend this week! #runway", "date": d(2), "source": "social"},
        {"text": "Blue blazer looks so sharp for SS24 collections.", "date": d(3), "source": "article"},
        {"text": "Streetwear vibes: green jacket and black boots combo is fire.", "date": d(6), "source": "social"},
        {"text": "Beige trench coats are back, very classic and elegant.", "date": d(10), "source": "article"},
        {"text": "Not a fan of the white shirt minimal looks lately.", "date": d(1), "source": "social"},
        {"text": "Designer spotlight: Stella Nova pairs pink with tailored skirts.", "date": d(8), "source": "article"},
        {"text": "Y2K revival with denim and bold colors everywhere!", "date": d(4), "source": "social"},
        {"text": "Black boots might be overdone, but still iconic.", "date": d(15), "source": "social"},
        {"text": "Minimalism on the runway: white shirt and beige trench.", "date": d(20), "source": "article"},
    ]
    pd.DataFrame(rows).to_csv(path, index=False)


def main():
    demo_dir = os.path.join("demo")
    images_dir = os.path.join(demo_dir, "images")
    ensure_dir(demo_dir)
    generate_images(images_dir)
    generate_texts_csv(os.path.join(demo_dir, "texts.csv"))
    print(f"Demo data created in: {demo_dir}")
    print(f"- Images: {images_dir}")
    print(f"- CSV: {os.path.join(demo_dir, 'texts.csv')}")


if __name__ == "__main__":
    main()

