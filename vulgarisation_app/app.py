import os
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re
import pytesseract
from openai import OpenAI
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm

st.set_page_config(page_title="mAidiClear", page_icon="🧠")

# Titre
st.markdown("<h1 style='text-align: center;'>🧠 mAidiClear</h1>", unsafe_allow_html=True)
st.markdown("---")
st.info("**Ce service est informatif uniquement. Aucun avis médical. Aucune donnée n’est stockée ou transmise.**")

# OpenAI
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Upload
uploaded_file = st.file_uploader("📤 Uploadez votre compte-rendu (PDF ou image)", type=["pdf", "png", "jpg", "jpeg"])
lang = st.selectbox("Langue de la vulgarisation :", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"

# Fonctions
def convertir_image_en_pdf(image_file):
    image = Image.open(image_file).convert("RGB")
    pdf_bytes = io.BytesIO()
    image.save(pdf_bytes, format="PDF")
    pdf_bytes.seek(0)
    return pdf_bytes

def extraire_texte_pdf(pdf_file):
    texte = ""
    with fitz.open(stream=pdf_file.read(), filetype="pdf") as doc:
        for page in doc:
            texte += page.get_text()
    return texte

def extraire_texte(uploaded_file):
    # Étape 1 : tentative standard
    if uploaded_file.name.lower().endswith(".pdf"):
        texte = extraire_texte_pdf(uploaded_file)
    else:
        pdf_file = convertir_image_en_pdf(uploaded_file)
        texte = extraire_texte_pdf(pdf_file)

    # Étape 2 : OCR si extraction vide
    if not texte.strip():
        st.warning("Aucun texte détecté — tentative d'OCR automatique...")
        try:
            image = Image.open(uploaded_file).convert("RGB")
            texte = pytesseract.image_to_string(image, lang="fra")
        except Exception as e:
            st.error(f"Erreur OCR : {e}")
            texte = ""
    return texte

def anonymiser_texte(texte):
    texte = re.sub(r'\b[A-Z][a-z]+\b', '[Nom]', texte)
    texte = re.sub(r'\b[A-Z]{2,}\b', '[TERME]', texte)
    return texte

def vulgariser(texte, lang):
    prompt = {
        "fr": "Tu es un médecin expert qui explique ce compte-rendu au patient de façon simple, sans donner de conseils médicaux.",
        "en": "You are a medical doctor explaining this report to the patient in plain language, without giving medical advice."
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
    temp_path = f"/tmp/vulgarisation_{datetime.now().timestamp()}.pdf"
    c = canvas.Canvas(temp_path, pagesize=A4)
    width, height = A4
    x_margin, y_margin = 2 * cm, height - 2 * cm
    line_height = 14

    c.setFont("Helvetica", 12)
    y = y_margin
    for line in texte_vulgarise.split("\n"):
        if y < 2 * cm:
            c.showPage()
            c.setFont("Helvetica", 12)
            y = y_margin
        c.drawString(x_margin, y, line)
        y -= line_height

    disclaimer = "\n\nDisclaimer : Ceci est une explication simplifiée à visée informative uniquement. Aucune donnée n’a été stockée. Contact : contact@maidiclear.fr"
    c.setFont("Helvetica", 8)
    for line in disclaimer.split("\n"):
        if y < 2 * cm:
            c.showPage()
            c.setFont("Helvetica", 8)
            y = y_margin
        c.drawString(x_margin, y, line)
        y -= line_height

    c.save()
    return temp_path

# Traitement principal
if uploaded_file:
    with st.spinner("⏳ Traitement en cours..."):
        texte_brut = extraire_texte(uploaded_file)
        if not texte_brut.strip():
            st.error("Impossible d'extraire le texte du document.")
        else:
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
