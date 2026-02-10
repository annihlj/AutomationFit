from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import csv
from io import StringIO

# Imports für Datenbank
from extensions import db
from models.database import (
    QuestionnaireVersion, Dimension, Question, ScaleOption,
    Process, Assessment, Answer, DimensionResult, TotalResult, OptionScore
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
            
            # Wenn Single-Choice oder Multiple-Choice, hole Optionen
            if question.question_type in ('single_choice', 'multiple_choice') and question.scale:
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
# ⭐ NEU: Route zum Bearbeiten eines Assessments
# ============================================
@app.route('/assessment/<int:assessment_id>/edit')
def edit_assessment(assessment_id):
    """Zeigt den Fragebogen mit vorausgefüllten Antworten zum Bearbeiten"""
    
    # Hole Assessment
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    
    # Hole alle Dimensionen
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    # Hole alle Antworten für dieses Assessment
    existing_answers = Answer.query.filter_by(
        assessment_id=assessment_id
    ).all()
    
    # Erstelle Lookup-Dictionary für schnellen Zugriff
    # Key: question_id → Value: Liste von Antworten (für multiple_choice)
    answers_by_question = {}
    for answer in existing_answers:
        if answer.question_id not in answers_by_question:
            answers_by_question[answer.question_id] = []
        answers_by_question[answer.question_id].append(answer)
    
    # Bereite Daten für Template vor
    dimensions_data = []
    
    for dimension in dimensions:
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
                'options': [],
                'answer': None  # ⭐ Vorausgefüllter Wert
            }
            
            # Hole existierende Antwort(en) für diese Frage
            question_answers = answers_by_question.get(question.id, [])
            
            # Setze Antwort basierend auf Fragetyp
            if question.question_type == 'number':
                if question_answers and question_answers[0].numeric_value is not None:
                    question_dict['answer'] = question_answers[0].numeric_value
            
            elif question.question_type == 'single_choice':
                if question_answers and question_answers[0].scale_option_id is not None:
                    question_dict['answer'] = question_answers[0].scale_option_id
            
            elif question.question_type == 'multiple_choice':
                # Liste aller gewählten Option-IDs
                selected_ids = [a.scale_option_id for a in question_answers if a.scale_option_id is not None]
                question_dict['answer'] = selected_ids
            
            # Hole Optionen für Auswahl-Fragen
            if question.question_type in ('single_choice', 'multiple_choice') and question.scale:
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
    
    # ⭐ Übergebe auch Process-Daten für Vorausfüllung
    process_data = {
        'name': process.name,
        'description': process.description,
        'industry': process.industry or ''
    }
    
    return render_template('index.html', 
                         questionnaire=qv,
                         dimensions=dimensions_data,
                         edit_mode=True,  # ⭐ Flag für Edit-Modus
                         assessment_id=assessment_id,
                         process_data=process_data)


