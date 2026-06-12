from __future__ import annotations

import argparse
import asyncio
import json
import re
import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from playwright.async_api import BrowserContext, Page, async_playwright


@dataclass
class Settings:
    url: str
    pages: int
    start_page: int
    output_dir: Path
    zip_path: Path
    width: int
    height: int
    scale: float
    full_page: bool
    show_browser: bool
    delay_ms: int
    clean: bool
    cookie_choice: str
    cookie_check_each_page: bool
    concurrency: int
    image_format: str
    quality: int
    quiet: bool
    verbose: bool


def log(settings: Settings, message: str, *, verbose_only: bool = False) -> None:
    if settings.quiet:
        return
    if verbose_only and not settings.verbose:
        return
    print(message, flush=True)


def build_page_url(base_url: str, page_number: int) -> str:
    if re.search(r"/page/\d+", base_url):
        return re.sub(r"/page/\d+", f"/page/{page_number}", base_url)
    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}page={page_number}"


def cookie_targets(choice: str) -> list[str]:
    reject = [
        "CONTINUA SENZA ACCETTARE",
        "Continua senza accettare",
        "Rifiuta",
        "Reject all",
        "Reject",
        "Continue without accepting",
    ]
    accept = [
        "ACCETTA TUTTI",
        "Accetta tutti",
        "Accetta tutto",
        "Accetta",
        "Accept all",
        "Accept",
        "OK",
        "Ok",
    ]
    close = ["Chiudi", "Close"]
    if choice == "accept":
        return accept + reject + close
    if choice == "reject":
        return reject + accept + close
    if choice == "hide":
        return []
    return reject + accept + close


async def click_cookie_by_text(page: Page, text: str) -> bool:
    pattern = re.compile(re.escape(text), re.I)
    candidates = [
        lambda: page.get_by_role("button", name=pattern),
        lambda: page.get_by_role("link", name=pattern),
        lambda: page.locator("button").filter(has_text=pattern),
        lambda: page.locator("a").filter(has_text=pattern),
        lambda: page.locator("[role='button']").filter(has_text=pattern),
        lambda: page.locator(f"text={text}"),
    ]
    for make_locator in candidates:
        try:
            loc = make_locator()
            if await loc.count() > 0:
                await loc.first.click(timeout=1800, force=True)
                await page.wait_for_timeout(500)
                return True
        except Exception:
            pass
    return False


async def click_cookie_by_javascript(page: Page, targets: list[str]) -> bool:
    js = """
    (targets) => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const wanted = targets.map(normalize);
      const selector = 'button,a,[role="button"],input[type="button"],input[type="submit"],div,span';
      const els = Array.from(document.querySelectorAll(selector));
      for (const el of els) {
        const text = normalize(el.innerText || el.textContent || el.value || '');
        if (!text) continue;
        const match = wanted.some(w => text === w || text.includes(w));
        if (!match) continue;
        const clickable = el.closest('button, a, [role="button"], input') || el;
        clickable.click();
        return text;
      }
      return null;
    }
    """
    try:
        clicked_text = await page.evaluate(js, targets)
        if clicked_text:
            await page.wait_for_timeout(600)
            return True
    except Exception:
        pass
    return False


async def hide_cookie_popup_by_javascript(page: Page) -> bool:
    js = """
    () => {
      const normalize = (s) => (s || '').replace(/\s+/g, ' ').trim().toLowerCase();
      const markers = [
        'prima di procedere',
        'trattamento dei suoi dati',
        'gestori dei siti web lidl',
        'continua senza accettare',
        'accetta tutti',
        'personalizza la scelta'
      ];
      const all = Array.from(document.querySelectorAll('body *'));
      let hidden = 0;
      function hide(el) {
        if (!el || el === document.body || el === document.documentElement) return;
        el.style.setProperty('display', 'none', 'important');
        el.style.setProperty('visibility', 'hidden', 'important');
        hidden += 1;
      }
      for (const el of all) {
        const text = normalize(el.innerText || el.textContent || '');
        if (!text) continue;
        if (!markers.some(m => text.includes(m))) continue;
        let current = el;
        let best = el;
        for (let i = 0; i < 8 && current; i++) {
          const style = window.getComputedStyle(current);
          const rect = current.getBoundingClientRect();
          if (
            style.position === 'fixed' ||
            style.position === 'absolute' ||
            current.getAttribute('role') === 'dialog' ||
            rect.width > window.innerWidth * 0.4
          ) {
            best = current;
          }
          current = current.parentElement;
        }
        hide(best);
      }
      for (const el of all) {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const opacity = parseFloat(style.opacity || '1');
        const z = parseInt(style.zIndex || '0', 10);
        const bigOverlay =
          (style.position === 'fixed' || style.position === 'absolute') &&
          rect.width > window.innerWidth * 0.75 &&
          rect.height > window.innerHeight * 0.75 &&
          (opacity < 1 || z > 10);
        if (bigOverlay) hide(el);
      }
      document.body.style.overflow = 'auto';
      document.documentElement.style.overflow = 'auto';
      return hidden;
    }
    """
    try:
        hidden = await page.evaluate(js)
        return bool(hidden and int(hidden) > 0)
    except Exception:
        return False


