"""Fallback fetcher through a headless Chrome for Testing (Playwright's own
bundled Chromium, its own throwaway profile).

Never the installed Google Chrome and never a visible window: the owner works in
that browser on this machine (11-17: a visible test window opened a PNAS
supplement on his screen).

Used only where plain HTTP gets a bot wall or a JavaScript interstitial: PMC's
"Preparing to download" page in front of supplement files, and publishers that
answer 403 to scripts. Opens public pages only; never signs in anywhere.
"""
import asyncio
import pathlib
import re

from playwright.async_api import async_playwright

ARGS = ["--disable-blink-features=AutomationControlled", "--use-mock-keychain"]


async def _fetch(jobs, headless=True):
    """jobs: list of (url, out_path, kind) where kind is 'file' or 'page'.
    Returns {url: status}."""
    res = {}
    async with async_playwright() as p:
        assert headless, "visible windows are not allowed on the owner's machine"
        b = await p.chromium.launch(headless=True, args=ARGS)  # bundled Chrome for Testing, not channel="chrome"
        ctx = await b.new_context(accept_downloads=True, viewport={"width": 1300, "height": 1600})
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")
        pg = await ctx.new_page()
        for url, out, kind in jobs:
            out = pathlib.Path(out)
            out.parent.mkdir(parents=True, exist_ok=True)
            try:
                if kind == "file":
                    try:
                        async with pg.expect_download(timeout=60000) as dl:
                            try:
                                await pg.goto(url, timeout=60000)
                            except Exception:
                                pass  # navigation is aborted when the download starts
                        d = await dl.value
                        await d.save_as(out)
                        res[url] = "ok"
                    except Exception:
                        # some servers render the PDF inline instead of downloading it
                        r = await ctx.request.get(url)
                        body = await r.body()
                        if body[:4] == b"%PDF" or body[:2] == b"PK":
                            out.write_bytes(body)
                            res[url] = "ok_inline"
                        else:
                            res[url] = f"no_file_{r.status}"
                else:
                    await pg.goto(url, wait_until="domcontentloaded", timeout=90000)
                    await pg.wait_for_timeout(8000)  # bot checks and article scripts settle; some pages never go network-idle
                    out.write_text(await pg.content())
                    res[url] = "ok"
            except Exception as e:
                res[url] = f"error:{type(e).__name__}"
        await b.close()
    return res


def fetch(jobs, headless=True):
    return asyncio.run(_fetch(jobs, headless))
