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
 *   GITHUB_TOKEN     Fine-grained Token, NUR dieses Repo,
 *                    Issues: Write UND Contents: Read and write
 *   GITHUB_REPO      z. B. JoanaBayraktar/gratis-in-freising
 *   ERLAUBTE_HERKUNFT  z. B. https://joanabayraktar.github.io
 *   VERWALTUNG_PASSWORT  langes Zufallspasswort für den internen Bereich
 *   TURNSTILE_SECRET   optional, siehe unten
 *
 * Zwei Türen, mit sehr unterschiedlichem Schlüssel:
 *
 *   POST /             Meldeformular. Offen für jeden, erzeugt nur ein Issue.
 *                      Ohne Ihr Etikett `freigegeben` passiert damit nichts.
 *   POST /verwaltung   Interner Bereich. Braucht das Passwort und darf
 *                      GENAU EINE Datei schreiben: daten/verwaltung.json.
 *
 * Diese Beschränkung auf einen einzigen Pfad ist Absicht und steht weiter
 * unten hart im Code. Der Token kann inzwischen mehr als früher — er darf
 * Inhalte schreiben —, und wer das Passwort hat, spricht mit GitHub durch
 * diesen Worker hindurch. Er soll dabei nicht mehr anrichten können als
 * Unsinn in einer Datei, die der Sammellauf ohnehin nur liest. Kein Zugriff
 * auf Workflows, keine anderen Dateien, kein Löschen.
 *
 * Wählen Sie ein langes, zufälliges Passwort. Es ist das Einzige, was
 * zwischen dem Internet und dieser Datei steht.
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


/* ------------------------------------------------------------------ *
 *  Interner Bereich                                                    *
 * ------------------------------------------------------------------ */

// Der einzige Pfad, den dieser Worker jemals schreibt. Nicht parametrisieren.
const VERWALTUNGSPFAD = "daten/verwaltung.json";
const HOECHSTGROESSE = 1_000_000;   // 1 MB, grosszuegig fuer ein paar hundert Termine

/** Passwortvergleich ohne Zeitunterschied.
 *
 *  Ein gewoehnlicher Vergleich bricht beim ersten falschen Zeichen ab. Wer
 *  die Antwortzeit misst, kann das Passwort daran Zeichen fuer Zeichen
 *  erraten. Beide Seiten werden deshalb erst gehasht — das ergibt immer
 *  gleich lange Werte — und dann vollstaendig durchlaufen.
 */
async function passwortStimmt(eingabe, erwartet) {
  if (!erwartet) return false;
  const roh = new TextEncoder();
  const [a, b] = await Promise.all([
    crypto.subtle.digest("SHA-256", roh.encode(String(eingabe ?? ""))),
    crypto.subtle.digest("SHA-256", roh.encode(erwartet)),
  ]);
  const x = new Uint8Array(a), y = new Uint8Array(b);
  let unterschied = 0;
  for (let i = 0; i < x.length; i++) unterschied |= x[i] ^ y[i];
  return unterschied === 0;
}

/** Sieht der Inhalt aus wie eine Verwaltungsdatei?
 *
 *  Nicht als Schutz vor Ihnen gedacht, sondern gegen einen halb
 *  uebertragenen oder verunglueckten Stand: Was hier durchgeht, liest der
 *  naechtliche Lauf, und ein kaputter Aufbau soll nicht erst dort auffallen.
 */
function inhaltPlausibel(inhalt) {
  if (!inhalt || typeof inhalt !== "object" || Array.isArray(inhalt))
    return "Kein Objekt.";
  if (!Array.isArray(inhalt.eigene)) return "Feld `eigene` fehlt oder ist keine Liste.";
  for (const feld of ["korrekturen", "ausgeblendet"]) {
    const wert = inhalt[feld];
    if (!wert || typeof wert !== "object" || Array.isArray(wert))
      return `Feld \`${feld}\` fehlt oder ist kein Objekt.`;
  }
  for (const ev of inhalt.eigene) {
    if (!ev || typeof ev !== "object") return "Ein eigener Termin ist kein Objekt.";
    if (!ev.titel || !ev.beginn) return "Ein eigener Termin hat keinen Titel oder kein Datum.";
    if (!ev.id) return "Ein eigener Termin hat keine ID.";
  }
  return null;
}

