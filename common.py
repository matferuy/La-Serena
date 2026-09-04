"""
Infraestructura compartida entre los aplicativos de La Serena:
  - App.py          → Obra (construcción)
  - Copropiedad.py  → Gestión de la copropiedad del inmueble

Contiene: estilos, conexión a Google Sheets / Drive / Calendar, login,
manejo de comprobantes múltiples y tipo de cambio.
"""
import streamlit as st
import pandas as pd
import os
import io
import datetime
import textwrap
import requests
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# =========================================================
# ESTILOS
# =========================================================
CSS_BASE = """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    #MainMenu { visibility: hidden; }
    footer { visibility: hidden; }
    header { visibility: hidden; }
    .block-container { padding-top: 0.5rem; max-width: 900px; }

    /* ── Botones ── */
    .stButton > button {
        border-radius: 14px; font-weight: 700; font-size: 0.92rem;
        height: 2.85rem; transition: all 0.2s cubic-bezier(.4,0,.2,1);
        letter-spacing: 0.01em;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, var(--grad-a) 0%, var(--grad-b) 100%);
        border: none; color: white;
        box-shadow: 0 4px 16px var(--grad-shadow);
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px var(--grad-shadow);
    }
    .stButton > button:not([kind="primary"]) {
        border: 1.5px solid rgba(148,163,184,0.3);
    }
    .stButton > button:not([kind="primary"]):hover {
        transform: translateY(-1px);
        border-color: var(--grad-a);
    }

    /* ── Inputs ── */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stSelectbox > div > div {
        border-radius: 12px !important;
        border: 1.5px solid rgba(148,163,184,0.25) !important;
        transition: border-color 0.15s ease !important;
    }
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus {
        border-color: var(--grad-a) !important;
        box-shadow: 0 0 0 3px var(--grad-shadow) !important;
    }

    /* ── Expanders ── */
    div[data-testid="stExpander"] {
        background: var(--secondary-background-color);
        border-radius: 18px;
        border: 1.5px solid rgba(148,163,184,0.13);
        margin-bottom: 10px;
        overflow: hidden;
        transition: box-shadow 0.2s ease;
    }
    div[data-testid="stExpander"]:hover {
        box-shadow: 0 4px 16px rgba(0,0,0,0.07);
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2px; background: var(--secondary-background-color);
        border-radius: 16px; padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px; font-weight: 700; font-size: 0.84rem;
        padding: 0.45rem 1rem;
    }
    .stTabs [aria-selected="true"] {
        background: var(--background-color) !important;
        box-shadow: 0 2px 10px rgba(0,0,0,0.09);
    }

    /* ── KPI Cards ── */
    .kpi-card {
        padding: 24px 26px 20px 26px;
        border-radius: 22px; margin-bottom: 14px;
        position: relative; overflow: hidden;
    }
    .kpi-card-primary {
        background: linear-gradient(135deg, var(--grad-dark) 0%, var(--grad-a) 60%, var(--grad-b) 100%);
        color: white; box-shadow: 0 10px 36px var(--grad-shadow);
    }
    .kpi-card-success {
        background: linear-gradient(135deg, #064E3B 0%, #059669 70%, #10B981 100%);
        color: white; box-shadow: 0 10px 36px rgba(5,150,105,0.3);
    }
    .kpi-card-amber {
        background: linear-gradient(135deg, #78350F 0%, #D97706 70%, #F59E0B 100%);
        color: white; box-shadow: 0 10px 36px rgba(217,119,6,0.3);
    }
    .kpi-card-rose {
        background: linear-gradient(135deg, #881337 0%, #E11D48 70%, #F43F5E 100%);
        color: white; box-shadow: 0 10px 36px rgba(225,29,72,0.3);
    }
    .kpi-card-slate {
        background: linear-gradient(135deg, #0F172A 0%, #334155 70%, #475569 100%);
        color: white; box-shadow: 0 10px 36px rgba(51,65,85,0.3);
    }
    .kpi-card-neutral {
        background: var(--background-color); color: var(--text-color);
        border: 1.5px solid rgba(148,163,184,0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }
    .kpi-icon {
        font-size: 2rem; margin-bottom: 12px; display: block; opacity: 0.9;
    }
    .kpi-label {
        font-size: 0.8rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 1.4px; opacity: 0.6; margin-bottom: 8px;
    }
    .kpi-value {
        font-size: 2.6rem; font-weight: 900;
        line-height: 1.05; letter-spacing: -0.04em; margin: 0;
    }
    .kpi-sub {
        font-size: 0.9rem; opacity: 0.55; font-weight: 500; margin-top: 6px;
    }

    /* ── Section Headers ── */
    .section-title {
        font-size: 1.05rem; font-weight: 800; letter-spacing: -0.02em;
        margin: 20px 0 14px 0; display: flex; align-items: center; gap: 8px;
    }
    .section-title::before {
        content: ''; display: block; width: 4px; height: 1.2em;
        background: linear-gradient(180deg, var(--grad-a), var(--grad-b));
        border-radius: 4px; flex-shrink: 0;
    }

    /* ── Badges de categoría ── */
    .badge {
        display: inline-block; padding: 2px 10px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 700; letter-spacing: 0.02em;
    }
    .badge-mat  { background: rgba(79,70,229,0.12);  color: #4F46E5; }
    .badge-mdo  { background: rgba(5,150,105,0.12);  color: #059669; }
    .badge-tram { background: rgba(245,158,11,0.12); color: #D97706; }
    .badge-ter  { background: rgba(239,68,68,0.12);  color: #DC2626; }
    .badge-otros{ background: rgba(100,116,139,0.12);color: #475569; }
    .badge-fijo { background: rgba(13,148,136,0.14); color: #0F766E; }
    .badge-uso  { background: rgba(245,158,11,0.14); color: #B45309; }
    .badge-ing  { background: rgba(5,150,105,0.12);  color: #059669; }
    .badge-cta  { background: rgba(51,65,85,0.12);   color: #334155; }

    /* ── Acción rápida cards ── */
    .action-card {
        background: var(--secondary-background-color);
        border: 1.5px solid rgba(148,163,184,0.15);
        border-radius: 20px; padding: 20px 18px;
        text-align: center; cursor: pointer;
        transition: all 0.2s ease;
    }
    .action-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
    .action-icon { font-size: 2rem; margin-bottom: 8px; }

    /* ── Progress bar ── */
    .balance-bar-wrap { border-radius: 100px; overflow: hidden; height: 12px; background: rgba(148,163,184,0.15); }
    .balance-bar-fill { height: 100%; border-radius: 100px; transition: width 0.6s cubic-bezier(.4,0,.2,1); }

    /* ── Etapa cards ── */
    .etapa-card {
        background: var(--background-color);
        border: 1.5px solid rgba(148,163,184,0.18);
        border-radius: 20px; padding: 20px 22px 16px 22px;
        margin-bottom: 14px;
        box-shadow: 0 2px 10px rgba(0,0,0,0.04);
    }
    .etapa-nombre { font-size: 1.05rem; font-weight: 800; letter-spacing: -0.02em; margin-bottom: 4px; }
    .etapa-desc { font-size: 0.82rem; opacity: 0.5; margin-bottom: 14px; }
    .etapa-progress-wrap { border-radius: 100px; overflow:hidden; height: 8px; background: rgba(148,163,184,0.15); margin-bottom: 6px; }
    .etapa-progress-fill { height: 100%; border-radius: 100px; }
    .estado-pendiente { background: rgba(100,116,139,0.12); color: #475569; }
    .estado-curso     { background: rgba(79,70,229,0.12);   color: #4F46E5; }
    .estado-completado{ background: rgba(5,150,105,0.12);   color: #059669; }

    /* ── Avance cards ── */
    .avance-card {
        background: var(--secondary-background-color);
        border-radius: 18px; padding: 16px 18px;
        margin-bottom: 10px; border: 1.5px solid rgba(148,163,184,0.13);
    }
    .avance-fecha { font-size: 0.72rem; font-weight:700; opacity:0.4; text-transform:uppercase; letter-spacing:0.8px; }
    .avance-titulo { font-size: 0.95rem; font-weight: 800; margin: 4px 0 6px 0; }
    .avance-detalle { font-size: 0.83rem; opacity: 0.65; line-height:1.5; }

    /* ── Calendario mensual ── */
    .cal-grid { display:grid; grid-template-columns: repeat(7, 1fr); gap: 4px; }
    .cal-head { font-size:0.7rem; font-weight:800; text-transform:uppercase; opacity:0.45; text-align:center; padding:4px 0; letter-spacing:0.5px; }
    .cal-day {
        min-height: 54px; border-radius: 10px; padding: 5px 6px;
        border: 1.5px solid rgba(148,163,184,0.15);
        background: var(--secondary-background-color);
        font-size: 0.75rem; position: relative; overflow: hidden;
    }
    .cal-day.empty { background: transparent; border-color: transparent; }
    .cal-day.today { border-color: var(--grad-a); box-shadow: 0 0 0 2px var(--grad-shadow); }
    .cal-num { font-weight: 800; opacity: 0.55; font-size: 0.72rem; }
    .cal-tag {
        display:block; margin-top:3px; border-radius:6px; padding:1px 5px;
        font-size:0.65rem; font-weight:700; color:white; white-space:nowrap;
        overflow:hidden; text-overflow:ellipsis;
    }

    /* ── Divider ── */
    .divider { border: none; border-top: 1.5px solid rgba(148,163,184,0.12); margin: 20px 0; }

    /* ── Login card ── */
    .login-hero {
        text-align: center; padding: 56px 0 32px 0;
    }
    .login-logo {
        width: 80px; height: 80px; border-radius: 24px; display: inline-flex;
        align-items: center; justify-content: center;
        background: linear-gradient(135deg, var(--grad-a), var(--grad-b));
        font-size: 2.2rem; margin-bottom: 20px;
        box-shadow: 0 12px 40px var(--grad-shadow);
    }
    </style>
"""

