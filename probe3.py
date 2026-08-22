"""Wegwerf: Alle sieben Wunsch-Accounts vom GitHub-Server aus abrufen."""
import json, re, time
from playwright.sync_api import sync_playwright

NAMEN = ["genussgarten.freising", "goldmarie.freising", "galerie_am_lindenkeller",
         "gasthof_lerner_", "cafebar_am_schlueter", "schafhof_art_forum",
         "lindenkeller.freising"]

HOLEN = """async (name) => {
    const r = await fetch(`/api/v1/users/web_profile_info/?username=${name}`,
                          {headers: {"X-IG-App-ID": "936619743392459"}});
    if (!r.ok) return {fehler: `HTTP ${r.status}`};
    const u = (await r.json()).data.user;
    return {beitraege: u.edge_owner_to_timeline_media.edges.map(e => ({
        datum: new Date(e.node.taken_at_timestamp*1000).toISOString().slice(0,10),
        text: (e.node.edge_media_to_caption.edges[0]||{node:{text:""}}).node.text,
        code: e.node.shortcode}))};
}"""

alles = {}
with sync_playwright() as p:
    browser = p.chromium.launch()
    ctx = browser.new_context(
        locale="de-DE", timezone_id="Europe/Berlin",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
    seite = ctx.new_page()
    try:
        seite.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print("Startseite:", type(e).__name__)
    seite.wait_for_timeout(3000)

    for name in NAMEN:
        e = seite.evaluate(HOLEN, name)
        if "fehler" in e:
            print(f"{name:26s} -> {e['fehler']}")
        else:
            b = e["beitraege"]
            alles[name] = b
            z = sum(len(x["text"]) for x in b)
            leer = sum(1 for x in b if not x["text"].strip())
            spanne = f"{b[-1]['datum']}..{b[0]['datum']}" if b else "—"
            print(f"{name:26s} -> OK {len(b):2d} Beitr. {z:5d} Z. {leer} leer  {spanne}")
        time.sleep(4)
    browser.close()

json.dump(alles, open("ig_roh.json", "w"), ensure_ascii=False, indent=1)
print(f"\n{len(alles)}/{len(NAMEN)} Accounts erreicht.")
