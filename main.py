from flask import Flask, render_template, request, redirect, url_for
import random
import datetime

app = Flask(__name__)

# --------------------------------------------
# Dummy-Daten für Kriterien
# --------------------------------------------
CRITERIA = [
    {"id": 1, "name": "Prozessstabilität", "weight": 0.25, "help": "Wie konstant läuft der Prozess ab?"},
    {"id": 2, "name": "Datenstrukturierung", "weight": 0.20, "help": "Sind die Eingabedaten strukturiert?"},
    {"id": 3, "name": "Fehleranfälligkeit", "weight": 0.15, "help": "Wie oft treten manuelle Fehler auf?"},
    {"id": 4, "name": "Ausnahmequote", "weight": 0.20, "help": "Wie häufig gibt es Sonderfälle?"},
    {"id": 5, "name": "Prozessvolumen", "weight": 0.20, "help": "Wie oft wird der Prozess monatlich ausgeführt?"},
]

# --------------------------------------------
# Route: Startseite / Fragebogen
# --------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', criteria=CRITERIA)

# --------------------------------------------
# Route: Bewertung auswerten
# --------------------------------------------
@app.route('/evaluate', methods=['POST'])
def evaluate():
    # Dummy-Auswertung – generiert zufällige Werte
    total_rpa = round(random.uniform(2.5, 4.5), 2)
    total_ipa = round(random.uniform(3.0, 5.0), 2)
    max_score = 5.0
    threshold = 0.25

    # Einfache Entscheidungslogik
    if total_ipa - total_rpa > threshold:
        recommendation = "IPA"
    elif total_rpa - total_ipa > threshold:
        recommendation = "RPA"
    else:
        recommendation = "Neutral / Weitere Analyse"

    # Dummy-Ergebnisaufbau
    result = {
        "recommendation": recommendation,
        "total_rpa": total_rpa,
        "total_ipa": total_ipa,
        "max_score": max_score,
        "threshold": threshold,
        "use_case": {
            "id": 1,
            "name": request.form.get("uc_name", "Unbekannter Anwendungsfall"),
            "industry": request.form.get("industry", "Nicht angegeben")
        },
        "run_id": "RUN-" + datetime.datetime.now().strftime("%H%M%S"),
        "breakdown": [
            {
                "name": c["name"],
                "weight": c["weight"],
                "score_rpa": round(random.uniform(2.0, 4.5), 2),
                "score_ipa": round(random.uniform(2.5, 5.0), 2),
                "comment": ""
            }
            for c in CRITERIA
        ]
    }

    return render_template('result.html', **result)

# --------------------------------------------
# Route: Export (Dummy)
# --------------------------------------------
@app.route('/export_result', methods=['POST'])
def export_result():
    # Hier würde ein CSV-/PDF-Export folgen
    print("Export requested for Use Case ID:", request.form.get("use_case_id"))
    return redirect(url_for('index'))

# --------------------------------------------
# App starten
# --------------------------------------------
if __name__ == '__main__':
    app.run(debug=True)


"""from flask import Flask, render_template, request, redirect, url_for
from models.database import db, UseCase, Criterion, Evaluation, Result
import os, random, datetime

app = Flask(__name__)

# --------------------------------------------
# Datenbank-Konfiguration
# --------------------------------------------
BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'decision_support.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiere Datenbank mit App
db.init_app(app)

# --------------------------------------------
# Hilfsfunktion: Tabellen erstellen
# --------------------------------------------
def init_database():
    
    with app.app_context():
        db.create_all()
        print("✅ Tabellen erfolgreich erstellt / geprüft.")


# --------------------------------------------
# Dummy-Daten (Kriterien) – können später aus DB kommen
# --------------------------------------------
CRITERIA = [
    {"id": 1, "name": "Prozessstabilität", "weight": 0.25},
    {"id": 2, "name": "Datenstrukturierung", "weight": 0.20},
    {"id": 3, "name": "Fehleranfälligkeit", "weight": 0.15},
    {"id": 4, "name": "Ausnahmequote", "weight": 0.20},
    {"id": 5, "name": "Prozessvolumen", "weight": 0.20},
]


# --------------------------------------------
# Route: Startseite / Fragebogen
# --------------------------------------------
@app.route('/')
def index():
    return render_template('index.html', criteria=CRITERIA)


# --------------------------------------------
# Route: Bewertung auswerten
# --------------------------------------------
@app.route('/evaluate', methods=['POST'])
def evaluate():
    uc_name = request.form.get('uc_name')
    uc_industry = request.form.get('industry')
    uc_desc = request.form.get('uc_desc')

    # 1️⃣ UseCase speichern
    new_case = UseCase(name=uc_name, description=uc_desc, industry=uc_industry)
    db.session.add(new_case)
    db.session.commit()

    # 2️⃣ Dummy-Scores generieren und speichern
    total_rpa = round(random.uniform(2.5, 4.5), 2)
    total_ipa = round(random.uniform(3.0, 5.0), 2)
    threshold = 0.25
    recommendation = (
        "IPA" if total_ipa - total_rpa > threshold
        else "RPA" if total_rpa - total_ipa > threshold
        else "Neutral"
    )

    # Einzelbewertungen als Evaluation speichern
    for c in CRITERIA:
        score = random.uniform(1, 5)
        ev = Evaluation(use_case_id=new_case.id, criterion_id=c["id"], score=score)
        db.session.add(ev)

    # 3️⃣ Ergebnis speichern
    res = Result(
        use_case_id=new_case.id,
        total_rpa=total_rpa,
        total_ipa=total_ipa,
        recommendation=recommendation
    )
    db.session.add(res)
    db.session.commit()

    # 4️⃣ Dummy-Resultseite anzeigen
    result = {
        "recommendation": recommendation,
        "total_rpa": total_rpa,
        "total_ipa": total_ipa,
        "max_score": 5.0,
        "threshold": threshold,
        "use_case": {"name": uc_name, "industry": uc_industry, "id": new_case.id},
        "run_id": "RUN-" + datetime.datetime.now().strftime("%H%M%S"),
        "breakdown": [
            {
                "name": c["name"],
                "weight": c["weight"],
                "score_rpa": round(random.uniform(2.0, 4.5), 2),
                "score_ipa": round(random.uniform(2.5, 5.0), 2),
                "comment": ""
            }
            for c in CRITERIA
        ]
    }

    return render_template('result.html', **result)


# --------------------------------------------
# Route: Export (Dummy)
# --------------------------------------------
@app.route('/export_result', methods=['POST'])
def export_result():
    use_case_id = request.form.get("use_case_id")
    result = Result.query.filter_by(use_case_id=use_case_id).first()
    print(f"Export requested for Use Case {use_case_id} – Empfehlung: {result.recommendation if result else 'n/a'}")
    return redirect(url_for('index'))


# --------------------------------------------
# Main – App starten
# --------------------------------------------
if __name__ == '__main__':
    init_database()
    app.run(debug=True)
"""