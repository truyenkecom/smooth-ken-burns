# smooth-ken-burns

Turn still images into smooth **vertical 9:16 Ken Burns clips** (Reels / Shorts / TikTok) without the jitter you get from ffmpeg's `zoompan`.

## Why

`zoompan` snaps the crop window to whole pixels. On slow zooms that rounding shows up as a constant shake. This script renders each frame with a **sub-pixel affine transform** (bicubic, from a 2× source) in Pillow and pipes raw frames into ffmpeg, plus an ease-in/out curve so zooms don't start or stop abruptly.

Layout: a square foreground image centred on a blurred, darkened copy of itself, 1080×1920 @ 30 fps.

## Install

```bash
pip install -r requirements.txt   # Pillow
# ffmpeg must be on PATH
```

## Usage

```bash
# one image, 6 s, zoom in
python ken_burns.py scene.jpg clip.mp4 --seconds 6 --zoom in

# several images, alternating zoom in/out, concatenated
python ken_burns.py img0.jpg img1.jpg img2.jpg -o story.mp4 --seconds 5
```

Or from Python:

```python
from ken_burns import make_clip
make_clip("scene.jpg", "clip.mp4", seconds=6, zoom_in=True, strength=0.08)
```

Measured on the same image, frame-to-frame jitter dropped by about a third compared with `zoompan`.

Used to make story trailers for [Truyện Kể](https://truyenke.com).

## License

MIT
