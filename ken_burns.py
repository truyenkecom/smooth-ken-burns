"""Smooth Ken Burns clips for vertical video (9:16) without the ffmpeg zoompan jitter.

ffmpeg's zoompan rounds the crop window to whole pixels, so slow zooms visibly
shake. Here every frame is rendered with a sub-pixel affine transform (bicubic)
in Pillow and piped as raw video into ffmpeg.

Usage:
    python ken_burns.py image.jpg out.mp4 --seconds 6 --zoom in
    python ken_burns.py a.jpg b.jpg c.jpg -o story.mp4 --seconds 5
"""
import argparse
import math
import os
import subprocess
import tempfile

from PIL import Image, ImageEnhance, ImageFilter

W, H, FPS = 1080, 1920, 30


def background(img):
    """Blurred, darkened cover fill for the 9:16 canvas."""
    s = max(W / img.width, H / img.height)
    bg = img.resize((int(img.width * s) + 1, int(img.height * s) + 1), Image.LANCZOS)
    left, top = (bg.width - W) // 2, (bg.height - H) // 2
    bg = bg.crop((left, top, left + W, top + H))
    return ImageEnhance.Brightness(bg.filter(ImageFilter.GaussianBlur(40))).enhance(0.75)


def make_clip(img_path, out, seconds=6.0, zoom_in=True, strength=0.08, y=None, crf=19):
    """Render one clip: square foreground (W x W) zooming over a blurred background."""
    img = Image.open(img_path).convert("RGB")
    side = min(img.width, img.height)
    img = img.crop(((img.width - side) // 2, (img.height - side) // 2,
                    (img.width + side) // 2, (img.height + side) // 2))
    src = img.resize((W * 2, W * 2), Image.LANCZOS)  # 2x source keeps detail while zooming
    bg = background(img)
    y = (H - W) // 2 if y is None else y
    n = max(2, int(round(seconds * FPS)))
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "veryfast", "-crf", str(crf),
           "-pix_fmt", "yuv420p", out]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    S = src.width
    try:
        for k in range(n):
            t = k / (n - 1)
            e = 0.5 - 0.5 * math.cos(math.pi * t)  # ease in/out, no abrupt start/stop
            z = 1 + strength * e if zoom_in else 1 + strength * (1 - e)
            vis = S / z
            x0 = (S - vis) / 2
            sc = vis / W
            fg = src.transform((W, W), Image.AFFINE, (sc, 0, x0, 0, sc, x0), resample=Image.BICUBIC)
            frame = bg.copy()
            frame.paste(fg, (0, y))
            p.stdin.write(frame.tobytes())
        p.stdin.close()
        if p.wait():
            raise RuntimeError(p.stderr.read().decode("utf-8", "replace")[-800:])
    finally:
        if p.poll() is None:
            p.kill()
    return out


def concat(clips, out):
    with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8") as f:
        for c in clips:
            f.write(f"file '{os.path.abspath(c)}'\n")
        lst = f.name
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", lst, "-c", "copy", out], check=True)
    os.remove(lst)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("images", nargs="+", help="one or more images; the last positional may be the output if -o is omitted")
    ap.add_argument("-o", "--output")
    ap.add_argument("--seconds", type=float, default=6.0, help="seconds per image")
    ap.add_argument("--zoom", choices=["in", "out", "alternate"], default="alternate")
    ap.add_argument("--strength", type=float, default=0.08, help="zoom amount, 0.08 = 8%%")
    a = ap.parse_args()
    imgs, out = list(a.images), a.output
    if not out:
        if len(imgs) < 2:
            ap.error("need an output path")
        out = imgs.pop()
    if len(imgs) == 1:
        make_clip(imgs[0], out, a.seconds, a.zoom != "out", a.strength)
    else:
        tmp = tempfile.mkdtemp()
        clips = []
        for i, im in enumerate(imgs):
            zin = {"in": True, "out": False}.get(a.zoom, i % 2 == 0)
            clips.append(make_clip(im, os.path.join(tmp, f"c{i}.mp4"), a.seconds, zin, a.strength))
        concat(clips, out)
    print(out)


if __name__ == "__main__":
    main()
