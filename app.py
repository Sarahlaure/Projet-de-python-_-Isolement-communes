
import streamlit as st
import streamlit.components.v1 as components

from pathlib import Path

st.set_page_config(
    page_title="Mon Dashboard",
    layout="wide"
)

# Lire le fichier HTML
html_path = Path(__file__).parent / "isolement_communes.html"

html = html_path.read_text(encoding="utf-8")

# Afficher le dashboard
components.html(
    html,
    height=1200,
    scrolling=True
)
