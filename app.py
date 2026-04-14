"""app.py - L'Interface Gradio pour l'Idéathon PACTE"""

import gradio as gr
import pandas as pd
from vision import process_idea
from database import insert_submission, get_leaderboard, get_leaderboard_by_school


ECOLES = ["SUP'COM", "IPEST", "ISSHT", "Autre"]

# --- Couleurs du thème PACTE ---
PACTE_THEME = """
:root {
    --pacte-blanc: #FFFFFF;
    --pacte-bleu-ciel: #87CEEB;
    --pacte-bleu-fonce: #5BA3D9;
    --pacte-gris-perle: #D3D3D3;
    --pacte-gris-clair: #F5F5F5;
    --pacte-bleu-acier: #4682B4;
}
.gradio-container {
    background: linear-gradient(135deg, var(--pacte-gris-clair) 0%, var(--pacte-blanc) 100%) !important;
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif !important;
}
.title-bar {
    background: linear-gradient(90deg, var(--pacte-bleu-acier), var(--pacte-bleu-ciel));
    color: white;
    padding: 20px;
    border-radius: 12px;
    text-align: center;
    margin-bottom: 20px;
}
.title-bar h1 { margin: 0; font-size: 2em; }
.title-bar p { margin: 5px 0 0 0; font-size: 1.1em; opacity: 0.9; }
.score-card {
    background: var(--pacte-blanc);
    border: 2px solid var(--pacte-bleu-ciel);
    border-radius: 10px;
    padding: 15px;
    text-align: center;
}
"""


def refresh_leaderboard():
    """Récupère le leaderboard actuel sous forme de DataFrame."""
    rows = get_leaderboard()
    if not rows:
        return pd.DataFrame(columns=["Nom", "École", "Score Total", "Impact", "Innovation", "Faisabilité"])
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "nom": "Nom",
        "ecole": "École",
        "score_total": "Score Total",
        "impact": "Impact",
        "innovation": "Innovation",
        "faisabilite": "Faisabilité",
    })
    return df[["Nom", "École", "Score Total", "Impact", "Innovation", "Faisabilité"]]


def refresh_leaderboard_school():
    """Récupère le leaderboard par école."""
    rows = get_leaderboard_by_school()
    if not rows:
        return pd.DataFrame(columns=["École", "Soumissions", "Score Moyen", "Meilleur Score"])
    df = pd.DataFrame(rows)
    df = df.rename(columns={
        "ecole": "École",
        "nb_submissions": "Soumissions",
        "score_moyen": "Score Moyen",
        "meilleur_score": "Meilleur Score",
    })
    return df[["École", "Soumissions", "Score Moyen", "Meilleur Score"]]


def submit_idea(nom: str, ecole: str, idee: str):
    """
    Soumet une idée, exécute la cascade IA, sauvegarde en base,
    et retourne les résultats + leaderboard mis à jour.
    """
    # Validation des entrées
    if not nom or not nom.strip():
        return (
            "⚠️ Veuillez entrer votre nom.",
            0, 0, 0, 0, "",
            refresh_leaderboard(),
            refresh_leaderboard_school(),
        )
    if not ecole:
        return (
            "⚠️ Veuillez sélectionner votre école.",
            0, 0, 0, 0, "",
            refresh_leaderboard(),
            refresh_leaderboard_school(),
        )
    if not idee or not idee.strip():
        return (
            "⚠️ Veuillez décrire votre idée.",
            0, 0, 0, 0, "",
            refresh_leaderboard(),
            refresh_leaderboard_school(),
        )

    try:
        result = process_idea(idee.strip())
    except Exception as e:
        return (
            f"❌ Erreur lors de l'analyse IA : {e}. Veuillez réessayer.",
            0, 0, 0, 0, "",
            refresh_leaderboard(),
            refresh_leaderboard_school(),
        )

    # Construction du message de statut
    if not result["valide"]:
        status = f"🔍 {result['raison']}"
        return (
            status,
            0, 0, 0, 0,
            result["feedback"],
            refresh_leaderboard(),
            refresh_leaderboard_school(),
        )

    # Sauvegarde en base
    try:
        insert_submission(
            nom=nom.strip(),
            ecole=ecole,
            idee=idee.strip(),
            impact=result["impact"],
            innovation=result["innovation"],
            faisabilite=result["faisabilite"],
            score_total=result["score_total"],
            feedback=result["feedback"],
        )
    except Exception as e:
        print(f"[app] Erreur sauvegarde BDD : {e}")

    status = f"✅ Idée validée ! {result['raison']}"

    return (
        status,
        result["impact"],
        result["innovation"],
        result["faisabilite"],
        result["score_total"],
        result["feedback"],
        refresh_leaderboard(),
        refresh_leaderboard_school(),
    )