# Paletas por aplicativo: (color A, color B, color oscuro, sombra rgba)
PALETAS = {
    "obra":  ("#4F46E5", "#7C3AED", "#2E1065", "rgba(79,70,229,0.4)"),
    "copro": ("#0D9488", "#0EA5E9", "#134E4A", "rgba(13,148,136,0.4)"),
}

def inject_css(paleta="obra"):
    """Inyecta los estilos base con la paleta de colores del aplicativo."""
    a, b, dark, shadow = PALETAS.get(paleta, PALETAS["obra"])
    vars_css = f":root{{--grad-a:{a};--grad-b:{b};--grad-dark:{dark};--grad-shadow:{shadow};}}"
    base = textwrap.dedent(CSS_BASE).strip()
    base = base.replace("<style>", "<style>\n" + vars_css, 1)
    st.markdown(base, unsafe_allow_html=True)

def gradiente(paleta="obra"):
    a, b, _, _ = PALETAS.get(paleta, PALETAS["obra"])
    return f"linear-gradient(135deg,{a},{b})"

# =========================================================
# ARCHIVOS LOCALES (fallback sin Google Sheets)
# =========================================================
USERS_FILE = "usuarios.csv"
DIR_COMPROBANTES = "comprobantes"
DIR_BACKUPS = "backups"

