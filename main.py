"""
AutomationFit - Phase 2, 3 & 4 Implementierung (KORRIGIERT)
Umfasst:
- Phase 2: Partial Completion (Dimensionen optional)
- Phase 3: Filterlogik UI + Speicherung (KORRIGIERT)
- Phase 4: Korrekte Berechnung + Wirtschaftlichkeit
"""

from flask import Flask, render_template, request, redirect, url_for, jsonify, Response
import os
import csv
from io import StringIO

# Imports für Datenbank
from extensions import db
from models.database import (
    QuestionnaireVersion, Dimension, Question, ScaleOption,
    Process, Assessment, Answer, DimensionResult, TotalResult, OptionScore, Hint, QuestionCondition,
    SharedDimensionAnswer, EconomicMetric
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

def build_answers_map(assessment_id: int):
    """
    Rückgabe:
      answers_map[qid] = {
        "numeric": float|None,
        "single": int|None,
        "multi": [int, ...]   # falls du multiple_choice als mehrere Answer-Zeilen speicherst
      }
    """
    rows = Answer.query.filter_by(assessment_id=assessment_id).all()
    answers_map = {}

    for a in rows:
        qid = a.question_id
        if qid not in answers_map:
            answers_map[qid] = {"numeric": None, "single": None, "multi": []}

        if a.numeric_value is not None:
            answers_map[qid]["numeric"] = a.numeric_value
        if a.scale_option_id is not None:
            # Wenn du multiple_choice als mehrere Answer-Datensätze pro Frage speicherst:
            answers_map[qid]["multi"].append(a.scale_option_id)
            # und als Single setzen wir den letzten Wert (für single_choice ok):
            answers_map[qid]["single"] = a.scale_option_id

    # multi deduplizieren
    for qid in answers_map:
        answers_map[qid]["multi"] = sorted(list(set(answers_map[qid]["multi"])))

    return answers_map


def build_hints_map(questionnaire_version_id: int):
    """
    Rückgabe:
      hints_map[qid][option_id] = [{"text": "...", "type": "info|warning|error"}, ...]
    """
    hints = (
        Hint.query
        .join(Question, Hint.question_id == Question.id)
        .filter(Question.questionnaire_version_id == questionnaire_version_id)
        .all()
    )

    hints_map = {}
    for h in hints:
        qid = h.question_id
        opt_id = h.scale_option_id  # kann None sein
        if qid not in hints_map:
            hints_map[qid] = {}
        if opt_id is None:
            continue
        hints_map[qid].setdefault(opt_id, []).append({
            "text": h.hint_text,
            "type": h.hint_type
        })
    return hints_map


# ============================================
# Gemeinsame Dimensionen - Hilfsfunktionen
# ============================================
def get_shared_dimension_ids():
    """Gibt die IDs der Dimensionen zurück, die gemeinsam gespeichert werden können (Dim 1 & 2)"""
    qv = QuestionnaireVersion.query.filter_by(is_active=True).first()
    if not qv:
        return []
    
    # Dimensionen 1 (Plattformverfügbarkeit) und 2 (Organisatorisch)
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).filter(
        Dimension.code.in_(['1', '2'])
    ).all()
    
    return [d.id for d in dimensions]


def load_shared_dimension_answers(dimension_id):
    """Lädt gemeinsame Antworten für eine Dimension"""
    shared_answers = SharedDimensionAnswer.query.filter_by(
        dimension_id=dimension_id
    ).all()
    
    answers_map = {}
    for sa in shared_answers:
        qid = sa.question_id
        if qid not in answers_map:
            answers_map[qid] = {"numeric": None, "single": None, "multi": []}
        
        if sa.numeric_value is not None:
            answers_map[qid]["numeric"] = sa.numeric_value
        if sa.scale_option_id is not None:
            answers_map[qid]["multi"].append(sa.scale_option_id)
            answers_map[qid]["single"] = sa.scale_option_id
    
    return answers_map