async def dismiss_cookie_popup(page: Page, settings: Settings) -> bool:
    if settings.cookie_choice == "manual":
        log(settings, "Cookie manuale: cliccalo nel browser se compare.")
        await page.wait_for_timeout(5000)
        return True
    if settings.cookie_choice == "skip":
        return False
    await page.wait_for_timeout(700)
    targets = cookie_targets(settings.cookie_choice)
    if settings.cookie_choice != "hide":
        for text in targets:
            if await click_cookie_by_text(page, text):
                log(settings, f"Cookie chiuso: {text}", verbose_only=True)
                return True
        if await click_cookie_by_javascript(page, targets):
            log(settings, "Cookie chiuso via JavaScript.", verbose_only=True)
            return True
    if await hide_cookie_popup_by_javascript(page):
        log(settings, "Cookie popup nascosto via JavaScript.", verbose_only=True)
        return True
    log(settings, "Nessun cookie popup trovato.", verbose_only=True)
    return False


async def prepare_cookie_context(context: BrowserContext, settings: Settings) -> None:
    if settings.cookie_choice == "skip":
        return
    page = await context.new_page()
    try:
        first_url = build_page_url(settings.url, settings.start_page)
        log(settings, "Preparo sessione cookie...", verbose_only=True)
        await page.goto(first_url, wait_until="domcontentloaded", timeout=45000)
        await dismiss_cookie_popup(page, settings)
    finally:
        await page.close()


async def wait_for_render(page: Page, settings: Settings) -> None:
    try:
        await page.wait_for_load_state("networkidle", timeout=9000)
    except Exception:
        pass
    await page.wait_for_timeout(settings.delay_ms)
    try:
        await page.mouse.wheel(0, 700)
        await page.wait_for_timeout(150)
        await page.mouse.wheel(0, -700)
        await page.wait_for_timeout(150)
    except Exception:
        pass


async def hide_annoying_fixed_elements(page: Page) -> None:
    js = """
    (() => {
      const els = Array.from(document.querySelectorAll('*'));
      for (const el of els) {
        const style = window.getComputedStyle(el);
        const rect = el.getBoundingClientRect();
        const z = parseInt(style.zIndex || '0', 10);
        const isLargeFixed =
          (style.position === 'fixed' || style.position === 'sticky') &&
          rect.width > window.innerWidth * 0.55 &&
          rect.height > 45 &&
          z >= 10;
        if (!isLargeFixed) continue;
        const text = (el.innerText || '').toLowerCase();
        if (text.includes('cookie') || text.includes('accetta') || text.includes('trattamento')) {
          el.style.setProperty('visibility', 'hidden', 'important');
          el.style.setProperty('display', 'none', 'important');
        }
      }
    })();
    """
    try:
        await page.evaluate(js)
    except Exception:
        pass