async function github(umgebung, pfad, optionen = {}) {
  return fetch(`https://api.github.com/repos/${umgebung.GITHUB_REPO}${pfad}`, {
    ...optionen,
    headers: {
      "Authorization": `Bearer ${umgebung.GITHUB_TOKEN}`,
      "Accept": "application/vnd.github+json",
      "X-GitHub-Api-Version": "2022-11-28",
      "Content-Type": "application/json",
      "User-Agent": "gratis-in-freising-verwaltung",
      ...(optionen.headers || {}),
    },
  });
}

async function verwaltung(anfrage, umgebung, erlaubt) {
  let eingabe;
  try {
    eingabe = await anfrage.json();
  } catch {
    return antwort({ fehler: "Kein gültiges JSON." }, 400, erlaubt);
  }

  if (!(await passwortStimmt(eingabe.passwort, umgebung.VERWALTUNG_PASSWORT))) {
    // Bremse gegen das Durchprobieren. Eine halbe Sekunde faellt beim
    // Anmelden nicht auf und macht systematisches Raten unbezahlbar.
    await new Promise((weiter) => setTimeout(weiter, 500));
    return antwort({ fehler: "Passwort falsch." }, 401, erlaubt);
  }

  if (eingabe.aktion === "lesen") {
    const a = await github(umgebung, `/contents/${VERWALTUNGSPFAD}`);
    if (a.status === 404)
      return antwort({ ok: true, inhalt: null, sha: null }, 200, erlaubt);
    if (!a.ok) {
      console.error("GitHub lesen", a.status, await a.text());
      return antwort({ fehler: "Konnte nicht gelesen werden." }, 502, erlaubt);
    }
    const datei = await a.json();
    let inhalt = null;
    try {
      // atob liefert Bytes als Zeichen; für Umlaute muss über UTF-8 dekodiert werden.
      const roh = Uint8Array.from(atob(datei.content.replace(/\n/g, "")),
                                  (c) => c.charCodeAt(0));
      inhalt = JSON.parse(new TextDecoder().decode(roh));
    } catch (e) {
      return antwort({ fehler: "Datei im Repo ist unlesbar." }, 502, erlaubt);
    }
    return antwort({ ok: true, inhalt, sha: datei.sha }, 200, erlaubt);
  }

  if (eingabe.aktion === "schreiben") {
    const grund = inhaltPlausibel(eingabe.inhalt);
    if (grund) return antwort({ fehler: `Inhalt abgelehnt: ${grund}` }, 400, erlaubt);

    const text = JSON.stringify(eingabe.inhalt, null, 2) + "\n";
    if (text.length > HOECHSTGROESSE)
      return antwort({ fehler: "Zu groß." }, 413, erlaubt);

    const kodiert = btoa(String.fromCharCode(...new TextEncoder().encode(text)));
    const a = await github(umgebung, `/contents/${VERWALTUNGSPFAD}`, {
      method: "PUT",
      body: JSON.stringify({
        message: "Verwaltung: Änderung aus dem internen Bereich",
        content: kodiert,
        // Ohne sha wuerde GitHub eine fremde Aenderung stillschweigend
        // ueberschreiben. Mit sha kommt stattdessen ein 409, und die Seite
        // kann neu laden statt Arbeit zu verlieren.
        ...(eingabe.sha ? { sha: eingabe.sha } : {}),
      }),
    });
    if (a.status === 409 || a.status === 422)
      return antwort({ fehler: "veraltet" }, 409, erlaubt);
    if (!a.ok) {
      console.error("GitHub schreiben", a.status, await a.text());
      return antwort({ fehler: "Konnte nicht gespeichert werden." }, 502, erlaubt);
    }
    const erg = await a.json();
    return antwort({ ok: true, sha: erg.content.sha }, 200, erlaubt);
  }

  return antwort({ fehler: "Unbekannte Aktion." }, 400, erlaubt);
}

export default {
  async fetch(anfrage, umgebung) {
    const erlaubt = umgebung.ERLAUBTE_HERKUNFT || "*";

    if (anfrage.method === "OPTIONS") return antwort({}, 204, erlaubt);
    if (anfrage.method !== "POST")
      return antwort({ fehler: "Nur POST." }, 405, erlaubt);

    // Herkunftspruefung gilt fuer beide Tueren gleichermassen.
    const woher = anfrage.headers.get("Origin");
    if (umgebung.ERLAUBTE_HERKUNFT && woher !== umgebung.ERLAUBTE_HERKUNFT)
      return antwort({ fehler: "Herkunft nicht erlaubt." }, 403, erlaubt);

    if (new URL(anfrage.url).pathname.replace(/\/+$/, "") === "/verwaltung")
      return verwaltung(anfrage, umgebung, erlaubt);

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
