"""Generates assets/banner.png (original artwork, no third-party logos or game art)."""
import math, numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont
S = 2; W, H = 1600 * S, 480 * S
FONT = "/usr/share/fonts/truetype/google-fonts/"
def f(name, size): return ImageFont.truetype(FONT + name, size * S)

# background: deep blue-black -> crimson glow on the left
y, x = np.mgrid[0:H, 0:W].astype(np.float32)
bg = np.zeros((H, W, 3), np.float32) + np.array([9, 10, 16], np.float32)
cx, cy = 380 * S, 240 * S
d = np.sqrt((x - cx) ** 2 + (y - cy) ** 2) / (520 * S)
glow = np.clip(1 - d, 0, 1) ** 2.2
bg += glow[..., None] * np.array([150, 18, 30], np.float32)
bg += (np.clip(1 - np.sqrt((x - 1500 * S) ** 2 + (y - 40 * S) ** 2) / (500 * S), 0, 1) ** 2)[..., None] * np.array([10, 30, 60], np.float32)
img = Image.fromarray(np.clip(bg, 0, 255).astype(np.uint8)).convert("RGBA")

# hex grid (very subtle)
grid = Image.new("RGBA", (W, H), (0, 0, 0, 0)); g = ImageDraw.Draw(grid); r = 34 * S
for row in range(-1, int(H / (r * 1.5)) + 2):
    for col in range(-1, int(W / (r * 1.74)) + 2):
        px = col * r * math.sqrt(3) + (r * math.sqrt(3) / 2 if row % 2 else 0); py = row * r * 1.5
        pts = [(px + r * math.cos(math.radians(60 * k + 30)), py + r * math.sin(math.radians(60 * k + 30))) for k in range(6)]
        g.polygon(pts, outline=(255, 255, 255, 9))
img = Image.alpha_composite(img, grid)

# emblem: ring + three fangs (Cerberus-inspired, abstract)
em = Image.new("RGBA", (W, H), (0, 0, 0, 0)); e = ImageDraw.Draw(em)
R = 170 * S
for rad, w, a in ((R, 5, 255), (R + 22 * S, 2, 120), (R - 26 * S, 2, 120)):
    e.ellipse([cx - rad, cy - rad, cx + rad, cy + rad], outline=(225, 40, 52, a), width=w * S)
def fang(ang, L=150, Wd=46):
    a = math.radians(ang); ux, uy = math.cos(a), math.sin(a); px, py = -uy, ux
    base = 18 * S; tip = L * S; w = Wd * S
    pts = [(cx + ux * base + px * w * .5, cy + uy * base + py * w * .5), (cx + ux * tip * .78 + px * w * .22, cy + uy * tip * .78 + py * w * .22),
           (cx + ux * (tip + 38 * S), cy + uy * (tip + 38 * S)), (cx + ux * tip * .9 - px * w * .05, cy + uy * tip * .9 - py * w * .05),
           (cx + ux * base - px * w * .5, cy + uy * base - py * w * .5)]
    return pts
for ang in (-90, 30, 150):
    e.polygon(fang(ang), fill=(236, 236, 242, 255))
    e.polygon(fang(ang + 60, 70, 30), fill=(225, 40, 52, 255))
e.ellipse([cx - 22 * S, cy - 22 * S, cx + 22 * S, cy + 22 * S], fill=(225, 40, 52, 255))
em_glow = em.filter(ImageFilter.GaussianBlur(14 * S))
img = Image.alpha_composite(img, em_glow); img = Image.alpha_composite(img, em)

# text
t = ImageDraw.Draw(img); tx = 700 * S
t.text((tx, 108 * S), "FF7-DoC", font=f("Poppins-Bold.ttf", 132), fill=(244, 244, 248, 255))
t.text((tx + 4 * S, 262 * S), "DECOMPILATION", font=f("Poppins-Bold.ttf", 54), fill=(225, 40, 52, 255))
t.line([(tx + 6 * S, 338 * S), (tx + 640 * S, 338 * S)], fill=(255, 255, 255, 70), width=2 * S)
mono = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 26 * S)
t.text((tx + 6 * S, 358 * S), "SLPM-66629   |   PS2   |   MIPS R5900   |   Japan", font=mono, fill=(170, 176, 192, 255))
img.convert("RGB").resize((W // S, H // S), Image.LANCZOS).save("assets/banner.png", optimize=True)
print("assets/banner.png")
