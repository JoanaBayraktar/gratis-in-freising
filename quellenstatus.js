/* Gemeinsam für öffentliche Übersicht und Verwaltung, ohne Bibliotheken. */
(() => {
  const host = document.querySelector("[data-quellenstatus]");
  if (!host) return;
  const esc = text => String(text ?? "").replace(/[&<>"']/g,
    c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const datum = wert => {
    if (!wert) return "noch nicht erfasst";
    const d = new Date(wert);
    if (Number.isNaN(d.getTime())) return "unbekannt";
    const mitZeit = wert.includes("T");
    return new Intl.DateTimeFormat("de-DE", { timeZone: "Europe/Berlin", day: "2-digit",
      month: "2-digit", year: "numeric", ...(mitZeit ? { hour: "2-digit", minute: "2-digit" } : {}) }).format(d);
  };
  const heute = new Intl.DateTimeFormat("sv-SE", { timeZone: "Europe/Berlin" }).format(new Date());
  const alter = tag => tag ? Math.round((Date.parse(heute) - Date.parse(tag.slice(0, 10))) / 86400000) : Infinity;
  function zustand(q) {
    if (!q.aktiv) return { text: "Pausiert", klasse: "qs-inaktiv", rang: 4 };
    if (q.fehlversuche > 0) return { text: "Abruf fehlgeschlagen", klasse: "qs-fehler", rang: 0 };
    if (!q.letzter_erfolg) return { text: "Noch nicht erfolgreich abgerufen", klasse: "qs-warnung", rang: 1 };
    if (alter(q.letzter_erfolg) > 3) return { text: "Nicht aktuell", klasse: "qs-warnung", rang: 1 };
    if (q.warnung) return { text: "Auffällig: keine Termine", klasse: "qs-warnung", rang: 1 };
    return { text: "Abruf erfolgreich", klasse: "qs-gut", rang: 3 };
  }
  function fehlerText(fehler) {
    if (!fehler) return "Der Abruf konnte nicht abgeschlossen werden.";
    if (/429|rate.?limit/i.test(fehler)) return "Anfragelimit erreicht (HTTP 429). Der Abruf oder die KI-Auswertung wurde begrenzt.";
    if (/401|403/.test(fehler)) return "Zugriff verweigert. Berechtigung oder Zugriffsschutz der Quelle prüfen.";
    if (/timeout|timed out/i.test(fehler)) return "Die Quelle oder KI hat nicht rechtzeitig geantwortet.";
    return "Der Abruf oder die Datenaufbereitung ist fehlgeschlagen. Details stehen im Sammelprotokoll auf GitHub.";
  }
  function link(url, name) {
    try {
      const u = new URL(url);
      if (!["https:", "http:"].includes(u.protocol)) throw new Error();
      return `<a href="${esc(u.href)}" target="_blank" rel="noopener noreferrer">${esc(name)}</a>`;
    } catch { return esc(name); }
  }
  async function laden() {
    host.innerHTML = '<summary>Quellenstatus · wird geladen …</summary>';
    try {
      const antwort = await fetch("daten/quellen-status.json", { cache: "no-cache" });
      if (!antwort.ok) throw new Error();
      const daten = await antwort.json();
      if (!daten || typeof daten !== "object" || Array.isArray(daten)) throw new Error();
      const quellen = Object.entries(daten).map(([name, q]) => {
        if (!q || typeof q !== "object" || !Array.isArray(q.verlauf)) throw new Error();
        return { ...q, name, zustand: zustand(q) };
      }).sort((a, b) => a.zustand.rang - b.zustand.rang || a.name.localeCompare(b.name, "de"));
      const aktive = quellen.filter(q => q.aktiv);
      const probleme = aktive.filter(q => q.zustand.rang < 3).length;
      host.dataset.probleme = String(probleme > 0);
      host.innerHTML = `<summary>Quellenstatus · ${aktive.length} aktiv${probleme ? ` · ${probleme} mit Hinweis` : " · keine aktuellen Abrufprobleme"}</summary>
        <p>Die Angaben zeigen die automatischen Abrufe, keine inhaltliche Prüfung.
        „Gefunden“ zählt Termine vor Filtern und dem Zusammenführen von Duplikaten, nicht nur neue oder kostenlose Termine.
        Ein erfolgreicher Abruf vor mehr als drei Tagen gilt als nicht aktuell.</p>
        ${quellen.length ? '<ul>' + quellen.map(q => {
          const anzahl = q.zuletzt_gefunden ?? q.verlauf.at(-1);
          return `<li><div class="qs-kopf"><strong>${link(q.url, q.name)}</strong>
            <span class="${q.zustand.klasse}">${q.zustand.text}</span></div>
            <div class="qs-meta"><span>Letzter Erfolg: ${datum(q.letzter_erfolg_um || q.letzter_erfolg)}</span>
            <span>Damals gefunden: ${Number.isInteger(anzahl) ? anzahl : "—"}</span>
            <span>Letzter Versuch: ${datum(q.letzter_versuch)}</span></div>
            ${q.aktiv && q.fehlversuche > 0 ? `<div class="qs-hinweis qs-fehler">${esc(fehlerText(q.letzter_fehler))} ${esc(q.fehlversuche)} Fehlversuche in Folge. Vorhandene Termine bleiben erhalten.</div>` : ""}
            ${q.aktiv && q.warnung ? `<div class="qs-hinweis qs-warnung">${esc(q.warnung)}</div>` : ""}</li>`;
        }).join("") + '</ul>' : '<p>Noch keine Quellen erfasst.</p>'}
        <p class="qs-actions"><a href="https://github.com/JoanaBayraktar/gratis-in-freising/actions/workflows/sammeln.yml" target="_blank" rel="noopener noreferrer">Sammelprotokolle auf GitHub</a></p>`;
    } catch {
      host.dataset.probleme = "true";
      host.innerHTML = '<summary>Quellenstatus · nicht verfügbar</summary><p>Der Quellenstatus konnte nicht geladen werden. Die Terminliste bleibt nutzbar.</p><button type="button">Erneut laden</button>';
      host.querySelector("button").addEventListener("click", laden);
    }
  }
  laden();
})();
