import streamlit as st
import os
import re
import pdfplumber
from openai import OpenAI
from dotenv import load_dotenv

# Chargement de la clé API
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Fonction d'anonymisation (à adapter selon tes besoins)
def anonymiser(texte):
    texte = re.sub(r'Nom\s?:\s?[A-Za-z]+', 'Nom : [anonymisé]', texte)
    texte = re.sub(r'Prénom\s?:\s?[A-Za-z]+', 'Prénom : [anonymisé]', texte)
    texte = re.sub(r'Date de naissance\s?:\s?[\d/]+', 'Date de naissance : [anonymisé]', texte)
    texte = re.sub(r'Médecin\s?:\s?[A-Za-z]+', 'Médecin : [anonymisé]', texte)
    texte = re.sub(r'Hôpital\s?:\s?[A-Za-z ]+', 'Hôpital : [anonymisé]', texte)
    return texte

# Fonction de vulgarisation
def vulgariser_texte(texte):
    prompt = f"""
    Tu es un médecin spécialisé qui explique simplement à un patient son compte rendu médical ci-dessous.
    Vulgarise clairement, sans inventer d'informations supplémentaires et sans donner d'avis médical.

    Compte rendu :
    {texte}

    Vulgarisation claire :
    """

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2,
        max_tokens=500,
    )

    return response.choices[0].message.content.strip()

# Configuration de l'interface
st.set_page_config(page_title="mAidiClear - Vulgarisation médicale", page_icon="🩺", layout="centered")
st.title("🩺 mAidiClear")

option = st.selectbox("Choisissez une méthode :", ("Uploader un PDF", "Copier-coller du texte"))

texte_extrait = ""

if option == "Uploader un PDF":
    fichier = st.file_uploader("📂 Chargez votre PDF médical", type="pdf")

    if fichier:
        with pdfplumber.open(fichier) as pdf:
            texte_extrait = "\n".join(page.extract_text() for page in pdf.pages if page.extract_text())

elif option == "Copier-coller du texte":
    texte_extrait = st.text_area("📋 Collez votre compte rendu médical ici :", height=250)

if st.button("Vulgariser"):
    if texte_extrait.strip() == "":
        st.warning("Veuillez fournir un texte ou un PDF avant de continuer.")
    else:
        with st.spinner("🔄 Traitement en cours..."):
            texte_anonyme = anonymiser(texte_extrait)
            texte_vulgarise = vulgariser_texte(texte_anonyme)
            
            st.subheader("📝 Texte vulgarisé :")
            st.markdown(texte_vulgarise)

# Disclaimer RGPD
st.markdown("""
---
🔒 **Confidentialité et RGPD :**  
Aucune donnée n'est stockée ou conservée après traitement.  
Cet outil ne remplace en aucun cas un avis médical professionnel.
""")