for _d in [DIR_COMPROBANTES, DIR_BACKUPS]:
    try: os.makedirs(_d, exist_ok=True)
    except Exception: pass

USERS_COLS = ["Usuario", "Clave"]

# =========================================================
# GOOGLE SHEETS
# =========================================================
def has_secret(key):
    """True si la key existe en st.secrets (tolerante a que no haya secrets.toml)."""
    try: return key in st.secrets
    except Exception: return False

def get_secret(key, default=""):
    try: return st.secrets[key] if key in st.secrets else default
    except Exception: return default

USE_GSHEETS = has_secret("gcp_service_account") and has_secret("spreadsheet_id")

@st.cache_resource
def get_gspread_client():
    creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"])
    return gspread.authorize(creds)

@st.cache_resource
def get_spreadsheet():
    return get_gspread_client().open_by_key(st.secrets["spreadsheet_id"])

def _get_or_create_ws(sheet_name, columns):
    spreadsheet = get_spreadsheet()
    try:
        return spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        ws = spreadsheet.add_worksheet(sheet_name, rows=1000, cols=max(len(columns), 1))
        ws.update(values=[columns], range_name='A1')
        return ws

@st.cache_data(ttl=300)
def load_sheet_as_df(sheet_name, _columns):
    ws = _get_or_create_ws(sheet_name, _columns)
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=_columns)

