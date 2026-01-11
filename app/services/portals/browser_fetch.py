from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

@dataclass
class BrowserSnapshot:
    url: str
    html: str
    used_browser: bool
    notes: str = ""
    final_url: Optional[str] = None


def looks_like_js_shell(html: str) -> bool:
    h = (html or "").lower()
    if not h:
        return True
    if "enable javascript" in h:
        return True
    if len(h) < 8000 and "<script" in h:
        return True
    return False


async def fetch_html_with_playwright(url: str) -> BrowserSnapshot:
    try:
        from playwright.async_api import async_playwright  # type: ignore
    except Exception as e:
        return BrowserSnapshot(url=url, html="", used_browser=False, notes=f"Playwright import failed: {e}")

    def _is_workday(u: str) -> bool:
        u = (u or "").lower()
        return ("myworkdayjobs.com" in u) or ("workday" in u)

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            notes_parts: list[str] = []

            # Go to the page and let it hydrate.
            resp = await page.goto(url, wait_until="domcontentloaded", timeout=60_000)
            status = resp.status if resp else None

            # Workday is React; wait for #root to exist and some content.
            try:
                await page.wait_for_selector("#root", timeout=30_000)
            except Exception:
                pass
            await page.wait_for_timeout(1500)

            # If Workday job page, click Apply and possibly the chooser button.
            if _is_workday(page.url):
                # 1) Find Apply (can be <a role="button">Apply</a>)
                apply_locators = [
                    page.get_by_role("button", name="Apply"),
                    page.get_by_role("link", name="Apply"),
                    page.locator("a[role='button']", has_text="Apply"),
                    page.locator("text=Apply").first,
                ]

                apply_btn = None
                for loc in apply_locators:
                    try:
                        if await loc.count() > 0 and await loc.first.is_visible():
                            apply_btn = loc.first
                            break
                    except Exception:
                        continue

                if apply_btn:
                    try:
                        await apply_btn.click(timeout=10_000)
                        notes_parts.append("clicked:apply")
                        await page.wait_for_timeout(2500)
                    except Exception as e:
                        notes_parts.append(f"apply_click_failed:{type(e).__name__}")

                    # 2) If chooser appears, click Autofill with Resume (preferred)
                    chooser_locators = [
                        page.get_by_role("button", name="Autofill with Resume"),
                        page.get_by_role("link", name="Autofill with Resume"),
                        page.locator("text=Autofill with Resume").first,
                        # fallback: Apply Manually
                        page.get_by_role("button", name="Apply Manually"),
                        page.get_by_role("link", name="Apply Manually"),
                        page.locator("text=Apply Manually").first,
                    ]

                    chooser_btn = None
                    for loc in chooser_locators:
                        try:
                            if await loc.count() > 0 and await loc.first.is_visible():
                                chooser_btn = loc.first
                                break
                        except Exception:
                            continue

                    if chooser_btn:
                        try:
                            txt = (await chooser_btn.inner_text()).strip()
                        except Exception:
                            txt = "chooser"
                        try:
                            await chooser_btn.click(timeout=10_000)
                            notes_parts.append(f"clicked:{txt.lower().replace(' ', '_')}")
                            await page.wait_for_timeout(3500)
                        except Exception as e:
                            notes_parts.append(f"chooser_click_failed:{type(e).__name__}")
                else:
                    notes_parts.append("apply_not_found")

                # Wait a bit more for Workday navigation/hydration after clicks.
                await page.wait_for_timeout(2000)

            # Try to wait for apply route or some inputs to appear (don’t hard fail).
            try:
                await page.wait_for_timeout(1500)
                # Either URL has /apply, OR inputs exist, OR data-automation-id elements exist.
                # This is deliberately soft.
                for _ in range(10):
                    u = page.url.lower()
                    inputs = await page.locator("input, textarea, select").count()
                    daid = await page.locator("[data-automation-id]").count()
                    if "/apply" in u or inputs > 0 or daid > 20:
                        break
                    await page.wait_for_timeout(500)
            except Exception:
                pass

            html = await page.content()
            final_url = page.url

            await context.close()
            await browser.close()

            notes = f"Playwright ok; status={status}"
            if notes_parts:
                notes += "; " + "; ".join(notes_parts)

            return BrowserSnapshot(
                url=url,
                html=html,
                used_browser=True,
                final_url=final_url,
                notes=notes,
            )

    except Exception as e:
        return BrowserSnapshot(url=url, html="", used_browser=False, notes=f"Playwright navigation failed: {e}")