def save_shared_dimension_answers(dimension_id, answers_data):
    """
    Speichert Antworten einer Dimension als gemeinsame Antworten.
    answers_data ist ein dict: {question_id: {'numeric': ..., 'single': ..., 'multi': [...]}}
    """
    # Lösche alte gemeinsame Antworten für diese Dimension
    SharedDimensionAnswer.query.filter_by(dimension_id=dimension_id).delete()
    
    # Speichere neue gemeinsame Antworten
    for question_id, answer_info in answers_data.items():
        numeric_val = answer_info.get('numeric')
        single_val = answer_info.get('single')
        multi_vals = answer_info.get('multi', [])
        
        if numeric_val is not None:
            # Numerische Antwort
            shared_answer = SharedDimensionAnswer(
                dimension_id=dimension_id,
                question_id=question_id,
                numeric_value=numeric_val
            )
            db.session.add(shared_answer)
        elif single_val is not None:
            # Single-Choice Antwort
            shared_answer = SharedDimensionAnswer(
                dimension_id=dimension_id,
                question_id=question_id,
                scale_option_id=single_val
            )
            db.session.add(shared_answer)
        elif multi_vals:
            # Multiple-Choice: Speichere als einzelne Option (vereinfacht)
            for opt_id in multi_vals:
                shared_answer = SharedDimensionAnswer(
                    dimension_id=dimension_id,
                    question_id=question_id,
                    scale_option_id=opt_id
                )
                db.session.add(shared_answer)


def serialize_question(question: Question, answers_map: dict, hints_map: dict):
    # Options (falls scale_id vorhanden)
    options = []
    if question.scale_id:
        opts = (
            ScaleOption.query
            .filter_by(scale_id=question.scale_id)
            .order_by(ScaleOption.sort_order.asc())
            .all()
        )
        options = [{
            "id": o.id,
            "code": o.code,
            "label": o.label,
            "is_na": bool(o.is_na),
        } for o in opts]

    # Answer aus answers_map
    ans = answers_map.get(question.id, {"numeric": None, "single": None, "multi": []})

    if question.question_type == "number":
        answer_value = ans["numeric"]
    elif question.question_type == "multiple_choice":
        answer_value = ans["multi"]  # Liste
    else:
        answer_value = ans["single"]  # single_choice

    # Conditions (neu)
    conds = (
        QuestionCondition.query
        .filter_by(question_id=question.id)
        .order_by(QuestionCondition.sort_order.asc())
        .all()
    )
    conditions = [{"question_id": c.depends_on_question_id, "option_id": c.depends_on_option_id} for c in conds]

    # Legacy fallback (wenn keine QuestionCondition vorhanden)
    legacy_dep_q = question.depends_on_question_id
    legacy_dep_opt = question.depends_on_option_id
    if not conditions and legacy_dep_q and legacy_dep_opt:
        conditions = [{"question_id": legacy_dep_q, "option_id": legacy_dep_opt}]

    question_dict = {
        "id": question.id,
        "code": question.code,
        "text": question.text,
        # Template nutzt question.type -> wir liefern 'type'
        "type": question.question_type,
        "unit": question.unit,
        "sort_order": question.sort_order,

        "options": options,
        "answer": answer_value,

        # Hints: Template erwartet question.hints als dict[option_id] -> list
        "hints": hints_map.get(question.id, {}),

        # Multi-Condition Felder (neu)
        "depends_logic": getattr(question, "depends_logic", "all"),
        "conditions": conditions,

        # Legacy Felder (damit altes Template/JS nicht bricht)
        "depends_on": legacy_dep_q,
        "depends_on_option": legacy_dep_opt,
    }

    return question_dict