# ============================================
# ⭐ NEU: Route zum Aktualisieren eines Assessments
# ============================================
@app.route('/assessment/<int:assessment_id>/update', methods=['POST'])
def update_assessment(assessment_id):
    """Aktualisiert ein existierendes Assessment mit neuen Antworten"""
    
    try:
        # Hole Assessment
        assessment = Assessment.query.get_or_404(assessment_id)
        process = db.session.get(Process, assessment.process_id)
        qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
        
        print(f"\n{'='*60}")
        print(f"UPDATE ASSESSMENT {assessment_id}")
        print(f"{'='*60}")
        
        # 1. Aktualisiere Process-Daten
        process.name = request.form.get('uc_name', process.name)
        process.description = request.form.get('uc_desc', process.description)
        process.industry = request.form.get('industry', process.industry)
        
        print(f"📝 Process aktualisiert: {process.name}")
        
        # 2. Lösche alte Antworten
        Answer.query.filter_by(assessment_id=assessment_id).delete()
        print(f"🗑️  Alte Antworten gelöscht")
        
        # 3. Speichere neue Antworten (wie bei /evaluate)
        all_questions = Question.query.filter_by(
            questionnaire_version_id=qv.id
        ).all()
        
        answered_count = 0
        unanswered_count = 0
        
        for question in all_questions:
            field_single = f"q_{question.id}"
            field_multi = f"q_{question.id}[]"
            
            # === SINGLE CHOICE ===
            if question.question_type == "single_choice":
                value = request.form.get(field_single)
                
                if value:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=int(value),
                        is_applicable=True
                    )
                    answered_count += 1
                else:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=None,
                        is_applicable=True
                    )
                    unanswered_count += 1
                
                db.session.add(answer)
            
            # === MULTIPLE CHOICE ===
            elif question.question_type == "multiple_choice":
                values = request.form.getlist(field_multi)
                
                if values:
                    for v in values:
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            scale_option_id=int(v),
                            is_applicable=True
                        )
                        db.session.add(answer)
                    answered_count += 1
                else:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=None,
                        is_applicable=True
                    )
                    unanswered_count += 1
                    db.session.add(answer)
            
            # === NUMBER ===
            elif question.question_type == "number":
                value = request.form.get(field_single)
                
                if value and value.strip():
                    try:
                        num = float(value)
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            numeric_value=num,
                            is_applicable=True
                        )
                        answered_count += 1
                    except ValueError:
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            numeric_value=None,
                            is_applicable=True
                        )
                        unanswered_count += 1
                else:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        numeric_value=None,
                        is_applicable=True
                    )
                    unanswered_count += 1
                
                db.session.add(answer)
        
        db.session.commit()
        
        print(f"✅ Neue Antworten gespeichert:")
        print(f"   - Beantwortet: {answered_count}")
        print(f"   - Unbeantworten: {unanswered_count}")
        
        # 4. Lösche alte Ergebnisse
        DimensionResult.query.filter_by(assessment_id=assessment_id).delete()
        TotalResult.query.filter_by(assessment_id=assessment_id).delete()
        print(f"🗑️  Alte Ergebnisse gelöscht")
        
        db.session.commit()
        
        # 5. Berechne neue Ergebnisse
        print("🔄 Starte Scoring-Service...")
        total_result = ScoringService.calculate_assessment_results(assessment.id)
        print("✅ Scoring abgeschlossen")
        
        print(f"{'='*60}\n")
        
        # 6. Redirect zur Ergebnisseite
        return redirect(url_for('view_assessment', assessment_id=assessment_id))
    
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ FEHLER beim Update: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Fehler beim Aktualisieren: {str(e)}", 500


