"""Record the demo of Radar innowacji: browser actions timed to the narration clips.

Output: JPEG frames of the CDP screencast in the temporary folder of the system.
Output in data/cache/video: frames.json (time stamps) and timeline.json (start of each segment).
"""

import asyncio
import base64
import json
import math
import sys
import tempfile
import time
from pathlib import Path

from playwright.async_api import async_playwright

OUT = Path(__file__).resolve().parents[2] / "data" / "cache" / "video"
# The frames go to the temporary folder of the system: a synchronized folder (OneDrive) makes the recording too slow.
FRAMES = Path(tempfile.gettempdir()) / "radar_video_frames"
BASE = "http://localhost:8000/"
DUR = json.loads((OUT / "durations.json").read_text())
GAP = 0.45

CURSOR_JS = r"""
(() => {
  const make = () => {
    if (document.getElementById('__cursor')) return;
    const c = document.createElement('div');
    c.id = '__cursor';
    c.style.cssText = 'position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;pointer-events:none;transform:translate(-100px,-100px)';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2.5l6.8 18.2 2.6-7.4 7.4-2.6z" fill="#1d1d1b" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    document.documentElement.appendChild(c);
    const r = document.createElement('div');
    r.id = '__ripple';
    r.style.cssText = 'position:fixed;left:0;top:0;width:34px;height:34px;margin:-17px 0 0 -17px;border-radius:50%;border:3px solid #0085cc;z-index:2147483646;pointer-events:none;opacity:0';
    document.documentElement.appendChild(r);
  };
  document.addEventListener('mousemove', (e) => {
    make();
    document.getElementById('__cursor').style.transform = `translate(${e.clientX - 4}px,${e.clientY - 2}px)`;
  }, true);
  document.addEventListener('mousedown', (e) => {
    make();
    const r = document.getElementById('__ripple');
    r.style.left = e.clientX + 'px'; r.style.top = e.clientY + 'px';
    r.animate([{opacity: .9, transform: 'scale(.4)'}, {opacity: 0, transform: 'scale(1.6)'}], {duration: 500, easing: 'ease-out'});
  }, true);
})();
"""


class Demo:
    def __init__(self, page, cdp):
        self.page, self.cdp = page, cdp
        self.x, self.y = 800, 450
        self.frames = []
        self.timeline = []

    async def on_frame(self, params):
        ts = params["metadata"]["timestamp"]
        name = f"f{len(self.frames):05d}.jpg"
        (FRAMES / name).write_bytes(base64.b64decode(params["data"]))
        self.frames.append((ts, name))
        await self.cdp.send("Page.screencastFrameAck", {"sessionId": params["sessionId"]})

    async def glide(self, x, y, duration=0.7):
        x0, y0 = self.x, self.y
        n = max(int(duration * 50), 1)
        for i in range(1, n + 1):
            t = i / n
            e = 0.5 - math.cos(math.pi * t) / 2
            await self.page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            await asyncio.sleep(duration / n)
        self.x, self.y = x, y

    async def to(self, locator, duration=0.7, dx=0.5, dy=0.5):
        await locator.scroll_into_view_if_needed()
        box = await locator.bounding_box()
        await self.glide(box["x"] + box["width"] * dx, box["y"] + box["height"] * dy, duration)

    async def click(self, locator, duration=0.7):
        await self.to(locator, duration)
        await asyncio.sleep(0.15)
        await self.page.mouse.down()
        await asyncio.sleep(0.08)
        await self.page.mouse.up()

    async def type(self, locator, text):
        await self.click(locator)
        await locator.press_sequentially(text, delay=65)

    async def scroll_to(self, selector, offset=96, duration=1.2):
        """Scroll smoothly so that the element is near the top, below the header."""
        y0 = await self.page.evaluate("scrollY")
        y1 = await self.page.locator(selector).first.evaluate("(e, o) => e.getBoundingClientRect().top + scrollY - o", offset)
        y1 = max(0, min(y1, await self.page.evaluate("document.documentElement.scrollHeight - innerHeight")))
        n = max(int(duration * 50), 1)
        for i in range(1, n + 1):
            e = 0.5 - math.cos(math.pi * i / n) / 2
            await self.page.evaluate(f"scrollTo(0, {y0 + (y1 - y0) * e})")
            await asyncio.sleep(duration / n)

    async def scroll_by(self, dy, duration=1.2):
        y0 = await self.page.evaluate("scrollY")
        n = max(int(duration * 50), 1)
        for i in range(1, n + 1):
            e = 0.5 - math.cos(math.pi * i / n) / 2
            await self.page.evaluate(f"scrollTo(0, {y0 + dy * e})")
            await asyncio.sleep(duration / n)

    async def goto(self, url):
        await self.page.goto(BASE + url, wait_until="networkidle")
        await self.page.mouse.move(self.x, self.y)

    async def wait_nav(self):
        await self.page.wait_for_load_state("networkidle")
        await self.page.mouse.move(self.x, self.y)

    async def segment(self, sid, actions):
        start = time.time()
        self.timeline.append({"id": sid, "start": start})
        await actions()
        left = DUR[sid] + GAP - (time.time() - start)
        if left < 0:
            print(f"{sid}: actions too long by {-left:.1f} s", file=sys.stderr)
        await asyncio.sleep(max(left, 0))


