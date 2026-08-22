"""Wegwerf: Kommt ein echtes Chromium von einer GitHub-IP an Instagram heran?"""
import re
from playwright.sync_api import sync_playwright

NAME = "lindenkeller_freising"

with sync_playwright() as p:
    browser = p.chromium.launch(args=["--disable-blink-features=AutomationControlled"])
    seite = browser.new_context(
        locale="de-DE", timezone_id="Europe/Berlin",
        viewport={"width": 1280, "height": 2000},
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"),
    ).new_page()

    antwort = seite.goto(f"https://www.instagram.com/{NAME}/",
                         wait_until="networkidle", timeout=60000)
    print(f"HTTP-Status der Seite: {antwort.status if antwort else '—'}")
    print(f"Endadresse:            {seite.url}")
    print(f"Titel:                 {seite.title()!r}")

    seite.wait_for_timeout(5000)
    text = seite.inner_text("body")
    text_kurz = re.sub(r"\s+", " ", text).strip()
    print(f"\nSichtbarer Text: {len(text_kurz)} Zeichen")
    print("  >>>", text_kurz[:600])

    for marke in ["Anmelden", "Log in", "Passwort", "Seite nicht verfügbar",
                  "etwas ist schiefgelaufen", "Beiträge", "Follower"]:
        if marke.lower() in text_kurz.lower():
            print(f"  gefunden: {marke!r}")

    # Zweiter Test: interner Abruf AUS dem Browser heraus (echte Cookies, echter Fingerabdruck)
    ergebnis = seite.evaluate("""async (name) => {
        try {
            const r = await fetch(
              `/api/v1/users/web_profile_info/?username=${name}`,
              {headers: {"X-IG-App-ID": "936619743392459"}});
            if (!r.ok) return `HTTP ${r.status}`;
            const j = await r.json();
            const m = j.data.user.edge_owner_to_timeline_media;
            return `OK — ${m.edges.length} Beitraege`;
        } catch (e) { return "Fehler: " + e.message; }
    }""", NAME)
    print(f"\nInterner Abruf aus dem Browser: {ergebnis}")

    seite.screenshot(path="profil.png", full_page=False)
    browser.close()