# ============================================
# Route: Bewertung auswerten - PHASE 1 ROBUST
# ============================================
@app.route('/evaluate', methods=['POST'])
def evaluate():
    """
    Speichert Antworten und berechnet Ergebnisse - Phase 1 Version
    
    WICHTIG - Phase 1 Anforderungen:
    1. ✅ Speichert ALLE Fragen mit Answer-Einträgen
    2. ✅ Unbeantwortete Fragen: scale_option_id=NULL, numeric_value=NULL
    3. ✅ is_applicable=TRUE für alle Fragen (Phase 3 wird Filter implementieren)
    4. ✅ Robustes Error-Handling
    """
    
    try:
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
        if not qv:
            return "Keine aktive Fragebogen-Version gefunden", 500
            
        assessment = Assessment(
            process_id=process.id,
            questionnaire_version_id=qv.id
        )
        db.session.add(assessment)
        db.session.flush()
        
        # 3. Hole ALLE Fragen der aktiven Version
        all_questions = Question.query.filter_by(
            questionnaire_version_id=qv.id
        ).all()
        
        print(f"\n{'='*60}")
        print(f"PHASE 1 - Submit Processing für Assessment {assessment.id}")
        print(f"{'='*60}")
        print(f"📊 Gesamtanzahl Fragen: {len(all_questions)}")
        
        # 4. Speichere Antworten für ALLE Fragen
        answered_count = 0
        unanswered_count = 0
        
        for question in all_questions:
            field_single = f"q_{question.id}"
            field_multi = f"q_{question.id}[]"
            
            # === SINGLE CHOICE ===
            if question.question_type == "single_choice":
                value = request.form.get(field_single)
                
                if value:  # Beantwortet
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=int(value),
                        is_applicable=True  # Phase 1: immer TRUE
                    )
                    db.session.add(answer)
                    answered_count += 1
                else:  # Nicht beantwortet
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=None,  # NULL = unbeantworten
                        is_applicable=True  # Phase 1: immer TRUE
                    )
                    db.session.add(answer)
                    unanswered_count += 1
            
            # === MULTIPLE CHOICE ===
            elif question.question_type == "multiple_choice":
                values = request.form.getlist(field_multi)
                
                if values:  # Mindestens eine Option gewählt
                    for v in values:
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            scale_option_id=int(v),
                            is_applicable=True
                        )
                        db.session.add(answer)
                    answered_count += 1
                    print(f"✅ Q{question.id} ({question.code}): Beantwortet ({len(values)} Optionen)")
                else:  # Keine Option gewählt
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=None,
                        is_applicable=True
                    )
                    db.session.add(answer)
                    unanswered_count += 1
                    print(f"⚠️  Q{question.id} ({question.code}): NICHT beantwortet (NULL)")
            
            # === NUMBER ===
            elif question.question_type == "number":
                value = request.form.get(field_single)
                
                if value and value.strip():  # Wert eingegeben
                    try:
                        num = float(value)
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            numeric_value=num,
                            is_applicable=True
                        )
                        db.session.add(answer)
                        answered_count += 1
                        print(f"✅ Q{question.id} ({question.code}): Beantwortet ({num})")
                    except ValueError:
                        # Ungültiger Wert - als unbeantworten speichern
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            numeric_value=None,
                            is_applicable=True
                        )
                        db.session.add(answer)
                        unanswered_count += 1
                        print(f"⚠️  Q{question.id} ({question.code}): Ungültiger Wert '{value}' → NULL")
                else:  # Kein Wert
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        numeric_value=None,
                        is_applicable=True
                    )
                    db.session.add(answer)
                    unanswered_count += 1
                    print(f"⚠️  Q{question.id} ({question.code}): NICHT beantwortet (NULL)")
        
        # 5. Commit aller Antworten
        db.session.commit()
        
        print(f"\n📈 Zusammenfassung:")
        print(f"   ✅ Beantwortet: {answered_count}")
        print(f"   ⚠️  Unbeantworten: {unanswered_count}")
        print(f"   📝 Gesamt: {answered_count + unanswered_count}")
        print(f"{'='*60}\n")
        
        # 6. Berechne Ergebnisse
        print("🔄 Starte Scoring-Service...")
        total_result = ScoringService.calculate_assessment_results(assessment.id)
        print("✅ Scoring abgeschlossen")
        
        # 7. Hole wirtschaftliche Kennzahlen
        economic_metrics = ScoringService.get_economic_metrics(assessment.id)
        
        # 8. Bereite Daten für Ergebnisseite vor
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
            'run_id': f'ASS-{assessment.id}',
            'breakdown': breakdown,
            'economic_metrics': economic_metrics
        }
        
        return render_template('result.html', **result_data)
    
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ FEHLER beim Submit: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Fehler beim Speichern: {str(e)}", 500


# ============================================
# Route: Vergleichsübersicht
# ============================================
@app.route('/comparison')
def comparison():
    """Zeigt alle gespeicherten Assessments zum Vergleich"""
    
    # Hole alle TotalResults mit zugehörigen Assessments und Prozessen
    results = db.session.query(
        TotalResult, Assessment, Process
    ).join(
        Assessment, TotalResult.assessment_id == Assessment.id
    ).join(
        Process, Assessment.process_id == Process.id
    ).all()
    
    # Bereite Daten auf
    assessments_data = []
    for total_result, assessment, process in results:
        # Berechne einen Gesamtscore für Sortierung
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
    
    # Sortiere nach combined_score
    assessments_data.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return render_template('comparison.html', assessments=assessments_data)