def save_df_to_sheet(df, sheet_name):
    ws = _get_or_create_ws(sheet_name, df.columns.tolist())
    ws.clear()
    ws.update(values=[df.columns.tolist()] + df.astype(str).values.tolist(), range_name='A1')

def load_table(sheet_name, csv_file, columns):
    """Carga una tabla desde Google Sheets o CSV local, garantizando las columnas."""
    if USE_GSHEETS:
        df = load_sheet_as_df(sheet_name, columns)
    elif os.path.exists(csv_file):
        df = pd.read_csv(csv_file)
    else:
        df = pd.DataFrame(columns=columns)
    for c in columns:
        if c not in df.columns:
            df[c] = ""
    return df

def save_table(df, sheet_name, csv_file):
    """Guarda una tabla en Google Sheets (invalidando caché) o CSV local."""
    if USE_GSHEETS:
        save_df_to_sheet(df, sheet_name)
        load_sheet_as_df.clear()
    else:
        df.to_csv(csv_file, index=False)

@st.cache_resource
def get_sheets_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build('sheets', 'v4', credentials=creds)

def extraer_hyperlinks(spreadsheet_id, sheet_name):
    """Devuelve dict {fila_idx: {col_idx: url}} con los hyperlinks de todas las celdas."""
    service = get_sheets_service()
    result = service.spreadsheets().get(
        spreadsheetId=spreadsheet_id,
        ranges=[f"'{sheet_name}'"],
        includeGridData=True
    ).execute()
    links = {}
    try:
        rows = result['sheets'][0]['data'][0]['rowData']
        for r_idx, row in enumerate(rows):
            row_links = {}
            for c_idx, cell in enumerate(row.get('values', [])):
                url = cell.get('hyperlink', '')
                if not url:
                    for run in cell.get('textFormatRuns', []):
                        url = run.get('format', {}).get('link', {}).get('uri', '')
                        if url: break
                if url:
                    row_links[c_idx] = url
            if row_links:
                links[r_idx] = row_links
    except (KeyError, IndexError):
        pass
    return links

# =========================================================
# GOOGLE OAUTH (Drive + Calendar)
# =========================================================
DRIVE_FOLDER_NAME = "La Serena - Comprobantes"

def _oauth_creds():
    """Credenciales OAuth del usuario (refresh token) para Drive y Calendar."""
    if not has_secret("google_oauth_refresh_token"):
        raise RuntimeError("Falta google_oauth_refresh_token en los secrets. Corré get_drive_token.py para generarlo.")
    from google.oauth2.credentials import Credentials as OAuthCredentials
    from google.auth.transport.requests import Request
    creds = OAuthCredentials(
        token=None,
        refresh_token=st.secrets["google_oauth_refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=st.secrets["google_oauth_client_id"],
        client_secret=st.secrets["google_oauth_client_secret"]
    )
    creds.refresh(Request())
    return creds

def get_drive_service():
    return build('drive', 'v3', credentials=_oauth_creds())

def get_calendar_service():
    return build('calendar', 'v3', credentials=_oauth_creds())

def get_drive_folder_id():
    if has_secret("drive_folder_id"):
        return str(st.secrets["drive_folder_id"]).strip()
    available = []
    try:
        for section_key in st.secrets:
            available.append(section_key)
            try:
                section = st.secrets[section_key]
                if hasattr(section, '__getitem__') and "drive_folder_id" in section:
                    return str(section["drive_folder_id"]).strip()
            except Exception:
                pass
    except Exception:
        pass
    raise ValueError(f"No se encontró 'drive_folder_id' en los Secrets. Keys disponibles: {available}. Asegurate de que esté al nivel raíz del TOML, no dentro de una sección.")

def upload_comprobante(file_bytes, filename, mimetype):
    service = get_drive_service()
    folder_id = get_drive_folder_id()
    media = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mimetype)
    archivo = service.files().create(
        body={'name': filename, 'parents': [folder_id]},
        media_body=media, fields='id, webViewLink',
        supportsAllDrives=True
    ).execute()
    service.permissions().create(
        fileId=archivo['id'], body={'type': 'anyone', 'role': 'reader'},
        supportsAllDrives=True
    ).execute()
    return archivo['webViewLink']

