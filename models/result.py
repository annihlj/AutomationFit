from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

# -------------------------------------------------
# Tabelle: UseCase – erfasste Anwendungsfälle
# -------------------------------------------------
class UseCase(db.Model):
    __tablename__ = 'use_case'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text, nullable=True)
    industry = db.Column(db.String(80), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    evaluations = db.relationship('Evaluation', backref='use_case', lazy=True)


# -------------------------------------------------
# Tabelle: Criterion – Bewertungskriterien
# -------------------------------------------------
class Criterion(db.Model):
    __tablename__ = 'criterion'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    weight = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)


# -------------------------------------------------
# Tabelle: Evaluation – Einzelbewertungen je UseCase
# -------------------------------------------------
class Evaluation(db.Model):
    __tablename__ = 'evaluation'
    id = db.Column(db.Integer, primary_key=True)
    use_case_id = db.Column(db.Integer, db.ForeignKey('use_case.id'), nullable=False)
    criterion_id = db.Column(db.Integer, db.ForeignKey('criterion.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    criterion = db.relationship('Criterion')

    class Result(db.Model):
    #__tablename__ = 'result'
    id = db.Column(db.Integer, primary_key=True)
    use_case_id = db.Column(db.Integer, db.ForeignKey('use_case.id'), nullable=False)
    total_rpa = db.Column(db.Float, nullable=False)
    total_ipa = db.Column(db.Float, nullable=False)
    recommendation = db.Column(db.String(20))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
