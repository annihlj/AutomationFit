"""
Seed-Script für Testdaten (Dimensionen 1 & 2)
"""
from extensions import db
from models.database import (
    QuestionnaireVersion, Dimension, Scale, ScaleOption, 
    Question, OptionScore, Hint, QuestionCondition
)

    # ========================================
# Helper für Filter-/Ausschluss-Scoring
# ========================================

def upsert_option_score(question_id, option_id, automation_type, score, is_exclusion, is_applicable):
    existing = OptionScore.query.filter_by(
        question_id=question_id,
        scale_option_id=option_id,
        automation_type=automation_type
    ).one_or_none()

    if existing:
        existing.score = score
        existing.is_exclusion = is_exclusion
        existing.is_applicable = is_applicable
    else:
        db.session.add(OptionScore(
            question_id=question_id,
            scale_option_id=option_id,
            automation_type=automation_type,
            score=score,
            is_exclusion=is_exclusion,
            is_applicable=is_applicable
        ))

def add_filter_scores(question_id, options, automation_types=("RPA", "IPA")):
    for opt in options:
        for auto_type in automation_types:
            upsert_option_score(question_id, opt.id, auto_type, None, False, False)

def add_exclusion(question_id, option_id, automation_types=("RPA", "IPA")):
    for auto_type in automation_types:
        upsert_option_score(question_id, option_id, auto_type, None, True, True)
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
        name="Plattformverfügbarkeit und Umsetzungsreife",
        sort_order=1,
        calc_method="filter"
    )
    dim2 = Dimension(
        questionnaire_version_id=qv.id,
        code="2",
        name="Organisatorisch",
        sort_order=2,
        calc_method="mean"
    )

    dim3 = Dimension(
        questionnaire_version_id=qv.id,
        code="3",
        name="Prozess",
        sort_order=3,
        calc_method="mean"
    )
    dim4 = Dimension(
        questionnaire_version_id=qv.id,
        code="4",
        name="Daten",
        sort_order=4,
        calc_method="mean"
    )    
    dim5 = Dimension(
        questionnaire_version_id=qv.id,
        code="5",
        name="Technologisch",
        sort_order=5,
        calc_method="mean"
    )
    dim6 = Dimension(
        questionnaire_version_id=qv.id,
        code="6",
        name="Risiko",
        sort_order=6,
        calc_method="mean"
    )
    dim7 = Dimension(
        questionnaire_version_id=qv.id,
        code="7",
        name="Wirtschaftlich",
        sort_order=7,
        calc_method="economic_score" 
    )

    
    db.session.add_all([dim1, dim2, dim3, dim4, dim5, dim6, dim7])
    db.session.flush()

    
    
    # ========================================
    # 3. Skalen
    # ========================================
    
    # Likert 1-5
    scale_likert = Scale(key="likert_1_5", label="Likert-Skala 1-5")
    db.session.add(scale_likert)
    db.session.flush()

    opt_a1 = ScaleOption(scale_id=scale_likert.id, code="1", label="trifft gar nicht zu", sort_order=1)
    opt_a2 = ScaleOption(scale_id=scale_likert.id, code="2", label="trifft eher nicht zu", sort_order=2)
    opt_a3 = ScaleOption(scale_id=scale_likert.id, code="3", label="teils / teils", sort_order=3)
    opt_a4 = ScaleOption(scale_id=scale_likert.id, code="4", label="trifft eher zu", sort_order=4)
    opt_a5 = ScaleOption(scale_id=scale_likert.id, code="5", label="trifft voll zu", sort_order=5)
    opt_a_na = ScaleOption(scale_id=scale_likert.id, code="KA", label="Keine Angabe", sort_order=6, is_na=True)

    db.session.add_all([opt_a1, opt_a2, opt_a3, opt_a4, opt_a5, opt_a_na])
    db.session.flush()


    scale_strategy = Scale(key="strategy", label="Strategie")
    db.session.add(scale_strategy)
    db.session.flush()

    opt_rpa = ScaleOption(scale_id=scale_strategy.id, code="RPA", label="RPA", sort_order=1)
    opt_ipa = ScaleOption(scale_id=scale_strategy.id, code="IPA", label="IPA", sort_order=2)
    opt_ki = ScaleOption(scale_id=scale_strategy.id, code="KI", label="KI", sort_order=3)
    opt_none = ScaleOption(scale_id=scale_strategy.id, code="NONE", label="Keine der genannten", sort_order=4)
    opt_na_strategy = ScaleOption(scale_id=scale_strategy.id, code="NA", label="Keine Angabe", sort_order=5, is_na=True)
    db.session.add_all([opt_rpa, opt_ipa, opt_ki, opt_none, opt_na_strategy])
    db.session.flush()
                          
                          
    # Ja/Nein Skala
    scale_yesno = Scale(key="yes_no", label="Ja/Nein")
    db.session.add(scale_yesno)
    db.session.flush()
    
    opt_yes = ScaleOption(scale_id=scale_yesno.id, code="JA", label="Ja", sort_order=1)
    opt_no = ScaleOption(scale_id=scale_yesno.id, code="NEIN", label="Nein", sort_order=2)
    opt_na = ScaleOption(scale_id=scale_yesno.id, code="KA", label="Keine Angabe", sort_order=3, is_na=True)
    db.session.add_all([opt_yes, opt_no, opt_na])
    db.session.flush()
    
    scale_frequency = Scale(key="frequency", label="Häufigkeit")
    db.session.add(scale_frequency)
    db.session.flush()

    opt_f1 = ScaleOption(scale_id=scale_frequency.id, code="1", label="Garnicht", sort_order=1)
    opt_f2 = ScaleOption(scale_id=scale_frequency.id, code="2", label="1 mal", sort_order=2)
    opt_f3 = ScaleOption(scale_id=scale_frequency.id, code="3", label="2–3 mal", sort_order=3)
    opt_f4 = ScaleOption(scale_id=scale_frequency.id, code="4", label="4–5 mal", sort_order=4)
    opt_f5 = ScaleOption(scale_id=scale_frequency.id, code="5", label="> 5 mal", sort_order=5)

    db.session.add_all([opt_f1, opt_f2, opt_f3, opt_f4, opt_f5])
    db.session.flush()

    scale_change = Scale(key="change_extent", label="Änderungsumfang")
    db.session.add(scale_change)
    db.session.flush()

    opt_c1 = ScaleOption(scale_id=scale_change.id, code="1", label="Nein, keine Änderungen geplant", sort_order=1)
    opt_c2 = ScaleOption(scale_id=scale_change.id, code="2", label="Ja, kleinere Anpassungen geplant", sort_order=2)
    opt_c3 = ScaleOption(scale_id=scale_change.id, code="3", label="Ja, mittlere Änderungen geplant", sort_order=3)
    opt_c4 = ScaleOption(scale_id=scale_change.id, code="4", label="Ja, größere Änderungen geplant", sort_order=4)
    opt_c5 = ScaleOption(scale_id=scale_change.id, code="5", label="Ja, grundlegende Neugestaltung geplant", sort_order=5)
    opt_c_na = ScaleOption(scale_id=scale_change.id, code="KA", label="Keine Angabe", sort_order=6, is_na=True)

    db.session.add_all([opt_c1, opt_c2, opt_c3, opt_c4, opt_c5, opt_c_na])
    db.session.flush()

    scale_data_structure = Scale(
    key="data_structure",
    label="Grad der Datenstrukturierung"
    )
    db.session.add(scale_data_structure)
    db.session.flush()

    opt_ds1 = ScaleOption(
        scale_id=scale_data_structure.id,
        code="1",
        label="strukturiert (z. B. Tabellen, Datenbanken)",
        sort_order=1
    )

    opt_ds2 = ScaleOption(
        scale_id=scale_data_structure.id,
        code="2",
        label="semi-strukturiert (z. B. PDFs, Formulare, E-Mails mit festen Mustern)",
        sort_order=2
    )

    opt_ds3 = ScaleOption(
        scale_id=scale_data_structure.id,
        code="3",
        label="unstrukturiert (z. B. Freitext, gescannte Dokumente, Bilder)",
        sort_order=3
    )

    opt_ds_na = ScaleOption(
        scale_id=scale_data_structure.id,
        code="KA",
        label="Keine Angabe",
        sort_order=4,
        is_na=True
    )

    db.session.add_all([opt_ds1, opt_ds2, opt_ds3, opt_ds_na])
    db.session.flush()

    scale_variants = Scale(key="variant_diversity", label="Variantenvielfalt")
    db.session.add(scale_variants)
    db.session.flush()

    opt_v1 = ScaleOption(
        scale_id=scale_variants.id,
        code="1",
        label="Es existiert nur eine Variante",
        sort_order=1
    )
    opt_v2 = ScaleOption(
        scale_id=scale_variants.id,
        code="2",
        label="Eine Variante dominiert, mit Ausnahmen",
        sort_order=2
    )
    opt_v3 = ScaleOption(
        scale_id=scale_variants.id,
        code="3",
        label="Wenige Varianten (2–3) decken den Großteil ab",
        sort_order=3
    )
    opt_v4 = ScaleOption(
        scale_id=scale_variants.id,
        code="4",
        label="Mehrere Varianten (4–6) sind regelmäßig, keine dominiert",
        sort_order=4
    )
    opt_v5 = ScaleOption(
        scale_id=scale_variants.id,
        code="5",
        label="Viele Varianten, jede kommt häufig vor",
        sort_order=5
    )
    opt_v_na = ScaleOption(
        scale_id=scale_variants.id,
        code="KA",
        label="Keine Angabe",
        sort_order=6,
        is_na=True
    )

    db.session.add_all([opt_v1, opt_v2, opt_v3, opt_v4, opt_v5, opt_v_na])
    db.session.flush()
    # ========================================
    # 4. DIMENSION 1: Plattformverfügbarkeit (Filterfragen)
    # ========================================

    yesno_options_all = [opt_yes, opt_no, opt_na]

    # 1.1
    q1_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.1",
        text="Wird im Unternehmen bereits mindestens eine Automatisierungsplattform eingesetzt?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=1,
        is_filter_question=True,
        filter_description="Wenn Ja -> Frage 1.2 und 1.3; wenn Nein -> direkt Frage 1.4"
    )
    db.session.add(q1_1)
    db.session.flush()
    add_filter_scores(q1_1.id, yesno_options_all)

    # 1.2 (nur wenn 1.1 = Ja)
    q1_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.2",
        text="Ist die Plattform reif und stabil für den produktiven Einsatz?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=2,
        is_filter_question=True,
        depends_on_question_id=q1_1.id,   # ok (single condition)
        depends_on_option_id=opt_yes.id,  # ok (single condition)
        filter_description="Wird nur gezeigt wenn 1.1 = Ja"
    )
    db.session.add(q1_2)
    db.session.flush()
    add_filter_scores(q1_2.id, yesno_options_all)

    # 1.3 (nur wenn 1.1 = Ja)
    q1_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.3",
        text="Stellt die Plattform alle benötigten Funktionen bereit oder bietet sie Möglichkeiten, diese zu integrieren (z. B. Schnittstellen, KI-Komponenten)?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=3,
        is_filter_question=True,
        depends_on_question_id=q1_1.id,   # ok (single condition)
        depends_on_option_id=opt_yes.id,  # ok (single condition)
        filter_description="Wird nur gezeigt wenn 1.1 = Ja"
    )
    db.session.add(q1_3)
    db.session.flush()
    add_filter_scores(q1_3.id, yesno_options_all)


    db.session.add(Hint(
        question_id=q1_3.id,
        scale_option_id=opt_no.id,
        automation_type=None,
        hint_text="Die Plattformverfügbarkeit bzw. Plattformreife ist aktuell nicht vollständig gegeben.",
        hint_type="info"
    ))

    # 1.4 (wenn 1.1=Nein ODER 1.2=Nein ODER 1.3=Nein)
    # -> NUR über QuestionCondition (keine Legacy-Felder setzen!)
    q1_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.4",
        text="Verfügt das Unternehmen über ausreichende Ressourcen und Kompetenzen, um die Automatisierung selbstständig zu entwickeln, zu testen, zu betreiben und weiterzuentwickeln?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=4,
        is_filter_question=True,
        depends_logic="any",
        depends_on_question_id=None,
        depends_on_option_id=None,
        filter_description="Wird gezeigt wenn 1.1 = Nein ODER 1.2 = Nein ODER 1.3 = Nein"
    )
    db.session.add(q1_4)
    db.session.flush()
    add_filter_scores(q1_4.id, yesno_options_all)

    db.session.add_all([
        QuestionCondition(question_id=q1_4.id, depends_on_question_id=q1_1.id, depends_on_option_id=opt_no.id, sort_order=1),
        QuestionCondition(question_id=q1_4.id, depends_on_question_id=q1_2.id, depends_on_option_id=opt_no.id, sort_order=2),
        QuestionCondition(question_id=q1_4.id, depends_on_question_id=q1_3.id, depends_on_option_id=opt_no.id, sort_order=3),
    ])
    db.session.add(Hint(
        question_id=q1_4.id,
        scale_option_id=opt_no.id,
        automation_type=None,
        hint_text="Interne Ressourcen/Kompetenzen reichen aktuell nicht aus für eine Eigenentwicklung.",
        hint_type="info"
    ))
    db.session.add(Hint(
        question_id=q1_4.id,
        scale_option_id=opt_yes.id,
        automation_type=None,
        hint_text="Interne Ressourcen/Kompetenzen sind ausreichend vorhanden. Damit ist die fehlende Plattformverfügbarkeit bzw. -reife kein limitierender Engpass für die Automatisierung.",
        hint_type="info"
    ))

    # 1.5 (nur wenn 1.4 = Nein)
    q1_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.5",
        text="Kann auf externe Unterstützung zugegriffen werden?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=5,
        is_filter_question=True,
        depends_on_question_id=q1_4.id,
        depends_on_option_id=opt_no.id,
        filter_description="Wird nur gezeigt wenn 1.4 = Nein"
    )
    db.session.add(q1_5)
    db.session.flush()
    add_filter_scores(q1_5.id, yesno_options_all)
    add_exclusion(q1_5.id, opt_no.id)

    db.session.add(Hint(
        question_id=q1_5.id,
        scale_option_id=opt_no.id,
        automation_type=None,
        hint_text="Ohne externe Unterstützung ist eine Automatisierung nicht umsetzbar.",
        hint_type="error"
    ))
    db.session.add(Hint(
        question_id=q1_5.id,
        scale_option_id=opt_yes.id,
        automation_type=None,
        hint_text="Nur mit externer Unterstützung ist eine Automatisierung umsetzbar.",
        hint_type="error"
    ))

    # 1.6 (nur wenn 1.1=Ja UND 1.2=Ja UND 1.3=Ja)
    # -> ebenfalls sauber über QuestionCondition
    q1_6 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim1.id,
        code="1.6",
        text="Für wie viele unterschiedliche Prozesse wird die Automatisierungsplattform derzeit insgesamt eingesetzt?",
        question_type="number",
        unit="Anzahl",
        sort_order=6,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None
    )
    db.session.add(q1_6)
    db.session.flush()
    db.session.add(Hint(
        question_id=q1_6.id,
        automation_type=None,
        hint_text="Die Plattform ist vorhanden, produktionsreif und funktional ausreichend.",
        hint_type="info"
    ))
    db.session.add_all([
        QuestionCondition(question_id=q1_6.id, depends_on_question_id=q1_1.id, depends_on_option_id=opt_yes.id, sort_order=1),
        QuestionCondition(question_id=q1_6.id, depends_on_question_id=q1_2.id, depends_on_option_id=opt_yes.id, sort_order=2),
        QuestionCondition(question_id=q1_6.id, depends_on_question_id=q1_3.id, depends_on_option_id=opt_yes.id, sort_order=3),
    ])
    
    # ========================================
    
    q2_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.1",
        text="Welche der folgenden Themen sind aktuell Bestandteil der Unternehmensstrategie?",
        question_type="multiple_choice",
        scale_id=scale_strategy.id,
        sort_order=1
    )
    
    q2_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.2",
        text="Risiken und Informationssicherheit werden vor der Produktivsetzung von Automatisierungen analysiert und bewertet. "
            "(Trifft voll zu: Vor dem Start wird geprüft, ob alles sicher ist und welche Risiken es gibt. "
            "Trifft gar nicht zu: Es wird einfach gestartet, ohne vorher zu prüfen, ob es sicher ist.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=2
    )

    q2_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.3",
        text="Vor der Produktivsetzung von Automatisierungen erfolgt eine Einbindung betroffener Mitarbeiter (z. B. Information, Mitwirkung, Feedback), um Mitarbeiterakzeptanz sicherzustellen. "
            "(Trifft voll zu: Betroffene werden vorher informiert, können mitreden und Feedback geben. "
            "Trifft gar nicht zu: Betroffene erfahren es erst, wenn es schon live ist.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=3
    )

    q2_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.4",
        text="Falls KI eingesetzt wird, ist für betroffene Mitarbeiter nachvollziehbar, dass und wie diese genutzt wird. "
            "(Trifft voll zu: Mitarbeitende wissen, dass KI genutzt wird und wofür (z. B. zum Vorschlagen oder Sortieren). "
            "Trifft gar nicht zu: Niemand weiß, dass KI im Hintergrund mitentscheidet oder unterstützt.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=4
    )

    q2_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.5",
        text="Es sind Regeln und Kontrollen definiert, die eine faire Behandlung aller betroffenen Mitarbeiter sicherstellen. "
            "(Trifft voll zu: Es gibt klare Regeln, damit niemand unfair behandelt wird, und es wird kontrolliert. "
            "Trifft gar nicht zu: Es gibt keine Regeln, und mögliche Ungleichbehandlung fällt nicht auf.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=5
    )

    q2_6 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.6",
        text="Das Automatisierungsvorhaben wird von der Führungsebene unterstützt. "
            "(Trifft voll zu: Führungskräfte stehen dahinter und geben Zeit/Geld/Ressourcen frei. "
            "Trifft gar nicht zu: Das Thema ist der Führung egal und das Projekt hat kaum Unterstützung.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=6,
    )

    q2_7 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.7",
        text="Betroffene Mitarbeiter verfügen über die notwendige Erfahrung, um die Automatisierung im Alltag zu nutzen und zu betreiben. "
            "(Trifft voll zu: Mitarbeitende können das im Alltag gut nutzen und wissen, was bei Problemen zu tun ist. "
            "Trifft gar nicht zu: Mitarbeitende wissen nicht, wie es funktioniert, und kommen ohne Hilfe nicht klar.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=7
    )

    q2_8 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.8",
        text="Im Unternehmen sind ausreichende Kenntnisse und Verantwortlichkeiten vorhanden, um Automatisierungen regelkonform, sicher und kontrolliert zu steuern. "
            "(Trifft voll zu: Es ist klar, wer verantwortlich ist, und es gibt genug Wissen im Unternehmen, um es sicher zu steuern. "
            "Trifft gar nicht zu: Es ist unklar, wer zuständig ist, und es fehlt Wissen, um das zu kontrollieren.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=8
    )

    q2_9 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim2.id,
        code="2.9",
        text="Es gibt Schulungen und Weiterbildungen für Mitarbeitende im Kontext Automatisierung. "
            "(Trifft voll zu: Es gibt Schulungen, damit Mitarbeitende damit arbeiten können. "
            "Trifft gar nicht zu: Es gibt keine Schulungen.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=9
    )
    
    
    db.session.add_all([q2_1, q2_2, q2_3, q2_4, q2_5, q2_6, q2_7, q2_8, q2_9])
    db.session.flush()
    # ----------------------------------------
    # Warnhinweise (nur bei opt_a1 / opt_a2)
    # Fokus: KI/IPA & EU AI Act
    # ----------------------------------------

    db.session.add_all([
        # 2.2 Risiken & Informationssicherheit
        Hint(
            question_id=q2_2.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Wenn vor dem Go-Live keine Risiko- und Sicherheitsprüfung erfolgt, steigt das Risiko für Datenpannen und Ausfälle. Bei KI/IPA kann das zudem Pflichten aus dem EU AI Act betreffen. Empfehlung: vor Produktivsetzung prüfen und kurz dokumentieren.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_2.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Die Prüfung von Risiken/Sicherheit ist noch nicht ausreichend. Bei KI/IPA kann das zu Compliance-Risiken führen. Empfehlung: feste Vorab-Checks vor Go-Live einführen (mindestens Datenschutz/Sicherheit/Risiken).",
            hint_type="warning"
        ),

        # 2.3 Einbindung betroffener Mitarbeitender (Change/Transparenz)
        Hint(
            question_id=q2_3.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Ohne frühzeitige Einbindung sinkt die Akzeptanz – und bei KI kann mangelnde Transparenz zusätzlich kritisch sein. Empfehlung: Betroffene früh informieren, Feedback einholen und sichtbar berücksichtigen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_3.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Einbindung/Kommunikation ist noch zu schwach. Empfehlung: kurze Info + Feedback-Schleife vor Go-Live (z. B. Pilotgruppe oder kurzer Testlauf).",
            hint_type="warning"
        ),

        # 2.4 KI-Nutzung nachvollziehbar machen (Transparenz)
        Hint(
            question_id=q2_4.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Wenn Mitarbeitende nicht erkennen, dass KI genutzt wird, kann das Transparenzpflichten berühren. Empfehlung: klar sagen, dass KI eingesetzt wird, wofür sie genutzt wird und wo Menschen final entscheiden.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_4.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: KI-Nutzung ist noch nicht ausreichend erklärt. Empfehlung: kurze, verständliche Erklärung (Zweck, Grenzen, wer prüft/entscheidet) bereitstellen.",
            hint_type="warning"
        ),

        # 2.5 Faire Behandlung / Regeln & Kontrollen
        Hint(
            question_id=q2_5.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Ohne Regeln/Kontrollen besteht das Risiko unfairer Behandlung (z. B. Benachteiligung einzelner Gruppen). Bei KI/IPA sollte das besonders geprüft werden. Empfehlung: klare Regeln + stichprobenartige Kontrollen einführen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_5.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Regeln/Kontrollen sind noch lückenhaft. Empfehlung: Mindestregeln definieren (was ist erlaubt/nicht erlaubt) und regelmäßige Checks einplanen.",
            hint_type="warning"
        ),

        # 2.7 Erfahrung der betroffenen Mitarbeitenden (Kompetenz für Nutzung/Betrieb)
        Hint(
            question_id=q2_7.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Wenn Mitarbeitende die Automatisierung nicht sicher nutzen können, fehlt wichtige menschliche Kontrolle. Bei KI/IPA verlangt der EU AI Act, dass Aufsicht/Bedienung durch kompetente, geschulte Personen erfolgt. Empfehlung: Einweisung + klare Ansprechperson.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_7.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Erfahrung ist noch nicht ausreichend. Empfehlung: kurze Schulung + einfache Anleitung (Was tun bei Fehlern? Wie prüfen?).",
            hint_type="warning"
        ),

        # 2.8 Wissen & Verantwortlichkeiten (Governance)
        Hint(
            question_id=q2_8.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Wenn Zuständigkeiten/Know-how fehlen, ist unklar, wer überwacht, eingreift und Verantwortung trägt. Bei KI/IPA ist das ein relevantes Compliance-Risiko. Empfehlung: Owner benennen + klare Regeln für Freigabe/Überwachung.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_8.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Governance ist noch nicht stabil. Empfehlung: Verantwortliche Rollen festlegen (z. B. fachlich/technisch/Compliance) und einfache Kontrollroutine definieren.",
            hint_type="warning"
        ),

        # 2.9 Schulungen & Weiterbildungen
        Hint(
            question_id=q2_9.id,
            scale_option_id=opt_a1.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Ohne Schulungen steigt das Risiko von Bedienfehlern und Fehlentscheidungen. Bei KI/IPA kann der EU AI Act zudem geschulte menschliche Aufsicht erfordern. Empfehlung: kurze Pflicht-Einweisung vor Go-Live + Wiederholung bei Änderungen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q2_9.id,
            scale_option_id=opt_a2.id,
            automation_type="IPA",
            hint_text="Warnhinweis: Schulungen sind noch nicht ausreichend. Empfehlung: mindestens eine Basisschulung (Nutzung, Kontrolle, Umgang mit Fehlern) einführen.",
            hint_type="warning"
        ),
    ])

    db.session.flush()
    # ========================================
    
    q3_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.1",
        text="Der aktuelle Prozess ist verstanden und dokumentiert. "
            "(Trifft voll zu: Die Schritte sind klar beschrieben (z. B. als Ablaufbeschreibung/Checkliste). "
            "Trifft gar nicht zu: Es gibt keine klare Beschreibung.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=1
    )
    
    q3_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.2",
        text="In den beteiligten Systemen existieren Event-Logs bzw. Ausführungsdaten, die eine Prozessanalyse ermöglichen.",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=2
    )
    
    q3_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.3",
        text="Wie oft wurde der Prozess im vergangenen Jahr verändert?",
        question_type="single_choice",
        scale_id=scale_frequency.id,
        sort_order=3
    )
    q3_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.4",
        text="Sind in den nächsten 12 Monaten größere Änderungen am Prozess geplant?",
        question_type="single_choice",
        scale_id=scale_change.id,
        sort_order=4
    )
    q3_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.5",
        text="Welche Aussage beschreibt die Verteilung der Prozessvarianten am besten?",
        question_type="single_choice",
        scale_id=scale_variants.id,
        sort_order=5
    )
    q3_6 = Question(
    questionnaire_version_id=qv.id,
    dimension_id=dim3.id,
    code="3.6",
    text="Der Prozess wird überwiegend durch klar definierte Regeln gesteuert. "
         "(Trifft voll zu: Für die meisten Fälle gibt es feste Regeln (z. B. „wenn Betrag > X, dann Freigabe nötig“). "
         "Trifft gar nicht zu: Es wird oft nach Gefühl entschieden; Regeln sind unklar oder ändern sich je nach Person.)",
    question_type="single_choice",
    scale_id=scale_likert.id,
    sort_order=6
    )

    q3_7 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.7",
        text="Werden Entscheidungen getroffen, die menschliches Urteilsvermögen erfordern? "
            "(Ja: Es wird abgewogen/entschieden, z. B. „Ist dieser Sonderfall okay?“, „Wie priorisieren wir bei Konflikten?“. "
            "Nein: Entscheidungen sind meist eindeutig nach Regeln möglich, z. B. „Wenn A, dann B“.)",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=7
    )

    q3_8 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim3.id,
        code="3.8",
        text="Im Prozess kommt es zu häufigen Systemwechseln. "
            "(Trifft voll zu: Man muss oft zwischen mehreren Programmen wechseln (z. B. E-Mail → Excel → ERP-System → Ticket-Tool). "
            "Trifft gar nicht zu: Alles passiert überwiegend in einem System.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=8
    )
    
    
    db.session.add_all([q3_1, q3_2, q3_3, q3_4, q3_5, q3_6, q3_7, q3_8])
    db.session.flush()
    
    
    # ========================================
    
        
    q4_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.1",
        text="In welcher Form liegen die für den Prozess relevanten Daten überwiegend vor?",
        question_type="single_choice",
        scale_id=scale_data_structure.id,
        sort_order=1
    )

    q4_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.2",
        text="Liegen alle für den Prozess erforderlichen Daten vollständig vor? "
            "(Ja: Alle benötigten Informationen sind immer da, z. B. Kunde, Auftragsnummer, Betrag, Datum – nichts fehlt. "
            "Nein: Es fehlen häufig Angaben, z. B. keine Auftragsnummer, unvollständige Kundendaten oder fehlende Dokumente.)",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=2
    )

    q4_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.3",
        text="Sind die verfügbaren Daten inhaltlich ausreichend und angemessen, um den Prozess auszuführen? "
            "(Ja: Die Daten sind nicht nur vorhanden, sondern auch brauchbar/korrekt, z. B. klare Werte, richtige Zuordnung, verständliche Angaben. "
            "Nein: Daten sind zwar da, aber unbrauchbar, z. B. widersprüchlich, veraltet, ungenau.)",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=3
    )

    db.session.add_all([q4_1, q4_2, q4_3])
    db.session.flush()

    q4_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.4",
        text="Ist es notwendig, Text aus gescannten Dokumenten oder Fotos (z. B. Scans, Screenshots, handschriftliche Inhalte) automatisch auszulesen, damit er weiterverarbeitet werden kann?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=4,
        is_filter_question=True,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
        filter_description='Wird nur gezeigt wenn 4.1 = "unstrukturiert"'
    )

    q4_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.5",
        text="Muss im Prozess natürliche Sprache verstanden und klassifiziert werden (z.B. E-Mails, Beschreibungen, Kommentare)?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=5,
        is_filter_question=True,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
        filter_description='Wird nur gezeigt wenn 4.1 = "unstrukturiert"'
    )

    q4_6 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim4.id,
        code="4.6",
        text="Soll die Automatisierung Vorhersagen oder automatische Entscheidungsvorschläge auf Basis historischer Daten liefern (z. B. Klassifizieren, Scoring, Priorisieren, Empfehlungen)?",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=6,
        is_filter_question=True,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
        filter_description='Wird nur gezeigt wenn 4.1 = "unstrukturiert"'
    )

    db.session.add_all([q4_4, q4_5, q4_6])
    db.session.flush()

    db.session.add_all([
        QuestionCondition(question_id=q4_4.id, depends_on_question_id=q4_1.id, depends_on_option_id=opt_ds3.id, sort_order=1),
        QuestionCondition(question_id=q4_5.id, depends_on_question_id=q4_1.id, depends_on_option_id=opt_ds3.id, sort_order=1),
        QuestionCondition(question_id=q4_6.id, depends_on_question_id=q4_1.id, depends_on_option_id=opt_ds3.id, sort_order=1),
    ])

    # ========================================
    
    q5_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim5.id,
        code="5.1",
        text="Die am Prozess beteiligten IT-Systeme sind stabil (wenige Ausfälle, verlässliche Performance). "
            "(Trifft voll zu: Die Systeme laufen meist ohne Störungen und sind schnell genug, der Prozess kann zuverlässig durchgeführt werden. "
            "Trifft gar nicht zu: Es gibt oft Ausfälle/Fehlermeldungen oder das System ist regelmäßig sehr langsam.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=1
    )

    q5_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim5.id,
        code="5.2",
        text="Veränderungen an den am Prozess beteiligten IT-Systemen sind planbar und werden frühzeitig mitgeteilt. "
            "(Trifft voll zu: Updates/Änderungen werden vorher angekündigt (z. B. Wartungsfenster), und man kann sich darauf einstellen. "
            "Trifft gar nicht zu: Änderungen passieren plötzlich ohne Info und führen unerwartet zu Problemen im Prozess.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=2
    )

    q5_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim5.id,
        code="5.3",
        text="Sind für die beteiligten IT-Systeme alle erforderlichen Voraussetzungen gegeben, damit RPA-/IPA-Bots darauf zugreifen können (technische Konnektivität, geeignete Zugriffsschnittstelle, Zulässigkeit technischer Benutzerkonten)? "
            "(Ja: Ein Bot darf und kann sich wie ein Nutzer anmelden und die nötigen Schritte ausführen (Zugänge sind erlaubt und vorhanden). "
            "Nein: Zugriff ist nicht möglich oder nicht erlaubt (z. B. kein Bot-Account, Anmeldung blockiert, wichtige Funktionen sind nicht erreichbar).",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=3
    )

    q5_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim5.id,
        code="5.4",
        text="Für die Automatisierung sind keine umfangreichen Änderungen der bestehenden IT-Infrastruktur erforderlich. "
            "(Trifft voll zu: Die Automatisierung kann mit der vorhandenen IT umgesetzt werden, höchstens kleine Anpassungen sind nötig. "
            "Trifft gar nicht zu: Es wären große Umbauten nötig, z. B. neue Systeme, größere Umstellungen oder viele technische Anpassungen.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=4
    )
    db.session.add_all([q5_1, q5_2, q5_3, q5_4])
    db.session.flush()
    # 5.5 (nur wenn 1.1 = Ja UND 1.2 = Ja UND 1.3 = Ja)
    q5_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim5.id,
        code="5.5",
        text="Hat das Projektteam die notwendige Erfahrung, um die Einführung der Automatisierung erfolgreich umzusetzen? (Bei Eigenentwicklung)",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=5,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
    )
    db.session.add(q5_5)
    db.session.flush()

    db.session.add_all([
        QuestionCondition(question_id=q5_5.id, depends_on_question_id=q1_1.id, depends_on_option_id=opt_yes.id, sort_order=1),
        QuestionCondition(question_id=q5_5.id, depends_on_question_id=q1_2.id, depends_on_option_id=opt_yes.id, sort_order=2),
        QuestionCondition(question_id=q5_5.id, depends_on_question_id=q1_3.id, depends_on_option_id=opt_yes.id, sort_order=3),
    ])
    # Gruppe 2: (1.4=Ja)
    db.session.add(
        QuestionCondition(question_id=q5_5.id, depends_on_question_id=q1_4.id, depends_on_option_id=opt_yes.id, sort_order=4, group_key=2)
    )
    # ========================================
    
    q6_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.1",
         text="Der operative Betrieb kann auch bei einem Ausfall des automatisierten Prozesses stabil weiterlaufen. "
         "(Trifft voll zu: Wenn die Automatisierung ausfällt, gibt es einen klaren manuellen Ersatz und die Arbeit geht weiter. "
         "Trifft gar nicht zu: Fällt die Automatisierung aus, steht der Prozess weitgehend still. "
         "Falls für diesen Prozess nicht relevant: keine Angabe.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=1
    )

    q6_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.2",
       text="Es existieren definierte Maßnahmen, um Risiken der Automatisierung zu steuern und zu überwachen (Kontrollen, Notfallpläne). "
         "(Trifft voll zu: Es gibt klare Regeln/Notfallpläne (z. B. wer informiert wird, was bei Fehlern zu tun ist) und es wird regelmäßig geprüft. "
         "Trifft gar nicht zu: Es gibt keine festgelegten Maßnahmen – man reagiert erst, wenn etwas schiefgeht. "
         "Falls für diesen Prozess nicht relevant: keine Angabe.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=2
    )

    q6_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.3",
        text="Für den Prozess sind menschliche Kontrollpunkte geplant und umsetzbar. "
         "(Trifft voll zu: An wichtigen Stellen prüft ein Mensch Ergebnisse (z. B. Stichprobe, Freigabe vor Versand/Zahlung). "
         "Trifft gar nicht zu: Es gibt keine realistische Möglichkeit zur Kontrolle – es läuft komplett automatisch durch. "
         "Falls für diesen Prozess nicht relevant: keine Angabe.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=3
    )

    q6_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.4",
        text="Werden im Prozess personenbezogene oder sensible Daten verarbeitet (z. B. Namen, Adressen, Betriebsgeheimnisse)? "
            "(Ja: Es werden z. B. Namen, Kontaktdaten, Gehälter, Gesundheitsdaten oder vertrauliche interne Informationen genutzt. "
            "Nein: Es werden keine personenbezogenen oder vertraulichen Daten verarbeitet, z. B. nur allgemeine Prozess-/Sachdaten.)",
        question_type="single_choice",
        scale_id=scale_yesno.id,
        sort_order=4
    )
    db.session.add_all([q6_1, q6_2, q6_3, q6_4])
    db.session.flush()

    q6_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.5",
        text="Es existieren definierte Maßnahmen zum Schutz dieser Daten (z. B. Verschlüsselung, sichere Speicherung). "
            "(Trifft voll zu: Daten sind geschützt (z. B. nur für Berechtigte sichtbar, sichere Ablage) und es gibt klare Regeln dafür. "
            "Trifft gar nicht zu: Daten liegen ungeschützt oder zu offen zugänglich, ohne klare Schutzmaßnahmen.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=5,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
    )

    q6_6 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.6",
        text="Bei Nutzung nicht selbst gehosteter (externer/online) KI wird ausgeschlossen, dass personenbezogene oder sensible Daten in Trainings- oder Lernprozesse einfließen. "
            "(Trifft voll zu: Es ist klar geregelt, dass solche Daten nicht zum „Lernen“ genutzt werden (z. B. nur anonymisierte Daten oder ein Dienst mit entsprechender Zusage). "
            "Trifft gar nicht zu: Es ist unklar oder nicht ausgeschlossen, ob eingegebene Daten zum Training genutzt werden.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=6,
        depends_logic="all",
        depends_on_question_id=None,
        depends_on_option_id=None,
    )

    db.session.add_all([q6_5, q6_6])
    db.session.flush()

    db.session.add_all([
        QuestionCondition(question_id=q6_5.id, depends_on_question_id=q6_4.id, depends_on_option_id=opt_yes.id, sort_order=1),
        QuestionCondition(question_id=q6_6.id, depends_on_question_id=q6_4.id, depends_on_option_id=opt_yes.id, sort_order=1),
    ])
    q6_7 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.7",
        text="Die Automatisierung erhält nur die Zugriffsrechte für Daten, die für die Ausführung erforderlich sind (z. B. Lesen, Schreiben). "
            "(Trifft voll zu: Der Bot darf nur das Nötigste (z. B. nur lesen, nicht löschen; nur bestimmte Ordner/Masken). "
            "Trifft gar nicht zu: Der Bot hat sehr viele Rechte „zur Sicherheit“, obwohl er sie nicht braucht.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=7
    )

    q6_8 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.8",
        text="Berechtigungen und Zugangsdaten der Automatisierung können sicher verwaltet werden. "
            "(Trifft voll zu: Zugangsdaten sind sicher gespeichert und nur wenige dürfen sie ändern; bei Bedarf kann man sie schnell sperren/ändern. "
            "Trifft gar nicht zu: Passwörter liegen offen herum oder viele haben Zugriff; Änderungen/Sperrungen sind schwierig.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=8
    )

    q6_9 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.9",
        text="Der Prozess ist bei manueller Bearbeitung anfällig für Fehler. "
            "(Trifft voll zu: Es passieren oft Fehler, z. B. Tippfehler, falsche Zuordnung, vergessene Schritte. "
            "Trifft gar nicht zu: Manuelle Bearbeitung läuft sehr zuverlässig und Fehler sind selten.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=9
    )

    q6_10 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.10",
        text="Eine Automatisierung kann voraussichtlich die Fehlerhäufigkeit im Prozess verringern. "
            "(Trifft voll zu: Viele Fehler entstehen durch Routinearbeit und könnten durch Automatisierung reduziert werden. "
            "Trifft gar nicht zu: Fehler entstehen meist durch unklare Fälle/Entscheidungen – Automatisierung würde kaum helfen.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=10
    )

    q6_11 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.11",
        text="Es sind Kontrollen oder Tests geplant, um potenzielle Fehler des automatisierten Prozesses zu erkennen. "
            "(Trifft voll zu: Es gibt geplante Prüfungen (z. B. Stichproben, Abgleich mit Erwartungen, Tests vor Updates). "
            "Trifft gar nicht zu: Es gibt keine geplanten Kontrollen – Fehler würden nur zufällig auffallen.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=11
    )

    q6_12 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.12",
        text="Die Ausführungsschritte der Automatisierung können nachvollzogen werden. "
            "(Trifft voll zu: Man kann später sehen, was der Bot gemacht hat (z. B. Protokoll/Verlauf: wann gestartet, was geändert, was schiefging). "
            "Trifft gar nicht zu: Man sieht nur das Ergebnis, aber nicht, welche Schritte passiert sind oder warum.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=12
    )

    q6_13 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim6.id,
        code="6.13",
        text="Es ist klar festgelegt, wer Verantwortung für KI-basierte Entscheidungen übernimmt. "
            "(Trifft voll zu: Es ist eindeutig benannt, wer verantwortlich ist (z. B. Rolle/Team), und wer bei Problemen entscheidet. "
            "Trifft gar nicht zu: Niemand fühlt sich zuständig – bei Fehlentscheidungen ist unklar, wer reagieren muss.)",
        question_type="single_choice",
        scale_id=scale_likert.id,
        sort_order=13
    )
    
    db.session.add_all([q6_7, q6_8, q6_9, q6_10, q6_11, q6_12, q6_13])
    db.session.flush()
    # ========================================
    # DIM 6: Zusatz-Hinweise / Warnhinweise (Experten-Input)
    # ========================================

    # Globale Disclaimer / Rechtsrahmen (als Info, damit KMU nicht abgeschreckt werden)
    db.session.add_all([
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a3.id,  # teils/teils als neutraler Trigger
            automation_type=None,
            hint_text="Hinweis: Diese Fragen ersetzen keine Rechtsberatung. Sie dienen als Orientierung/Sensibilisierung. Rechtliche Pflichten hängen u. a. von Datenart, Einsatzgebiet und Entscheidungsart ab.",
            hint_type="info"
        ),
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a3.id,
            automation_type=None,
            hint_text="Mögliche relevante Regelwerke (je nach Fall): DSGVO, BDSG, NIS2, EU AI Act, Cyber Resilience Act, Digital Services Act, TDDDG.",
            hint_type="info"
        ),
    ])

    # 6.1 – Prozesskritikalität / Robustheit / Hochrisiko-Hinweis
    db.session.add_all([
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a1.id,  # trifft gar nicht zu
            automation_type=None,
            hint_text="Warnhinweis: Wenn der Betrieb bei Ausfall nicht stabil weiterlaufen kann, ist das Risiko hoch. Bei kritischen Prozessen (z. B. sicherheitsrelevant/hohe Auswirkungen) sind robuste Maßnahmen besonders wichtig – bei KI/IPA ggf. auch im Sinne des EU AI Act.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a2.id,  # trifft eher nicht zu
            automation_type=None,
            hint_text="Warnhinweis: Der Fallback ist noch nicht ausreichend. Empfehlung: klaren manuellen Ersatzweg/Notfallablauf definieren und regelmäßig testen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a_na.id,  # Keine Angabe
            automation_type=None,
            hint_text="Hinweis: Wenn das für diesen Prozess nicht relevant ist, wähle „Keine Angabe“.",
            hint_type="info"
        ),
        Hint(
            question_id=q6_1.id,
            scale_option_id=opt_a4.id,  # trifft eher zu
            automation_type=None,
            hint_text="Hinweis: Bewerte einen konkreten Prozess – falls der Prozess stark von anderen Prozessen/Systemen abhängt, diese Abhängigkeiten mitdenken (Ketten-/Folgeeffekte).",
            hint_type="info"
        ),
    ])

    # 6.2 – Notfallpläne / unterschiedliche Risikotypen / nicht immer erforderlich
    db.session.add_all([
        Hint(
            question_id=q6_2.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Ohne definierte Maßnahmen/Notfallplan steigt das Risiko deutlich. Je nach Prozessart können Fehler kleine Auswirkungen haben oder sehr gravierend sein. Empfehlung: Mindest-Notfallablauf festlegen (Wer? Was? Wann?).",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_2.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Maßnahmen sind noch zu wenig konkret. Empfehlung: Verantwortlichkeiten + Reaktionsplan + einfache Kontrollen definieren (auch wenn KMU das oft noch nicht formalisiert haben).",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_2.id,
            scale_option_id=opt_a_na.id,
            automation_type=None,
            hint_text="Hinweis: Ein umfassender Notfallplan ist nicht bei jedem Prozess notwendig. Wenn es hier nicht passt, nutze „Keine Angabe“.",
            hint_type="info"
        ),
        Hint(
            question_id=q6_2.id,
            scale_option_id=opt_a3.id,
            automation_type=None,
            hint_text="Hinweis: IT-Sicherheitsbewertung ist ohne Branchen-/Domänenkontext schwierig – bei Unsicherheit lieber mit einem einfachen Standard-Check starten.",
            hint_type="info"
        ),
    ])

    # 6.3 – Menschliche Kontrollpunkte abhängig vom Anwendungsfall
    db.session.add_all([
        Hint(
            question_id=q6_3.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Wenn keine menschlichen Kontrollpunkte möglich sind, steigt das Risiko (Fehler bleiben unbemerkt). Empfehlung: mindestens Stichproben oder Freigabe an kritischen Stellen einbauen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_3.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Kontrollpunkte sind noch nicht ausreichend geplant. Empfehlung: festlegen, *wo* und *wie oft* geprüft wird und wer verantwortlich ist.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_3.id,
            scale_option_id=opt_a_na.id,
            automation_type=None,
            hint_text="Hinweis: Die Notwendigkeit hängt stark vom Anwendungsfall ab. Wenn nicht passend, nutze „Keine Angabe“.",
            hint_type="info"
        ),
    ])

    # 6.4 – Sensible Daten inkl. Betriebsgeheimnisse + Rechtsrahmen (Ja/Nein)
    db.session.add_all([
        Hint(
            question_id=q6_4.id,
            scale_option_id=opt_yes.id,
            automation_type=None,
            hint_text="Hinweis: Bei personenbezogenen oder sensiblen Daten gelten je nach Fall zusätzliche Anforderungen (z. B. DSGVO/BDSG; bei KI/IPA ggf. EU AI Act). Art der Daten und Art der Entscheidung sind entscheidend.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_4.id,
            scale_option_id=opt_na.id,
            automation_type=None,
            hint_text="Hinweis: Wenn unklar ist, ob sensible Daten betroffen sind, lieber prüfen lassen oder konservativ von „Ja“ ausgehen.",
            hint_type="info"
        ),
    ])

    # 6.5 – Datenschutzmaßnahmen (nur sichtbar wenn 6.4=Ja, via QuestionCondition)
    db.session.add_all([
        Hint(
            question_id=q6_5.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Wenn Schutzmaßnahmen fehlen, ist das kritisch (z. B. unberechtigter Zugriff/Datenabfluss). Empfehlung: Zugriff beschränken, sichere Ablage, Protokollierung und klare Regeln zur Datennutzung.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_5.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Schutzmaßnahmen sind noch lückenhaft. Empfehlung: Mindestschutz definieren (wer darf was sehen/ändern?) und technisch absichern.",
            hint_type="warning"
        ),
    ])

    # 6.6 – Externe/Online-KI & Training/Lernen (Hosting/Training entscheidend)
    db.session.add_all([
        Hint(
            question_id=q6_6.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Wenn nicht ausgeschlossen ist, dass Daten ins Training/Lernen fließen, ist das ein hohes Risiko. Empfehlung: nur Dienste/Settings nutzen, die Training mit deinen Daten ausschließen oder Daten vorher anonymisieren – je nach Fall können DSGVO/BDSG und EU AI Act relevant sein.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_6.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Die Regelung ist noch nicht eindeutig. Empfehlung: klären, ob die KI extern/online ist, ob Daten gespeichert werden und ob sie für Training genutzt werden dürfen.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_6.id,
            scale_option_id=opt_a3.id,
            automation_type=None,
            hint_text="Hinweis: Anforderungen unterscheiden sich je nach KI-Technologie sowie Hosting- und Trainingsform (selbst gehostet vs. extern; Training an/aus).",
            hint_type="info"
        ),
    ])

    # 6.7 – Berechtigungen: Beispiel konkretisieren + Begriff „Bot“ entschärfen
    db.session.add_all([
        Hint(
            question_id=q6_7.id,
            scale_option_id=opt_a3.id,
            automation_type=None,
            hint_text="Hinweis: Mit „Automatisierung/Bot“ ist hier die automatisierte Ausführung gemeint (RPA/IPA). Beispiel Rechte: nur lesen, nur in bestimmten Bereichen schreiben, niemals löschen, kein Admin-Zugriff.",
            hint_type="info"
        ),
    ])

    # 6.8 – Zugangsdaten sicher verwalten + Begriff „Bot“
    db.session.add_all([
        Hint(
            question_id=q6_8.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Unsichere Zugangsdaten sind ein häufiges Einfallstor. Empfehlung: Zugangsdaten nicht offen teilen, klare Zuständigkeiten, regelmäßiger Wechsel/Sperrung möglich.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_8.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Verwaltung ist noch nicht sicher genug. Empfehlung: zentrale, kontrollierte Ablage und nur wenige berechtigte Personen.",
            hint_type="warning"
        ),
    ])

    # 6.9 / 6.10 – KI kann neue Fehlerarten bringen (z. B. Halluzinationen)
    db.session.add_all([
        Hint(
            question_id=q6_10.id,
            scale_option_id=opt_a4.id,  # trifft eher zu
            automation_type=None,
            hint_text="Hinweis: Bei KI/IPA können trotz Automatisierung neue Fehlerarten auftreten (z. B. falsche Antworten/„Halluzinationen“). Empfehlung: Ergebnisse prüfen und klare Grenzen definieren, wofür KI genutzt wird.",
            hint_type="info"
        ),
        Hint(
            question_id=q6_10.id,
            scale_option_id=opt_a5.id,  # trifft voll zu
            automation_type=None,
            hint_text="Hinweis: Auch wenn Fehler sinken, können bei KI/IPA neue Fehlerarten entstehen (z. B. Halluzinationen). Empfehlung: Kontrollen und klare Regeln zur Ergebnisprüfung einplanen.",
            hint_type="info"
        ),
    ])

    # 6.11 – Kontrollen/Tests: kritische Beispiele + KI ggf. besonders relevant
    db.session.add_all([
        Hint(
            question_id=q6_11.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Ohne Kontrollen/Tests bleiben Fehler oft lange unbemerkt. Kritische Beispiele: falsche Zahlungen, falsche Datenweitergabe, falsche Freigaben. Empfehlung: Tests vor Go-Live und nach Änderungen + regelmäßige Stichproben.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_11.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Kontrollen sind noch nicht ausreichend geplant. Empfehlung: mindestens Stichprobenkontrolle + Abweichungsalarm + Tests bei Änderungen einführen.",
            hint_type="warning"
        ),
    ])

    # 6.12 – Nachvollziehbarkeit/Dokumentation (besonders wichtig bei AI-Agenten)
    db.session.add_all([
        Hint(
            question_id=q6_12.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Wenn Schritte nicht nachvollziehbar sind, ist Ursachenanalyse und Verantwortung schwer. Bei KI/AI-Agenten ist Dokumentation/Protokollierung besonders wichtig. Empfehlung: Logging/Verlauf + Ablage der wichtigsten Entscheidungen/Inputs.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_12.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Nachvollziehbarkeit ist noch zu schwach. Empfehlung: mindestens Start/Ende, bearbeitete Fälle, Änderungen und Fehlergründe protokollieren.",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_12.id,
            scale_option_id=opt_a3.id,
            automation_type=None,
            hint_text="Hinweis: Bei KI ist vollständige Nachvollziehbarkeit teils schwieriger umzusetzen – umso wichtiger sind klare Logs, Versionen und definierte Prüfpunkte.",
            hint_type="info"
        ),
    ])

    # 6.13 – Verantwortlichkeit (auch wenn die Frage evtl. später entfernt wird)
    db.session.add_all([
        Hint(
            question_id=q6_13.id,
            scale_option_id=opt_a1.id,
            automation_type=None,
            hint_text="Warnhinweis: Wenn keine klare Verantwortung festgelegt ist, ist das organisatorisch und rechtlich riskant – besonders bei KI-gestützten Entscheidungen. Empfehlung: klare Rolle/Owner festlegen (wer entscheidet, wer prüft, wer reagiert).",
            hint_type="warning"
        ),
        Hint(
            question_id=q6_13.id,
            scale_option_id=opt_a2.id,
            automation_type=None,
            hint_text="Warnhinweis: Verantwortung ist noch nicht eindeutig. Empfehlung: Verantwortliche Person/Team benennen und Eskalationsweg festlegen.",
            hint_type="warning"
        ),
    ])

    db.session.flush()
        # ========================================
    
    q7_1 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.1",
        text="Wie hoch schätzen Sie die einmaligen Kosten für die Einführung der Prozessautomatisierung ein? (Fixkosten, die vor dem laufenden Betrieb anfallen, wie z. B. einmalige Lizenz- oder Setupgebühren, initiale Schulungen, Infrastruktur)",
        question_type="number",
        unit="Euro gesamt",
        sort_order=1
    )
    
    q7_2 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.2",
        text="Wie hoch schätzen Sie den Arbeitsaufwand in Stunden für die initiale Implementierung der Automatisierung vor der Produktivsetzung ein? (Analyse, Umsetzung, Tests, Produktivsetzung)",
        question_type="number",
        unit="Stunden gesamt",
        sort_order=2
    )
    
    q7_3 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.3",
        text="Wie hoch schätzen Sie die laufenden Betriebs- und Wartungskosten pro Jahr ein, die durch den Betrieb der Automatisierung nach der Produktivsetzung entstehen? (Variable Kosten z. B. laufende Lizenzkosten, zusätzliche Infrastrukturkosten)",
        question_type="number",
        unit="Euro pro Jahr",
        sort_order=3
    )
    
    q7_4 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.4",
        text="Wie hoch schätzen Sie den laufenden Arbeitsaufwand in Stunden pro Monat für Betrieb und Wartung der Automatisierung nach der Produktivsetzung? (Monitoring, Fehlerbehebung, Anpassungen bei Prozess-/Systemänderungen, Pflege)",
        question_type="number",
        unit="Stunden pro Monat",
        sort_order=4
    )
    
    q7_5 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.5",
        text="Wie häufig tritt der zu automatisierende Prozess pro Monat auf? ",
        question_type="number",
        unit="Anzahl pro Monat",
        sort_order=5
    )
    q7_6 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.6",
        text="Wie hoch ist die durchschnittliche manuelle Bearbeitungszeit pro Prozessdurchlauf in Minuten?",
        question_type="number",
        unit="Minuten pro Prozessdurchlauf",
        sort_order=6
    )
    
    q7_7 = Question(
        questionnaire_version_id=qv.id,
        dimension_id=dim7.id,
        code="7.7",
        text="Wie hoch ist der geschätzte verbleibende durchschnittliche menschliche Aufwand pro Prozessdurchlauf nach einer Automatisierung in Minuten?",
        question_type="number",
        unit="Minuten pro Prozessdurchlauf",
        sort_order=7
    )
    
    db.session.add_all([q7_1, q7_2, q7_3, q7_4, q7_5, q7_6, q7_7])
    db.session.flush()

   #00000000000000000000000000000000000000000000000

