"""
Datenbankmodelle für RPA/IPA-Bewertungssystem
"""
from datetime import datetime
from extensions import db

# ========================================
# FRAGEBOGEN-DEFINITION (Masterdaten)
# ========================================

class QuestionnaireVersion(db.Model):
    __tablename__ = "questionnaire_version"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    version = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    dimensions = db.relationship('Dimension', backref='questionnaire_version', lazy=True)
    questions = db.relationship('Question', backref='questionnaire_version', lazy=True)


class Dimension(db.Model):
    __tablename__ = "dimension"
    id = db.Column(db.Integer, primary_key=True)
    questionnaire_version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_version.id"), nullable=False)
    code = db.Column(db.String(10), nullable=False)
    name = db.Column(db.String(120), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    calc_method = db.Column(db.String(30), nullable=False, default="mean")

    # Relationships
    questions = db.relationship('Question', backref='dimension', lazy=True)


class Scale(db.Model):
    __tablename__ = "scale"
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(50), unique=True, nullable=False)
    label = db.Column(db.String(120), nullable=False)

    # Relationships
    options = db.relationship('ScaleOption', backref='scale', lazy=True)


class ScaleOption(db.Model):
    __tablename__ = "scale_option"
    id = db.Column(db.Integer, primary_key=True)
    scale_id = db.Column(db.Integer, db.ForeignKey("scale.id"), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    label = db.Column(db.String(255), nullable=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    is_na = db.Column(db.Boolean, default=False)

    __table_args__ = (
        db.UniqueConstraint("scale_id", "code", name="uq_scale_option"),
    )


class Question(db.Model):
    __tablename__ = "question"
    id = db.Column(db.Integer, primary_key=True)
    questionnaire_version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_version.id"), nullable=False)
    dimension_id = db.Column(db.Integer, db.ForeignKey("dimension.id"), nullable=False)
    code = db.Column(db.String(20), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), nullable=False)
    unit = db.Column(db.String(20), nullable=True)
    scale_id = db.Column(db.Integer, db.ForeignKey("scale.id"), nullable=True)
    sort_order = db.Column(db.Integer, nullable=False, default=0)
    
    # Neue Felder für Filterlogik
    is_filter_question = db.Column(db.Boolean, default=False)
    depends_on_question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=True)
    depends_on_option_id = db.Column(db.Integer, db.ForeignKey("scale_option.id"), nullable=True)
    filter_description = db.Column(db.Text, nullable=True)  # Beschreibung der Filterlogik

    __table_args__ = (
        db.UniqueConstraint("questionnaire_version_id", "code", name="uq_question_code"),
    )

    # Relationships
    scale = db.relationship('Scale', backref='questions')
    option_scores = db.relationship('OptionScore', backref='question', lazy=True)
    dependent_questions = db.relationship('Question', 
                                         backref=db.backref('parent_question', remote_side=[id]),
                                         foreign_keys=[depends_on_question_id])


class OptionScore(db.Model):
    __tablename__ = "option_score"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    scale_option_id = db.Column(db.Integer, db.ForeignKey("scale_option.id"), nullable=False)
    automation_type = db.Column(db.String(10), nullable=False)
    score = db.Column(db.Float, nullable=True)
    is_exclusion = db.Column(db.Boolean, default=False)
    is_applicable = db.Column(db.Boolean, default=True)

    __table_args__ = (
        db.UniqueConstraint("question_id", "scale_option_id", "automation_type", name="uq_option_score"),
    )

    # Relationships
    scale_option = db.relationship('ScaleOption', backref='scores')


# ========================================
# AUSFÜLLUNG & ANTWORTEN
# ========================================

class Process(db.Model):
    __tablename__ = "process"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    industry = db.Column(db.String(80))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assessments = db.relationship('Assessment', backref='process', lazy=True)


class Assessment(db.Model):
    __tablename__ = "assessment"
    id = db.Column(db.Integer, primary_key=True)
    process_id = db.Column(db.Integer, db.ForeignKey("process.id"), nullable=False)
    questionnaire_version_id = db.Column(db.Integer, db.ForeignKey("questionnaire_version.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    answers = db.relationship('Answer', backref='assessment', lazy=True)
    dimension_results = db.relationship('DimensionResult', backref='assessment', lazy=True)


class Answer(db.Model):
    __tablename__ = "answer"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    scale_option_id = db.Column(db.Integer, db.ForeignKey("scale_option.id"), nullable=True)
    numeric_value = db.Column(db.Float, nullable=True)

    __table_args__ = (
        db.UniqueConstraint("assessment_id", "question_id", name="uq_answer_once"),
    )

    # Relationships
    question_obj = db.relationship('Question', backref='answers')
    scale_option = db.relationship('ScaleOption', backref='answers')


# ========================================
# ERGEBNISSE
# ========================================

class DimensionResult(db.Model):
    __tablename__ = "dimension_result"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    dimension_id = db.Column(db.Integer, db.ForeignKey("dimension.id"), nullable=False)
    automation_type = db.Column(db.String(10), nullable=False)
    mean_score = db.Column(db.Float, nullable=True)
    is_excluded = db.Column(db.Boolean, default=False)
    excluded_by_question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=True)

    __table_args__ = (
        db.UniqueConstraint("assessment_id", "dimension_id", "automation_type", name="uq_dim_result"),
    )

    # Relationships
    dimension_obj = db.relationship('Dimension', backref='results')


class TotalResult(db.Model):
    __tablename__ = "total_result"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False, unique=True)
    total_rpa = db.Column(db.Float, nullable=True)
    total_ipa = db.Column(db.Float, nullable=True)
    rpa_excluded = db.Column(db.Boolean, default=False)
    ipa_excluded = db.Column(db.Boolean, default=False)
    recommendation = db.Column(db.String(20), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    assessment_obj = db.relationship('Assessment', backref='total_result', uselist=False)


class EconomicMetric(db.Model):
    __tablename__ = "economic_metric"
    id = db.Column(db.Integer, primary_key=True)
    assessment_id = db.Column(db.Integer, db.ForeignKey("assessment.id"), nullable=False)
    automation_type = db.Column(db.String(10), nullable=True)
    key = db.Column(db.String(50), nullable=False)
    value = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(20), nullable=True)

    # Relationships
    assessment_obj = db.relationship('Assessment', backref='economic_metrics')


class Hint(db.Model):
    """Hinweise für bestimmte Antworten"""
    __tablename__ = "hint"
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.Integer, db.ForeignKey("question.id"), nullable=False)
    scale_option_id = db.Column(db.Integer, db.ForeignKey("scale_option.id"), nullable=True)
    automation_type = db.Column(db.String(10), nullable=True)  # RPA/IPA/NULL (für beide)
    hint_text = db.Column(db.Text, nullable=False)
    hint_type = db.Column(db.String(20), default="info")  # info, warning, error
    
    # Relationships
    question_obj = db.relationship('Question', backref='hints')
    scale_option = db.relationship('ScaleOption', backref='hints')
