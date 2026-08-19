"""Entscheidungen, die Mail und Kalender gleich beantworten muessen.

Diese Datei gab es zuerst nicht, und das war ein Fehler: "zu pruefen" war an
drei Stellen verschieden definiert, weshalb die Mail 3 Faelle meldete und die
Pruefliste 7 enthielt. Wer zwei Zahlen fuer dieselbe Sache sieht, glaubt
keiner von beiden. Also steht die Regel jetzt einmal hier.
"""

# Werte, die in der Mail erscheinen duerfen. "unklar" gehoert nicht dazu:
# eine Mail mit dem Titel "Gratis in Freising" darf nichts auffuehren, von dem
# wir nicht wissen, ob es gratis ist.
IN_DIE_MAIL = ("frei", "spende")


def zu_pruefen(ev: dict) -> bool:
    """Muss ein Mensch sich diesen Fall ansehen?

    Massstab ist nicht die Vollstaendigkeit der Daten, sondern das Versprechen,
    das wir geben. Wir behaupten "kostenlos" — also muss geprueft werden, was
    diese Behauptung traegt, ohne belegt zu sein.

    Nicht geprueft wird deshalb `kostenpflichtig`: ist die Einstufung falsch,
    entgeht jemandem eine Gelegenheit. Aergerlich, aber kein gebrochenes
    Versprechen. Bei einem faelschlich freien Eintritt steht jemand vor der
    Kasse und wundert sich.
    """
    if ev.get("manuell_bestaetigt"):
        return False
    if ev.get("eintritt") == "unklar":
        return True
    return (ev.get("eintritt") in IN_DIE_MAIL
            and ev.get("eintritt_confidence") != "hoch")
