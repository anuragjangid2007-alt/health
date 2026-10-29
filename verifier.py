import re
import sqlite3
from pathlib import Path

from database import DB_PATH


def tokenize(text):
    """Convert text into searchable keywords."""
    if not text:
        return []

    words = re.findall(r"[a-zA-Z0-9]+", text.lower())

    stop_words = {
        "the", "is", "are", "was", "were", "what",
        "how", "why", "when", "where", "does", "do",
        "can", "could", "should", "would", "about",
        "and", "or", "of", "to", "in", "on", "for",
        "a", "an", "it", "this", "that", "with",
        "me", "my", "tell", "explain", "please"
    }

    return [
        word for word in words
        if word not in stop_words and len(word) > 2
    ]


def get_evidence(question, limit=3):
    """
    Find potentially relevant records in the local evidence database.

    Keyword matching only identifies potentially relevant sources.
    It does not prove that a healthcare claim is true.
    """

    keywords = tokenize(question)

    if not keywords:
        return []

    connection = None

    try:
        connection = sqlite3.connect(DB_PATH)
        connection.row_factory = sqlite3.Row

        rows = connection.execute(
            """
            SELECT *
            FROM evidence
            """
        ).fetchall()

        results = []

        for row in rows:
            item = dict(row)

            searchable_text = " ".join(
                str(value)
                for key, value in item.items()
                if value is not None
                and key.lower() not in {
                    "id", "created_at", "updated_at"
                }
            ).lower()

            score = sum(
                1 for keyword in keywords
                if keyword in searchable_text
            )

            if score > 0:
                item["_match_score"] = score
                results.append(item)

        results.sort(
            key=lambda item: item["_match_score"],
            reverse=True
        )

        return results[:max(1, min(limit, 10))]

    except sqlite3.Error as error:
        print("Evidence database error:", type(error).__name__)
        return []

    finally:
        if connection is not None:
            connection.close()


def verify_question(question):
    """
    Return a result structure suitable for use by the Flask app.
    """

    evidence = get_evidence(question)

    if not evidence:
        return {
            "status": "INSUFFICIENT_EVIDENCE",
            "message": (
                "No matching source was found in the local database. "
                "This does not mean the claim is true or false."
            ),
            "evidence": []
        }

    return {
        "status": "SOURCES_FOUND",
        "message": (
            "Potentially relevant sources were found. "
            "Keyword matching alone cannot verify a healthcare claim."
        ),
        "evidence": evidence
    }