# --- Construction de l'interface ---
with gr.Blocks(css=PACTE_THEME, title="Idéathon PACTE") as demo:

    # En-tête
    gr.HTML("""
        <div class="title-bar">
            <h1>🧠 Idéathon PACTE</h1>
            <p>Innovez pour la santé mentale — Soumettez votre idée et laissez l'IA vous guider !</p>
        </div>
    """)

    # --- Zone principale : deux colonnes ---
    with gr.Row():
        # Colonne gauche : Formulaire
        with gr.Column(scale=1):
            gr.Markdown("### 📝 Votre Soumission")
            input_nom = gr.Textbox(
                label="Nom",
                placeholder="Entrez votre nom...",
                lines=1,
            )
            input_ecole = gr.Dropdown(
                choices=ECOLES,
                label="École",
                value=None,
                allow_custom_value=True,
            )
            input_idee = gr.Textbox(
                label="Votre Idée",
                placeholder="Décrivez votre idée liée à la santé mentale...",
                lines=5,
                max_lines=10,
            )
            btn_submit = gr.Button(
                "🚀 Soumettre",
                variant="primary",
                size="lg",
            )

        # Colonne droite : Résultats IA
        with gr.Column(scale=1):
            gr.Markdown("### 🤖 Résultats de l'Analyse IA")
            output_status = gr.Textbox(label="Statut", interactive=False, lines=1)

            with gr.Row():
                score_impact = gr.Number(label="💪 Impact", value=0, minimum=0, maximum=10)
                score_innovation = gr.Number(label="💡 Innovation", value=0, minimum=0, maximum=10)
                score_faisabilite = gr.Number(label="🔧 Faisabilité", value=0, minimum=0, maximum=10)

            score_total = gr.Number(label="🏆 Score Total", value=0, minimum=0, maximum=30)
            output_feedback = gr.Textbox(
                label="💬 Feedback IA",
                interactive=False,
                lines=4,
            )

    # --- Leaderboard ---
    gr.Markdown("### 🏅 Leaderboard")
    with gr.Row():
        leaderboard_df = gr.Dataframe(
            value=refresh_leaderboard,
            headers=["Nom", "École", "Score Total", "Impact", "Innovation", "Faisabilité"],
            label="Top 10 Participants",
            interactive=False,
            every=30,
        )
        leaderboard_school_df = gr.Dataframe(
            value=refresh_leaderboard_school,
            headers=["École", "Soumissions", "Score Moyen", "Meilleur Score"],
            label="Classement par École",
            interactive=False,
            every=30,
        )

    # --- Connexion du bouton ---
    btn_submit.click(
        fn=submit_idea,
        inputs=[input_nom, input_ecole, input_idee],
        outputs=[
            output_status,
            score_impact,
            score_innovation,
            score_faisabilite,
            score_total,
            output_feedback,
            leaderboard_df,
            leaderboard_school_df,
        ],
    )

    # Note de bas de page
    gr.Markdown(
        "---\n*Idéathon PACTE — Propulsé par Groq, Gemini & Tavily | "
        "Chaque idée compte pour la santé mentale 💙*"
    )


if __name__ == "__main__":
    demo.launch(
        server_name="0.0.0.0",
        server_port=7860,
        share=False,
    )
