# AC3 Brettspiel-Assistent · Morris & Fanorona

**Den nächsten Zug planen, Mühlen bilden und Fanorona-Schlagketten berechnen:** Ein kostenloser Desktop-Assistent für Mühle und Fanorona in Assassin’s Creed III.

Du möchtest den Tavernen-Gegner bei Six, Nine oder Twelve Men’s Morris schlagen? Trage die Partie auf dem Brett nach und lass dir einen Zug einschließlich Schlagziel empfehlen. Der Assistent unterstützt dich beim Spielen und beim Verstehen taktischer Drohungen.

## Funktionen

- **6er-, 9er- und 12er-Mühle** mit passendem Brett und Steinzahl.
- **Zugempfehlungen** mit 1–60 Sekunden einstellbarer Rechenzeit.
- **Schlagempfehlungen direkt bei einer Mühle**, mit roter Markierung am Brett.
- Beide Seiten manuell spielen, Züge zurücknehmen und laufende Stellungen eintragen.
- Springen mit drei Steinen einstellbar; diagonale Mühlen für die 12er-Variante.
- Deutsche Oberfläche, Python-Standardbibliothek, keine zusätzlichen Python-Pakete.

## Start unter Windows

1. Dieses Repository über **Code → Download ZIP** herunterladen und entpacken.
2. Python 3.10 oder neuer mit **tkinter** installieren. Beim Windows-Installer Python zum PATH hinzufügen.
3. **Starten.bat** doppelt anklicken.

Alternativ:

```sh
python mainmenu.py
```

## Hauptmenü

Beim Start öffnet sich die Spielauswahl: **Mühle** oder **Fanorona**. Über
**← Hauptmenü** oder das Schließen des Spielfensters gelangst du zurück.
Beim Wechsel bleibt die aktuelle Partie erhalten; **Neues Spiel** setzt sie zurück.
**Beenden** im Hauptmenü schließt die Anwendung samt Spielfenstern.

## So verwendest du den Assistenten mit AC3

1. Oben die passende Mühle-Variante wählen. Ein Wechsel startet eine neue Partie.
2. Jeden tatsächlichen Zug aus AC3 auf dem Hilfsbrett nachtragen.
3. Wenn du am Zug bist, **Besten Zug berechnen** anklicken.
4. Den vorgeschlagenen Zug in AC3 ausführen und im Assistenten **Empfehlung übernehmen** drücken.
5. Bei einer Mühle auch den rot markierten gegnerischen Stein in AC3 entfernen und den Schlag im Assistenten übernehmen.

Beim Ziehen zuerst den eigenen Stein, dann das Zielfeld anklicken. Nach einer Mühle sind erlaubte Schlagziele rosa umrandet. Du kannst Weiß oder Schwarz spielen; die Empfehlungen gelten immer für die Seite, die im Assistenten am Zug ist.

### Laufende Partie übernehmen

**Stellung bearbeiten** einschalten, Brett mit Weiß/Schwarz/Feld leeren eintragen, verbleibenden Vorrat und Spieler am Zug wählen. Wenn nach einer Mühle noch geschlagen werden muss, **Am Zug muss noch einen Stein nehmen** aktivieren. Danach **Stellung anwenden** drücken.

## Fanorona

Im Hauptmenü **Fanorona öffnen** anklicken. Das eigene Fenster zeigt das
9×5-Brett mit 22 Steinen pro Seite. Weiß beginnt. Alternativ direkt starten:

```sh
python fanorona.py
```

- Eigenen Stein und dann ein freies verbundenes Nachbarfeld anklicken.
- **Schlagen ist Pflicht**, sobald irgendein eigener Stein schlagen kann.
- **Annäherung (A):** Die ununterbrochene gegnerische Reihe vor dem Zielfeld entfernen.
- **Rückzug (W):** Die gegnerische Reihe hinter dem Startfeld entfernen.
- Sind beide Arten möglich, über die beiden Schaltflächen eine auswählen.
  Es wird pro Schritt nur eine Seite geschlagen.
