"""
La Serena — punto de entrada.

Una sola app con dos secciones independientes (login compartido):
  🏗️ Obra          → obra.py         (contabilidad de la construcción)
  🏠 Copropiedad   → copropiedad.py  (gestión de la casa entre hermanos)
"""
import streamlit as st
from common import inject_css, load_users, init_session, render_login, render_header

st.set_page_config(page_title="La Serena", page_icon="🏡", layout="wide", initial_sidebar_state="collapsed")

# --- SECCIONES ---
pg_obra = st.Page("obra.py", title="Obra", icon="🏗️", url_path="obra", default=True)
pg_copro = st.Page("copropiedad.py", title="Copropiedad", icon="🏠", url_path="copropiedad")
pg = st.navigation([pg_obra, pg_copro], position="hidden")
seccion = "copro" if pg.url_path == "copropiedad" else "obra"

inject_css(seccion)

# --- SESIÓN Y LOGIN (una sola vez para ambas secciones) ---
KEYS_OBRA = ["modo_registro", "gasto_a_editar", "transfer_a_editar", "obra_modo", "etapa_a_editar", "avance_a_editar", "nueva_subetapa_parent"]
KEYS_COPRO = ["copro_modo", "copro_edit_id"]
init_session({k: None for k in KEYS_OBRA + KEYS_COPRO})
usuarios_df = load_users()

if not st.session_state.logueado:
    render_login(usuarios_df, "🏡", "La Serena", "Playa Serena",
                 "Obra y copropiedad de la casa", paleta=seccion)
    st.stop()

# --- CABECERA + SELECTOR DE SECCIÓN ---
def _logout():
    for k in KEYS_OBRA + KEYS_COPRO:
        st.session_state[k] = None
    st.session_state.tab_activa = 0

titulo = "La Serena · Obra" if seccion == "obra" else "La Serena · Copropiedad"
render_header("🏗️" if seccion == "obra" else "🏠", titulo, "Playa Serena", paleta=seccion, on_logout=_logout)

c_obra, c_copro = st.columns(2)
if c_obra.button("🏗️  Obra", type="primary" if seccion == "obra" else "secondary", use_container_width=True) and seccion != "obra":
    st.session_state.tab_activa = 0
    st.switch_page(pg_obra)
if c_copro.button("🏠  Copropiedad", type="primary" if seccion == "copro" else "secondary", use_container_width=True) and seccion != "copro":
    st.session_state.tab_activa = 0
    st.switch_page(pg_copro)

# --- SECCIÓN ACTIVA ---
pg.run()
