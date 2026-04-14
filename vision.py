"""vision.py - Le Cerveau : Appels API (Groq, Tavily, Gemini)"""

import json
import os
from dotenv import load_dotenv

load_dotenv()

from groq import Groq
import google.generativeai as genai
from tavily import TavilyClient

# --- Configuration des clients API ---
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

groq_client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None
genai.configure(api_key=GEMINI_API_KEY) if GEMINI_API_KEY else None
tavily_client = TavilyClient(api_key=TAVILY_API_KEY) if TAVILY_API_KEY else None

GROQ_MODEL = "llama3-8b-8192"
GEMINI_MODEL = "gemini-1.5-flash"


def _call_groq_validation(text: str) -> dict:
    """Utilise Groq (Llama-3-8b) pour valider si l'idée est liée à la santé mentale."""
    if not groq_client:
        raise RuntimeError("Groq client non configuré (clé API manquante)")

    prompt = (
        "Tu es un validateur d'idées pour un hackathon sur la santé mentale. "
        "Détermine si l'idée suivante est liée à la santé mentale (bien-être psychologique, "
        "soutien émotionnel, prévention du burnout, thérapie numérique, etc.). "
        "Réponds UNIQUEMENT en JSON avec deux champs :\n"
        '- "valide" : true ou false\n'
        '- "raison" : une phrase courte expliquant ta décision\n\n'
        f"Idée : {text}"
    )

    response = groq_client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=200,
    )

    raw = response.choices[0].message.content.strip()
    # Extraction du JSON même s'il est enveloppé dans des balises markdown
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def _call_gemini_validation(text: str) -> dict:
    """Fallback : utilise Gemini pour valider l'idée si Groq échoue."""
    if not GEMINI_API_KEY:
        return {"valide": True, "raison": "Validation par défaut (API indisponible)"}

    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = (
        "Tu es un validateur d'idées pour un hackathon sur la santé mentale. "
        "Détermine si l'idée suivante est liée à la santé mentale. "
        "Réponds UNIQUEMENT en JSON : {\"valide\": true/false, \"raison\": \"...\"}\n\n"
        f"Idée : {text}"
    )

    response = model.generate_content(prompt)
    raw = response.text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    return json.loads(raw)


def _call_tavily_search(query: str) -> str:
    """Utilise Tavily API pour extraire des informations contextuelles."""
    if not tavily_client:
        return "Aucune information contextuelle disponible (Tavily non configuré)."

    try:
        results = tavily_client.search(
            query=f"santé mentale {query}",
            max_results=3,
            search_depth="basic",
        )
        context_parts = []
        for r in results.get("results", []):
            context_parts.append(f"- {r.get('title', '')} : {r.get('content', '')}")
        return "\n".join(context_parts) if context_parts else "Aucun résultat contextuel trouvé."
    except Exception as e:
        return f"Recherche contextuelle indisponible : {e}"


def _call_gemini_scoring(text: str, context: str) -> dict:
    """Utilise Gemini 1.5 Flash pour générer un JSON de notation."""
    if not GEMINI_API_KEY:
        return {
            "Impact": 5,
            "Innovation": 5,
            "Faisabilité": 5,
            "Feedback": "Notation par défaut — API Gemini indisponible. Votre idée est intéressante, continuez à innover !",
        }

    model = genai.GenerativeModel(GEMINI_MODEL)
    prompt = (
        "Tu es un jury bienveillant et encourageant pour un idéathon sur la santé mentale (PACTE). "
        "Évalue l'idée suivante en tenant compte du contexte fourni. "
        "Attribue une note de 1 à 10 pour chaque critère et un feedback encourageant.\n\n"
        "Réponds UNIQUEMENT en JSON avec exactement ces champs :\n"
        '- "Impact" : note de 1 à 10 (potentiel d\'impact sur la santé mentale)\n'
        '- "Innovation" : note de 1 à 10 (caractère novateur)\n'
        '- "Faisabilité" : note de 1 à 10 (réalisabilité technique et pratique)\n'
        '- "Feedback" : commentaire encourageant et constructif (2-3 phrases)\n\n'
        f"Idée : {text}\n\n"
        f"Contexte recherché :\n{context}"
    )

    response = model.generate_content(prompt)
    raw = response.text.strip()
    if "```" in raw:
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    result = json.loads(raw)

    # S'assurer que les notes sont des entiers entre 1 et 10
    for key in ["Impact", "Innovation", "Faisabilité"]:
        if key in result:
            result[key] = max(1, min(10, int(result[key])))
        else:
            result[key] = 5

    if "Feedback" not in result or not result["Feedback"]:
        result["Feedback"] = "Continuez à développer vos idées, chaque contribution compte !"

    return result


def process_idea(text: str) -> dict:
    """
    Pipeline complet de traitement d'une idée :
    1. Validation via Groq (fallback Gemini)
    2. Recherche contextuelle Tavily
    3. Notation via Gemini

    Retourne un dict avec : valide, raison, impact, innovation, faisabilité, feedback, score_total
    """
    # --- Étape 1 : Validation ---
    validation = None
    try:
        validation = _call_groq_validation(text)
    except Exception as e:
        print(f"[vision] Groq échoué, fallback Gemini : {e}")
        try:
            validation = _call_gemini_validation(text)
        except Exception as e2:
            print(f"[vision] Gemini validation échoué aussi : {e2}")
            validation = {"valide": True, "raison": f"Validation automatique (APIs indisponibles : {e}, {e2})"}

    if not validation.get("valide", True):
        return {
            "valide": False,
            "raison": validation.get("raison", "Idée non liée à la santé mentale"),
            "impact": 0,
            "innovation": 0,
            "faisabilité": 0,
            "feedback": "Votre idée est intéressante, mais elle ne semble pas directement liée à la santé mentale. Essayez de la reformuler en mettant l'accent sur le bien-être psychologique ou le soutien émotionnel.",
            "score_total": 0,
        }

    # --- Étape 2 : Recherche contextuelle ---
    try:
        context = _call_tavily_search(text)
    except Exception as e:
        print(f"[vision] Tavily échoué : {e}")
        context = "Contexte non disponible."

    # --- Étape 3 : Notation ---
    try:
        scoring = _call_gemini_scoring(text, context)
    except Exception as e:
        print(f"[vision] Gemini scoring échoué : {e}")
        scoring = {
            "Impact": 5,
            "Innovation": 5,
            "Faisabilité": 5,
            "Feedback": f"Notation par défaut (API indisponible). Votre idée a du potentiel, continuez ! Détail : {e}",
        }

    score_total = scoring["Impact"] + scoring["Innovation"] + scoring["Faisabilité"]

    return {
        "valide": True,
        "raison": validation.get("raison", "Idée validée"),
        "impact": scoring["Impact"],
        "innovation": scoring["Innovation"],
        "faisabilité": scoring["Faisabilité"],
        "feedback": scoring["Feedback"],
        "score_total": score_total,
    }
