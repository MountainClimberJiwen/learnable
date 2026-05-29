#!/usr/bin/env python3
"""
Create a hand-drawn style app icon for Learnable.
Generates .icns file for macOS.

Usage:
    python create_icon.py
    # outputs: build/icon.icns
"""

import struct
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

R = lambda a, b: __import__("random").uniform(a, b)


def hand_line(draw, x1, y1, x2, y2, fill, width=2, seg=15, wobble=1.5):
    """Draw a hand-drawn line with organic jitter."""
    pts = []
    for i in range(seg + 1):
        t = i / seg
        x = x1 + (x2 - x1) * t + R(-wobble, wobble)
        y = y1 + (y2 - y1) * t + R(-wobble, wobble)
        pts.append((x, y))
    for i in range(len(pts) - 1):
        draw.line([pts[i], pts[i + 1]], fill=fill, width=width)


def hand_curve(draw, points, fill, width=2, seg=20, wobble=2):
    """Draw a hand-drawn quadratic bezier through points."""
    if len(points) < 2:
        return
    all_pts = []
    for i in range(len(points) - 1):
        p0 = points[i]
        p1 = points[i + 1]
        mx = (p0[0] + p1[0]) / 2 + R(-wobble * 3, wobble * 3)
        my = (p0[1] + p1[1]) / 2 + R(-wobble * 3, wobble * 3)
        for t in range(seg + 1):
            t = t / seg
            # Quadratic bezier
            x = (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * mx + t ** 2 * p1[0]
            y = (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * my + t ** 2 * p1[1]
            all_pts.append((x + R(-wobble, wobble), y + R(-wobble, wobble)))
    for i in range(len(all_pts) - 1):
        draw.line([all_pts[i], all_pts[i + 1]], fill=fill, width=width)


def draw_pencil(draw, cx, cy, angle=45, scale=1.0):
    """Draw a hand-drawn pencil at center (cx, cy)."""
    import math
    rad = math.radians(angle)
    cos_a = math.cos(rad)
    sin_a = math.sin(rad)

    def rot(x, y):
        return cx + (x * cos_a - y * sin_a) * scale, cy + (x * sin_a + y * cos_a) * scale

    # Pencil body (hexagonal-ish)
    body_pts = [rot(-10, -60), rot(10, -60), rot(12, 40), rot(-12, 40)]
    draw.polygon(body_pts, fill="#f4d03f")  # yellow body
    hand_line(draw, *body_pts[0], *body_pts[1], fill="#d4a853", width=2)
    hand_line(draw, *body_pts[1], *body_pts[2], fill="#d4a853", width=2)
    hand_line(draw, *body_pts[2], *body_pts[3], fill="#d4a853", width=2)
    hand_line(draw, *body_pts[3], *body_pts[0], fill="#d4a853", width=2)

    # Wood tip
    tip_pts = [rot(-12, 40), rot(12, 40), rot(0, 65)]
    draw.polygon(tip_pts, fill="#e8c9a0")
    hand_line(draw, *tip_pts[0], *tip_pts[1], fill="#d4a853", width=2)
    hand_line(draw, *tip_pts[1], *tip_pts[2], fill="#d4a853", width=2)
    hand_line(draw, *tip_pts[2], *tip_pts[0], fill="#d4a853", width=2)

    # Graphite tip
    graphite_pts = [rot(-4, 52), rot(4, 52), rot(0, 65)]
    draw.polygon(graphite_pts, fill="#5a4a3a")

    # Metal band
    band_pts = [rot(-11, 35), rot(11, 35), rot(11, 45), rot(-11, 45)]
    draw.polygon(band_pts, fill="#c0c0c0")
    hand_line(draw, *band_pts[0], *band_pts[1], fill="#a0a0a0", width=1)
    hand_line(draw, *band_pts[1], *band_pts[2], fill="#a0a0a0", width=1)
    hand_line(draw, *band_pts[2], *band_pts[3], fill="#a0a0a0", width=1)
    hand_line(draw, *band_pts[3], *band_pts[0], fill="#a0a0a0", width=1)

    # Eraser
    eras_pts = [rot(-10, -60), rot(10, -60), rot(9, -75), rot(-9, -75)]
    draw.polygon(eras_pts, fill="#f8a5c2")
    hand_line(draw, *eras_pts[0], *eras_pts[1], fill="#e890a0", width=2)
    hand_line(draw, *eras_pts[1], *eras_pts[2], fill="#e890a0", width=2)
    hand_line(draw, *eras_pts[2], *eras_pts[3], fill="#e890a0", width=2)
    hand_line(draw, *eras_pts[3], *eras_pts[0], fill="#e890a0", width=2)


def draw_knowledge_tree(draw, start_x, start_y, scale=1.0):
    """Draw a small hand-drawn tree growing from pencil tip."""
    s = scale
    # Main trunk curving up-right
    hand_curve(draw, [
        (start_x, start_y),
        (start_x + 30 * s, start_y - 40 * s),
        (start_x + 60 * s, start_y - 90 * s),
    ], fill="#8a6a3a", width=3, wobble=1.5)

    # Branches with leaves (small circles)
    branches = [
        ((start_x + 25 * s, start_y - 35 * s), (start_x - 10 * s, start_y - 60 * s)),
        ((start_x + 40 * s, start_y - 60 * s), (start_x + 80 * s, start_y - 50 * s)),
        ((start_x + 55 * s, start_y - 82 * s), (start_x + 40 * s, start_y - 120 * s)),
        ((start_x + 60 * s, start_y - 90 * s), (start_x + 100 * s, start_y - 100 * s)),
    ]

    for b_start, b_end in branches:
        hand_curve(draw, [b_start, b_end], fill="#8a6a3a", width=2, wobble=1)
        # Leaf
        leaf_x, leaf_y = b_end
        r = 6 * s
        draw.ellipse([leaf_x - r, leaf_y - r, leaf_x + r, leaf_y + r], fill="#a8d5a2")
        draw.ellipse([leaf_x - r, leaf_y - r, leaf_x + r, leaf_y + r], outline="#7ab570", width=1)

    # Top leaf cluster
    top_x, top_y = start_x + 60 * s, start_y - 90 * s
    for dx, dy in [(-8, -15), (5, -20), (15, -12)]:
        lx, ly = top_x + dx * s, top_y + dy * s
        r = 7 * s
        draw.ellipse([lx - r, ly - r, lx + r, ly + r], fill="#c8e6c9")
        draw.ellipse([lx - r, ly - r, lx + r, ly + r], outline="#a5d6a7", width=1)


def draw_icon(size: int) -> Image.Image:
    """Render the Learnable icon at given size."""
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(size * 0.06)
    r = int(size * 0.22)

    # Background: warm paper color with rounded corners
    bg_color = (250, 246, 240, 255)
    shadow = (180, 170, 150, 60)

    # Soft shadow
    shadow_offset = max(2, size // 60)
    d.rounded_rectangle(
        [pad + shadow_offset, pad + shadow_offset, size - pad + shadow_offset, size - pad + shadow_offset],
        radius=r,
        fill=shadow,
    )

    # Main background
    d.rounded_rectangle(
        [pad, pad, size - pad, size - pad],
        radius=r,
        fill=bg_color,
        outline=(212, 196, 168, 255),
        width=max(1, size // 80),
    )

    # Subtle paper noise (few random dots)
    import random
    random.seed(42)
    for _ in range(size * 2):
        x = random.randint(pad + 5, size - pad - 5)
        y = random.randint(pad + 5, size - pad - 5)
        if (x - size // 2) ** 2 + (y - size // 2) ** 2 < (size // 2 - pad) ** 2:
            alpha = random.randint(10, 30)
            d.point((x, y), fill=(160, 150, 130, alpha))

    # Draw pencil and tree
    pencil_scale = size / 256
    px = size // 2 - int(20 * pencil_scale)
    py = size // 2 + int(30 * pencil_scale)
    draw_pencil(d, px, py, angle=55, scale=pencil_scale)

    tx = px + int(5 * pencil_scale)
    ty = py - int(60 * pencil_scale)
    draw_knowledge_tree(d, tx, ty, scale=pencil_scale * 0.9)

    # Small text "L" near bottom
    try:
        font_size = max(10, size // 12)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", font_size)
    except Exception:
        font = ImageFont.load_default()
    d.text((size // 2, size - pad - font_size), "L", fill=(138, 106, 58, 200), font=font, anchor="mm")

    # Slight vignette
    vignette = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for i in range(min(8, r // 2)):
        alpha = 3 + i
        offset = i * 2
        inner_pad = pad + offset
        outer_pad = size - pad - offset
        corner_r = max(1, r - offset)
        if inner_pad < outer_pad:
            vd.rounded_rectangle(
                [inner_pad, inner_pad, outer_pad, outer_pad],
                radius=corner_r,
                outline=(100, 90, 70, alpha),
                width=1,
            )
    img = Image.alpha_composite(img, vignette)

    return img


def build_icns(sizes, output_path):
    """Build .icns file from PNG images."""
    icns_entries = []
    total_size = 8  # header size

    # Type mapping for modern macOS
    type_map = {
        16: b"icp4",
        32: b"icp5",
        64: b"icp6",
        128: b"ic07",
        256: b"ic08",
        512: b"ic09",
        1024: b"ic10",
    }

    for size in sizes:
        img = draw_icon(size)
        buf = BytesIO()
        img.save(buf, format="PNG")
        data = buf.getvalue()

        icon_type = type_map.get(size, b"ic09")
        entry_size = 8 + len(data)
        icns_entries.append((icon_type, struct.pack(">I", entry_size) + data))
        total_size += entry_size

    with open(output_path, "wb") as f:
        f.write(b"icns")
        f.write(struct.pack(">I", total_size))
        for icon_type, data in icns_entries:
            f.write(icon_type)
            f.write(data)

    print(f"Created: {output_path}")


def main():
    out_dir = Path(__file__).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # Build .icns
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    icns_path = out_dir / "icon.icns"
    build_icns(sizes, icns_path)

    # Also save a preview
    preview = draw_icon(512)
    preview_path = out_dir / "icon_preview.png"
    preview.save(preview_path)
    print(f"Preview: {preview_path}")


if __name__ == "__main__":
    main()
