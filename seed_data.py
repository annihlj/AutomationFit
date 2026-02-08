"""
Seed-Script für Testdaten (Dimensionen 1 & 2)
"""
from extensions import db
from models.database import (
    QuestionnaireVersion, Dimension, Scale, ScaleOption, 
    Question, OptionScore
)


def seed_data():
    """Lädt Testdaten für Dimensionen 1 und 2"""
    
    print("🌱 Starte Seed-Vorgang...")
    
    # Prüfen ob bereits Daten vorhanden sind
    if QuestionnaireVersion.query.first():
        print("⚠️  Daten bereits vorhanden. Überspringe Seed.")
        return
    
    # ========================================
    # 1. Questionnaire Version
    # ========================================
    qv = QuestionnaireVersion(
        name="RPA/IPA Assessment Fragebogen",
        version="1.0",
        is_active=True
    )
    db.session.add(qv)
    db.session.flush()
    
    # ========================================
    # 2. Dimensionen
    # ========================================
    dim1 = Dimension(
        questionnaire_version_id=qv.id,
        code="1",
        name="Wirtschaftlich",
        sort_order=1,
        calc_method="economic"
    )
    
    dim2 = Dimension(
        questionnaire_version_id=qv.id,
        code="2",
        name="Organisatorisch",
        sort_order=2,
        calc_method="mean"
    )
    
    db.session.add_all([dim1, dim2])
    db.session.flush()
    
    # ========================================
    # 3. Skalen
    # ========================================
    
    # Likert 1-5
    scale_likert = Scale(key="likert_1_5", label="Likert-Skala 1-5")
    db.session.add(scale_likert)
    db.session.flush()
    
    for i in range(1, 6):
        option = ScaleOption(
            scale_id=scale_likert.id,
            code=str(i),
            label=f"Stufe {i}",
            sort_order=i,
            is_na=False
        )
        db.session.add(option)
    
    # Ja/Nein Skala
    scale_yesno = Scale(key="yes_no", label="Ja/Nein")
    db.session.add(scale_yesno)
    db.session.flush()
    
    opt_yes = ScaleOption(scale_id=scale_yesno.id, code="JA", label="Ja", sort_order=1)
    opt_no = ScaleOption(scale_id=scale_yesno.id, code="NEIN", label="Nein", sort_order=2)
    opt_na = ScaleOption(scale_id=scale_yesno.id, code="KA", label="Keine Angabe", sort_order=3, is_na=True)
    db.session.add_all([opt_yes, opt_no, opt_na])
    db.session.flush()
    
    # ========================================
    # 4. Fragen Dimension 1 (Wirtschaftlich)
    # ========================================
    
    q1_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.1",
        text="Anzahl der betroffenen Mitarbeiter (FTE)",
        question_type="number",
        unit="FTE",
        sort_order=1
    )
    
    q1_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.2",
        text="Durchschnittliche Bearbeitungszeit pro Fall (in Minuten)",
        question_type="number",
        unit="min",
        sort_order=2
    )
    
    q1_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.3",
        text="Geschätztes monatliches Volumen (Anzahl Fälle)",
        question_type="number",
        unit="Fälle",
        sort_order=3
    )
    
    db.session.add_all([q1_1, q1_2, q1_3])
    
    # ========================================
    # 5. Fragen Dimension 2 (Organisatorisch)
    # ========================================
    
    q2_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.1",
        text="Ist der Prozess standardisiert und dokumentiert?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=1
    )
    
    q2_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.2",
        text="Wie häufig ändert sich der Prozess?",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=2
    )
    
    q2_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.3",
        text="Wie hoch ist die Mitarbeiterakzeptanz für Automatisierung?",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=3
    )
    
    db.session.add_all([q2_1, q2_2, q2_3])
    db.session.flush()
    
    # ========================================
    # 6. Option Scores für Frage 2.1 (Ja/Nein)
    # ========================================
    
    # Frage 2.1: Ist der Prozess standardisiert?
    # Ja → gut für RPA (5) und mittel für IPA (3)
    score_2_1_yes_rpa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_yes.id,
        automation_type="RPA",
        score=5.0,
        is_exclusion=False,
        is_applicable=True
    )
    
    score_2_1_yes_ipa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_yes.id,
        automation_type="IPA",
        score=3.0,
        is_exclusion=False,
        is_applicable=True
    )
    
    # Nein → Ausschluss für RPA (A), aber gut für IPA (4)
    score_2_1_no_rpa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_no.id,
        automation_type="RPA",
        score=None,
        is_exclusion=True,  # A = Ausschluss
        is_applicable=True
    )
    
    score_2_1_no_ipa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_no.id,
        automation_type="IPA",
        score=4.0,
        is_exclusion=False,
        is_applicable=True
    )
    
    # Keine Angabe → nicht anwendbar
    score_2_1_na_rpa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_na.id,
        automation_type="RPA",
        score=None,
        is_exclusion=False,
        is_applicable=False  # - = nicht anwendbar
    )
    
    score_2_1_na_ipa = OptionScore(
        question_id=q2_1.id,
        scale_option_id=opt_na.id,
        automation_type="IPA",
        score=None,
        is_exclusion=False,
        is_applicable=False
    )
    
    db.session.add_all([
        score_2_1_yes_rpa, score_2_1_yes_ipa,
        score_2_1_no_rpa, score_2_1_no_ipa,
        score_2_1_na_rpa, score_2_1_na_ipa
    ])
    
    # ========================================
    # 7. Option Scores für Frage 2.2 (Likert)
    # ========================================
    
    # Frage 2.2: Wie häufig ändert sich der Prozess?
    # 1 = sehr häufig → schlecht für RPA, gut für IPA
    # 5 = sehr selten → gut für RPA, mittel für IPA
    
    likert_options = ScaleOption.query.filter_by(scale_id=scale_likert.id).order_by(ScaleOption.sort_order).all()
    
    # Mapping: Option 1-5 → RPA-Score (umgekehrt), IPA-Score (normal)
    rpa_scores = [1.0, 2.0, 3.0, 4.0, 5.0]
    ipa_scores = [5.0, 4.0, 3.0, 2.0, 2.0]
    
    for idx, option in enumerate(likert_options):
        # RPA Score
        db.session.add(OptionScore(
            question_id=q2_2.id,
            scale_option_id=option.id,
            automation_type="RPA",
            score=rpa_scores[idx],
            is_exclusion=False,
            is_applicable=True
        ))
        
        # IPA Score
        db.session.add(OptionScore(
            question_id=q2_2.id,
            scale_option_id=option.id,
            automation_type="IPA",
            score=ipa_scores[idx],
            is_exclusion=False,
            is_applicable=True
        ))
    
    # ========================================
    # 8. Option Scores für Frage 2.3 (Likert)
    # ========================================
    
    # Frage 2.3: Mitarbeiterakzeptanz
    # 1 = sehr niedrig → schlecht für beide
    # 5 = sehr hoch → gut für beide
    
    for idx, option in enumerate(likert_options):
        score = float(idx + 1)  # 1.0, 2.0, 3.0, 4.0, 5.0
        
        db.session.add(OptionScore(
            question_id=q2_3.id,
            scale_option_id=option.id,
            automation_type="RPA",
            score=score,
            is_exclusion=False,
            is_applicable=True
        ))
        
        db.session.add(OptionScore(
            question_id=q2_3.id,
            scale_option_id=option.id,
            automation_type="IPA",
            score=score,
            is_exclusion=False,
            is_applicable=True
        ))
    
    # ========================================
    # Commit
    # ========================================
    db.session.commit()
    print("✅ Testdaten erfolgreich geladen!")
    print(f"   - Fragebogen-Version: {qv.name} v{qv.version}")
    print(f"   - Dimensionen: {Dimension.query.count()}")
    print(f"   - Skalen: {Scale.query.count()}")
    print(f"   - Fragen: {Question.query.count()}")
    print(f"   - Option Scores: {OptionScore.query.count()}")