# ============================================
# Route: Einzelnes Assessment anzeigen
# ============================================
@app.route('/assessment/<int:assessment_id>')
def view_assessment(assessment_id):
    """Zeigt ein spezifisches Assessment mit Details"""

    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    total_result = TotalResult.query.filter_by(assessment_id=assessment_id).first()

    if not total_result:
        return "Assessment wurde noch nicht ausgewertet", 404

    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()

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

        questions = Question.query.filter_by(dimension_id=dimension.id).order_by(Question.sort_order).all()
        answers_detail = []

        for question in questions:
            # Hole Answer-Eintrag für diese Frage
            answers = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=question.id
            ).all()
            
            # Überspringe nicht anwendbare oder komplett fehlende Antworten
            if not answers:
                continue
            
            # Prüfe ob Frage als "nicht anwendbar" markiert wurde
            if answers[0].is_applicable is False:
                continue
            
            answer_text = ""
            rpa_score = None
            ipa_score = None

            # === NUMBER ===
            if question.question_type == "number":
                a = answers[0]
                if a.numeric_value is None:
                    continue  # Unbeantworten, nicht anzeigen
                
                answer_text = f"{a.numeric_value} {question.unit or ''}".strip()
                rpa_score = "–"
                ipa_score = "–"

            # === SINGLE CHOICE ===
            elif question.question_type == "single_choice":
                a = answers[0]
                if not a.scale_option_id:
                    continue  # Unbeantworten, nicht anzeigen

                option = db.session.get(ScaleOption, a.scale_option_id)
                answer_text = option.label if option else ""

                score_rpa = OptionScore.query.filter_by(
                    question_id=question.id,
                    scale_option_id=a.scale_option_id,
                    automation_type="RPA"
                ).first()

                score_ipa = OptionScore.query.filter_by(
                    question_id=question.id,
                    scale_option_id=a.scale_option_id,
                    automation_type="IPA"
                ).first()

                def fmt(os):
                    if not os:
                        return None
                    if os.is_exclusion:
                        return "AUSSCHLUSS"
                    if not os.is_applicable:
                        return "N/A"
                    return os.score

                rpa_score = fmt(score_rpa)
                ipa_score = fmt(score_ipa)

            # === MULTIPLE CHOICE ===
            elif question.question_type == "multiple_choice":
                option_ids = [a.scale_option_id for a in answers if a.scale_option_id]
                if not option_ids:
                    continue  # Unbeantworten, nicht anzeigen

                options = [db.session.get(ScaleOption, oid) for oid in option_ids]
                labels = [o.label for o in options if o]
                answer_text = ", ".join(labels)

                scores_rpa = OptionScore.query.filter(
                    OptionScore.question_id == question.id,
                    OptionScore.automation_type == "RPA",
                    OptionScore.scale_option_id.in_(option_ids)
                ).all()

                scores_ipa = OptionScore.query.filter(
                    OptionScore.question_id == question.id,
                    OptionScore.automation_type == "IPA",
                    OptionScore.scale_option_id.in_(option_ids)
                ).all()

                def best_of(option_scores):
                    if not option_scores:
                        return None
                    if any(os.is_exclusion for os in option_scores):
                        return "AUSSCHLUSS"
                    applicable = [os.score for os in option_scores if os.is_applicable and os.score is not None]
                    if not applicable:
                        return "N/A"
                    return max(applicable)

                rpa_score = best_of(scores_rpa)
                ipa_score = best_of(scores_ipa)

            else:
                continue

            answers_detail.append({
                "question_code": question.code,
                "question_text": question.text,
                "answer": answer_text,
                "rpa_score": rpa_score,
                "ipa_score": ipa_score
            })

        breakdown.append({
            "name": dimension.name,
            "code": dimension.code,
            "score_rpa": dim_result_rpa.mean_score if dim_result_rpa and not dim_result_rpa.is_excluded else None,
            "score_ipa": dim_result_ipa.mean_score if dim_result_ipa and not dim_result_ipa.is_excluded else None,
            "excluded_rpa": dim_result_rpa.is_excluded if dim_result_rpa else False,
            "excluded_ipa": dim_result_ipa.is_excluded if dim_result_ipa else False,
            "answers": answers_detail
        })

    result_data = {
        "recommendation": total_result.recommendation,
        "total_rpa": total_result.total_rpa,
        "total_ipa": total_result.total_ipa,
        "rpa_excluded": total_result.rpa_excluded,
        "ipa_excluded": total_result.ipa_excluded,
        "max_score": 5.0,
        "threshold": 0.25,
        "use_case": {
            "id": process.id,
            "name": process.name,
            "industry": process.industry
        },
        "run_id": f"ASS-{assessment.id}",
        "breakdown": breakdown,
        "assessment_id": assessment_id  # ⭐ Für Edit-Button
    }

    return render_template("result.html", **result_data)