# ============================================
# Hilfsfunktion: Filterlogik anwenden (KORRIGIERT)
# ============================================
def apply_filter_logic(assessment_id):
    """
    KORRIGIERTE VERSION:
    Wendet die Filterlogik an und setzt is_applicable für alle Antworten basierend auf Bedingungen.
    
    Die Funktion:
    1. Lädt alle Fragen und Antworten für das Assessment
    2. Baut eine Map der beantworteten Optionen auf
    3. Evaluiert für jede Frage, ob sie anwendbar ist (basierend auf Bedingungen)
    4. Setzt das is_applicable Flag entsprechend
    5. Iteriert mehrfach, um Kaskaden-Abhängigkeiten zu behandeln
    """
    print(f"\n{'='*60}")
    print(f"🔍 FILTERLOGIK für Assessment {assessment_id}")
    print(f"{'='*60}")
    
    assessment = Assessment.query.get(assessment_id)
    if not assessment:
        print(f"❌ Assessment {assessment_id} nicht gefunden!")
        return

    # Alle Fragen für diese Questionnaire Version
    all_questions = Question.query.filter_by(
        questionnaire_version_id=assessment.questionnaire_version_id
    ).order_by(Question.dimension_id, Question.sort_order).all()

    print(f"📊 Anzahl Fragen: {len(all_questions)}")

    def get_conditions(q):
        """Liefert alle Bedingungen für eine Frage (neu + legacy)"""
        if q.conditions:
            return [(c.depends_on_question_id, c.depends_on_option_id) for c in q.conditions]
        if q.depends_on_question_id and q.depends_on_option_id:
            return [(q.depends_on_question_id, q.depends_on_option_id)]
        return []

    def build_answer_map():
        """
        Baut eine Map: question_id -> set(selected_option_ids)
        Nur für is_applicable=True Antworten
        """
        answers = Answer.query.filter_by(
            assessment_id=assessment_id,
            is_applicable=True
        ).all()
        
        answer_map = {}
        for ans in answers:
            qid = ans.question_id
            if qid not in answer_map:
                answer_map[qid] = set()
            
            if ans.scale_option_id is not None:
                answer_map[qid].add(ans.scale_option_id)
        
        return answer_map

    def evaluate_applicable(q, answer_map):
        """
        Prüft, ob eine Frage anwendbar ist basierend auf ihren Bedingungen
        """
        conds = get_conditions(q)
        
        # Keine Bedingungen = immer anwendbar
        if not conds:
            return True
        
        # Logik: "all" oder "any"
        logic = getattr(q, 'depends_logic', 'all').lower()
        
        # Prüfe jede Bedingung
        results = []
        for parent_q_id, required_opt_id in conds:
            # Wurde die erforderliche Option für die parent-Frage gewählt?
            is_met = required_opt_id in answer_map.get(parent_q_id, set())
            results.append(is_met)
        
        # Wende Logik an
        if logic == "any":
            return any(results)  # Mindestens eine Bedingung erfüllt
        else:  # "all"
            return all(results)  # Alle Bedingungen erfüllt

    # Iterative Anwendung (für Kaskaden-Abhängigkeiten)
    max_iterations = 10
    iteration = 0
    changes_made = True

    while changes_made and iteration < max_iterations:
        iteration += 1
        changes_made = False
        
        print(f"\n🔄 Iteration {iteration}")
        
        # Aktuelle Antwort-Map bauen
        answer_map = build_answer_map()
        
        # Für jede Frage prüfen
        for question in all_questions:
            # Ist die Frage anwendbar?
            should_be_applicable = evaluate_applicable(question, answer_map)
            
            # Hole alle Antworten für diese Frage
            answers = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=question.id
            ).all()
            
            # Update is_applicable wenn nötig
            for answer in answers:
                if answer.is_applicable != should_be_applicable:
                    print(f"  📝 Frage {question.code}: is_applicable {answer.is_applicable} -> {should_be_applicable}")
                    answer.is_applicable = should_be_applicable
                    changes_made = True
                    
                    # Wenn Frage nicht mehr anwendbar, lösche die Antwort-Werte
                    if not should_be_applicable:
                        answer.scale_option_id = None
                        answer.numeric_value = None
        
        if not changes_made:
            print(f"  ✅ Keine Änderungen in Iteration {iteration} - Filterlogik stabil")

    if iteration >= max_iterations:
        print(f"  ⚠️  Maximale Iterationen erreicht!")
    
    print(f"{'='*60}\n")


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
# Route: Startseite (Fragebogen)
# ============================================
@app.route('/')
def index():
    """Zeigt den Fragebogen an"""
    
    qv = QuestionnaireVersion.query.filter_by(is_active=True).first()
    if not qv:
        return "Keine aktive Fragebogen-Version gefunden", 500
    
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    hints_map = build_hints_map(qv.id)
    shared_dim_ids = get_shared_dimension_ids()
    
    # Für jede Dimension: Fragen laden
    for dim in dimensions:
        questions = Question.query.filter_by(
            dimension_id=dim.id
        ).order_by(Question.sort_order).all()
        
        # Lade gemeinsame Antworten für Dimensionen 1 & 2
        if dim.id in shared_dim_ids:
            answers_map = load_shared_dimension_answers(dim.id)
        else:
            answers_map = {}
        
        # Serialize Fragen in separates Attribut (nicht die SQLAlchemy relationship ändern)
        dim.serialized_questions = [serialize_question(q, answers_map, hints_map) for q in questions]
        
        # Markiere Dimension als "gemeinsam nutzbar"
        dim.is_shared = dim.id in shared_dim_ids
    
    return render_template(
        'index.html',
        questionnaire=qv,
        dimensions=dimensions,
        edit_mode=False
    )