def h2(text):
    return f"xpath=//h2[normalize-space()='{text}'] | //h3[normalize-space()='{text}']"


async def main():
    FRAMES.mkdir(parents=True, exist_ok=True)
    for f in FRAMES.glob("*.jpg"):
        f.unlink()
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(
            viewport={"width": 1600, "height": 900}, device_scale_factor=1.2, locale="pl-PL"
        )
        await context.add_init_script(CURSOR_JS)
        page = await context.new_page()
        cdp = await context.new_cdp_session(page)
        d = Demo(page, cdp)
        cdp.on("Page.screencastFrame", lambda params: asyncio.ensure_future(d.on_frame(params)))

        await page.goto(BASE, wait_until="networkidle")
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": 1920, "maxHeight": 1080})
        await page.mouse.move(d.x, d.y)
        await asyncio.sleep(0.8)
        loc = page.locator

        async def s1():
            await d.glide(700, 330, 1.6)
            await asyncio.sleep(3)
            await d.to(loc("#q"), 1.5, dx=0.3)
            await asyncio.sleep(3)
            await d.to(loc("#examples button").first, 1.2)

        async def s2():
            await d.click(loc(".nav a", has_text="O radarze"))
            await d.wait_nav()
            await asyncio.sleep(2.5)
            await d.scroll_to("#zrodla", duration=1.6)
            await asyncio.sleep(1)
            tiles = loc("#source-list > li")
            for i in range(min(await tiles.count(), 8)):
                await d.to(tiles.nth(i), 0.7)
                await asyncio.sleep(0.6)
            await d.scroll_to("#oznaczenia", duration=1.4)
            await asyncio.sleep(1.5)
            await d.scroll_to("#prywatnosc", duration=1.4)

        async def s3():
            await d.click(loc(".nav a", has_text="Szukaj"))
            await d.wait_nav()
            await d.to(loc("#group"), 0.8)
            await page.select_option("#group", "public")
            await d.wait_nav()
            await asyncio.sleep(1.2)
            await d.type(loc("#q"), "e-urząd")
            await asyncio.sleep(0.4)
            await d.click(loc("#search-form button[type=submit]"), 0.6)
            await d.wait_nav()
            await asyncio.sleep(2.5)
            await d.to(loc("#area"), 0.8)
            await asyncio.sleep(0.6)
            await d.to(loc("#voivodeship"), 0.6)
            await page.select_option("#voivodeship", "podkarpackie")
            await d.wait_nav()
            await asyncio.sleep(0.8)
            await d.to(loc("#level_min"), 0.6)
            await asyncio.sleep(1.2)
            await d.scroll_to("#results", duration=1.4)
            await d.to(loc("#result-list > li").first, 0.9, dx=0.3)

        async def s4():
            link = loc("#result-list a", has_text="Horyniec-Zdrój").first
            await d.scroll_to("#result-list > li:nth-child(3)", duration=0.8)
            await d.click(link)
            await d.wait_nav()
            await asyncio.sleep(2.2)
            await d.to(loc(".result-tags").first, 0.8)
            await asyncio.sleep(1.2)
            await d.scroll_to(".tiles", offset=150, duration=1.2)
            level_tile = loc(".tile", has_text="Status wdrożenia")
            await d.to(level_tile, 0.8)
            await asyncio.sleep(1.5)
            await d.click(level_tile.locator("summary"))
            await asyncio.sleep(2.5)
            await d.to(level_tile.locator(".provenance-body a"), 0.8)

        async def s5():
            await d.scroll_to(".card-layout", offset=110, duration=1.0)
            await d.to(loc(".score-value"), 0.9)
            await asyncio.sleep(2.5)
            await d.to(loc(".range"), 0.8)
            await asyncio.sleep(3.2)
            await d.to(loc(".confidence-line .chip"), 0.8)
            await asyncio.sleep(2.4)
            await d.scroll_to(".panel-title", offset=110, duration=1.2)
            rows = loc(".criteria-list > li.criterion")
            for i in range(min(await rows.count(), 3)):
                await d.to(rows.nth(i), 0.6, dx=0.3)
                await asyncio.sleep(0.7)
            await d.scroll_to("body", duration=0.8)
            await d.click(loc(".score-panel .compare-toggle input"), 0.7)

        async def s6():
            await d.scroll_to(h2("Gdzie można zastosować"), duration=1.2)
            await asyncio.sleep(1.0)
            await d.to(loc(h2("Rekomendowana ścieżka")), 0.8)
            await d.scroll_to(h2("Rekomendowana ścieżka"), duration=1.0)
            await d.to(loc(".mini-tile.path").first, 0.8)
            await asyncio.sleep(1.5)
            await d.scroll_to(h2("Kto ma podobne rozwiązania"), duration=1.0)
            await asyncio.sleep(1.8)
            await d.scroll_to(h2("Jak nawiązać kontakt"), duration=1.0)
            await asyncio.sleep(1.6)
            await d.scroll_to(h2("Kto kupuje podobne rozwiązania"), duration=1.0)

        async def s7():
            await d.click(loc(".nav a", has_text="Szukaj"))
            await d.wait_nav()
            await d.type(loc("#q"), "elektroda zgrzewanie")
            await page.keyboard.press("Enter")
            await d.wait_nav()
            await asyncio.sleep(1.0)
            await d.click(loc("#result-list a", has_text="Bezodpadowa").first)
            await d.wait_nav()
            await asyncio.sleep(1.0)
            await d.click(loc(".score-panel .compare-toggle input"), 0.8)
            await d.scroll_to(".tiles", offset=150, duration=1.0)
            await d.to(loc(".tile", has_text="Gotowość technologiczna"), 0.8)
            await asyncio.sleep(1.2)
            await d.scroll_to(h2("Historia"), duration=1.0)
            await d.to(loc(h2("Historia")), 0.7)
            await asyncio.sleep(1.6)
            await d.scroll_to(h2("Rekomendowana ścieżka"), duration=1.0)
            await d.to(loc(".mini-tile.path").first, 0.8)
            await asyncio.sleep(1.4)
            await d.scroll_to(h2("Jak nawiązać kontakt"), offset=300, duration=1.0)
            await d.to(loc("a", has_text="kancelaria@").first, 0.8)

        async def s8():
            await d.click(loc("#compare-go"), 0.9)
            await d.wait_nav()
            await asyncio.sleep(1.4)
            await d.scroll_by(450, 1.6)
            await asyncio.sleep(0.6)
            await d.scroll_by(450, 1.6)

        async def s9():
            await d.goto("?q=e-urz%C4%85d&group=public&voivodeship=podkarpackie")
            await asyncio.sleep(1.0)
            await d.click(loc("#watch-button"), 0.8)
            await asyncio.sleep(1.0)
            await d.scroll_to("#watchlist", offset=120, duration=0.8)
            await asyncio.sleep(2.2)
            await d.goto("docs")
            await asyncio.sleep(1.0)
            await d.to(loc(".opblock-summary-path", has_text="export.csv").first, 0.9)
            await asyncio.sleep(3.0)
            await d.goto("about.html")
            await d.scroll_to("#ocena", duration=1.4)
            await d.to(loc("#criteria-list > *").first, 0.8)

        for sid, fn in [("s1", s1), ("s2", s2), ("s3", s3), ("s4", s4), ("s5", s5), ("s6", s6), ("s7", s7), ("s8", s8), ("s9", s9)]:
            print(sid, flush=True)
            await d.segment(sid, fn)
        await asyncio.sleep(1.2)
        end = time.time()
        await cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.3)
        await browser.close()

    (OUT / "frames.json").write_text(json.dumps({"frames": d.frames, "end": end}))
    (OUT / "timeline.json").write_text(json.dumps(d.timeline))
    print(len(d.frames), "frames")


asyncio.run(main())
