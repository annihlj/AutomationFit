"""
Service für die Berechnung von Assessment-Ergebnissen
Inkl. vollständiger Wirtschaftlichkeitsberechnung basierend auf Excel-Formeln
"""
from models.database import (
    Assessment, Answer, DimensionResult, TotalResult, 
    Question, OptionScore, Dimension, EconomicMetric
)
from extensions import db
from collections import defaultdict

class ScoringService:
    """Service zur Berechnung von RPA/IPA-Scores"""
    
    # Konstanten für Wirtschaftlichkeitsberechnung
    ANNUAL_WORK_HOURS_PER_FTE = 1700  # K96: Jahresarbeitsstunden pro FTE
    COST_PER_FTE_YEAR = 55000  # Kosten pro FTE/Jahr in Euro
    
    @staticmethod
    def calculate_assessment_results(assessment_id):
        """
        Berechnet alle Ergebnisse für ein Assessment
        
        Returns:
            TotalResult-Objekt
        """
        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} nicht gefunden")
        
        # 1. Lösche alte Ergebnisse (falls vorhanden)
        DimensionResult.query.filter_by(assessment_id=assessment_id).delete()
        TotalResult.query.filter_by(assessment_id=assessment_id).delete()
        EconomicMetric.query.filter_by(assessment_id=assessment_id).delete()
        
        # 2. Berechne Dimension-Ergebnisse
        dimensions = Dimension.query.filter_by(
            questionnaire_version_id=assessment.questionnaire_version_id
        ).order_by(Dimension.sort_order).all()
        
        for dimension in dimensions:
            if dimension.calc_method == "economic_score":
                # Spezielle Behandlung für wirtschaftliche Dimension
                ScoringService._calculate_economic_dimension(assessment_id, dimension)
            else:
                # Normale Berechnung für RPA und IPA
                for automation_type in ["RPA", "IPA"]:
                    ScoringService._calculate_dimension_result(
                        assessment_id, dimension, automation_type
                    )
        
        # 3. Berechne Gesamt-Ergebnis
        total_result = ScoringService._calculate_total_result(assessment_id)
        
        db.session.commit()
        
        return total_result
    
    @staticmethod
    def _calculate_dimension_result(assessment_id, dimension, automation_type):
        """Berechnet das Ergebnis für eine Dimension (inkl. multiple_choice Best-of)"""

        questions = Question.query.filter_by(dimension_id=dimension.id).all()
        question_ids = [q.id for q in questions]

        answers = Answer.query.filter(
            Answer.assessment_id == assessment_id,
            Answer.question_id.in_(question_ids)
        ).all()

        # Antworten nach question_id gruppieren (wichtig für multiple_choice)
        answers_by_q = defaultdict(list)
        for a in answers:
            answers_by_q[a.question_id].append(a)

        scores = []
        is_excluded = False
        excluded_by_question_id = None

        for question in questions:
            q_answers = answers_by_q.get(question.id, [])
            if not q_answers:
                continue

            # -----------------------------
            # SINGLE CHOICE
            # -----------------------------
            if question.question_type == "single_choice":
                a = q_answers[0]
                if not a.scale_option_id:
                    continue

                option_score = OptionScore.query.filter_by(
                    question_id=question.id,
                    scale_option_id=a.scale_option_id,
                    automation_type=automation_type
                ).first()

                if not option_score:
                    continue

                if option_score.is_exclusion:
                    is_excluded = True
                    excluded_by_question_id = question.id
                    break

                if option_score.is_applicable and option_score.score is not None:
                    scores.append(option_score.score)

            # -----------------------------
            # MULTIPLE CHOICE (Best-of)
            # -----------------------------
            elif question.question_type == "multiple_choice":
                option_ids = [a.scale_option_id for a in q_answers if a.scale_option_id]
                if not option_ids:
                    continue

                option_scores = OptionScore.query.filter(
                    OptionScore.question_id == question.id,
                    OptionScore.automation_type == automation_type,
                    OptionScore.scale_option_id.in_(option_ids)
                ).all()

                if not option_scores:
                    continue

                # Ausschluss schlägt alles
                if any(os.is_exclusion for os in option_scores):
                    is_excluded = True
                    excluded_by_question_id = question.id
                    break

                # nur anwendbare Scores berücksichtigen
                applicable = [
                    os.score for os in option_scores
                    if os.is_applicable and os.score is not None
                ]

                if applicable:
                    scores.append(max(applicable))

            # number hat in deinem Modell keine OptionScores -> ignorieren (wie bisher)
            else:
                continue

        mean_score = None
        if not is_excluded and scores:
            mean_score = sum(scores) / len(scores)

        dim_result = DimensionResult(
            assessment_id=assessment_id,
            dimension_id=dimension.id,
            automation_type=automation_type,
            mean_score=mean_score,
            is_excluded=is_excluded,
            excluded_by_question_id=excluded_by_question_id
        )
        db.session.add(dim_result)
    @staticmethod
    def _calculate_economic_dimension(assessment_id, dimension):
        """Berechnet Dimension 7 (Wirtschaftlichkeit) + speichert Kennzahlen & Score."""

        assessment = Assessment.query.get(assessment_id)
        if not assessment:
            raise ValueError(f"Assessment {assessment_id} nicht gefunden")

        # Antworten aus Dimension 7 laden
        q7_questions = Question.query.filter_by(dimension_id=dimension.id).all()
        q7_ids = [q.id for q in q7_questions]

        answers = Answer.query.filter(
            Answer.assessment_id == assessment_id,
            Answer.question_id.in_(q7_ids)
        ).all()

        values = {}
        for a in answers:
            if a.numeric_value is None:
                continue
            q = Question.query.get(a.question_id)
            if q:
                values[q.code] = a.numeric_value

        # 1.6 separat holen (liegt nicht in Dimension 7)
        q_1_6 = Question.query.filter_by(
            questionnaire_version_id=assessment.questionnaire_version_id,
            code="1.6"
        ).first()
        if q_1_6:
            a_1_6 = Answer.query.filter_by(
                assessment_id=assessment_id,
                question_id=q_1_6.id
            ).first()
            if a_1_6 and a_1_6.numeric_value is not None:
                values["1.6"] = a_1_6.numeric_value

        required = ["1.6", "7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"]
        missing = [c for c in required if c not in values]
        if missing:
            print(f"⚠️ Wirtschaftlichkeit: Werte fehlen: {missing}")
            return

        # Inputs
        anzahl_prozesse = max(float(values["1.6"]), 1.0)  # Schutz vor Division durch 0
        einmalige_kosten = float(values["7.1"])
        impl_stunden = float(values["7.2"])
        laufende_kosten_jahr = float(values["7.3"])
        wartung_stunden_monat = float(values["7.4"])
        haeufigkeit_monat = float(values["7.5"])
        bearbeitungszeit_min = float(values["7.6"])
        verbleibende_zeit_min = float(values["7.7"])

        jahresarbeitsstunden = float(ScoringService.ANNUAL_WORK_HOURS_PER_FTE)
        kosten_pro_fte = float(ScoringService.COST_PER_FTE_YEAR)

        # Baselines
        haeufigkeit_jahr = haeufigkeit_monat * 12.0
        stundensatz = kosten_pro_fte / jahresarbeitsstunden  # €/h

        # Zeit / FTE
        bearb_h = bearbeitungszeit_min / 60.0
        verbleib_h = verbleibende_zeit_min / 60.0

        gesamt_aktuell_h = bearb_h * haeufigkeit_jahr
        gesamt_neu_h = verbleib_h * haeufigkeit_jahr
        zeitersparnis_h = max(gesamt_aktuell_h - gesamt_neu_h, 0.0)

        fte_einsparung = zeitersparnis_h / jahresarbeitsstunden
        personeller_nutzen = fte_einsparung * kosten_pro_fte

        # Kosten
        initiale_fixkosten = (einmalige_kosten / anzahl_prozesse) + (impl_stunden * stundensatz)
        wartung_stunden_jahr = wartung_stunden_monat * 12.0
        variable_kosten_jahr = laufende_kosten_jahr + (wartung_stunden_jahr * stundensatz)

        gesamtkosten = initiale_fixkosten + variable_kosten_jahr
        roi = (personeller_nutzen - gesamtkosten) / gesamtkosten if gesamtkosten > 0 else 0.0

        # Kennzahlen speichern
        metrics = [
            ("roi", roi, "%"),
            ("personeller_nutzen", personeller_nutzen, "€"),
            ("fte_einsparung", fte_einsparung, "FTE"),
            ("initiale_fixkosten", initiale_fixkosten, "€"),
            ("variable_kosten_jahr", variable_kosten_jahr, "€"),
            ("haeufigkeit_jahr", haeufigkeit_jahr, "Anzahl"),
            ("zeitersparnis_h_jahr", zeitersparnis_h, "Stunden"),
        ]
        for key, val, unit in metrics:
            db.session.add(EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key=key,
                value=val,
                unit=unit
            ))

        # ROI -> Score
        if roi < 0:
            economic_score, is_excluded = None, True
        elif roi < 0.05:
            economic_score, is_excluded = 1.0, False
        elif roi < 0.20:
            economic_score, is_excluded = 2.0, False
        elif roi < 0.50:
            economic_score, is_excluded = 3.0, False
        elif roi < 1.0:
            economic_score, is_excluded = 4.0, False
        else:
            economic_score, is_excluded = 5.0, False

        # DimensionResult für RPA & IPA (gleich)
        for auto in ["RPA", "IPA"]:
            db.session.add(DimensionResult(
                assessment_id=assessment_id,
                dimension_id=dimension.id,
                automation_type=auto,
                mean_score=economic_score,
                is_excluded=is_excluded,
                excluded_by_question_id=None
            ))

        print(f"✅ Wirtschaftlichkeit: ROI={roi:.2%}, Score={economic_score}, Excluded={is_excluded}")
    @staticmethod
    def _calculate_total_result(assessment_id):
        """Berechnet das Gesamt-Ergebnis"""
        
        # Hole alle Dimension-Ergebnisse
        dim_results_rpa = DimensionResult.query.filter_by(
            assessment_id=assessment_id,
            automation_type="RPA"
        ).all()
        
        dim_results_ipa = DimensionResult.query.filter_by(
            assessment_id=assessment_id,
            automation_type="IPA"
        ).all()
        
        # RPA berechnen
        rpa_excluded = any(dr.is_excluded for dr in dim_results_rpa)
        rpa_scores = [dr.mean_score for dr in dim_results_rpa 
                      if not dr.is_excluded and dr.mean_score is not None]
        total_rpa = sum(rpa_scores) / len(rpa_scores) if rpa_scores else None
        
        # IPA berechnen
        ipa_excluded = any(dr.is_excluded for dr in dim_results_ipa)
        ipa_scores = [dr.mean_score for dr in dim_results_ipa 
                      if not dr.is_excluded and dr.mean_score is not None]
        total_ipa = sum(ipa_scores) / len(ipa_scores) if ipa_scores else None
        
        # Empfehlung bestimmen
        recommendation = ScoringService._determine_recommendation(
            total_rpa, total_ipa, rpa_excluded, ipa_excluded
        )
        
        # Speichere Gesamt-Ergebnis
        total_result = TotalResult(
            assessment_id=assessment_id,
            total_rpa=total_rpa,
            total_ipa=total_ipa,
            rpa_excluded=rpa_excluded,
            ipa_excluded=ipa_excluded,
            recommendation=recommendation
        )
        db.session.add(total_result)
        
        return total_result
    
    @staticmethod
    def _determine_recommendation(total_rpa, total_ipa, rpa_excluded, ipa_excluded):
        """Bestimmt die Empfehlung basierend auf den Scores"""
        
        threshold = 0.25
        
        # Fall 1: Beide ausgeschlossen
        if rpa_excluded and ipa_excluded:
            return "Keine Automatisierung"
        
        # Fall 2: Nur RPA ausgeschlossen
        if rpa_excluded and not ipa_excluded:
            return "IPA"
        
        # Fall 3: Nur IPA ausgeschlossen
        if ipa_excluded and not rpa_excluded:
            return "RPA"
        
        # Fall 4: Beide verfügbar - vergleiche Scores
        if total_rpa is not None and total_ipa is not None:
            diff = total_ipa - total_rpa
            
            if diff > threshold:
                return "IPA"
            elif diff < -threshold:
                return "RPA"
            else:
                return "Neutral"
        
        # Fall 5: Unvollständige Daten
        return "Unvollständig"
    
    @staticmethod
    def get_economic_metrics(assessment_id):
        """
        Holt die wirtschaftlichen Kennzahlen für ein Assessment
        
        Returns:
            Dict mit allen Kennzahlen
        """
        metrics = EconomicMetric.query.filter_by(assessment_id=assessment_id).all()
        
        result = {}
        for metric in metrics:
            result[metric.key] = {
                'value': metric.value,
                'unit': metric.unit
            }
        
        return result