# ============================================
# Route: Assessment bearbeiten
# ============================================
@app.route('/assessment/<int:assessment_id>/edit')
def edit_assessment(assessment_id):
    """Zeigt Fragebogen zum Bearbeiten eines Assessments"""
    
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    qv = db.session.get(QuestionnaireVersion, assessment.questionnaire_version_id)
    
    dimensions = Dimension.query.filter_by(
        questionnaire_version_id=qv.id
    ).order_by(Dimension.sort_order).all()
    
    # Answers laden
    answers_map = build_answers_map(assessment_id)
    hints_map = build_hints_map(qv.id)
    shared_dim_ids = get_shared_dimension_ids()
    
    # Für jede Dimension: Fragen laden
    for dim in dimensions:
        questions = Question.query.filter_by(
            dimension_id=dim.id
        ).order_by(Question.sort_order).all()
        
        dim.serialized_questions = [serialize_question(q, answers_map, hints_map) for q in questions]
        
        # Markiere Dimension als "gemeinsam nutzbar"
        dim.is_shared = dim.id in shared_dim_ids
    
    process_data = {
        "name": process.name,
        "description": process.description,
        "industry": process.industry
    }
    
    return render_template(
        'index.html',
        questionnaire=qv,
        dimensions=dimensions,
        edit_mode=True,
        process_data=process_data,
        assessment_id=assessment.id
    )

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
        
        # 3.5. Speichere gemeinsame Antworten für Dimensionen 1 & 2 wenn aktiviert
        use_shared_dims = request.form.get('use_shared_dimensions') == 'on'
        if use_shared_dims:
            print("\n💾 Speichere gemeinsame Dimensionen-Antworten...")
            shared_dim_ids = get_shared_dimension_ids()
            
            for dim_id in shared_dim_ids:
                # Sammle alle Antworten für diese Dimension
                dim_questions = Question.query.filter_by(dimension_id=dim_id).all()
                dim_answers = {}
                
                for q in dim_questions:
                    field_single = f"q_{q.id}"
                    field_multi = f"q_{q.id}[]"
                    
                    if q.question_type == "number":
                        value = request.form.get(field_single)
                        if value and value.strip():
                            try:
                                dim_answers[q.id] = {'numeric': float(value), 'single': None, 'multi': []}
                            except ValueError:
                                pass
                    elif q.question_type == "single_choice":
                        value = request.form.get(field_single)
                        if value:
                            dim_answers[q.id] = {'numeric': None, 'single': int(value), 'multi': []}
                    elif q.question_type == "multiple_choice":
                        values = request.form.getlist(field_multi)
                        if values:
                            dim_answers[q.id] = {'numeric': None, 'single': None, 'multi': [int(v) for v in values]}
                
                if dim_answers:
                    save_shared_dimension_answers(dim_id, dim_answers)
                    print(f"   ✅ Dimension {dim_id}: {len(dim_answers)} Antworten gespeichert")
            
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
        
        # 4.5. Speichere gemeinsame Antworten für Dimensionen 1 & 2 wenn aktiviert
        use_shared_dims = request.form.get('use_shared_dimensions') == 'on'
        if use_shared_dims:
            print("\n💾 Speichere gemeinsame Dimensionen-Antworten...")
            shared_dim_ids = get_shared_dimension_ids()
            
            for dim_id in shared_dim_ids:
                # Sammle alle Antworten für diese Dimension
                dim_questions = Question.query.filter_by(dimension_id=dim_id).all()
                dim_answers = {}
                
                for q in dim_questions:
                    field_single = f"q_{q.id}"
                    field_multi = f"q_{q.id}[]"
                    
                    if q.question_type == "number":
                        value = request.form.get(field_single)
                        if value and value.strip():
                            try:
                                dim_answers[q.id] = {'numeric': float(value), 'single': None, 'multi': []}
                            except ValueError:
                                pass
                    elif q.question_type == "single_choice":
                        value = request.form.get(field_single)
                        if value:
                            dim_answers[q.id] = {'numeric': None, 'single': int(value), 'multi': []}
                    elif q.question_type == "multiple_choice":
                        values = request.form.getlist(field_multi)
                        if values:
                            dim_answers[q.id] = {'numeric': None, 'single': None, 'multi': [int(v) for v in values]}
                
                if dim_answers:
                    save_shared_dimension_answers(dim_id, dim_answers)
                    print(f"   ✅ Dimension {dim_id}: {len(dim_answers)} Antworten gespeichert")
            
            db.session.commit()
        
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
            'combined_score': combined_score
        })
    
    return render_template('comparison.html', assessments=assessments_data)


