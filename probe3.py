"""Wegwerf: Warum antworten fuenf Accounts mit 400? Existieren sie, sind sie privat?"""
import json, re, time, urllib.request, urllib.error

NAMEN = ["genussgarten.freising", "goldmarie.freising", "galerie_am_lindenkeller",
         "gasthof_lerner_", "cafebar_am_schlueter", "schafhof_art_forum",
         "lindenkeller.freising"]

# Instagram liefert Crawlern (Facebook, Google) Metadaten statt der App-Huelle.
BOT = {"User-Agent": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)"}

def metadaten(name):
    url = f"https://www.instagram.com/{name}/"
    try:
        with urllib.request.urlopen(urllib.request.Request(url, headers=BOT), timeout=25) as r:
            t = r.read().decode("utf-8", "replace")
            status = r.status
    except urllib.error.HTTPError as e:
        return f"HTTP {e.code}", "", ""
    except Exception as e:
        return type(e).__name__, "", ""
    titel = re.search(r'<meta property="og:title" content="([^"]*)"', t)
    besch = re.search(r'<meta property="og:description" content="([^"]*)"', t)
    return f"{status}", (titel.group(1) if titel else "—"), (besch.group(1) if besch else "—")

for n in NAMEN:
    st, titel, besch = metadaten(n)
    print(f"{n:26s} {st:8s} titel={titel[:60]!r}")
    print(f"{'':26s}          besch={besch[:150]!r}")
    time.sleep(3)
