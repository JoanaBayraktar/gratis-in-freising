"""Wegwerf: Ist der Abruf aus dem Browser heraus stabil? Und was kommt inhaltlich an?"""
import re, time
from playwright.sync_api import sync_playwright

NAMEN = ["lindenkeller_freising", "uferlos_festival", "instagram"]

def lauf(nummer, browser):
    ctx = browser.new_context(
        locale="de-DE", timezone_id="Europe/Berlin",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
    seite = ctx.new_page()
    # Irgendeine Instagram-Adresse laden, nur damit Cookies gesetzt werden.
    try:
        seite.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
    except Exception as e:
        print(f"  Aufruf der Startseite: {type(e).__name__}")
    seite.wait_for_timeout(3000)
    kekse = {c["name"] for c in ctx.cookies()}
    print(f"Durchgang {nummer}: Cookies = {sorted(kekse)}")

    for name in NAMEN:
        ergebnis = seite.evaluate("""async (name) => {
            const r = await fetch(`/api/v1/users/web_profile_info/?username=${name}`,
                                  {headers: {"X-IG-App-ID": "936619743392459"}});
            if (!r.ok) return {fehler: `HTTP ${r.status}`};
            const j = await r.json();
            const u = j.data.user;
            return {beitraege: u.edge_owner_to_timeline_media.edges.map(e => ({
                datum: new Date(e.node.taken_at_timestamp*1000).toISOString().slice(0,10),
                text: (e.node.edge_media_to_caption.edges[0]||{node:{text:""}}).node.text,
                link: "https://instagram.com/p/" + e.node.shortcode }))};
        }""", name)
        if "fehler" in ergebnis:
            print(f"  {name:24s} -> {ergebnis['fehler']}")
            continue
        b = ergebnis["beitraege"]
        zeichen = sum(len(x["text"]) for x in b)
        print(f"  {name:24s} -> OK {len(b)} Beitraege, {zeichen} Zeichen Text")
        if nummer == 1 and name != "instagram":
            for x in b[:2]:
                print(f"        [{x['datum']}] {re.sub(chr(10),' / ',x['text'])[:150]}")
        time.sleep(2)
    ctx.close()

with sync_playwright() as p:
    browser = p.chromium.launch()
    for i in (1, 2, 3):
        lauf(i, browser)
        time.sleep(5)
    browser.close()