async def find_best_flyer_clip(page: Page) -> Optional[dict]:
    js = """
    (() => {
      const candidates = [];
      function addCandidate(el, kind) {
        const r = el.getBoundingClientRect();
        const style = window.getComputedStyle(el);
        if (style.visibility === 'hidden' || style.display === 'none') return;
        if (r.width < 350 || r.height < 500) return;
        candidates.push({
          x: Math.max(0, r.x),
          y: Math.max(0, r.y),
          width: Math.min(r.width, window.innerWidth - Math.max(0, r.x)),
          height: Math.min(r.height, document.documentElement.scrollHeight - Math.max(0, r.y)),
          area: r.width * r.height,
          kind
        });
      }
      document.querySelectorAll('img, canvas, picture, svg').forEach(el => {
        addCandidate(el, el.tagName.toLowerCase());
      });
      document.querySelectorAll('div, section, article').forEach(el => {
        const style = window.getComputedStyle(el);
        const bg = style.backgroundImage || '';
        const cls = (el.className || '').toString().toLowerCase();
        const id = (el.id || '').toLowerCase();
        if (
          (bg && bg !== 'none') ||
          cls.includes('flyer') ||
          cls.includes('leaflet') ||
          cls.includes('page') ||
          id.includes('flyer') ||
          id.includes('leaflet')
        ) {
          addCandidate(el, 'container');
        }
      });
      candidates.sort((a, b) => b.area - a.area);
      const best = candidates[0];
      if (!best) return null;
      const pad = 12;
      return {
        x: Math.max(0, best.x - pad),
        y: Math.max(0, best.y - pad),
        width: Math.max(1, Math.min(best.width + pad * 2, window.innerWidth - Math.max(0, best.x - pad))),
        height: Math.max(1, best.height + pad * 2)
      };
    })();
    """
    try:
        clip = await page.evaluate(js)
        if clip and clip["width"] > 350 and clip["height"] > 500:
            return clip
    except Exception:
        pass
    return None


def screenshot_kwargs(settings: Settings, output_path: Path, clip: Optional[dict] = None) -> dict:
    kwargs = {"path": str(output_path)}
    if settings.image_format == "jpg":
        kwargs["type"] = "jpeg"
        kwargs["quality"] = settings.quality
    else:
        kwargs["type"] = "png"
    if clip:
        kwargs["clip"] = clip
    else:
        kwargs["full_page"] = settings.full_page
    return kwargs


async def capture_page(context: BrowserContext, page_number: int, index: int, total: int, settings: Settings) -> dict:
    ext = "jpg" if settings.image_format == "jpg" else "png"
    output_path = settings.output_dir / f"page_{page_number:03d}.{ext}"
    page_url = build_page_url(settings.url, page_number)
    result = {
        "page_number": page_number,
        "url": page_url,
        "file": str(output_path),
        "ok": False,
        "mode": None,
        "error": None,
    }
    page = await context.new_page()
    try:
        await page.goto(page_url, wait_until="domcontentloaded", timeout=45000)
        if settings.cookie_check_each_page:
            await dismiss_cookie_popup(page, settings)
        await wait_for_render(page, settings)
        if settings.cookie_check_each_page:
            await hide_cookie_popup_by_javascript(page)
        await hide_annoying_fixed_elements(page)
        if settings.full_page:
            await page.screenshot(**screenshot_kwargs(settings, output_path))
            result["ok"] = True
            result["mode"] = "full_page"
        else:
            clip = await find_best_flyer_clip(page)
            if clip:
                await page.screenshot(**screenshot_kwargs(settings, output_path, clip=clip))
                result["ok"] = True
                result["mode"] = "smart_clip"
            else:
                fallback_kwargs = screenshot_kwargs(settings, output_path)
                fallback_kwargs["full_page"] = True
                await page.screenshot(**fallback_kwargs)
                result["ok"] = True
                result["mode"] = "fallback_full_page"
        log(settings, f"[{index}/{total}] pagina {page_number}: OK")
        log(settings, f"  modo={result['mode']} file={output_path.name}", verbose_only=True)
    except Exception as exc:
        result["error"] = str(exc)
        log(settings, f"[{index}/{total}] pagina {page_number}: ERRORE")
        log(settings, f"  {exc}", verbose_only=True)
    finally:
        await page.close()
    return result


def make_zip(folder: Path, zip_path: Path) -> None:
    zip_path.parent.mkdir(parents=True, exist_ok=True)
    if zip_path.exists():
        zip_path.unlink()
    image_files = sorted(list(folder.glob("*.jpg")) + list(folder.glob("*.png")))
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for file in image_files:
            z.write(file, arcname=file.name)
        manifest = folder / "manifest.json"
        if manifest.exists():
            z.write(manifest, arcname="manifest.json")


