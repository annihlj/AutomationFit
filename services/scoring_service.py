"""
Service für die Berechnung von Assessment-Ergebnissen
Inkl. vollständiger Wirtschaftlichkeitsberechnung basierend auf Excel-Formeln
"""
from models.database import (
    Assessment, Answer, DimensionResult, TotalResult, 
    Question, OptionScore, Dimension, EconomicMetric
)
from extensions import db


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
        """Berechnet das Ergebnis für eine Dimension"""
        
        # Hole alle Antworten für diese Dimension
        questions = Question.query.filter_by(dimension_id=dimension.id).all()
        question_ids = [q.id for q in questions]
        
        answers = Answer.query.filter(
            Answer.assessment_id == assessment_id,
            Answer.question_id.in_(question_ids)
        ).all()
        
        scores = []
        is_excluded = False
        excluded_by_question_id = None
        
        for answer in answers:
            question = Question.query.get(answer.question_id)
            
            # Nur Single-Choice Fragen haben Scores
            if question.question_type == "single_choice" and answer.scale_option_id:
                # Hole den Score für diese Option
                option_score = OptionScore.query.filter_by(
                    question_id=question.id,
                    scale_option_id=answer.scale_option_id,
                    automation_type=automation_type
                ).first()
                
                if option_score:
                    # Prüfe auf Ausschluss
                    if option_score.is_exclusion:
                        is_excluded = True
                        excluded_by_question_id = question.id
                        break
                    
                    # Prüfe auf Anwendbarkeit
                    if option_score.is_applicable and option_score.score is not None:
                        scores.append(option_score.score)
        
        # Berechne Mittelwert
        mean_score = None
        if not is_excluded and scores:
            mean_score = sum(scores) / len(scores)
        
        # Speichere Ergebnis
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
        """
        Berechnet die wirtschaftliche Dimension (Dimension 7)
        Basiert auf Excel-Formeln
        """
        
        # Hole alle Antworten für diese Dimension
        questions = Question.query.filter_by(dimension_id=dimension.id).all()
        
        # Hole Antworten
        answers = Answer.query.filter(
            Answer.assessment_id == assessment_id,
            Answer.question_id.in_([q.id for q in questions])
        ).all()
        
        # Erstelle Mapping: Fragencode -> Wert
        values = {}
        for answer in answers:
            question = Question.query.get(answer.question_id)
            if answer.numeric_value is not None:
                values[question.code] = answer.numeric_value
        
        # Prüfe ob alle benötigten Werte vorhanden sind
        required_codes = ["1.6","7.1", "7.2", "7.3", "7.4", "7.5", "7.6", "7.7"]
        if not all(code in values for code in required_codes):
            # Nicht alle Werte vorhanden - keine Berechnung möglich
            print(f"⚠️ Wirtschaftlichkeit: Nicht alle Werte vorhanden. Fehlen: {set(required_codes) - set(values.keys())}")
            return
        
        # ========================================
        # WERTE EXTRAHIEREN
        # ========================================
        
        # C88: Einmalige Kosten
        anzahl_prozesse = values["1.6"]

        # C88: Einmalige Kosten
        einmalige_kosten = values["7.1"]
        
        # C89: Implementierungsstunden
        impl_stunden = values["7.2"]
        
        # C90: Laufende Kosten pro Jahr
        laufende_kosten_jahr = values["7.3"]
        
        # C91: Wartungsstunden pro Monat
        wartung_stunden_monat = values["7.4"]
        
        # C95: Häufigkeit pro Monat
        haeufigkeit_monat = values["7.5"]
        
        # C94: Bearbeitungszeit in Minuten
        bearbeitungszeit_min = values["7.6"]
        
        # C97: Verbleibende Zeit in Minuten
        verbleibende_zeit_min = values["7.7"]
        
        # Konstanten
        jahresarbeitsstunden = ScoringService.ANNUAL_WORK_HOURS_PER_FTE  # K96 = 1700
        kosten_pro_fte = ScoringService.COST_PER_FTE_YEAR  # 55000
        
        # ========================================
        # BERECHNUNGEN (Excel-Formeln)
        # ========================================
        
        # K93 = Häufigkeit pro Jahr
        haeufigkeit_jahr = haeufigkeit_monat * 12
        
        # K93/K96 = Stundensatz-Faktor
        stundensatz = kosten_pro_fte / jahresarbeitsstunden  # 55000 / 1700 = 32.35 €/h
        
        # ========================================
        # FTE-EINSPARUNG
        # Excel: =(((K94/60)*K95)/K96)*(1-((K97/60)/(K94/60)))
        # K94 = C94 (bearbeitungszeit_min)
        # K95 = K93 (haeufigkeit_jahr)
        # K96 = 1700
        # K97 = C97 (verbleibende_zeit_min)
        # ========================================
        
        # Umrechnung in Stunden
        bearbeitungszeit_h = bearbeitungszeit_min / 60
        verbleibende_zeit_h = verbleibende_zeit_min / 60
        
        # Gesamtzeit aktuell pro Jahr
        gesamtzeit_aktuell_h = bearbeitungszeit_h * haeufigkeit_jahr
        
        # Gesamtzeit nach Automatisierung
        gesamtzeit_neu_h = verbleibende_zeit_h * haeufigkeit_jahr
        
        # Zeitersparnis
        zeitersparnis_h = gesamtzeit_aktuell_h - gesamtzeit_neu_h
        
        # FTE-Einsparung
        # Original-Formel umgeformt:
        # = ((bearbeitungszeit_h * haeufigkeit_jahr) / jahresarbeitsstunden) * (1 - (verbleibende_zeit_h / bearbeitungszeit_h))
        # = (gesamtzeit_aktuell_h / jahresarbeitsstunden) * (1 - (verbleibende_zeit_h / bearbeitungszeit_h))
        # = zeitersparnis_h / jahresarbeitsstunden
        
        fte_einsparung = zeitersparnis_h / jahresarbeitsstunden
        
        # ========================================
        # PERSONELLER NUTZEN
        # Excel: =K90*K93
        # K90 = Zeitersparnis in Minuten pro Monat (oder ähnlich)
        # K93 = haeufigkeit_jahr
        # 
        # Interpretation: Personeller Nutzen = FTE-Einsparung * Kosten pro FTE
        # ========================================
        
        personeller_nutzen_euro = fte_einsparung * kosten_pro_fte
        
        # ========================================
        # INITIALE FIXKOSTEN
        # Excel: =(C88/C16)+(C89*(K93/K96))
        # C88 = einmalige_kosten
        # C16 = unklar (vermutlich 1 oder Anzahl Prozesse)
        # C89 = impl_stunden
        # K93 = haeufigkeit_jahr
        # K96 = jahresarbeitsstunden
        # 
        # Interpretation: C16 ist vermutlich 1 (keine Aufteilung)
        # Formel vereinfacht zu: einmalige_kosten + (impl_stunden * stundensatz)
        # ========================================
        
        # Initiale Fixkosten
        initiale_fixkosten = (einmalige_kosten / anzahl_prozesse) + (impl_stunden * stundensatz)
        
        # ========================================
        # VARIABLE KOSTEN PRO JAHR
        # Excel: =(C90)+((C91*12)*(K93/K96))
        # C90 = laufende_kosten_jahr
        # C91 = wartung_stunden_monat
        # K93 = haeufigkeit_jahr
        # K96 = jahresarbeitsstunden
        # 
        # Interpretation: 
        # Variable Kosten = laufende_kosten_jahr + (wartung_stunden_jahr * stundensatz)
        # ========================================
        
        wartung_stunden_jahr = wartung_stunden_monat * 12
        
        variable_kosten_jahr = laufende_kosten_jahr + (wartung_stunden_jahr * stundensatz)
        
        # ========================================
        # ROI (Return on Investment)
        # Excel: =((K89)-(K91+K92))/(K91+K92)
        # K89 = personeller_nutzen_euro
        # K91 = initiale_fixkosten
        # K92 = variable_kosten_jahr
        # 
        # ROI = (Nutzen - Kosten) / Kosten
        # ========================================
        
        gesamtkosten = initiale_fixkosten + variable_kosten_jahr
        
        if gesamtkosten > 0:
            roi = (personeller_nutzen_euro - gesamtkosten) / gesamtkosten
        else:
            roi = 0
        
        # ========================================
        # SPEICHERE METRIKEN
        # ========================================
        
        metrics = [
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,  # Gilt für beide
                key="roi",
                value=roi,
                unit="%"
            ),
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="personeller_nutzen",
                value=personeller_nutzen_euro,
                unit="€"
            ),
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="fte_einsparung",
                value=fte_einsparung,
                unit="FTE"
            ),
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="initiale_fixkosten",
                value=initiale_fixkosten,
                unit="€"
            ),
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="variable_kosten_jahr",
                value=variable_kosten_jahr,
                unit="€"
            ),
            # Zusätzliche Debug-Metriken
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="haeufigkeit_jahr",
                value=haeufigkeit_jahr,
                unit="Anzahl"
            ),
            EconomicMetric(
                assessment_id=assessment_id,
                automation_type=None,
                key="zeitersparnis_h_jahr",
                value=zeitersparnis_h,
                unit="Stunden"
            ),
        ]
        
        for metric in metrics:
            db.session.add(metric)
        
        print(f"✅ Wirtschaftlichkeit berechnet:")
        print(f"   - Häufigkeit/Jahr: {haeufigkeit_jahr}")
        print(f"   - FTE-Einsparung: {fte_einsparung:.2f}")
        print(f"   - Personeller Nutzen: {personeller_nutzen_euro:.2f} €")
        print(f"   - Initiale Fixkosten: {initiale_fixkosten:.2f} €")
        print(f"   - Variable Kosten/Jahr: {variable_kosten_jahr:.2f} €")
        print(f"   - ROI: {roi:.2%}")
        
        # ========================================
        # KONVERTIERE ROI ZU SCORE (1-5)
        # ========================================
        
        # Score-Logik:
        # ROI < 0%     -> Ausschluss
        # ROI 0-5%     -> Score 1
        # ROI 5-20%    -> Score 2
        # ROI 20-50%   -> Score 3
        # ROI 50-100%  -> Score 4
        # ROI > 100%   -> Score 5
        
        if roi < 0:
            # Negativer ROI = Ausschluss
            economic_score = None
            is_excluded = True
        elif roi < 0.05:
            economic_score = 1.0
            is_excluded = False
        elif roi < 0.20:
            economic_score = 2.0
            is_excluded = False
        elif roi < 0.50:
            economic_score = 3.0
            is_excluded = False
        elif roi < 1.0:
            economic_score = 4.0
            is_excluded = False
        else:
            economic_score = 5.0
            is_excluded = False
        
        # Speichere Dimension-Ergebnis für beide Automation-Types
        # (Wirtschaftlichkeit ist unabhängig von RPA/IPA)
        for automation_type in ["RPA", "IPA"]:
            dim_result = DimensionResult(
                assessment_id=assessment_id,
                dimension_id=dimension.id,
                automation_type=automation_type,
                mean_score=economic_score,
                is_excluded=is_excluded,
                excluded_by_question_id=None
            )
            db.session.add(dim_result)
    
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