# ============================================
# Route: Assessment anzeigen
# ============================================
@app.route('/assessment/<int:assessment_id>')
def view_assessment(assessment_id):
    """Zeigt Ergebnisse eines Assessments"""
    
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    
    # Gesamtergebnis
    total_result = TotalResult.query.filter_by(assessment_id=assessment_id).first()
    
    # Dimensionsergebnisse
    dim_results = db.session.query(
        DimensionResult, Dimension
    ).join(
        Dimension, DimensionResult.dimension_id == Dimension.id
    ).filter(
        DimensionResult.assessment_id == assessment_id
    ).order_by(
        Dimension.sort_order, DimensionResult.automation_type
    ).all()
    
    # Gruppiere Ergebnisse nach Dimension (pro Dimension gibt es RPA und IPA)
    dimensions_by_id = {}
    for dim_result, dimension in dim_results:
        if dimension.id not in dimensions_by_id:
            dimensions_by_id[dimension.id] = {
                'code': dimension.code,
                'name': dimension.name,
                'calc_method': dimension.calc_method,
                'is_shared': dimension.code in ['1', '2'],  # Dimensionen 1 & 2 sind gemeinsam
                'rpa_score': None,
                'ipa_score': None,
                'rpa_excluded': False,
                'ipa_excluded': False,
                'answers': []  # Wird später gefüllt
            }
        
        # Speichere Score basierend auf automation_type
        if dim_result.automation_type == "RPA":
            dimensions_by_id[dimension.id]['rpa_score'] = dim_result.mean_score
            dimensions_by_id[dimension.id]['rpa_excluded'] = dim_result.is_excluded
        elif dim_result.automation_type == "IPA":
            dimensions_by_id[dimension.id]['ipa_score'] = dim_result.mean_score
            dimensions_by_id[dimension.id]['ipa_excluded'] = dim_result.is_excluded
    
    # Lade Antworten für jede Dimension
    from models.database import Question, Answer, ScaleOption, OptionScore
    
    for dimension_id, dim_data in dimensions_by_id.items():
        # Hole alle Fragen für diese Dimension
        questions = Question.query.filter_by(dimension_id=dimension_id).order_by(Question.sort_order).all()
        
        for question in questions:
            # Hole ALLE Antworten für diese Frage (wichtig für Multiple Choice)
            answers = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=question.id
            ).all()
            
            if not answers:
                continue
            
            # Formatiere Antwort(en)
            answer_text = "Keine Antwort"
            all_option_ids = []
            
            if question.question_type == "number":
                # Numerische Frage - nur eine Antwort
                if answers[0].numeric_value is not None:
                    answer_text = f"{answers[0].numeric_value}"
                    if question.unit:
                        answer_text += f" {question.unit}"
                        
            elif question.question_type == "multiple_choice":
                # Multiple Choice - mehrere Antworten möglich
                selected_options = []
                for ans in answers:
                    if ans.scale_option_id:
                        option = ScaleOption.query.get(ans.scale_option_id)
                        if option:
                            selected_options.append(option.label)
                            all_option_ids.append(ans.scale_option_id)
                
                if selected_options:
                    answer_text = ", ".join(selected_options)
                    
            else:
                # Single Choice - nur eine Antwort
                if answers[0].scale_option_id:
                    option = ScaleOption.query.get(answers[0].scale_option_id)
                    if option:
                        answer_text = option.label
                        all_option_ids.append(answers[0].scale_option_id)
            
            # Hole Scores für diese Antwort(en)
            rpa_score_text = "–"
            ipa_score_text = "–"
            
            if all_option_ids:
                # Für Multiple Choice: Zeige den höchsten Score an
                if question.question_type == "multiple_choice":
                    # Hole alle OptionScores für die gewählten Optionen
                    rpa_scores_objs = OptionScore.query.filter(
                        OptionScore.question_id == question.id,
                        OptionScore.scale_option_id.in_(all_option_ids),
                        OptionScore.automation_type == "RPA"
                    ).all()
                    
                    ipa_scores_objs = OptionScore.query.filter(
                        OptionScore.question_id == question.id,
                        OptionScore.scale_option_id.in_(all_option_ids),
                        OptionScore.automation_type == "IPA"
                    ).all()
                    
                    # RPA: Prüfe auf Ausschluss, dann höchster Score
                    if any(s.is_exclusion for s in rpa_scores_objs):
                        rpa_score_text = "AUSSCHLUSS"
                    else:
                        applicable_rpa = [s.score for s in rpa_scores_objs if s.is_applicable and s.score is not None]
                        if applicable_rpa:
                            rpa_score_text = f"{max(applicable_rpa):.1f} (max)"
                    
                    # IPA: Prüfe auf Ausschluss, dann höchster Score
                    if any(s.is_exclusion for s in ipa_scores_objs):
                        ipa_score_text = "AUSSCHLUSS"
                    else:
                        applicable_ipa = [s.score for s in ipa_scores_objs if s.is_applicable and s.score is not None]
                        if applicable_ipa:
                            ipa_score_text = f"{max(applicable_ipa):.1f} (max)"
                
                else:
                    # Single Choice - wie bisher
                    option_id = all_option_ids[0]
                    
                    # RPA Score
                    rpa_score_obj = OptionScore.query.filter_by(
                        question_id=question.id,
                        scale_option_id=option_id,
                        automation_type="RPA"
                    ).first()
                    
                    if rpa_score_obj:
                        if rpa_score_obj.is_exclusion:
                            rpa_score_text = "AUSSCHLUSS"
                        elif not rpa_score_obj.is_applicable:
                            rpa_score_text = "N/A"
                        elif rpa_score_obj.score is not None:
                            rpa_score_text = f"{rpa_score_obj.score:.1f}"
                    
                    # IPA Score
                    ipa_score_obj = OptionScore.query.filter_by(
                        question_id=question.id,
                        scale_option_id=option_id,
                        automation_type="IPA"
                    ).first()
                    
                    if ipa_score_obj:
                        if ipa_score_obj.is_exclusion:
                            ipa_score_text = "AUSSCHLUSS"
                        elif not ipa_score_obj.is_applicable:
                            ipa_score_text = "N/A"
                        elif ipa_score_obj.score is not None:
                            ipa_score_text = f"{ipa_score_obj.score:.1f}"
            
            dim_data['answers'].append({
                'question_code': question.code,
                'question_text': question.text,
                'answer': answer_text,
                'is_applicable': answers[0].is_applicable,
                'rpa_score': rpa_score_text,
                'ipa_score': ipa_score_text
            })
    
    # Formatiere Dimensionsergebnisse (sortiert nach Sort-Order)
    dimensions_data = []
    for dim_result, dimension in dim_results:
        if dimension.id in dimensions_by_id:
            data = dimensions_by_id.pop(dimension.id)
            dimensions_data.append(data)
    
    # Berechne max_score basierend auf Anzahl der Dimensionen
    # Jede Dimension hat einen Score von 0-5, also max_score = Anzahl Dimensionen * 5
    num_dimensions = len(dimensions_data)
    max_score = num_dimensions * 5.0
    
    # Extrahiere Gesamtscores für einfacheren Template-Zugriff
    total_rpa = total_result.total_rpa if total_result else None
    total_ipa = total_result.total_ipa if total_result else None
    rpa_excluded = total_result.rpa_excluded if total_result else False
    ipa_excluded = total_result.ipa_excluded if total_result else False
    
    # Lade Economic Metrics
    economic_metrics_data = {}
    econ_metrics = EconomicMetric.query.filter_by(assessment_id=assessment_id).all()
    for metric in econ_metrics:
        economic_metrics_data[metric.key] = {
            'value': metric.value,
            'unit': metric.unit
        }
    
    return render_template(
        'result.html',
        use_case=process,
        assessment=assessment,
        assessment_id=assessment_id,  # WICHTIG: assessment_id für Edit-Button
        total_result=total_result,
        total_rpa=total_rpa,  # Für Template-Zugriff
        total_ipa=total_ipa,  # Für Template-Zugriff
        rpa_excluded=rpa_excluded,  # Für Template-Zugriff
        ipa_excluded=ipa_excluded,  # Für Template-Zugriff
        max_score=max_score,  # Für Balkendiagramme
        dimensions=dimensions_data,
        breakdown=dimensions_data,  # Für Dimensionsdetails-Dropdown
        economic_metrics=economic_metrics_data if economic_metrics_data else None,  # Wirtschaftlichkeit
        run_id=assessment_id,
        recommendation=total_result.recommendation if total_result else None,
        threshold=0.25  # Schwellenwert für Empfehlung
    )