# =========================================================
# COMPROBANTES MÚLTIPLES
# =========================================================
ADJUNTO_SEP = " ||| "

def parse_adjuntos(val):
    """Devuelve la lista de URLs/archivos guardados en el campo Archivo_Adjunto."""
    s = str(val or "").strip()
    if not s or s in ("Sin adjunto", "nan", "None"):
        return []
    return [u.strip() for u in s.split(ADJUNTO_SEP) if u.strip() and u.strip() != "Sin adjunto"]

def subir_comprobantes(archivos, prefijo, fecha=""):
    """Sube una lista de archivos. Devuelve (str_urls_unidas, lista_errores)."""
    urls, errores = [], []
    for archivo in archivos or []:
        try:
            file_bytes = bytes(archivo.getbuffer())
            base = f"{prefijo}_{fecha}_{archivo.name}" if fecha else f"{prefijo}_{archivo.name}"
            if USE_GSHEETS:
                urls.append(upload_comprobante(file_bytes, base, archivo.type))
            else:
                ruta = os.path.join(DIR_COMPROBANTES, base)
                with open(ruta, "wb") as f: f.write(file_bytes)
                urls.append(base)
        except Exception as e:
            errores.append(str(e))
    return ADJUNTO_SEP.join(urls), errores

def links_adjuntos_md(val, etiqueta="Ver comprobante"):
    """Markdown con links numerados a todos los comprobantes, o '' si no hay."""
    adj = parse_adjuntos(val)
    if not adj:
        return ""
    return " · ".join(f"[📎 {etiqueta} {i+1}]({u})" for i, u in enumerate(adj))

# =========================================================
# TIPO DE CAMBIO
# =========================================================
@st.cache_data(ttl=3600)
def obtener_tasa_usd_uyu():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        return round(requests.get(url, timeout=5).json()["rates"]["UYU"], 2)
    except Exception:
        return 39.00

def a_usd(row, tasa):
    """Convierte una fila con Moneda/Monto_Original/Monto_UYU a USD."""
    if str(row.get("Moneda", "")).upper() == "USD":
        return float(row.get("Monto_Original", 0) or 0)
    return float(row.get("Monto_UYU", 0) or 0) / tasa

# =========================================================
# USUARIOS Y LOGIN
# =========================================================
def load_users():
    if USE_GSHEETS:
        df = load_sheet_as_df("Usuarios", USERS_COLS)
        if df.empty:
            default = pd.DataFrame([{"Usuario": "admin", "Clave": "1234"}])
            save_df_to_sheet(default, "Usuarios")
            return default
        return df.astype(str)
    if os.path.exists(USERS_FILE): return pd.read_csv(USERS_FILE, dtype={"Usuario": str, "Clave": str})
    default_users = pd.DataFrame([{"Usuario": "admin", "Clave": "1234"}])
    default_users.to_csv(USERS_FILE, index=False)
    return default_users

def save_users(df):
    save_table(df, "Usuarios", USERS_FILE)

def socios(usuarios_df):
    """Usuarios no-admin (los socios / hermanos)."""
    return [u for u in usuarios_df["Usuario"].tolist() if str(u).lower() != "admin"]

def init_session(extra=None):
    defaults = {"logueado": False, "usuario_actual": "", "tab_activa": 0}
    if extra: defaults.update(extra)
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v

