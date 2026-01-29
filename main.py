from flask import Flask, render_template, request, redirect, url_for
import os

# Imports für Datenbank
from extensions import db
from models.database import (
    QuestionnaireVersion, Dimension, Question, ScaleOption,
    Process, Assessment, Answer, DimensionResult, TotalResult
)
from services.scoring_service import ScoringService
from seed_data import seed_data

# ============================================
# App-Konfiguration
# ============================================
app = Flask(__name__)

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
db_path = os.path.join(BASE_DIR, 'data', 'decision_support.db')
app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialisiere Datenbank
db.init_app(app)


# ============================================
# Hilfsfunktion: Datenbank initialisieren
# ============================================
def init_database():
    """Erstellt Tabellen und lädt Testdaten"""
    with app.app_context():
        # Erstelle Tabellen
        db.create_all()
        print("✅ Datenbank-Tabellen erstellt")
        
        # Lade Testdaten
        seed_data()


# ============================================
# Route: Startseite / Fragebogen
# ============================================
@app.route('/')
def index():
    """Zeigt den Fragebogen mit Fragen aus der Datenbank"""
    
    # Hole aktive Fragebogen-Version
    qv = QuestionnaireVersion.query.filter_by(is_active=True).first()
    
    if not qv:
        return "Keine aktive Fragebogen-Version gefunden. Bitte Datenbank initialisieren.", 500
    
    # Hole alle Dimensionen sortiert
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    # Bereite Daten für Template vor
    dimensions_data = []
    
    for dimension in dimensions:
        # Hole Fragen für diese Dimension
        questions = Question.query.filter_by(
            dimension_id=dimension.id
        ).order_by(Question.sort_order).all()
        
        questions_data = []
        for question in questions:
            question_dict = {
                'id': question.id,
                'code': question.code,
                'text': question.text,
                'type': question.question_type,
                'unit': question.unit,
                'options': []
            }
            
            # Wenn Single-Choice, hole Optionen
            if question.question_type == 'single_choice' and question.scale:
                options = ScaleOption.query.filter_by(
                    scale_id=question.scale_id
                ).order_by(ScaleOption.sort_order).all()
                
                question_dict['options'] = [
                    {
                        'id': opt.id,
                        'code': opt.code,
                        'label': opt.label,
                        'is_na': opt.is_na
                    }
                    for opt in options
                ]
            
            questions_data.append(question_dict)
        
        dimensions_data.append({
            'id': dimension.id,
            'code': dimension.code,
            'name': dimension.name,
            'questions': questions_data
        })
    
    return render_template('index.html', 
                         questionnaire=qv,
                         dimensions=dimensions_data)


# ============================================
# Route: Bewertung auswerten
# ============================================
@app.route('/evaluate', methods=['POST'])
def evaluate():
    """Speichert Antworten und berechnet Ergebnisse"""
    
    # 1. Erstelle Prozess
    process = Process(
        name=request.form.get('uc_name', 'Unbekannter Prozess'),
        description=request.form.get('uc_desc', ''),
        industry=request.form.get('industry', '')
    )
    db.session.add(process)
    db.session.flush()
    
    # 2. Erstelle Assessment
    qv = QuestionnaireVersion.query.filter_by(is_active=True).first()
    assessment = Assessment(
        process_id=process.id,
        questionnaire_version_id=qv.id
    )
    db.session.add(assessment)
    db.session.flush()
    
    # 3. Speichere Antworten
    for key, value in request.form.items():
        # Frage-IDs haben Format "q_<question_id>"
        if key.startswith('q_'):
            question_id = int(key.split('_')[1])
            question = Question.query.get(question_id)
            
            if not question:
                continue
            
            answer = Answer(
                assessment_id=assessment.id,
                question_id=question_id
            )
            
            if question.question_type == 'single_choice':
                # Value ist scale_option_id
                answer.scale_option_id = int(value)
            elif question.question_type == 'number':
                # Value ist numerischer Wert
                try:
                    answer.numeric_value = float(value)
                except ValueError:
                    continue
            
            db.session.add(answer)
    
    db.session.commit()
    
    # 4. Berechne Ergebnisse
    total_result = ScoringService.calculate_assessment_results(assessment.id)
    
    # 5. Bereite Daten für Ergebnisseite vor
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    breakdown = []
    for dimension in dimensions:
        dim_result_rpa = DimensionResult.query.filter_by(
            assessment_id=assessment.id,
            dimension_id=dimension.id,
            automation_type="RPA"
        ).first()
        
        dim_result_ipa = DimensionResult.query.filter_by(
            assessment_id=assessment.id,
            dimension_id=dimension.id,
            automation_type="IPA"
        ).first()
        
        breakdown.append({
            'name': dimension.name,
            'code': dimension.code,
            'score_rpa': dim_result_rpa.mean_score if dim_result_rpa and not dim_result_rpa.is_excluded else None,
            'score_ipa': dim_result_ipa.mean_score if dim_result_ipa and not dim_result_ipa.is_excluded else None,
            'excluded_rpa': dim_result_rpa.is_excluded if dim_result_rpa else False,
            'excluded_ipa': dim_result_ipa.is_excluded if dim_result_ipa else False
        })
    
    result_data = {
        'recommendation': total_result.recommendation,
        'total_rpa': total_result.total_rpa,
        'total_ipa': total_result.total_ipa,
        'rpa_excluded': total_result.rpa_excluded,
        'ipa_excluded': total_result.ipa_excluded,
        'max_score': 5.0,
        'threshold': 0.25,
        'use_case': {
            'id': process.id,
            'name': process.name,
            'industry': process.industry
        },
        'run_id': f"ASS-{assessment.id}",
        'breakdown': breakdown
    }
    
    return render_template('result.html', **result_data)


# ============================================
# Route: Export (Placeholder)
# ============================================
@app.route('/export_result', methods=['POST'])
def export_result():
    """Export-Funktion (noch zu implementieren)"""
    assessment_id = request.form.get("assessment_id")
    print(f"Export angefordert für Assessment {assessment_id}")
    return redirect(url_for('index'))


# ============================================
# App starten
# ============================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True)