# ============================================
# Route: Assessment löschen
# ============================================
@app.route('/assessment/<int:assessment_id>/delete', methods=['POST'])
def delete_assessment(assessment_id):
    """Löscht ein Assessment"""
    
    try:
        assessment = Assessment.query.get_or_404(assessment_id)
        process_id = assessment.process_id
        
        # Lösche Assessment (cascade löscht Antworten, Ergebnisse)
        db.session.delete(assessment)
        
        # Lösche Process wenn keine weiteren Assessments
        remaining = Assessment.query.filter_by(process_id=process_id).count()
        if remaining == 0:
            process = db.session.get(Process, process_id)
            if process:
                db.session.delete(process)
        
        db.session.commit()
        return redirect(url_for('comparison'))
    
    except Exception as e:
        db.session.rollback()
        return f"Fehler beim Löschen: {str(e)}", 500


# ============================================
# Route: CSV Export
# ============================================
@app.route('/assessment/<int:assessment_id>/export')
def export_assessment(assessment_id):
    """Exportiert Assessment als CSV"""
    
    assessment = Assessment.query.get_or_404(assessment_id)
    process = db.session.get(Process, assessment.process_id)
    total_result = TotalResult.query.filter_by(assessment_id=assessment_id).first()
    
    dim_results = db.session.query(
        DimensionResult, Dimension
    ).join(
        Dimension, DimensionResult.dimension_id == Dimension.id
    ).filter(
        DimensionResult.assessment_id == assessment_id
    ).order_by(
        Dimension.sort_order
    ).all()
    
    # CSV erstellen
    output = StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['Assessment Export'])
    writer.writerow(['Prozess', process.name])
    writer.writerow(['Branche', process.industry or '-'])
    writer.writerow(['Beschreibung', process.description or '-'])
    writer.writerow([])
    
    # Gesamtergebnis
    writer.writerow(['Gesamtergebnis'])
    writer.writerow(['Typ', 'Score', 'Status'])
    writer.writerow(['RPA', total_result.total_rpa or '-', 
                     'Ausgeschlossen' if total_result.rpa_excluded else 'Bewertet'])
    writer.writerow(['IPA', total_result.total_ipa or '-',
                     'Ausgeschlossen' if total_result.ipa_excluded else 'Bewertet'])
    writer.writerow([])
    
    # Dimensionsergebnisse
    writer.writerow(['Dimensionsergebnisse'])
    writer.writerow(['Code', 'Dimension', 'RPA Score', 'IPA Score'])
    
    # Gruppiere Dimensionsergebnisse nach Dimension
    dims_by_id = {}
    for dim_result, dimension in dim_results:
        if dimension.id not in dims_by_id:
            dims_by_id[dimension.id] = {
                'code': dimension.code,
                'name': dimension.name,
                'rpa': None,
                'ipa': None
            }
        if dim_result.automation_type == 'RPA':
            dims_by_id[dimension.id]['rpa'] = dim_result.mean_score
        elif dim_result.automation_type == 'IPA':
            dims_by_id[dimension.id]['ipa'] = dim_result.mean_score
    
    # Schreibe Zeilen
    for dim_id, dim_data in dims_by_id.items():
        writer.writerow([
            dim_data['code'],
            dim_data['name'],
            dim_data['rpa'] if dim_data['rpa'] is not None else '-',
            dim_data['ipa'] if dim_data['ipa'] is not None else '-'
        ])
    
    # Response
    output.seek(0)
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment; filename=assessment_{assessment_id}.csv'}
    )


# ============================================
# Main
# ============================================
if __name__ == '__main__':
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)