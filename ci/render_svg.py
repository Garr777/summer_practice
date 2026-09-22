#!/usr/bin/env python3
"""
Rasterise a diagram SVG to PNG.

The SVG is the versioned source -- text, diffable, reviewable. The PNG is what
actually ships, because gramax embeds an .svg into the DOCX as raw SVG bytes
under a .png part name, which Word cannot display.

Tries the rasterisers in order of how likely they are to be present, and
reports which one it used. Exits 3 when none is available, so the caller can
fall back to a committed PNG rather than failing the build.
"""
import shutil
import subprocess
import sys
from pathlib import Path

SCALE = 2  # print resolution


def with_rsvg(src: Path, out: Path, w: int, h: int) -> bool:
    if not shutil.which("rsvg-convert"):
        return False
    subprocess.run(["rsvg-convert", "-w", str(w * SCALE), "-h", str(h * SCALE),
                    "-o", str(out), str(src)], check=True)
    return True


def with_cairosvg(src: Path, out: Path, w: int, h: int) -> bool:
    try:
        import cairosvg
    except ImportError:
        return False
    cairosvg.svg2png(url=str(src), write_to=str(out),
                     output_width=w * SCALE, output_height=h * SCALE)
    return True


def with_chromium(src: Path, out: Path, w: int, h: int) -> bool:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return False
    chrome = sorted(Path("/root/.cache/ms-playwright").glob("chromium-*/chrome-linux64/chrome"))
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=str(chrome[-1]) if chrome else None, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": w, "height": h},
                                device_scale_factor=SCALE)
        page.goto(src.resolve().as_uri(), wait_until="load")
        page.wait_for_timeout(500)
        page.screenshot(path=str(out))
        browser.close()
    return True


def viewbox(src: Path):
    head = src.read_text(encoding="utf-8")[:600]
    for key in ('width="', 'height="'):
        if key not in head:
            return 1280, 800
    w = int(float(head.split('width="')[1].split('"')[0]))
    h = int(float(head.split('height="')[1].split('"')[0]))
    return w, h


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: render_svg.py <in.svg> <out.png>")
    src, out = Path(sys.argv[1]), Path(sys.argv[2])
    w, h = viewbox(src)
    for name, fn in (("rsvg-convert", with_rsvg),
                     ("cairosvg", with_cairosvg),
                     ("chromium", with_chromium)):
        try:
            if fn(src, out, w, h):
                print(f"{src.name} -> {out.name}  ({w * SCALE}x{h * SCALE}, via {name})")
                return
        except Exception as exc:                      # a present but broken renderer
            print(f"  {name} failed: {exc}", file=sys.stderr)
    sys.exit(3)


if __name__ == "__main__":
    main()
