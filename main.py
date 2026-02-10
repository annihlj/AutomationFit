"""
AutomationFit - Phase 2, 3 & 4 Implementierung
Umfasst:
- Phase 2: Partial Completion (Dimensionen optional)
- Phase 3: Filterlogik UI + Speicherung
- Phase 4: Korrekte Berechnung + Wirtschaftlichkeit
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify
import os

# Imports für Datenbank
from extensions import db
from models.database_v2 import (
    QuestionnaireVersion, Dimension, Question, ScaleOption,
    Process, Assessment, Answer, DimensionResult, TotalResult, OptionScore, Hint
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
        db.create_all()
        print("✅ Datenbank-Tabellen erstellt")
        seed_data()


# ============================================
# Hilfsfunktion: Filterlogik anwenden
# ============================================
def apply_filter_logic(assessment_id):
    """
    Phase 3: Filterlogik für Dimension 1 anwenden
    
    Prüft Frage 1.5 (Plattform vorhanden?):
    - Ja → alle Folgefragen anwendbar
    - Nein → Folgefragen nicht anwendbar, Ausschluss-Hint anzeigen
    """
    
    # Hole Frage 1.5 (Plattformverfügbarkeit)
    q15 = Question.query.filter_by(code="1.5").first()
    if not q15:
        return  # Frage nicht gefunden
    
    # Hole Antwort auf Frage 1.5
    answer_15 = Answer.query.filter_by(
        assessment_id=assessment_id,
        question_id=q15.id
    ).first()
    
    if not answer_15 or not answer_15.scale_option_id:
        return  # Keine Antwort
    
    # Hole Option
    option = db.session.get(ScaleOption, answer_15.scale_option_id)
    
    # Hole alle abhängigen Fragen
    dependent_questions = Question.query.filter_by(
        depends_on_question_id=q15.id
    ).all()
    
    if option.code == "NEIN":
        # NEIN gewählt → Folgefragen NICHT anwendbar
        print(f"   🔒 Filterlogik: Frage 1.5 = NEIN → {len(dependent_questions)} Folgefragen nicht anwendbar")
        
        for dep_q in dependent_questions:
            # Aktualisiere oder erstelle Answer mit is_applicable=False
            dep_answer = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=dep_q.id
            ).first()
            
            if dep_answer:
                dep_answer.is_applicable = False
                dep_answer.scale_option_id = None
                dep_answer.numeric_value = None
            else:
                # Erstelle neuen Answer-Eintrag
                dep_answer = Answer(
                    assessment_id=assessment_id,
                    question_id=dep_q.id,
                    is_applicable=False,
                    scale_option_id=None,
                    numeric_value=None
                )
                db.session.add(dep_answer)
    
    else:
        # JA gewählt → Folgefragen SIND anwendbar
        print(f"   ✅ Filterlogik: Frage 1.5 = JA → {len(dependent_questions)} Folgefragen anwendbar")
        
        for dep_q in dependent_questions:
            dep_answer = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=dep_q.id
            ).first()
            
            if dep_answer:
                dep_answer.is_applicable = True


# ============================================
# Hilfsfunktion: Dimension Status berechnen
# ============================================
def get_dimension_status(dimension_id, assessment_id=None):
    """
    Phase 2: Berechnet Status einer Dimension
    
    Returns:
        - 'not_started': Keine Frage beantwortet
        - 'partial': Einige Fragen beantwortet
        - 'complete': Alle Fragen beantwortet
    """
    
    questions = Question.query.filter_by(dimension_id=dimension_id).all()
    total_questions = len(questions)
    
    if total_questions == 0:
        return 'not_started'
    
    if not assessment_id:
        return 'not_started'
    
    # Zähle beantwortete Fragen
    answered_count = 0
    
    for question in questions:
        answer = Answer.query.filter_by(
            assessment_id=assessment_id,
            question_id=question.id,
            is_applicable=True
        ).first()
        
        if not answer:
            continue
        
        # Prüfe ob beantwortet
        if question.question_type == 'number':
            if answer.numeric_value is not None:
                answered_count += 1
        else:
            if answer.scale_option_id is not None:
                answered_count += 1
    
    if answered_count == 0:
        return 'not_started'
    elif answered_count == total_questions:
        return 'complete'
    else:
        return 'partial'


# ============================================
# Route: Startseite / Fragebogen
# ============================================
@app.route('/')
def index():
    """Zeigt den Fragebogen mit Fragen aus der Datenbank"""
    
    qv = QuestionnaireVersion.query.filter_by(is_active=True).first()
    
    if not qv:
        return "Keine aktive Fragebogen-Version gefunden.", 500
    
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
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
                'depends_on': question.depends_on_question_id,  # Phase 3
                'depends_on_option': question.depends_on_option_id,  # Phase 3
                'filter_description': question.filter_description  # Phase 3
            }
            
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
                
                # Phase 3: Hints für Optionen laden
                question_dict['hints'] = {}
                for opt in options:
                    hints = Hint.query.filter_by(
                        question_id=question.id,
                        scale_option_id=opt.id
                    ).all()
                    
                    if hints:
                        question_dict['hints'][opt.id] = [
                            {
                                'text': h.hint_text,
                                'type': h.hint_type,
                                'automation_type': h.automation_type
                            }
                            for h in hints
                        ]
            
            questions_data.append(question_dict)
        
        dimensions_data.append({
            'id': dimension.id,
            'code': dimension.code,
            'name': dimension.name,
            'calc_method': dimension.calc_method,  # Phase 4
            'questions': questions_data,
            'status': 'not_started'  # Phase 2: Wird im Template aktualisiert
        })
    
    return render_template('index_phase234.html', 
                         questionnaire=qv,
                         dimensions=dimensions_data)


# ============================================
# Route: Assessment bearbeiten
# ============================================
@app.route('/assessment/<int:assessment_id>/edit')
def edit_assessment(assessment_id):
    """Zeigt den Fragebogen mit vorausgefüllten Antworten"""
    
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    # Hole alle Antworten
    existing_answers = Answer.query.filter_by(
        assessment_id=assessment_id
    ).all()
    
    answers_by_question = {}
    for answer in existing_answers:
        if answer.question_id not in answers_by_question:
            answers_by_question[answer.question_id] = []
        answers_by_question[answer.question_id].append(answer)
    
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
                'answer': None,
                'is_applicable': True,  # Phase 3
                'depends_on': question.depends_on_question_id,
                'depends_on_option': question.depends_on_option_id,
                'filter_description': question.filter_description
            }
            
            question_answers = answers_by_question.get(question.id, [])
            
            # Phase 3: is_applicable Status
            if question_answers:
                question_dict['is_applicable'] = question_answers[0].is_applicable
            
            # Vorausfüllung
            if question.question_type == 'number':
                if question_answers and question_answers[0].numeric_value is not None:
                    question_dict['answer'] = question_answers[0].numeric_value
            
            elif question.question_type == 'single_choice':
                if question_answers and question_answers[0].scale_option_id is not None:
                    question_dict['answer'] = question_answers[0].scale_option_id
            
            elif question.question_type == 'multiple_choice':
                selected_ids = [a.scale_option_id for a in question_answers if a.scale_option_id is not None]
                question_dict['answer'] = selected_ids
            
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
                
                # Hints
                question_dict['hints'] = {}
                for opt in options:
                    hints = Hint.query.filter_by(
                        question_id=question.id,
                        scale_option_id=opt.id
                    ).all()
                    
                    if hints:
                        question_dict['hints'][opt.id] = [
                            {
                                'text': h.hint_text,
                                'type': h.hint_type,
                                'automation_type': h.automation_type
                            }
                            for h in hints
                        ]
            
            questions_data.append(question_dict)
        
        # Phase 2: Status berechnen
        status = get_dimension_status(dimension.id, assessment_id)
        
        dimensions_data.append({
            'id': dimension.id,
            'code': dimension.code,
            'name': dimension.name,
            'calc_method': dimension.calc_method,
            'questions': questions_data,
            'status': status  # Phase 2
        })
    
    process_data = {
        'name': process.name,
        'description': process.description,
        'industry': process.industry or ''
    }
    
    return render_template('index_phase234.html', 
                         questionnaire=qv,
                         dimensions=dimensions_data,
                         edit_mode=True,
                         assessment_id=assessment_id,
                         process_data=process_data)


# ============================================
# Route: Assessment aktualisieren
# ============================================
@app.route('/assessment/<int:assessment_id>/update', methods=['POST'])
def update_assessment(assessment_id):
    """Aktualisiert ein existierendes Assessment"""
    
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        process = db.session.get(Process, assessment.process_id)
        qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
        
        print(f"\n{'='*60}")
        print(f"UPDATE ASSESSMENT {assessment_id}")
        print(f"{'='*60}")
        
        # 1. Aktualisiere Process
        process.name = request.form.get('uc_name', process.name)
        process.description = request.form.get('uc_desc', process.description)
        process.industry = request.form.get('industry', process.industry)
        
        # 2. Lösche alte Antworten
        Answer.query.filter_by(assessment_id=assessment_id).delete()
        
        # 3. Speichere neue Antworten (wie /evaluate)
        all_questions = Question.query.filter_by(
            questionnaire_version_id=qv.id
        ).all()
        
        for question in all_questions:
            field_single = f"q_{question.id}"
            field_multi = f"q_{question.id}[]"
            
            if question.question_type == "single_choice":
                value = request.form.get(field_single)
                answer = Answer(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    scale_option_id=int(value) if value else None,
                    is_applicable=True
                )
                db.session.add(answer)
            
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
                else:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        scale_option_id=None,
                        is_applicable=True
                    )
                    db.session.add(answer)
            
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
                    except ValueError:
                        answer = Answer(
                            assessment_id=assessment.id,
                            question_id=question.id,
                            numeric_value=None,
                            is_applicable=True
                        )
                else:
                    answer = Answer(
                        assessment_id=assessment.id,
                        question_id=question.id,
                        numeric_value=None,
                        is_applicable=True
                    )
                db.session.add(answer)
        
        db.session.commit()
        
        # 4. Phase 3: Filterlogik anwenden
        apply_filter_logic(assessment_id)
        db.session.commit()
        
        # 5. Lösche alte Ergebnisse
        DimensionResult.query.filter_by(assessment_id=assessment_id).delete()
        TotalResult.query.filter_by(assessment_id=assessment_id).delete()
        db.session.commit()
        
        # 6. Phase 4: Berechne neue Ergebnisse
        total_result = ScoringService.calculate_assessment_results(assessment.id)
        
        return redirect(url_for('view_assessment', assessment_id=assessment_id))
    
    except Exception as e:
        db.session.rollback()
        print(f"❌ FEHLER: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Fehler: {str(e)}", 500


# ============================================
# Route: Bewertung auswerten
# ============================================
@app.route('/evaluate', methods=['POST'])
def evaluate():
    """
    Phase 2, 3, 4: Speichert Antworten mit Filterlogik und berechnet Ergebnisse
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
        
        # 3. Hole ALLE Fragen
        all_questions = Question.query.filter_by(
            questionnaire_version_id=qv.id
        ).all()
        
        print(f"\n{'='*60}")
        print(f"PHASE 2+3+4 - Submit für Assessment {assessment.id}")
        print(f"{'='*60}")
        print(f"📊 Gesamtanzahl Fragen: {len(all_questions)}")
        
        # 4. Speichere Antworten
        answered_count = 0
        unanswered_count = 0
        
        for question in all_questions:
            field_single = f"q_{question.id}"
            field_multi = f"q_{question.id}[]"
            
            if question.question_type == "single_choice":
                value = request.form.get(field_single)
                
                answer = Answer(
                    assessment_id=assessment.id,
                    question_id=question.id,
                    scale_option_id=int(value) if value else None,
                    is_applicable=True  # Phase 3: Wird durch Filter angepasst
                )
                db.session.add(answer)
                
                if value:
                    answered_count += 1
                else:
                    unanswered_count += 1
            
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
                    db.session.add(answer)
                    unanswered_count += 1
            
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
        
        print(f"\n📈 Antworten:")
        print(f"   ✅ Beantwortet: {answered_count}")
        print(f"   ⚠️  Unbeantworten: {unanswered_count}")
        
        # 5. Phase 3: Filterlogik anwenden
        apply_filter_logic(assessment.id)
        db.session.commit()
        
        # 6. Phase 4: Berechne Ergebnisse
        print("\n🔄 Starte Scoring (Phase 4)...")
        total_result = ScoringService.calculate_assessment_results(assessment.id)
        print("✅ Scoring abgeschlossen")
        
        print(f"{'='*60}\n")
        
        # 7. Redirect zur Ergebnisseite
        return redirect(url_for('view_assessment', assessment_id=assessment.id))
    
    except Exception as e:
        db.session.rollback()
        print(f"\n❌ FEHLER: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Fehler: {str(e)}", 500


# ============================================
# Route: Vergleichsübersicht
# ============================================
@app.route('/comparison')
def comparison():
    """Zeigt alle gespeicherten Assessments zum Vergleich"""
    
    results = db.session.query(
        TotalResult, Assessment, Process
    ).join(
        Assessment, TotalResult.assessment_id == Assessment.id
    ).join(
        Process, Assessment.process_id == Process.id
    ).all()
    
    assessments_data = []
    for total_result, assessment, process in results:
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
    
    assessments_data.sort(key=lambda x: x['combined_score'], reverse=True)
    
    return render_template('comparison.html', assessments=assessments_data)


# ============================================
# Route: Einzelnes Assessment anzeigen
# ============================================
@app.route('/assessment/<int:assessment_id>')
def view_assessment(assessment_id):
    """Zeigt ein spezifisches Assessment mit Details - Phase 2, 3, 4"""

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
            answers = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=question.id
            ).all()
            
            if not answers:
                continue
            
            # Phase 3: Nicht anwendbare Fragen anders behandeln
            if answers[0].is_applicable is False:
                # Zeige als "Nicht anwendbar"
                answers_detail.append({
                    "question_code": question.code,
                    "question_text": question.text,
                    "answer": "Nicht anwendbar",
                    "rpa_score": "–",
                    "ipa_score": "–",
                    "is_applicable": False
                })
                continue
            
            answer_text = ""
            rpa_score = None
            ipa_score = None

            if question.question_type == "number":
                a = answers[0]
                if a.numeric_value is None:
                    continue
                
                answer_text = f"{a.numeric_value} {question.unit or ''}".strip()
                rpa_score = "–"
                ipa_score = "–"

            elif question.question_type == "single_choice":
                a = answers[0]
                if not a.scale_option_id:
                    continue

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

            elif question.question_type == "multiple_choice":
                option_ids = [a.scale_option_id for a in answers if a.scale_option_id]
                if not option_ids:
                    continue

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
                "ipa_score": ipa_score,
                "is_applicable": True
            })

        # Phase 2: Dimension Status
        status = get_dimension_status(dimension.id, assessment_id)
        
        # Phase 4: Shared Dimensions (Dimension 1 und 7)
        is_shared = dimension.calc_method in ('filter', 'economic_score')

        breakdown.append({
            "name": dimension.name,
            "code": dimension.code,
            "calc_method": dimension.calc_method,  # Phase 4
            "is_shared": is_shared,  # Phase 4
            "status": status,  # Phase 2
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
        "assessment_id": assessment_id
    }

    return render_template("result.html", **result_data)


# ============================================
# App starten
# ============================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True)