- Nach einem Schlag darf derselbe Stein weiterschlagen. Kein bereits in diesem
  Zug besuchtes Feld und keine Wiederholung der unmittelbar vorherigen Zugrichtung.
- Standardmäßig darf eine Schlagkette beendet werden. Falls deine Spielvariante
  die Fortsetzung erzwingt, **Schlagkette muss fortgesetzt werden** aktivieren.
- **Besten Zug / Schlagkette berechnen** zeigt die berechnete eigene Zugfolge samt
  Schlagart und betroffenen Feldern. Der nächste Schritt ist als Pfeil markiert;
  zu entfernende Steine sind rot mit einem Kreuz markiert.
- Empfehlungen **Schritt für Schritt** ins Spiel übertragen und übernehmen.
  Gegnerzüge genauso nachtragen; geschlagene Steine entfernt der Assistent automatisch.

Der Stellungseditor übernimmt Positionen **zu Beginn eines Zuges**. Eine bereits
laufende Schlagkette lässt sich nur durch Nachspielen ihrer Schritte korrekt
rekonstruieren; der Editor verwirft Kettenverlauf und Zugrichtung.
Gewonnen wird durch das Entfernen aller gegnerischen Steine; ein Spieler ohne
legalen Zug verliert ebenfalls. Wiederholungsremis werden in der Suche bewertet,
aber nicht automatisch in der Oberfläche durchgesetzt. Keine Vela-Sonderregeln.

Regelgrundlage: [ICGA – Rules of Fanorona](https://icga.org/icga/games/Fanorona/).
Die Fanorona-Suche bewertet komplette eigene Schlagketten, ist aber zeitlich
begrenzt und verwendet keine Endspieldatenbank. Auch hier gibt es keine Gewinngarantie.

## Wie stark ist die KI?

Die KI nutzt iterative Tiefensuche, Alpha-Beta-Suche und eine Stellungsbewertung. Längere Rechenzeit ermöglicht meist tiefere Suche. Das Programm kann taktische Gewinnzüge finden und hilft beim Kampf gegen AC3-Gegner. Es gibt **keine Garantie für einen Sieg oder perfekte Spielweise**: Es verwendet weder eine vollständige Lösung des Spiels noch Endspieldatenbanken. Ein Gewinn gegen AC3 ist bisher nicht durch einen reproduzierbaren Partie-Nachweis belegt.

Wiederholungen im Suchpfad werden als Remis bewertet. Die Oberfläche erzwingt keine vollständigen Wiederholungs- oder Zugzahl-Remisregeln. Der Assistent erkennt den Bildschirm nicht und steuert AC3 nicht automatisch. Abweichende Spielregeln müssen über die Einstellungen berücksichtigt werden.

## Tests

```sh
python -m unittest -v
```

Die Tests prüfen unter anderem Varianten, Mühlenschutz, Springen, taktische Gewinnzüge, Schlagempfehlungen und die GUI-Bedienung. GUI-Tests benötigen eine grafische Sitzung.

## English

A German-language Python desktop companion for Assassin’s Creed III Morris minigames. Supports Six, Nine and Twelve Men’s Morris plus 9×5 Fanorona with approach/withdrawal captures, capture chains, timed move search and position editing. Run `python mainmenu.py` with Python 3.10+ and tkinter. Moves must be entered manually; this is a heuristic assistant, not a solved-game engine or a guaranteed-win tool.

## Projektstatus

Frühe Version. Rückmeldungen mit Variante, Brettstellung, Vorrat, Spieler am Zug und Rechenzeit helfen bei der Verbesserung. Wenn du mit dem Assistenten gewinnst, teile gerne die Zugfolge als Issue – so lassen sich Erfolge nachvollziehen und analysieren.

Inoffizielles Fanprojekt; keine Verbindung zu Ubisoft. Assassin’s Creed ist eine Marke ihrer jeweiligen Rechteinhaber.
