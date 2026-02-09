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
            question = db.session.get(Question, question_id)
            
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
    
    # 5. Hole wirtschaftliche Kennzahlen
    economic_metrics = ScoringService.get_economic_metrics(assessment.id)
    
    # 6. Bereite Daten für Ergebnisseite vor
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
        'breakdown': breakdown,
        'economic_metrics': economic_metrics  # Neu!
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
# Route: Vergleich aller Assessments
# ============================================
@app.route('/comparison')
def comparison():
    """Zeigt alle bisherigen Assessments sortiert nach Score"""
    
    # Hole alle Total-Results mit ihren Assessments
    results = db.session.query(TotalResult, Assessment, Process).join(
        Assessment, TotalResult.assessment_id == Assessment.id
    ).join(
        Process, Assessment.process_id == Process.id
    ).all()
    
    # Bereite Daten auf
    assessments_data = []
    for total_result, assessment, process in results:
        # Berechne einen Gesamtscore für Sortierung
        # Priorität: Beide verfügbar > Einer verfügbar > Keiner verfügbar
        if total_result.total_rpa and total_result.total_ipa:
            combined_score = max(total_result.total_rpa, total_result.total_ipa)
        elif total_result.total_rpa:
            combined_score = total_result.total_rpa
        elif total_result.total_ipa:
            combined_score = total_result.total_ipa
        else:
            combined_score = 0
        
        assessments_data.append({
            'id': assessment.id,
            'process_name': process.name,
            'industry': process.industry,
            'created_at': assessment.created_at,
            'total_rpa': total_result.total_rpa,
            'total_ipa': total_result.total_ipa,
            'rpa_excluded': total_result.rpa_excluded,
            'ipa_excluded': total_result.ipa_excluded,
            'recommendation': total_result.recommendation,
            'combined_score': combined_score
        })
    
    # Sortiere nach combined_score (höchste zuerst)
    assessments_data.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return render_template('comparison.html', assessments=assessments_data)


# ============================================
# Route: Einzelnes Assessment anzeigen
# ============================================
@app.route('/assessment/<int:assessment_id>')
def view_assessment(assessment_id):
    """Zeigt ein spezifisches Assessment mit Details"""
    
    # Hole Assessment
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    total_result = TotalResult.query.filter_by(assessment_id=assessment_id).first()
    
    if not total_result:
        return "Assessment wurde noch nicht ausgewertet", 404
    
    # Hole Dimensionen
    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    # Bereite detaillierte Breakdown-Daten vor
    breakdown = []
    for dimension in dimensions:
        dim_result_rpa = DimensionResult.query.filter_by(
            assessment_id=assessment_id,
            dimension_id=dimension.id,
            automation_type="RPA"
        ).first()
        
        dim_result_ipa = DimensionResult.query.filter_by(
            assessment_id=assessment_id,
            dimension_id=dimension.id,
            automation_type="IPA"
        ).first()
        
        # Hole alle Antworten für diese Dimension mit Details
        questions = Question.query.filter_by(dimension_id=dimension.id).all()
        answers_detail = []
        
        for question in questions:
            answer = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=question.id
            ).first()
            
            if answer:
                answer_text = ""
                rpa_score = None
                ipa_score = None
                
                if question.question_type == 'single_choice' and answer.scale_option_id:
                    option = db.session.get(ScaleOption, answer.scale_option_id)
                    answer_text = option.label
                    
                    # Hole Scores
                    from models.database import OptionScore
                    score_rpa = OptionScore.query.filter_by(
                        question_id=question.id,
                        scale_option_id=option.id,
                        automation_type="RPA"
                    ).first()
                    
                    score_ipa = OptionScore.query.filter_by(
                        question_id=question.id,
                        scale_option_id=option.id,
                        automation_type="IPA"
                    ).first()
                    
                    if score_rpa:
                        if score_rpa.is_exclusion:
                            rpa_score = "AUSSCHLUSS"
                        elif not score_rpa.is_applicable:
                            rpa_score = "N/A"
                        else:
                            rpa_score = score_rpa.score
                    
                    if score_ipa:
                        if score_ipa.is_exclusion:
                            ipa_score = "AUSSCHLUSS"
                        elif not score_ipa.is_applicable:
                            ipa_score = "N/A"
                        else:
                            ipa_score = score_ipa.score
                
                elif question.question_type == 'number' and answer.numeric_value:
                    answer_text = f"{answer.numeric_value} {question.unit or ''}"
                    rpa_score = "–"
                    ipa_score = "–"
                
                answers_detail.append({
                    'question_code': question.code,
                    'question_text': question.text,
                    'answer': answer_text,
                    'rpa_score': rpa_score,
                    'ipa_score': ipa_score
                })
        
        breakdown.append({
            'name': dimension.name,
            'code': dimension.code,
            'score_rpa': dim_result_rpa.mean_score if dim_result_rpa and not dim_result_rpa.is_excluded else None,
            'score_ipa': dim_result_ipa.mean_score if dim_result_ipa and not dim_result_ipa.is_excluded else None,
            'excluded_rpa': dim_result_rpa.is_excluded if dim_result_rpa else False,
            'excluded_ipa': dim_result_ipa.is_excluded if dim_result_ipa else False,
            'answers': answers_detail
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
# App starten
# ============================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True)