# ============================================
# Route: Ergebnis exportieren
# ============================================
@app.route('/export_result', methods=['POST'])
def export_result():
    """Exportiert Assessment-Ergebnisse als CSV"""
    assessment_id = request.form.get('assessment_id')
    
    if not assessment_id:
        return "Assessment ID erforderlich", 400
    
    try:
        assessment_id = int(assessment_id.replace('ASS-', ''))
    except (ValueError, AttributeError):
        return "Ungültige Assessment ID", 400
    
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    total_result = TotalResult.query.filter_by(assessment_id=assessment_id).first()
    
    if not total_result:
        return "Assessment wurde nicht gefunden", 404
    
    # Erstelle CSV-Datei
    output = StringIO()
    writer = csv.writer(output, delimiter=';')
    
    # Header
    writer.writerow(['AutomationFit Assessment Export'])
    writer.writerow([])
    writer.writerow(['Prozess-Name', process.name])
    writer.writerow(['Industrie', process.industry])
    writer.writerow(['Assessment ID', f'ASS-{assessment.id}'])
    writer.writerow(['Erstellt am', assessment.created_at.strftime('%d.%m.%Y %H:%M')] if assessment.created_at else ['Erstellt am', 'N/A'])
    writer.writerow([])
    writer.writerow(['Gesamtergebnisse'])
    writer.writerow(['RPA Score', total_result.total_rpa if total_result.total_rpa is not None else 'N/A'])
    writer.writerow(['IPA Score', total_result.total_ipa if total_result.total_ipa is not None else 'N/A'])
    writer.writerow(['Empfehlung', total_result.recommendation or 'N/A'])
    writer.writerow([])
    writer.writerow(['Dimensionen'])
    writer.writerow(['Dimension', 'RPA Score', 'IPA Score', 'RPA Ausgeschlossen', 'IPA Ausgeschlossen'])
    
    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
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
        
        rpa_score = dim_result_rpa.mean_score if dim_result_rpa and not dim_result_rpa.is_excluded else 'N/A'
        ipa_score = dim_result_ipa.mean_score if dim_result_ipa and not dim_result_ipa.is_excluded else 'N/A'
        rpa_excluded = 'Ja' if (dim_result_rpa and dim_result_rpa.is_excluded) else 'Nein'
        ipa_excluded = 'Ja' if (dim_result_ipa and dim_result_ipa.is_excluded) else 'Nein'
        
        writer.writerow([dimension.code, rpa_score, ipa_score, rpa_excluded, ipa_excluded])
    
    # Speichere in Variable und sende als Download
    csv_data = output.getvalue()
    output.close()
    
    # Erstelle Response mit CSV-Datei
    response = Response(csv_data, mimetype='text/csv')
    response.headers['Content-Disposition'] = f'attachment; filename="Assessment_ASS-{assessment.id}.csv"'
    
    return response


# ============================================
# App starten
# ============================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True)