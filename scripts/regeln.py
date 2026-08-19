"""Entscheidungen, die Mail, Kalender und Webseite gleich beantworten muessen.

Diese Datei gab es zuerst nicht, und das war ein Fehler: "zu pruefen" war an
drei Stellen verschieden definiert, weshalb die Mail 3 Faelle meldete und die
Pruefliste 7 enthielt. Wer zwei Zahlen fuer dieselbe Sache sieht, glaubt
keiner von beiden. Also steht die Regel jetzt einmal hier.
"""

# Was in der Anzeige aus der Einstufung wird.
#
#   frei         auf der Seite steht woertlich, dass es nichts kostet
#   spende       Hutkasse, Spendenbasis
#   vermutlich   die Seite sagt nichts zum Preis, oder die Einstufung ist
#                nicht belegt
#   kosten       ein Preis ist genannt
#
# Die Kategorie "vermutlich" ist eine bewusste Entscheidung gegen die
# vorsichtigere Variante: Frueher fielen diese Termine ganz aus der Mail. Das
# war zwar ehrlich, aber unbrauchbar — der Grossteil dessen, was in Freising
# ohne Preisangabe angekuendigt wird, ist tatsaechlich kostenlos, und wer eine
# Gratis-Uebersicht liest, will davon erfahren. Sie erscheinen deshalb, aber
# nie unter derselben Beschriftung wie ein belegter freier Eintritt.
FREI = "frei"
SPENDE = "spende"
VERMUTLICH = "vermutlich"
KOSTEN = "kosten"

BESCHRIFTUNG = {
    FREI: "Eintritt frei",
    SPENDE: "Spende erbeten",
    VERMUTLICH: "vermutlich kostenfrei",
    KOSTEN: "kostenpflichtig",
}

# Was in Mail und Kalender auftauchen darf.
IN_DIE_MAIL = (FREI, SPENDE, VERMUTLICH)


def anzeige(ev: dict) -> str:
    """Die eine Frage, die Mail, Kalender und Webseite gleich beantworten.

    Massgeblich ist der Beleg, nicht die Einstufung allein. "frei" ohne Zitat
    von der Seite ist eine Vermutung und wird auch so beschriftet — sonst
    stuende ueber einer geratenen Angabe dieselbe Zuversicht wie ueber einem
    zitierten "Eintritt frei".
    """
    if ev.get("manuell_bestaetigt"):
        # Von Hand geprueft: dann gilt, was dort steht, ohne Abschlag.
        return {"frei": FREI, "spende": SPENDE,
                "kostenpflichtig": KOSTEN}.get(ev.get("eintritt"), VERMUTLICH)

    if ev.get("eintritt") == "kostenpflichtig":
        return KOSTEN
    if ev.get("eintritt") in ("frei", "spende") and ev.get("eintritt_confidence") == "hoch":
        return FREI if ev.get("eintritt") == "frei" else SPENDE
    return VERMUTLICH


def zu_pruefen(ev: dict) -> bool:
    """Muss ein Mensch sich diesen Fall ansehen?

    Deckungsgleich mit `anzeige(ev) == VERMUTLICH`: Was als Vermutung in der
    Mail steht, ist genau das, was einen Blick auf die Veranstalterseite
    verdient. Zwei Begriffe fuer eine Menge waeren wieder der Anfang davon,
    dass beide auseinanderlaufen — deshalb ist das hier nur ein anderer Name.

    `kostenpflichtig` wird nie vorgelegt: Ist die Einstufung falsch, entgeht
    jemandem eine Gelegenheit. Aergerlich, aber kein gebrochenes Versprechen.
    Bei einem faelschlich freien Eintritt steht jemand vor der Kasse.
    """
    return anzeige(ev) == VERMUTLICH
