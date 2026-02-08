"""
Service für die Berechnung von Assessment-Ergebnissen
"""
from models.database import (
    Assessment, Answer, DimensionResult, TotalResult, 
    Question, OptionScore, Dimension
)
from extensions import db


class ScoringService:
    """Service zur Berechnung von RPA/IPA-Scores"""
    
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
        
        # 2. Berechne Dimension-Ergebnisse
        dimensions = Dimension.query.filter_by(
            questionnaire_version_id=assessment.questionnaire_version_id
        ).order_by(Dimension.sort_order).all()
        
        for dimension in dimensions:
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
