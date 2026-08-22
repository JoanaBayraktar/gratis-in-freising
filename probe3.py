"""Wegwerf: Beitragscodes fuer einen betroffenen Account finden."""
import json, time
from playwright.sync_api import sync_playwright

NAME = "genussgarten.freising"

JS = """async ({name}) => {
  const kopf = {"X-IG-App-ID": "936619743392459"};
  const hole = async (u) => {
    try { const r = await fetch(u, {headers: kopf});
          const t = await r.text();
          return {status: r.status, len: t.length, kopfstueck: t.slice(0,200), text: t}; }
    catch (e) { return {status: "EX", kopfstueck: e.message}; }
  };
  const aus = {};

  // 1) Nutzer-ID ueber die Suche
  const s = await hole(`/web/search/topsearch/?context=blended&query=${name}`);
  aus.suche = {status: s.status, kopfstueck: s.kopfstueck};
  let pk = null;
  try { const j = JSON.parse(s.text);
        const tr = (j.users||[]).find(u => u.user.username === name);
        if (tr) { pk = tr.user.pk; aus.gefunden = {pk, privat: tr.user.is_private,
                                                   voll: tr.user.full_name}; } } catch(e){}

  if (pk) {
    // 2) Mobile-Feed
    const f = await hole(`/api/v1/feed/user/${pk}/?count=12`);
    aus.feed = {status: f.status, len: f.len, kopfstueck: f.kopfstueck};
    try { const j = JSON.parse(f.text);
          aus.feed.codes = (j.items||[]).slice(0,12).map(i => i.code); } catch(e){}

    // 3) Alter GraphQL-Hash
    const g = await hole(`/graphql/query/?query_hash=e769aa130647d2354c40ea6a439bfc08`
                       + `&variables=${encodeURIComponent(JSON.stringify({id:String(pk),first:12}))}`);
    aus.graphql = {status: g.status, len: g.len, kopfstueck: g.kopfstueck};
    try { const j = JSON.parse(g.text);
          aus.graphql.codes = j.data.user.edge_owner_to_timeline_media.edges
                                .map(e => e.node.shortcode); } catch(e){}
  }
  return aus;
}"""

with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(locale="de-DE",
        user_agent=("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"))
    s = ctx.new_page()
    s.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=45000)
    s.wait_for_timeout(4000)
    try:
        print(json.dumps(s.evaluate(JS, {"name": NAME}), ensure_ascii=False, indent=1)[:2500])
    except Exception as e:
        print("FEHLER", type(e).__name__, str(e)[:300])
    b.close()
