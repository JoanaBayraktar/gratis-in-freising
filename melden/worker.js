/**
 * Nimmt Meldungen von der Übersichtsseite entgegen und legt daraus ein
 * GitHub-Issue an. Läuft als Cloudflare Worker — kostenlos, kein Server.
 *
 * Warum es diese Zwischenstelle überhaupt gibt: Die Übersichtsseite ist
 * statisch und liegt öffentlich auf GitHub Pages. Ein Token, mit dem sie
 * selbst ein Issue anlegen könnte, stünde damit im Quelltext und wäre für
 * jeden lesbar — wer ihn findet, kann in Ihr Repository schreiben. Der Token
 * liegt deshalb hier, wo ihn niemand sehen kann.
 *
 * Einrichtung steht in der README unter „Veranstaltungen melden".
 * Nötige Variablen (im Cloudflare-Dashboard als Secret hinterlegen):
 *
 *   GITHUB_TOKEN     Fine-grained Token, NUR dieses Repo, NUR Issues: Write
 *   GITHUB_REPO      z. B. JoanaBayraktar/gratis-in-freising
 *   ERLAUBTE_HERKUNFT  z. B. https://joanabayraktar.github.io
 *   TURNSTILE_SECRET   optional, siehe unten
 *
 * Der Token darf ausdrücklich nur Issues schreiben. Selbst wenn diese Adresse
 * jemand missbraucht, entstehen daraus Issues — nichts, was im Repository
 * landet, und nichts, was ohne Ihr Etikett `freigegeben` in den Kalender geht.
 */

const GRENZEN = { titel: 140, wann: 60, wo: 160, link: 300, beschreibung: 1200 };

function antwort(daten, status, herkunft) {
  return new Response(JSON.stringify(daten), {
    status,
    headers: {
      "Content-Type": "application/json; charset=utf-8",
      "Access-Control-Allow-Origin": herkunft,
      "Access-Control-Allow-Methods": "POST, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type",
      "Vary": "Origin",
    },
  });
}

/** Zeilenumbrüche und Steuerzeichen raus, Länge begrenzen.
 *  Der Text landet in einem Markdown-Dokument; ein `###` am Zeilenanfang
 *  würde dort eine Überschrift erzeugen und den Parser durcheinanderbringen. */
function saeubern(wert, grenze, mehrzeilig = false) {
  let text = String(wert ?? "").trim();
  text = text.replace(/[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g, "");
  if (!mehrzeilig) text = text.replace(/\s+/g, " ");
  text = text.replace(/^\s*#{1,6}\s/gm, "");
  text = text.replace(/^\s*---\s*$/gm, "—");
  return text.slice(0, grenze);
}

async function turnstileGeprueft(umgebung, token, ip) {
  if (!umgebung.TURNSTILE_SECRET) return true;   // nicht eingerichtet
  if (!token) return false;
  const koerper = new FormData();
  koerper.append("secret", umgebung.TURNSTILE_SECRET);
  koerper.append("response", token);
  if (ip) koerper.append("remoteip", ip);
  const pruefung = await fetch(
    "https://challenges.cloudflare.com/turnstile/v0/siteverify",
    { method: "POST", body: koerper });
  const ergebnis = await pruefung.json();
  return ergebnis.success === true;
}

export default {
  async fetch(anfrage, umgebung) {
    const erlaubt = umgebung.ERLAUBTE_HERKUNFT || "*";

    if (anfrage.method === "OPTIONS") return antwort({}, 204, erlaubt);
    if (anfrage.method !== "POST")
      return antwort({ fehler: "Nur POST." }, 405, erlaubt);

    // Der Browser schickt Origin mit. Fremde Seiten sollen dieses Formular
    // nicht als Versandstelle benutzen können.
    const herkunft = anfrage.headers.get("Origin");
    if (umgebung.ERLAUBTE_HERKUNFT && herkunft !== umgebung.ERLAUBTE_HERKUNFT)
      return antwort({ fehler: "Herkunft nicht erlaubt." }, 403, erlaubt);

    let eingabe;
    try {
      eingabe = await anfrage.json();
    } catch {
      return antwort({ fehler: "Kein gültiges JSON." }, 400, erlaubt);
    }

    // Honigtopf: ein Feld, das im Formular unsichtbar ist. Menschen füllen es
    // nie aus, einfache Bots füllen jedes Feld aus.
    if (saeubern(eingabe.webseite, 20)) return antwort({ ok: true }, 200, erlaubt);

    const ip = anfrage.headers.get("CF-Connecting-IP");
    if (!(await turnstileGeprueft(umgebung, eingabe.turnstile, ip)))
      return antwort({ fehler: "Prüfung fehlgeschlagen." }, 403, erlaubt);

    const titel = saeubern(eingabe.titel, GRENZEN.titel);
    const wann = saeubern(eingabe.wann, GRENZEN.wann);
    if (!titel || !wann)
      return antwort({ fehler: "Titel und Datum werden gebraucht." }, 400, erlaubt);

    let link = saeubern(eingabe.link, GRENZEN.link);
    if (link && !/^https?:\/\//i.test(link)) link = "";

    const koerper = [
      "### Titel", titel, "",
      "### Wann", wann, "",
      "### Wo", saeubern(eingabe.wo, GRENZEN.wo) || "_nicht angegeben_", "",
      "### Eintritt", saeubern(eingabe.eintritt, 40) || "weiß ich nicht", "",
      "### Link", link || "_keiner_", "",
      "### Beschreibung",
      saeubern(eingabe.beschreibung, GRENZEN.beschreibung, true) || "_keine_", "",
      // Genau diese Trennlinie sucht abschnitte() in scripts/meldungen.py,
      // um die Fussnote vom Inhalt zu trennen. Nicht verzieren.
      "---",
      "Über das Formular der Übersichtsseite eingegangen. Ungeprüft.",
      "Zum Übernehmen das Etikett `freigegeben` anhängen.",
    ].join("\n");

    const erstellt = await fetch(
      `https://api.github.com/repos/${umgebung.GITHUB_REPO}/issues`, {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${umgebung.GITHUB_TOKEN}`,
          "Accept": "application/vnd.github+json",
          "X-GitHub-Api-Version": "2022-11-28",
          "Content-Type": "application/json",
          "User-Agent": "gratis-in-freising-melder",
        },
        body: JSON.stringify({
          title: `Veranstaltung: ${titel}`.slice(0, 200),
          body: koerper,
          labels: ["meldung"],
        }),
      });

    if (!erstellt.ok) {
      // Die Antwort von GitHub bleibt hier — sie kann Hinweise auf die
      // Einrichtung enthalten, die niemanden draußen etwas angehen.
      console.error("GitHub", erstellt.status, await erstellt.text());
      return antwort({ fehler: "Konnte nicht gespeichert werden." }, 502, erlaubt);
    }

    const issue = await erstellt.json();
    return antwort({ ok: true, nummer: issue.number }, 200, erlaubt);
  },
};
