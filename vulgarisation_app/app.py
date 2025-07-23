import streamlit as st

st.set_page_config(page_title="mAidiClear : Vulgarisation de Compte Rendu Médical", page_icon="🩺")

st.markdown("<h1 style='text-align: center;'>🩺 mAidiClear</h1>", unsafe_allow_html=True)

st.markdown("""
<div style='text-align: center; font-size: 16px; color: gray;'>
<p>mAidiClear est un outil d’aide à la compréhension des comptes rendus médicaux.</p>
<p>Il simplifie leur contenu sans interprétation ni avis médical.</p>
<p>Ce service ne remplace en aucun cas une consultation ou un échange avec un professionnel de santé.</p>
<p>Aucune donnée n’est stockée ni transmise.</p>
</div>
""", unsafe_allow_html=True)


import os
import io
import re
import pdfplumber
from openai import OpenAI
import tempfile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
from reportlab.lib.styles import ParagraphStyle

# Config
lang = st.sidebar.selectbox("🌐 Language / Langue", ["Français", "English"])
is_fr = lang == "Français"

T = {
    "title": {"Français": "🩺 mAIdiClear : Vulgarisation de Compte Rendu Médical", "English": "🩺 mAIdiClear: Medical Report Explanation"},
    "upload": {"Français": "📄 Uploadez un compte rendu PDF", "English": "📄 Upload a medical report (PDF)"},
    "error": {"Français": "❌ Aucun texte détecté dans ce fichier.", "English": "❌ No readable text detected in this file."},
    "process": {"Français": "💬 Vulgariser le compte rendu", "English": "💬 Simplify the report"},
    "processing": {"Français": "Traitement en cours...", "English": "Processing..."},
    "done": {"Français": "✅ Vulgarisation terminée", "English": "✅ Simplification complete"},
    "result": {"Français": "📘 Résultat", "English": "📘 Result"},
    "download": {"Français": "📥 Télécharger au format PDF", "English": "📥 Download PDF"},
    "feedback": {"Français": "💬 Avez-vous des remarques ou questions ?", "English": "💬 Any feedback or question?"},
    "send": {"Français": "Envoyer", "English": "Send"},
    "disclaimer": {
        "Français": "⚠️ Ce document est une explication simplifiée à but informatif uniquement. Il ne constitue pas un avis médical. Aucun stockage ou transmission de données n\'a lieu.",
        "English": "⚠️ This is a simplified explanation for informational purposes only. It does not constitute medical advice. No data is stored or transmitted."
    }
}


client = OpenAI(api_key=st.secrets["openai_api_key"])

def anonymiser(texte):
    texte = re.sub(r"(?i)(nom|prénom|patient|docteur|dr)[ :]*[A-ZÉÈÀÂÊÎÔÛÇ\-]+", "[ANONYME]", texte)
    texte = re.sub(r"[A-Z]{2,}( [A-Z]{2,})*", "[ANONYME]", texte)
    texte = re.sub(r"\d{2}/\d{2}/\d{4}", "[DATE]", texte)
    texte = re.sub(r"\d{1,3} ?(ans|yo)", "[ÂGE]", texte, flags=re.IGNORECASE)
    texte = re.sub(r"\d{11,}", "[NUMÉRO]", texte)
    texte = re.sub(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", "[EMAIL]", texte)
    return texte

def get_prompt(texte, langue):
    if langue == "Français":
        return (
            "Tu es un médecin spécialiste en imagerie médicale. "
            "Ta mission est d’expliquer de manière neutre un compte rendu médical à un patient non médecin.\n\n"
            "Voici le compte rendu (déjà anonymisé) :\n\n"
            f"{texte}\n\n"
            "Ta réponse doit suivre ces règles :\n"
            "- Aucune mention de traitement ou de suivi.\n"
            "- Ne jamais inventer d'information : si quelque chose n'est pas dans le texte, dis-le simplement.\n"
            "- Aucun nom de radiologue, ni formule de politesse.\n"
            "- Utilise un langage clair, factuel, compréhensible par un patient, sans jargon.\n\n"
            "Structure la réponse comme suit :\n"
            "1. Résumé des résultats\n"
            "2. Explication pédagogique\n"
            "3. Impact potentiel (si cela est mentionné dans le texte)\n\n"
            "Ne sors jamais du cadre du contenu fourni."
        )
    else:
        return (
            "You are a medical imaging specialist. "
            "Your task is to explain a radiology report in plain language to a non-medical patient.\n\n"
            "Here is the anonymized report:\n\n"
            f"{texte}\n\n"
            "Your response must follow these rules:\n"
            "- No mention of treatment or follow-up.\n"
            "- Do not invent information: if something is not in the text, say so.\n"
            "- No mention of radiologist or polite phrases.\n"
            "- Use clear, factual language understandable by a non-doctor.\n\n"
            "Structure your response as:\n"
            "1. Summary of findings\n"
            "2. Educational explanation\n"
            "3. Potential impact (if mentioned)\n\n"
            "Stick strictly to the content provided."
        )

def vulgariser(texte, langue):
    prompt = get_prompt(texte, langue)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "You are a neutral medical explainer."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    return response.choices[0].message.content

def generer_pdf(texte, langue):
    temp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(temp.name, pagesize=A4, rightMargin=20, leftMargin=20, topMargin=20, bottomMargin=30)
    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle('Normal', fontName='Helvetica', fontSize=11, leading=14)
    disclaimer_style = ParagraphStyle('Disclaimer', fontSize=9, textColor='gray')

    flowables = []
    for line in texte.split("\n"):
        flowables.append(Paragraph(line.strip(), normal_style))
        flowables.append(Spacer(1, 5))
    flowables.append(Spacer(1, 10))
    flowables.append(Paragraph(T["disclaimer"][langue], disclaimer_style))

    doc.build(flowables)
    return temp.name

uploaded_file = st.file_uploader(T["upload"][lang], type=["pdf"])

if uploaded_file:
    with pdfplumber.open(io.BytesIO(uploaded_file.read())) as pdf:
        texte = "\n".join(page.extract_text() or "" for page in pdf.pages)

    if not texte.strip():
        st.error(T["error"][lang])
    else:
        texte_anonyme = anonymiser(texte)

        if st.button(T["process"][lang]):
            with st.spinner(T["processing"][lang]):
                texte_vulgarise = vulgariser(texte_anonyme, lang)
            st.success(T["done"][lang])
            st.subheader(T["result"][lang])
            st.write(texte_vulgarise)

            pdf_path = generer_pdf(texte_vulgarise, lang)
            with open(pdf_path, "rb") as f:
                st.download_button(T["download"][lang], data=f, file_name="vulgarisation.pdf", mime="application/pdf")
            os.remove(pdf_path)

feedback = st.text_area(T["feedback"][lang])
if st.button(T["send"][lang]):
    st.success("✅ Merci pour votre retour." if is_fr else "✅ Thank you for your feedback.")