async def run_capture(settings: Settings) -> None:
    if settings.clean and settings.output_dir.exists():
        shutil.rmtree(settings.output_dir)
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    settings.zip_path.parent.mkdir(parents=True, exist_ok=True)
    manifest = {
        "source_url": settings.url,
        "start_page": settings.start_page,
        "pages_requested": settings.pages,
        "cookie_choice": settings.cookie_choice,
        "concurrency": settings.concurrency,
        "image_format": settings.image_format,
        "quality": settings.quality if settings.image_format == "jpg" else None,
        "items": [],
    }
    log(settings, f"Avvio cattura: {settings.pages} pagine, concorrenza {settings.concurrency}, formato {settings.image_format}")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=not settings.show_browser)
        context = await browser.new_context(
            viewport={"width": settings.width, "height": settings.height},
            device_scale_factor=settings.scale,
            locale="it-IT",
            ignore_https_errors=True,
        )
        await prepare_cookie_context(context, settings)
        page_numbers = list(range(settings.start_page, settings.start_page + settings.pages))
        semaphore = asyncio.Semaphore(settings.concurrency)
        async def guarded_capture(idx: int, page_number: int) -> dict:
            async with semaphore:
                return await capture_page(context, page_number, idx, len(page_numbers), settings)
        tasks = [guarded_capture(idx, pn) for idx, pn in enumerate(page_numbers, start=1)]
        manifest["items"] = await asyncio.gather(*tasks)
        await browser.close()
    manifest_path = settings.output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    make_zip(settings.output_dir, settings.zip_path)
    ok_count = sum(1 for item in manifest["items"] if item["ok"])
    if not settings.quiet:
        print("\nFatto.")
        print(f"Screenshot riusciti: {ok_count}/{settings.pages}")
        print(f"ZIP da caricare su ChatGPT: {settings.zip_path.resolve()}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Cattura immagini delle pagine di un volantino online. Nessun OCR, nessuna API.")
    parser.add_argument("--url", required=True, help="URL della pagina 1 del volantino.")
    parser.add_argument("--pages", type=int, required=True, help="Numero pagine da catturare.")
    parser.add_argument("--start-page", type=int, default=1, help="Pagina iniziale. Default: 1")
    parser.add_argument("--output-dir", default="captured_pages", help="Cartella immagini.")
    parser.add_argument("--zip-path", default="output/flyer_pages_for_chatgpt.zip", help="ZIP finale.")
    parser.add_argument("--width", type=int, default=1600, help="Viewport width.")
    parser.add_argument("--height", type=int, default=2200, help="Viewport height.")
    parser.add_argument("--scale", type=float, default=1.5, help="Device scale factor.")
    parser.add_argument("--delay-ms", type=int, default=1200, help="Attesa rendering pagina.")
    parser.add_argument("--full-page", action="store_true", help="Screenshot pagina intera.")
    parser.add_argument("--show-browser", action="store_true", help="Mostra browser.")
    parser.add_argument("--no-clean", action="store_true", help="Non pulire output precedente.")
    parser.add_argument("--cookie-choice", choices=["reject", "accept", "hide", "manual", "skip"], default="reject", help="Come gestire popup cookie. Default: reject.")
    parser.add_argument("--cookie-check-each-page", action="store_true", help="Controlla/nasconde cookie popup su ogni pagina. Più lento.")
    parser.add_argument("--concurrency", type=int, default=2, help="Pagine catturate in parallelo. Default: 2")
    parser.add_argument("--image-format", choices=["jpg", "png"], default="jpg", help="Formato immagini. Default: jpg")
    parser.add_argument("--quality", type=int, default=88, help="Qualità JPG 1-100. Default: 88")
    parser.add_argument("--quiet", action="store_true", help="Riduce al minimo la stampa in console.")
    parser.add_argument("--verbose", action="store_true", help="Log dettagliati.")
    parser.add_argument("--fast", action="store_true", help="Imposta delay 700ms, concurrency 3, jpg quality 86.")
    args = parser.parse_args()
    if args.fast:
        if args.delay_ms == 1200:
            args.delay_ms = 700
        if args.concurrency == 2:
            args.concurrency = 3
        if args.image_format == "jpg" and args.quality == 88:
            args.quality = 86
    if args.concurrency < 1:
        raise ValueError("--concurrency deve essere almeno 1")
    if args.quality < 1 or args.quality > 100:
        raise ValueError("--quality deve essere tra 1 e 100")
    settings = Settings(
        url=args.url,
        pages=args.pages,
        start_page=args.start_page,
        output_dir=Path(args.output_dir),
        zip_path=Path(args.zip_path),
        width=args.width,
        height=args.height,
        scale=args.scale,
        full_page=args.full_page,
        show_browser=args.show_browser,
        delay_ms=args.delay_ms,
        clean=not args.no_clean,
        cookie_choice=args.cookie_choice,
        cookie_check_each_page=args.cookie_check_each_page,
        concurrency=args.concurrency,
        image_format=args.image_format,
        quality=args.quality,
        quiet=args.quiet,
        verbose=args.verbose,
    )
    asyncio.run(run_capture(settings))


if __name__ == "__main__":
    main()
