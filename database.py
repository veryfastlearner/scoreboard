"""database.py - La Mémoire : Gestion SQLite pour les soumissions et le leaderboard"""

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pacte_ideathon.db")


def get_connection():
    """Retourne une connexion à la base SQLite."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Initialise la base de données avec la table des soumissions."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nom TEXT NOT NULL,
            ecole TEXT NOT NULL,
            idee TEXT NOT NULL,
            impact INTEGER DEFAULT 0,
            innovation INTEGER DEFAULT 0,
            faisabilite INTEGER DEFAULT 0,
            score_total INTEGER DEFAULT 0,
            feedback TEXT DEFAULT '',
            date_submission TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def insert_submission(nom: str, ecole: str, idee: str, impact: int, innovation: int, faisabilite: int, score_total: int, feedback: str) -> int:
    """Insère une soumission dans la base et retourne son ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO submissions (nom, ecole, idee, impact, innovation, faisabilite, score_total, feedback)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (nom, ecole, idee, impact, innovation, faisabilite, score_total, feedback))
    conn.commit()
    row_id = cursor.lastrowid
    conn.close()
    return row_id


def get_leaderboard() -> list:
    """Récupère le top 10 des participants par score total."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT nom, ecole, score_total, impact, innovation, faisabilite
        FROM submissions
        ORDER BY score_total DESC
        LIMIT 10
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


def get_leaderboard_by_school() -> list:
    """Récupère le classement agrégé par école (score moyen et nombre de soumissions)."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT ecole,
               COUNT(*) as nb_submissions,
               ROUND(AVG(score_total), 1) as score_moyen,
               MAX(score_total) as meilleur_score
        FROM submissions
        GROUP BY ecole
        ORDER BY score_moyen DESC
    """)
    rows = cursor.fetchall()
    conn.close()
    return [dict(row) for row in rows]


# Initialisation automatique au import
init_db()
