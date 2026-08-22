"""Wegwerf: Andere Wege zu den Beitraegen der fuenf betroffenen Accounts."""
import json, re, time
from playwright.sync_api import sync_playwright

TEST = ["genussgarten.freising", "schafhof_art_forum", "lindenkeller.freising"]

def sicher(fn, *a):
    try: return fn(*a)
    except Exception as e: return f"FEHLER {type(e).__name__}: {str(e)[:120]}"

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(locale="de-DE", viewport={"width":1280,"height":2400},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
    s = ctx.new_page()
    s.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
    s.wait_for_timeout(4000)
    print("Cookies nach Startseite:", sorted(c["name"] for c in ctx.cookies()))

    for name in TEST:
        print(f"\n{'='*60}\n{name}\n{'='*60}")

        # A) Profilseite MIT Cookies rendern
        def profil():
            r = s.goto(f"https://www.instagram.com/{name}/",
                       wait_until="domcontentloaded", timeout=45000)
            s.wait_for_timeout(6000)
            txt = re.sub(r"\s+", " ", s.inner_text("body")).strip()
            codes = s.evaluate("""() => [...new Set([...document.querySelectorAll('a[href*="/p/"]')]
                .map(a => (a.getAttribute('href').match(/\\/p\\/([^/]+)/)||[])[1]).filter(Boolean))]""")
            return (f"status={r.status if r else '—'} url={s.url[:70]} "
                    f"text={len(txt)}Z codes={codes[:6]}")
        print("A) Profilseite:", sicher(profil))

        # B) Beitrags-Einbettung (liefert Bildtext ohne Anmeldung)
        def einbettung(code):
            r = s.goto(f"https://www.instagram.com/p/{code}/embed/captioned/",
                       wait_until="domcontentloaded", timeout=45000)
            s.wait_for_timeout(2500)
            txt = re.sub(r"\s+", " ", s.inner_text("body")).strip()
            return f"status={r.status if r else '—'} text={len(txt)}Z >>> {txt[:200]}"
        print("B) Einbettung:", sicher(einbettung, "DcL7ISqDeLB"))
        time.sleep(3)
    b.close()
