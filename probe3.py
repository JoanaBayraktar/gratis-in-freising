"""Wegwerf: Was steht im Fehlerkoerper der 400er?"""
import json, time
from playwright.sync_api import sync_playwright

NAMEN = ["genussgarten.freising", "goldmarie.freising", "schafhof_art_forum",
         "gasthof_lerner_", "lindenkeller.freising"]

HOLEN = """async (name) => {
    const r = await fetch(`/api/v1/users/web_profile_info/?username=${name}`,
                          {headers: {"X-IG-App-ID": "936619743392459"}});
    const txt = await r.text();
    return {status: r.status, koerper: txt.slice(0, 400)};
}"""

# Zweiter Versuch ueber eine andere Schnittstelle: Nutzer-ID per Suche
SUCHE = """async (name) => {
    const r = await fetch(`/web/search/topsearch/?context=blended&query=${name}`,
                          {headers: {"X-IG-App-ID": "936619743392459"}});
    if (!r.ok) return `HTTP ${r.status}`;
    const j = await r.json();
    return (j.users||[]).slice(0,3).map(u =>
        `${u.user.username} (privat=${u.user.is_private}, verifiziert=${u.user.is_verified})`);
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(locale="de-DE",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
    s = ctx.new_page()
    s.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
    s.wait_for_timeout(3000)
    for n in NAMEN:
        e = s.evaluate(HOLEN, n)
        print(f"--- {n}: status={e['status']}")
        print(f"    koerper: {e['koerper'][:250]}")
        time.sleep(3)
        print(f"    suche:   {s.evaluate(SUCHE, n)}")
        time.sleep(4)
    b.close()