def render_login(usuarios_df, icono, titulo, subtitulo, descripcion, paleta="obra"):
    """Dibuja la pantalla de login. Devuelve True si el usuario quedó logueado en este run."""
    st.markdown(f"""
        <div class="login-hero">
            <div class="login-logo">{icono}</div>
            <h1 style='font-size:2.6rem; font-weight:900; letter-spacing:-0.05em; margin:0 0 6px 0;
                background:{gradiente(paleta)};
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>{titulo}</h1>
            <p style='font-size:0.9rem; font-weight:600; margin:0 0 4px 0; opacity:0.45; text-transform:uppercase; letter-spacing:1.5px;'>{subtitulo}</p>
            <p style='font-size:0.82rem; font-weight:400; margin:0; opacity:0.35;'>{descripcion}</p>
        </div>
    """, unsafe_allow_html=True)
    with st.container():
        with st.form("login_form"):
            usuario = st.text_input("Usuario", placeholder="Tu nombre de usuario")
            clave = st.text_input("Contraseña", type="password", placeholder="••••••••")
            submit_login = st.form_submit_button("Ingresar →", type="primary", use_container_width=True)
            if submit_login:
                if not usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"].astype(str) == str(clave))].empty:
                    st.session_state.logueado, st.session_state.usuario_actual = True, usuario
                    st.rerun()
                else:
                    st.error("Usuario o contraseña incorrectos.")
    return False

def render_header(icono, titulo, subtitulo, paleta="obra", link_otro=None, on_logout=None):
    """Cabecera con avatar, título, subtítulo, link al otro aplicativo y botón Salir."""
    col_perfil, col_salir = st.columns([4, 1])
    with col_perfil:
        initials = str(st.session_state.usuario_actual)[:2].upper()
        otro = ""
        if link_otro:
            otro = f"&nbsp;·&nbsp; <a href='{link_otro[1]}' target='_self' style='text-decoration:none;'>{link_otro[0]}</a>"
        st.markdown(f"""
            <div style='padding:12px 0 6px 0; display:flex; align-items:center; gap:12px;'>
                <div style='width:40px;height:40px;border-radius:12px;background:{gradiente(paleta)};
                    display:inline-flex;align-items:center;justify-content:center;
                    color:white;font-size:0.85rem;font-weight:800;flex-shrink:0;'>{initials}</div>
                <div>
                    <div style='font-size:1.15rem; font-weight:800; letter-spacing:-0.03em; line-height:1.2;'>{icono} {titulo}</div>
                    <div style='font-size:0.72rem; opacity:0.5; font-weight:600; margin-top:1px; text-transform:uppercase; letter-spacing:0.8px;'>Hola, {st.session_state.usuario_actual} &nbsp;·&nbsp; {subtitulo}{otro}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_salir:
        st.markdown("<div style='padding-top:14px;'></div>", unsafe_allow_html=True)
        if st.button("Salir", use_container_width=True):
            st.session_state.logueado = False
            if on_logout: on_logout()
            st.rerun()
    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

def restaurar_tab():
    """Tras cerrar un formulario, vuelve a la pestaña que estaba activa."""
    if st.session_state.get("tab_activa", 0) > 0:
        idx = st.session_state.tab_activa
        st.session_state.tab_activa = 0
        st.markdown(f"""<script>
            window.setTimeout(function() {{
                var tabs = window.parent.document.querySelectorAll('button[role="tab"]');
                if (tabs[{idx}]) tabs[{idx}].click();
            }}, 80);
        </script>""", unsafe_allow_html=True)

def kpi(col, clase, icono, label, valor, sub=""):
    with col:
        st.markdown(f'<div class="kpi-card {clase}"><span class="kpi-icon">{icono}</span><div class="kpi-label">{label}</div><div class="kpi-value">{valor}</div><div class="kpi-sub">{sub}</div></div>', unsafe_allow_html=True)

def fmt_monto(moneda, monto):
    simbolo = "U$S " if str(moneda).upper() == "USD" else "$ "
    return f"{simbolo}{float(monto):,.0f}"

def hoy():
    return datetime.date.today()
