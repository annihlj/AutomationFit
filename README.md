# RPA/IPA Entscheidungsunterstützungs-System

Ein Flask-basiertes Bewertungssystem zur Entscheidung zwischen RPA (Robotic Process Automation) und IPA (Intelligent Process Automation).

## 🎯 Features

- ✅ Datenbankgestütztes Fragebogen-System
- ✅ Dynamische Fragen aus 6 Dimensionen
- ✅ Separate RPA/IPA-Bewertung mit Ausschlusslogik
- ✅ Automatische Ergebnisberechnung
- ✅ Übersichtliche Ergebnisdarstellung

## 📋 Installation

1. **Python-Abhängigkeiten installieren:**
```bash
pip install -r requirements.txt
```

2. **Datenbank initialisieren und Testdaten laden:**
```bash
python main.py
```

Die Datenbank wird automatisch beim ersten Start erstellt und mit Testdaten für die Dimensionen 1 (Wirtschaftlich) und 2 (Organisatorisch) befüllt.

## 🚀 Verwendung

1. **Anwendung starten:**
```bash
python main.py
```

2. **Im Browser öffnen:**
```
http://127.0.0.1:5000
```

3. **Fragebogen ausfüllen:**
   - Prozessinformationen eingeben
   - Fragen aus den Dimensionen beantworten
   - Auf "Bewertung berechnen" klicken

4. **Ergebnisse ansehen:**
   - Gesamtscores für RPA und IPA
   - Detaillierte Dimensionsergebnisse
   - Automatische Empfehlung

## 📊 Datenbankstruktur

Das System verwendet folgende Haupttabellen:

### Fragebogen-Definition
- `questionnaire_version` - Fragebogen-Versionen
- `dimension` - Bewertungsdimensionen (1-6)
- `question` - Fragen mit Typen (single_choice, number)
- `scale` & `scale_option` - Antwortskalen
- `option_score` - RPA/IPA-Bewertungen pro Option

### Ausfüllung
- `process` - Zu bewertende Prozesse
- `assessment` - Bewertungssitzungen
- `answer` - Gespeicherte Antworten

### Ergebnisse
- `dimension_result` - Scores pro Dimension
- `total_result` - Gesamtergebnisse mit Empfehlung

## 🔧 Testdaten

Aktuell sind Testdaten für folgende Dimensionen verfügbar:

### Dimension 1: Wirtschaftlich
- Anzahl betroffener Mitarbeiter (FTE)
- Durchschnittliche Bearbeitungszeit
- Monatliches Volumen

### Dimension 2: Organisatorisch
- Prozess standardisiert? (Ja/Nein)
- Häufigkeit von Prozessänderungen (Likert 1-5)
- Mitarbeiterakzeptanz (Likert 1-5)

## 💡 Bewertungslogik

### Scoring
- **Likert-Skala:** 1-5 (je nach Frage unterschiedliche Bedeutung)
- **Ausschluss:** Wert "A" führt zum Ausschluss des Automation-Typs
- **Nicht anwendbar:** Wert "-" wird nicht in Berechnung einbezogen

### Berechnung
1. Pro Dimension: Mittelwert aller anwendbaren Scores
2. Ausschlusslogik: Bei Ausschlusswert wird Dimension markiert
3. Gesamtscore: Durchschnitt aller Dimensionen
4. Empfehlung: Basierend auf Differenz und Schwellenwert (0.25)

## 📁 Projektstruktur

```
Prototyp/
├── main.py                    # Haupt-Flask-Anwendung
├── extensions.py              # SQLAlchemy-Instanz
├── seed_data.py              # Testdaten-Script
├── requirements.txt           # Python-Abhängigkeiten
├── models/
│   └── database.py           # Datenbank-Modelle
├── services/
│   └── scoring_service.py    # Berechnungslogik
├── templates/
│   ├── index.html            # Fragebogen
│   └── result.html           # Ergebnisseite
├── static/
│   └── css/
│       └── style.css         # Styling
└── data/
    └── decision_support.db   # SQLite-Datenbank (wird erstellt)
```

## 🔄 Weitere Dimensionen hinzufügen

Um weitere Dimensionen (3-6) hinzuzufügen, bearbeiten Sie `seed_data.py`:

1. Dimension erstellen
2. Fragen definieren
3. Skalen zuweisen
4. Option-Scores für RPA/IPA festlegen

## 📝 Lizenz

Bachelorarbeit-Prototyp - Nur für akademische Zwecke
