"""
Generate genecr GUI icon.ico with embedded multi-resolution PNGs.
Run: python gui/make-icon.py
Output: gui/icon.ico (used by tk window + PyInstaller --icon)
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).with_name("icon.ico")
SIZES = [16, 24, 32, 48, 64, 128, 256]


def draw(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Rounded background — slate gradient feel via two layers
    pad = max(2, size // 14)
    radius = size // 4
    # Outer dark slate
    d.rounded_rectangle((0, 0, size, size), radius=radius, fill=(15, 23, 42, 255))
    # Inner accent stripe (top)
    d.rounded_rectangle(
        (pad, pad, size - pad, pad + size // 4),
        radius=radius // 2, fill=(59, 130, 246, 255)
    )

    # "ECR" lettermark, centered lower
    text = "ECR"
    font_size = max(8, int(size * 0.42))
    try:
        font = ImageFont.truetype("arialbd.ttf", font_size)
    except Exception:
        try:
            font = ImageFont.truetype("DejaVuSans-Bold.ttf", font_size)
        except Exception:
            font = ImageFont.load_default()

    bbox = d.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]; th = bbox[3] - bbox[1]
    tx = (size - tw) // 2 - bbox[0]
    ty = (size - th) // 2 + size // 12 - bbox[1]
    d.text((tx, ty), text, fill=(255, 255, 255, 255), font=font)

    # Tiny dot indicator at bottom (yellow accent)
    dot = max(3, size // 12)
    cx = size // 2; cy = size - pad - dot // 2
    d.ellipse((cx - dot, cy - dot, cx + dot, cy + dot), fill=(245, 158, 11, 255))

    return img


def main():
    # Render the largest image once; PIL's ICO will downscale internally.
    big = draw(256)
    big.save(OUT, format="ICO", sizes=[(s, s) for s in SIZES])
    big.save(OUT.with_suffix(".png"), format="PNG")
    print(f"✓ {OUT} ({OUT.stat().st_size:,} bytes)")
    print(f"✓ {OUT.with_suffix('.png')} (256x256, {OUT.with_suffix('.png').stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
