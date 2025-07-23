import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import pytesseract
import io
import re
from openai import OpenAI
from fpdf import FPDF
import os
from datetime import datetime

st.set_page_config(page_title="mAidiClear", page_icon="🧠")

# Titre
st.markdown("<h1 style='text-align: center;'>🧠 mAidiClear</h1>", unsafe_allow_html=True)
st.markdown("---")

# Disclaimer
st.info("**Ce service est informatif uniquement. Aucun avis médical. Aucune donnée n’est stockée ou transmise.**")

# Initialiser l'API OpenAI
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Upload
uploaded_file = st.file_uploader("📤 Uploadez votre compte-rendu (PDF ou image)", type=["pdf", "png", "jpg", "jpeg", "tiff", "bmp"])

# Langue
lang = st.selectbox("Langue de la vulgarisation :", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"

def extraire_texte_pdf(uploaded_file):
    texte = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            texte += page.get_text()
    return texte

def extraire_texte_image(uploaded_file):
    image = Image.open(uploaded_file).convert("RGB")
    return pytesseract.image_to_string(image, lang="fra")

def extraire_texte(uploaded_file):
    if uploaded_file.name.lower().endswith(".pdf"):
        return extraire_texte_pdf(uploaded_file)
    else:
        return extraire_texte_image(uploaded_file)

def anonymiser_texte(texte):
    texte = re.sub(r'\b[A-Z][a-z]+\b', '[Nom]', texte)
    texte = re.sub(r'\b[A-Z]{2,}\b', '[TERME]', texte)
    return texte

def vulgariser(texte, lang):
    prompt = {
        "fr": "Tu es un médecin expert qui explique ce compte-rendu au patient de façon simple, sans donner de conseils médicaux. Ne fais pas semblant de savoir si des infos manquent.",
        "en": "You are a medical doctor explaining this report to the patient in plain language, without giving medical advice. Do not invent information if anything is missing."
    }[lang]
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": texte}
            ],
            temperature=0.4
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Erreur API : {e}")
        return ""

def generer_pdf(texte_vulgarise):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)

    for line in texte_vulgarise.split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf.ln(10)
    pdf.set_font("Arial", "I", 8)
    pdf.multi_cell(0, 8, "\n\nDisclaimer : Ceci est une explication simplifiée à visée informative uniquement. Aucune donnée n’a été stockée. Contact : contact@maidiclear.fr")

    temp_path = f"/tmp/vulgarisation_{datetime.now().timestamp()}.pdf"
    pdf.output(temp_path)
    return temp_path

# Traitement principal
if uploaded_file:
    with st.spinner("⏳ Traitement en cours..."):
        texte_brut = extraire_texte(uploaded_file)
        texte_anonyme = anonymiser_texte(texte_brut)
        texte_vulgarise = vulgariser(texte_anonyme, lang_code)

    if texte_vulgarise:
        st.subheader("📝 Texte vulgarisé")
        st.write(texte_vulgarise)

        pdf_path = generer_pdf(texte_vulgarise)
        with open(pdf_path, "rb") as f:
            st.download_button(
                label="📄 Télécharger le résumé en PDF",
                data=f,
                file_name="compte_rendu_vulgarise.pdf",
                mime="application/pdf"
            )

        os.remove(pdf_path)