# ========================================
# Option Scores (nur RPA) für Dimension 2 – Fragen 2.1 bis 2.9
# gemäß deiner Tabelle (inkl. "-" = nicht anwendbar)
# ========================================

# --- 2.1 (Strategie / multiple_choice) ---
# RPA-Spalte: RPA=5, KI=3, IPA=3, NONE=2, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_rpa.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_ki.id,
            automation_type="RPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_ipa.id,
            automation_type="RPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_none.id,
            automation_type="RPA",
            score=2.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_na_strategy.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- Likert Optionen 1–5 + k.A. holen ---
    likert_options = (
        ScaleOption.query
        .filter_by(scale_id=scale_likert.id, is_na=False)
        .order_by(ScaleOption.sort_order)
        .all()
    )
    likert_na_option = ScaleOption.query.filter_by(scale_id=scale_likert.id, is_na=True).first()

    def add_rpa_likert_scores(question, scores_or_none):
        """
        scores_or_none:
        - Liste mit 5 Scores (für Likert 1..5) -> is_applicable=True
        - None -> "-" (nicht anwendbar): alle Optionen score=None, is_applicable=False
        """
        if scores_or_none is None:
            # "-" für alle 1..5
            for opt in likert_options:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
        else:
            # Scores für 1..5
            for idx, opt in enumerate(likert_options):
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=float(scores_or_none[idx]),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-"
        if likert_na_option:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=likert_na_option.id,
                automation_type="RPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))

    # --- 2.2 bis 2.9 (Likert / single_choice) ---
    # RPA-Spalte aus deiner Tabelle:
    # 2.2: 2 2 3 4 5 -
    # 2.3: 2 2 3 4 5 -
    # 2.4: - - - - - -
    # 2.5: - - - - - -
    # 2.6: 2 2 3 4 5 -
    # 2.7: 1 2 3 4 5 -
    # 2.8: 2 2 3 4 5 -
    # 2.9: 1 2 3 4 5 -
    add_rpa_likert_scores(q2_2, [2, 2, 3, 4, 5])
    add_rpa_likert_scores(q2_3, [2, 2, 3, 4, 5])
    add_rpa_likert_scores(q2_4, None)
    add_rpa_likert_scores(q2_5, None)
    add_rpa_likert_scores(q2_6, [2, 2, 3, 4, 5])
    add_rpa_likert_scores(q2_7, [1, 2, 3, 4, 5])
    add_rpa_likert_scores(q2_8, [2, 2, 3, 4, 5])
    add_rpa_likert_scores(q2_9, [1, 2, 3, 4, 5])

    # ========================================
    # Option Scores (nur IPA) für Dimension 2 – Fragen 2.1 bis 2.9
    # gemäß deiner Tabelle (inkl. "-" = nicht anwendbar)
    # ========================================

    # --- 2.1 (Strategie / multiple_choice) ---
    # IPA-Spalte: RPA="-", KI=5, IPA=5, NONE=1, k.A.="-"
    db.session.add_all([
        # RPA als Option in der Strategie-Skala ist für IPA-Bewertung nicht anwendbar ("-")
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_rpa.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_ki.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_ipa.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_none.id,
            automation_type="IPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q2_1.id,
            scale_option_id=opt_na_strategy.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- Likert Optionen 1–5 + k.A. holen ---
    likert_options = (
        ScaleOption.query
        .filter_by(scale_id=scale_likert.id, is_na=False)
        .order_by(ScaleOption.sort_order)
        .all()
    )
    likert_na_option = ScaleOption.query.filter_by(scale_id=scale_likert.id, is_na=True).first()

    def add_ipa_likert_scores(question, scores_or_none):
        """
        scores_or_none:
        - Liste mit 5 Scores (für Likert 1..5) -> is_applicable=True
        - None -> "-" (nicht anwendbar): alle Optionen score=None, is_applicable=False
        """
        if scores_or_none is None:
            # "-" für alle 1..5
            for opt in likert_options:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
        else:
            # Scores für 1..5
            for idx, opt in enumerate(likert_options):
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=float(scores_or_none[idx]),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-"
        if likert_na_option:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=likert_na_option.id,
                automation_type="IPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))

    # --- 2.2 bis 2.9 (Likert / single_choice) ---
    # IPA-Spalte aus deiner Tabelle:
    # 2.2: 1 2 3 3 5 -
    # 2.3: 1 2 3 3 5 -
    # 2.4: 1 2 3 4 5 -
    # 2.5: 1 2 3 4 5 -
    # 2.6: 1 2 3 3 5 -
    # 2.7: 1 2 3 4 5 -
    # 2.8: 1 2 3 4 5 -
    # 2.9: 1 1 2 3 5 -
    add_ipa_likert_scores(q2_2, [1, 2, 3, 3, 5])
    add_ipa_likert_scores(q2_3, [1, 2, 3, 3, 5])
    add_ipa_likert_scores(q2_4, [1, 2, 3, 4, 5])
    add_ipa_likert_scores(q2_5, [1, 2, 3, 4, 5])
    add_ipa_likert_scores(q2_6, [1, 2, 3, 3, 5])
    add_ipa_likert_scores(q2_7, [1, 2, 3, 4, 5])
    add_ipa_likert_scores(q2_8, [1, 2, 3, 4, 5])
    add_ipa_likert_scores(q2_9, [1, 1, 2, 3, 5])


        # ========================================
    # Option Scores (nur RPA) für Dimension 3 – Fragen 3.1 bis 3.8
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    def add_rpa_scores_generic(question, option_value_pairs, na_option=None):
        """
        option_value_pairs: Liste von Tupeln (ScaleOption, value)
        - value = Zahl  -> score=value, applicable=True
        - value = "A"   -> score=None, is_exclusion=True, applicable=True
        - value = None  -> score=None, applicable=False   (für "-")
        na_option: optional ScaleOption für k.A. (wird als "-" gesetzt)
        """
        for opt, val in option_value_pairs:
            if val == "A":
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=None,
                    is_exclusion=True,
                    is_applicable=True
                ))
            elif val is None:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
            else:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=float(val),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-" (nicht anwendbar), falls Option existiert
        if na_option is not None:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=na_option.id,
                automation_type="RPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))


    # --- 3.1 (Likert 1–5) ---
    # A, A, 1, 3, 5, -
    add_rpa_scores_generic(
        q3_1,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.2 (Likert 1–5) ---
    # 3, 3, 3, 4, 5, -
    add_rpa_scores_generic(
        q3_2,
        [(opt_a1, 3), (opt_a2, 3), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.3 (Häufigkeit 1–5) ---
    # 5, 3, 1, A, A, -
    # (Hinweis: in deinem Seed existiert für frequency aktuell keine k.A.-Option.)
    add_rpa_scores_generic(
        q3_3,
        [(opt_f1, 5), (opt_f2, 3), (opt_f3, 1), (opt_f4, "A"), (opt_f5, "A")],
        na_option=None
    )

    # --- 3.4 (Änderungsumfang 1–5 + k.A.) ---
    # 5, 4, 3, 1, A, -
    add_rpa_scores_generic(
        q3_4,
        [(opt_c1, 5), (opt_c2, 4), (opt_c3, 3), (opt_c4, 1), (opt_c5, "A")],
        na_option=opt_c_na
    )

    # --- 3.5 (Variantenvielfalt 1–5 + k.A.) ---
    # 5, 4, 3, 2, 1, -
    add_rpa_scores_generic(
        q3_5,
        [(opt_v1, 5), (opt_v2, 4), (opt_v3, 3), (opt_v4, 2), (opt_v5, 1)],
        na_option=opt_v_na
    )

    # --- 3.6 (Likert 1–5) ---
    # A, A, 1, 3, 5, -
    add_rpa_scores_generic(
        q3_6,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.7 (Ja/Nein + k.A.) ---
    # Ja = A, Nein = 5, k.A. = -
    db.session.add_all([
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=None,
            is_exclusion=True,   # A
            is_applicable=True
        ),
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 3.8 (Likert 1–5) ---
    # 3, 3, 4, 5, 5, -
    add_rpa_scores_generic(
        q3_8,
        [(opt_a1, 3), (opt_a2, 3), (opt_a3, 4), (opt_a4, 5), (opt_a5, 5)],
        na_option=opt_a_na
    )

        # ========================================
    # Option Scores (nur IPA) für Dimension 3 – Fragen 3.1 bis 3.8
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    def add_ipa_scores_generic(question, option_value_pairs, na_option=None):
        """
        option_value_pairs: Liste von Tupeln (ScaleOption, value)
        - value = Zahl  -> score=value, applicable=True
        - value = "A"   -> score=None, is_exclusion=True, applicable=True
        - value = None  -> score=None, applicable=False   (für "-")
        na_option: optional ScaleOption für k.A. (wird als "-" gesetzt)
        """
        for opt, val in option_value_pairs:
            if val == "A":
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=True,
                    is_applicable=True
                ))
            elif val is None:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
            else:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=float(val),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-" (nicht anwendbar), falls Option existiert
        if na_option is not None:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=na_option.id,
                automation_type="IPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))


    # --- 3.1 (Likert 1–5) ---
    # A, A, 1, 2, 5, -
    add_ipa_scores_generic(
        q3_1,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 2), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.2 (Likert 1–5) ---
    # 3, 3, 3, 4, 5, -
    add_ipa_scores_generic(
        q3_2,
        [(opt_a1, 3), (opt_a2, 3), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.3 (Häufigkeit 1–5) ---
    # 5, 3, 1, A, A, -
    # (Hinweis: in deinem Seed existiert für frequency aktuell keine k.A.-Option.)
    add_ipa_scores_generic(
        q3_3,
        [(opt_f1, 5), (opt_f2, 3), (opt_f3, 1), (opt_f4, "A"), (opt_f5, "A")],
        na_option=None
    )

    # --- 3.4 (Änderungsumfang 1–5 + k.A.) ---
    # 5, 4, 3, 1, A, -
    add_ipa_scores_generic(
        q3_4,
        [(opt_c1, 5), (opt_c2, 4), (opt_c3, 3), (opt_c4, 1), (opt_c5, "A")],
        na_option=opt_c_na
    )

    # --- 3.5 (Variantenvielfalt 1–5 + k.A.) ---
    # 5, 4, 4, 3, 2, -
    add_ipa_scores_generic(
        q3_5,
        [(opt_v1, 5), (opt_v2, 4), (opt_v3, 4), (opt_v4, 3), (opt_v5, 2)],
        na_option=opt_v_na
    )

    # --- 3.6 (Likert 1–5) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generic(
        q3_6,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 3.7 (Ja/Nein + k.A.) ---
    # Ja = 3, Nein = 5, k.A. = -
    db.session.add_all([
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q3_7.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 3.8 (Likert 1–5) ---
    # 3, 3, 3, 4, 5, -
    add_ipa_scores_generic(
        q3_8,
        [(opt_a1, 3), (opt_a2, 3), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

        # ========================================
    # Option Scores (nur RPA) für Dimension 4 – Fragen 4.1 bis 4.6
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    # Wir verwenden die bereits vorhandene Helper-Funktion:
    # add_rpa_scores_generic(question, option_value_pairs, na_option=None)

    # --- 4.1 (Datenstrukturierung: 1..3 + k.A.) ---
    # Skala: scale_data_structure (opt_ds1/opt_ds2/opt_ds3 + opt_ds_na)
    # Werte (RPA): strukturiert=5, semi=3, unstrukturiert=A, k.A.="-"
    add_rpa_scores_generic(
        q4_1,
        [(opt_ds1, 5), (opt_ds2, 3), (opt_ds3, "A")],
        na_option=opt_ds_na
    )

    # --- 4.2 (Ja/Nein + k.A.) ---
    # Ja=5, Nein=1, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.3 (Ja/Nein + k.A.) ---
    # Ja=5, Nein=1, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.4 (Ja/Nein + k.A.) ---
    # "-" für alle (Ja/Nein/k.A.)
    db.session.add_all([
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- 4.5 (Ja/Nein + k.A.) ---
    # "-" für alle (Ja/Nein/k.A.)
    db.session.add_all([
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- 4.6 (Ja/Nein + k.A.) ---
    # "-" für alle (Ja/Nein/k.A.)
    db.session.add_all([
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])
        # ========================================
    # Option Scores (nur IPA) für Dimension 4 – Fragen 4.1 bis 4.6
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    def add_ipa_score_generic(question, option_value_pairs, na_option=None):
        """
        option_value_pairs: Liste von Tupeln (ScaleOption, value)
        - value = Zahl  -> score=value, applicable=True
        - value = "A"   -> score=None, is_exclusion=True, applicable=True
        - value = None  -> score=None, applicable=False   (für "-")
        na_option: optional ScaleOption für k.A. (wird als "-" gesetzt)
        """
        for opt, val in option_value_pairs:
            if val == "A":
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=True,
                    is_applicable=True
                ))
            elif val is None:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
            else:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=float(val),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-" (nicht anwendbar), falls Option existiert
        if na_option is not None:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=na_option.id,
                automation_type="IPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))


    # --- 4.1 (Datenstrukturierung: 1..3 + k.A.) ---
    # Werte (IPA): strukturiert=5, semi=5, unstrukturiert=3, k.A.="-"
    add_ipa_score_generic(
        q4_1,
        [(opt_ds1, 5), (opt_ds2, 5), (opt_ds3, 3)],
        na_option=opt_ds_na
    )

    # --- 4.2 (Ja/Nein + k.A.) ---
    # Ja=5, Nein=1, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_2.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.3 (Ja/Nein + k.A.) ---
    # Ja=5, Nein=1, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_3.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.4 (Ja/Nein + k.A.) ---
    # Ja=3, Nein=5, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_4.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.5 (Ja/Nein + k.A.) ---
    # Ja=3, Nein=5, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_5.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 4.6 (Ja/Nein + k.A.) ---
    # Ja=3, Nein=5, k.A.="-"
    db.session.add_all([
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=3.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q4_6.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])
    # ========================================
    # Option Scores (RPA) für Dimension 5 – Fragen 5.1 bis 5.5
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    def add_rpa_scores_generics(question, option_value_pairs, na_option=None):
        """
        option_value_pairs: Liste von Tupeln (ScaleOption, value)
        - value = Zahl  -> score=value, applicable=True
        - value = "A"   -> score=None, is_exclusion=True, applicable=True
        - value = None  -> score=None, applicable=False   (für "-")
        na_option: optional ScaleOption für k.A. (wird als "-" gesetzt)
        """
        for opt, val in option_value_pairs:
            if val == "A":
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=None,
                    is_exclusion=True,
                    is_applicable=True
                ))
            elif val is None:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
            else:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="RPA",
                    score=float(val),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-" (nicht anwendbar), falls Option existiert
        if na_option is not None:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=na_option.id,
                automation_type="RPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))


    # --- 5.1 (Likert 1–5 + k.A.) ---
    # Werte: 1, 1, 3, 4, 5, "-"
    # (d.h. Option 2 bekommt score=1)
    add_rpa_scores_generics(
        q5_1,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.2 (Likert 1–5 + k.A.) ---
    # Werte: 1, 1, 3, 4, 5, "-"
    add_rpa_scores_generics(
        q5_2,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.3 (Ja/Nein + k.A.) ---
    # Ja = 5, Nein = A, k.A. = "-"
    db.session.add_all([
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=None,
            is_exclusion=True,   # A
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 5.4 (Likert 1–5 + k.A.) ---
    # Werte: 1, 1, 3, 4, 5, "-"
    add_rpa_scores_generics(
        q5_4,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.5 (Ja/Nein + k.A.) ---
    # Ja = 5, Nein = 1, k.A. = "-"
    db.session.add_all([
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])
        # ========================================
    # Option Scores (nur IPA) für Dimension 5 – Fragen 5.1 bis 5.5
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    def add_ipa_scores_generics(question, option_value_pairs, na_option=None):
        """
        option_value_pairs: Liste von Tupeln (ScaleOption, value)
        - value = Zahl  -> score=value, applicable=True
        - value = "A"   -> score=None, is_exclusion=True, applicable=True
        - value = None  -> score=None, applicable=False   (für "-")
        na_option: optional ScaleOption für k.A. (wird als "-" gesetzt)
        """
        for opt, val in option_value_pairs:
            if val == "A":
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=True,
                    is_applicable=True
                ))
            elif val is None:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=None,
                    is_exclusion=False,
                    is_applicable=False
                ))
            else:
                db.session.add(OptionScore(
                    question_id=question.id,
                    scale_option_id=opt.id,
                    automation_type="IPA",
                    score=float(val),
                    is_exclusion=False,
                    is_applicable=True
                ))

        # k.A. immer "-" (nicht anwendbar), falls Option existiert
        if na_option is not None:
            db.session.add(OptionScore(
                question_id=question.id,
                scale_option_id=na_option.id,
                automation_type="IPA",
                score=None,
                is_exclusion=False,
                is_applicable=False
            ))


    # --- 5.1 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generics(
        q5_1,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.2 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generics(
        q5_2,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.3 (Ja/Nein + k.A.) ---
    # Ja = 5, Nein = A, k.A. = "-"
    db.session.add_all([
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=None,
            is_exclusion=True,   # A
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_3.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

    # --- 5.4 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generics(
        q5_4,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 5.5 (Ja/Nein + k.A.) ---
    # Ja = 5, Nein = 1, k.A. = "-"
    db.session.add_all([
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=5.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=1.0,
            is_exclusion=False,
            is_applicable=True
        ),
        OptionScore(
            question_id=q5_5.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False  # "-"
        ),
    ])

        # ========================================
    # Option Scores (nur RPA) für Dimension 6 – Fragen 6.1 bis 6.13
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    # Wir nutzen wieder die vorhandene Helper-Funktion:
    # add_rpa_scores_generic(question, option_value_pairs, na_option=None)

    # --- 6.1 (Likert 1–5 + k.A.) ---
    # A, 1, 2, 3, 5, -
    add_rpa_scores_generic(
        q6_1,
        [(opt_a1, "A"), (opt_a2, 1), (opt_a3, 2), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.2 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_2,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.3 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_3,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.4 (Ja/Nein + k.A.) ---
    # Ja = "-", Nein = "-", k.A. = "-"
    # (Die Relevanz wird über die Skip-Logik gesteuert: bei "Ja" -> 6.5/6.6; bei "Nein" -> 6.7)
    db.session.add_all([
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_yes.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_no.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_na.id,
            automation_type="RPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- 6.5 (Likert 1–5 + k.A.) ---
    # A, A, 1, 3, 5, -
    add_rpa_scores_generic(
        q6_5,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.6 (Likert 1–5 + k.A.) ---
    # "-", "-", "-", "-", "-", "-"
    add_rpa_scores_generic(
        q6_6,
        [(opt_a1, None), (opt_a2, None), (opt_a3, None), (opt_a4, None), (opt_a5, None)],
        na_option=opt_a_na
    )

    # --- 6.7 (Likert 1–5 + k.A.) ---
    # 1, 1, 1, 3, 5, -
    add_rpa_scores_generic(
        q6_7,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.8 (Likert 1–5 + k.A.) ---
    # 1, 1, 1, 3, 5, -
    add_rpa_scores_generic(
        q6_8,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.9 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_9,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.10 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_10,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.11 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_11,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.12 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_rpa_scores_generic(
        q6_12,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.13 (Likert 1–5 + k.A.) ---
    # "-", "-", "-", "-", "-", "-"
    add_rpa_scores_generic(
        q6_13,
        [(opt_a1, None), (opt_a2, None), (opt_a3, None), (opt_a4, None), (opt_a5, None)],
        na_option=opt_a_na
    )
        # ========================================
    # Option Scores (nur IPA) für Dimension 6 – Fragen 6.1 bis 6.13
    # gemäß deiner Tabelle (A = Ausschluss, "-" = nicht anwendbar)
    # ========================================

    # Wir nutzen die bereits vorhandene Helper-Funktion aus deinem IPA-Block:
    # add_ipa_scores_generic(question, option_value_pairs, na_option=None)

    # --- 6.1 (Likert 1–5 + k.A.) ---
    # A, A, 1, 3, 5, -
    add_ipa_scores_generic(
        q6_1,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.2 (Likert 1–5 + k.A.) ---
    # A, 1, 2, 3, 5, -
    add_ipa_scores_generic(
        q6_2,
        [(opt_a1, "A"), (opt_a2, 1), (opt_a3, 2), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.3 (Likert 1–5 + k.A.) ---
    # 1, 1, 3, 4, 5, -
    add_ipa_scores_generic(
        q6_3,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.4 (Ja/Nein + k.A.) ---
    # Ja = "-", Nein = "-", k.A. = "-"
    # (Steuerung erfolgt über Skip-Logik: Ja -> 6.5/6.6; Nein -> 6.7)
    db.session.add_all([
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_yes.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_no.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
        OptionScore(
            question_id=q6_4.id,
            scale_option_id=opt_na.id,
            automation_type="IPA",
            score=None,
            is_exclusion=False,
            is_applicable=False
        ),
    ])

    # --- 6.5 (Likert 1–5 + k.A.) ---
    # A, A, 1, 3, 5, -
    add_ipa_scores_generic(
        q6_5,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, 1), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.6 (Likert 1–5 + k.A.) ---
    # A, A, A, 2, 5, -
    add_ipa_scores_generic(
        q6_6,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, "A"), (opt_a4, 2), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.7 (Likert 1–5 + k.A.) ---
    # A, A, A, 2, 5, -
    add_ipa_scores_generic(
        q6_7,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, "A"), (opt_a4, 2), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.8 (Likert 1–5 + k.A.) ---
    # A, A, A, 2, 5, -
    add_ipa_scores_generic(
        q6_8,
        [(opt_a1, "A"), (opt_a2, "A"), (opt_a3, "A"), (opt_a4, 2), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.9 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generic(
        q6_9,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.10 (Likert 1–5 + k.A.) ---
    # 1, 2, 3, 4, 5, -
    add_ipa_scores_generic(
        q6_10,
        [(opt_a1, 1), (opt_a2, 2), (opt_a3, 3), (opt_a4, 4), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.11 (Likert 1–5 + k.A.) ---
    # A, 1, 1, 2, 5, -
    add_ipa_scores_generic(
        q6_11,
        [(opt_a1, "A"), (opt_a2, 1), (opt_a3, 1), (opt_a4, 2), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.12 (Likert 1–5 + k.A.) ---
    # 1, 1, 2, 3, 5, -
    add_ipa_scores_generic(
        q6_12,
        [(opt_a1, 1), (opt_a2, 1), (opt_a3, 2), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )

    # --- 6.13 (Likert 1–5 + k.A.) ---
    # A, 1, 2, 3, 5, -
    add_ipa_scores_generic(
        q6_13,
        [(opt_a1, "A"), (opt_a2, 1), (opt_a3, 2), (opt_a4, 3), (opt_a5, 5)],
        na_option=opt_a_na
    )
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
