import os
import streamlit as st
import fitz  # PyMuPDF
from PIL import Image
import io
import re
from openai import OpenAI
from fpdf import FPDF
from datetime import datetime
import requests

st.set_page_config(page_title="mAidiClear", page_icon="🧠")
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

# Titre
st.markdown("<h1 style='text-align: center;'>🧠 mAidiClear</h1>", unsafe_allow_html=True)
st.markdown("---")
st.info("**Ce service est informatif uniquement. Aucun avis médical. Aucune donnée n’est stockée ou transmise.**")

# Init OpenAI
client = OpenAI(api_key=st.secrets["openai_api_key"])

# Upload
uploaded_file = st.file_uploader("📤 Uploadez votre compte-rendu (PDF ou image)", type=["pdf", "png", "jpg", "jpeg"])

# Langue
lang = st.selectbox("Langue de la vulgarisation :", ["Français", "English"])
lang_code = "fr" if lang == "Français" else "en"

# ---------- Traitements ----------

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
    if uploaded_file.name.lower().endswith(".pdf"):
        return extraire_texte_pdf(uploaded_file)
    else:
        pdf_file = convertir_image_en_pdf(uploaded_file)
        return extraire_texte_pdf(pdf_file)

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
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Télécharger la police automatiquement
    font_dir = "/tmp/fonts"
    font_path = os.path.join(font_dir, "DejaVuSans.ttf")
    os.makedirs(font_dir, exist_ok=True)

    if not os.path.exists(font_path):
        url = "https://github.com/dejavu-fonts/dejavu-fonts/raw/version_2_37/ttf/DejaVuSans.ttf"
        r = requests.get(url)
        with open(font_path, "wb") as f:
            f.write(r.content)

    pdf.add_font("DejaVu", "", font_path, uni=True)
    pdf.set_font("DejaVu", size=12)

    for line in texte_vulgarise.split("\n"):
        pdf.multi_cell(0, 10, line)

    pdf.ln(10)
    pdf.set_font("DejaVu", size=8)
    disclaimer = "\n\nDisclaimer : Ceci est une explication simplifiée à visée informative uniquement. Aucune donnée n’a été stockée. Contact : contact@maidiclear.fr"
    pdf.multi_cell(0, 8, disclaimer)

    temp_path = f"/tmp/vulgarisation_{datetime.now().timestamp()}.pdf"
    pdf.output(temp_path)
    return temp_path

# ---------- Affichage ----------

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
