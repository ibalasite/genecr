"""
Generate splash.png for PyInstaller --splash bootloader-level splash screen.
Run: python gui/make-splash.py
Output: gui/splash.png (480x200, used by `--splash` PyInstaller flag)

This PNG is displayed by PyInstaller bootloader BEFORE Python starts —
roughly 30-50ms after process launch, far earlier than any tk-based splash.
"""
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

OUT = Path(__file__).with_name("splash.png")
W, H = 480, 200


def main():
    img = Image.new("RGB", (W, H), (15, 23, 42))  # slate-900
    d = ImageDraw.Draw(img)

    # Top accent stripe
    d.rectangle((0, 0, W, 8), fill=(59, 130, 246))   # blue-500

    # "genecr" big title
    try:
        title_font = ImageFont.truetype("arialbd.ttf", 48)
        sub_font   = ImageFont.truetype("arial.ttf", 16)
    except Exception:
        try:
            title_font = ImageFont.truetype("DejaVuSans-Bold.ttf", 48)
            sub_font   = ImageFont.truetype("DejaVuSans.ttf", 16)
        except Exception:
            title_font = ImageFont.load_default()
            sub_font   = ImageFont.load_default()

    title = "genecr"
    bbox = d.textbbox((0, 0), title, font=title_font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    d.text(((W - tw) // 2 - bbox[0], 60), title, fill=(255, 255, 255), font=title_font)

    # Subtitle
    sub = "啟動中…"
    bbox = d.textbbox((0, 0), sub, font=sub_font)
    sw = bbox[2] - bbox[0]
    d.text(((W - sw) // 2 - bbox[0], 130), sub, fill=(148, 163, 184), font=sub_font)  # slate-400

    # Yellow accent dot
    cx, cy = W // 2, 170
    d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=(245, 158, 11))

    img.save(OUT, format="PNG", optimize=True)
    print(f"✓ {OUT} ({W}x{H}, {OUT.stat().st_size:,} bytes)")


if __name__ == "__main__":
    main()
