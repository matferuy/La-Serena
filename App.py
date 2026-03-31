import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import uuid
import io
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide", initial_sidebar_state="collapsed")

# --- DISEÑO ---
st.markdown("""
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
        background: linear-gradient(135deg, #4F46E5 0%, #7C3AED 100%);
        border: none; color: white;
        box-shadow: 0 4px 16px rgba(79,70,229,0.4);
    }
    .stButton > button[kind="primary"]:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(79,70,229,0.55);
    }
    .stButton > button:not([kind="primary"]) {
        border: 1.5px solid rgba(148,163,184,0.3);
    }
    .stButton > button:not([kind="primary"]):hover {
        transform: translateY(-1px);
        border-color: rgba(79,70,229,0.4);
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
        border-color: #4F46E5 !important;
        box-shadow: 0 0 0 3px rgba(79,70,229,0.12) !important;
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
        background: linear-gradient(135deg, #2E1065 0%, #4F46E5 60%, #7C3AED 100%);
        color: white; box-shadow: 0 10px 36px rgba(79,70,229,0.32);
    }
    .kpi-card-success {
        background: linear-gradient(135deg, #064E3B 0%, #059669 70%, #10B981 100%);
        color: white; box-shadow: 0 10px 36px rgba(5,150,105,0.3);
    }
    .kpi-card-amber {
        background: linear-gradient(135deg, #78350F 0%, #D97706 70%, #F59E0B 100%);
        color: white; box-shadow: 0 10px 36px rgba(217,119,6,0.3);
    }
    .kpi-card-neutral {
        background: var(--background-color); color: var(--text-color);
        border: 1.5px solid rgba(148,163,184,0.2);
        box-shadow: 0 2px 12px rgba(0,0,0,0.05);
    }
    .kpi-icon {
        font-size: 1.6rem; margin-bottom: 10px; display: block; opacity: 0.9;
    }
    .kpi-label {
        font-size: 0.67rem; font-weight: 800; text-transform: uppercase;
        letter-spacing: 1.4px; opacity: 0.6; margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 2.1rem; font-weight: 900;
        line-height: 1.05; letter-spacing: -0.04em; margin: 0;
    }
    .kpi-sub {
        font-size: 0.75rem; opacity: 0.55; font-weight: 500; margin-top: 4px;
    }

    /* ── Section Headers ── */
    .section-title {
        font-size: 1.05rem; font-weight: 800; letter-spacing: -0.02em;
        margin: 20px 0 14px 0; display: flex; align-items: center; gap: 8px;
    }
    .section-title::before {
        content: ''; display: block; width: 4px; height: 1.2em;
        background: linear-gradient(180deg, #4F46E5, #7C3AED);
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

    /* ── Divider ── */
    .divider { border: none; border-top: 1.5px solid rgba(148,163,184,0.12); margin: 20px 0; }

    /* ── Login card ── */
    .login-hero {
        text-align: center; padding: 56px 0 32px 0;
    }
    .login-logo {
        width: 80px; height: 80px; border-radius: 24px; display: inline-flex;
        align-items: center; justify-content: center;
        background: linear-gradient(135deg, #4F46E5, #7C3AED);
        font-size: 2.2rem; margin-bottom: 20px;
        box-shadow: 0 12px 40px rgba(79,70,229,0.4);
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_FILE = "contabilidad_casa.csv"
USERS_FILE = "usuarios.csv"
TRANSFERS_FILE = "transferencias.csv"
DIR_COMPROBANTES = "comprobantes"
DIR_BACKUPS = "backups"

for d in [DIR_COMPROBANTES, DIR_BACKUPS]:
    try: os.makedirs(d, exist_ok=True)
    except: pass

# --- GOOGLE SHEETS ---
USE_GSHEETS = "gcp_service_account" in st.secrets and "spreadsheet_id" in st.secrets

SHEET_NAMES = {DATA_FILE: "Gastos", TRANSFERS_FILE: "Transferencias", USERS_FILE: "Usuarios"}
GASTOS_COLS = ["ID", "Fecha", "Concepto", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Pagado_por", "Categoria", "Archivo_Adjunto", "Modificado_por_Admin"]
TRANSFERS_COLS = ["ID", "Fecha", "Origen", "Destino", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Archivo_Adjunto", "Modificado_por_Admin"]
USERS_COLS = ["Usuario", "Clave"]

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
        ws = spreadsheet.add_worksheet(sheet_name, rows=1000, cols=len(columns))
        ws.update(values=[columns], range_name='A1')
        return ws

@st.cache_data(ttl=60)
def load_sheet_as_df(sheet_name, _columns):
    ws = _get_or_create_ws(sheet_name, _columns)
    records = ws.get_all_records()
    return pd.DataFrame(records) if records else pd.DataFrame(columns=_columns)

def save_df_to_sheet(df, sheet_name):
    ws = _get_or_create_ws(sheet_name, df.columns.tolist())
    ws.clear()
    ws.update(values=[df.columns.tolist()] + df.astype(str).values.tolist(), range_name='A1')

# --- GOOGLE DRIVE ---
DRIVE_FOLDER_NAME = "La Serena - Comprobantes"

@st.cache_resource
def get_sheets_service():
    creds = Credentials.from_service_account_info(
        st.secrets["gcp_service_account"],
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    return build('sheets', 'v4', credentials=creds)

def extraer_hyperlinks(spreadsheet_id, sheet_name):
    """Devuelve dict {fila_idx: url} con los hyperlinks de todas las celdas."""
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

@st.cache_resource
def get_drive_service():
    if "google_oauth_refresh_token" in st.secrets:
        from google.oauth2.credentials import Credentials as OAuthCredentials
        creds = OAuthCredentials(
            token=None,
            refresh_token=st.secrets["google_oauth_refresh_token"],
            token_uri="https://oauth2.googleapis.com/token",
            client_id=st.secrets["google_oauth_client_id"],
            client_secret=st.secrets["google_oauth_client_secret"]
        )
    else:
        creds = Credentials.from_service_account_info(
            st.secrets["gcp_service_account"],
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        if "drive_impersonate_email" in st.secrets:
            creds = creds.with_subject(st.secrets["drive_impersonate_email"])
    return build('drive', 'v3', credentials=creds)

def get_drive_folder_id():
    # Intenta top-level primero, luego busca en secciones anidadas
    if "drive_folder_id" in st.secrets:
        return str(st.secrets["drive_folder_id"]).strip()
    # Busca en secciones anidadas (por si el usuario puso la key bajo [gcp_service_account] u otra sección)
    for section_key in st.secrets:
        try:
            section = st.secrets[section_key]
            if hasattr(section, '__getitem__') and "drive_folder_id" in section:
                return str(section["drive_folder_id"]).strip()
        except Exception:
            pass
    # Armar mensaje útil con las keys disponibles
    available = list(st.secrets.keys())
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

# --- FUNCIÓN: OBTENER TIPO DE CAMBIO AUTOMÁTICO ---
@st.cache_data(ttl=3600)
def obtener_tasa_usd_uyu():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        return round(requests.get(url, timeout=5).json()["rates"]["UYU"], 2)
    except:
        return 39.00

# --- FUNCIONES DE DATOS Y LOGS ---
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

def load_data():
    if USE_GSHEETS:
        df = load_sheet_as_df("Gastos", GASTOS_COLS)
        if not df.empty:
            if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
            if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
            else: df["Modificado_por_Admin"] = df["Modificado_por_Admin"].isin([True, "True", "true", 1, "1"])
        return df
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
        if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
        df.to_csv(DATA_FILE, index=False)
        return df
    return pd.DataFrame(columns=GASTOS_COLS)

def load_transfers():
    if USE_GSHEETS:
        df = load_sheet_as_df("Transferencias", TRANSFERS_COLS)
        if not df.empty:
            if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
            if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
            else: df["Modificado_por_Admin"] = df["Modificado_por_Admin"].isin([True, "True", "true", 1, "1"])
        return df
    if os.path.exists(TRANSFERS_FILE):
        df = pd.read_csv(TRANSFERS_FILE)
        if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
        if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
        df.to_csv(TRANSFERS_FILE, index=False)
        return df
    return pd.DataFrame(columns=TRANSFERS_COLS)

def save_data(df, file_name):
    if USE_GSHEETS:
        save_df_to_sheet(df, SHEET_NAMES[file_name])
        st.cache_data.clear()
    else:
        df.to_csv(file_name, index=False)

def generar_respaldo_excel(df_g, df_t):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre = f"respaldo_{timestamp}.xlsx"
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df_g.to_excel(writer, sheet_name="Gastos", index=False)
        df_t.to_excel(writer, sheet_name="Transferencias", index=False)
    datos = buffer.getvalue()
    try:
        ruta = os.path.join(DIR_BACKUPS, nombre)
        with open(ruta, "wb") as f: f.write(datos)
    except Exception:
        ruta = nombre
    return ruta, nombre, datos

# --- INICIALIZACIÓN DE SESIÓN ---
if "logueado" not in st.session_state: st.session_state.logueado = False
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = ""
if "gasto_a_editar" not in st.session_state: st.session_state.gasto_a_editar = None
if "transfer_a_editar" not in st.session_state: st.session_state.transfer_a_editar = None
if "modo_registro" not in st.session_state: st.session_state.modo_registro = None

usuarios_df = load_users()

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.markdown("""
        <div class="login-hero">
            <div class="login-logo">🏡</div>
            <h1 style='font-size:2.6rem; font-weight:900; letter-spacing:-0.05em; margin:0 0 6px 0;
                background:linear-gradient(135deg,#4F46E5,#7C3AED);
                -webkit-background-clip:text; -webkit-text-fill-color:transparent;'>La Serena</h1>
            <p style='font-size:0.9rem; font-weight:600; margin:0 0 4px 0; opacity:0.45; text-transform:uppercase; letter-spacing:1.5px;'>Playa Serena · Proyecto</p>
            <p style='font-size:0.82rem; font-weight:400; margin:0; opacity:0.35;'>Contabilidad compartida de la construcción</p>
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

# --- APLICACIÓN PRINCIPAL ---
else:
    df_gastos = load_data()
    df_transfers = load_transfers()
    es_admin = st.session_state.usuario_actual.lower() == "admin"

    # --- CABECERA ---
    total_inv = df_gastos["Monto_UYU"].sum() if not df_gastos.empty else 0
    col_perfil, col_salir = st.columns([4, 1])
    with col_perfil:
        initials = st.session_state.usuario_actual[:2].upper()
        st.markdown(f"""
            <div style='padding:12px 0 6px 0; display:flex; align-items:center; gap:12px;'>
                <div style='width:40px;height:40px;border-radius:12px;background:linear-gradient(135deg,#4F46E5,#7C3AED);
                    display:inline-flex;align-items:center;justify-content:center;
                    color:white;font-size:0.85rem;font-weight:800;flex-shrink:0;'>{initials}</div>
                <div>
                    <div style='font-size:1.15rem; font-weight:800; letter-spacing:-0.03em; line-height:1.2;'>🏡 La Serena</div>
                    <div style='font-size:0.72rem; opacity:0.4; font-weight:600; margin-top:1px; text-transform:uppercase; letter-spacing:0.8px;'>Hola, {st.session_state.usuario_actual} &nbsp;·&nbsp; ${total_inv:,.0f} UYU invertidos</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
    with col_salir:
        st.markdown("<div style='padding-top:14px;'></div>", unsafe_allow_html=True)
        if st.button("Salir", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.modo_registro = None
            st.session_state.gasto_a_editar = None
            st.session_state.transfer_a_editar = None
            st.rerun()

    st.markdown("<hr class='divider'>", unsafe_allow_html=True)

    # --- ACCIONES RÁPIDAS ---
    if st.session_state.modo_registro is None and st.session_state.gasto_a_editar is None and st.session_state.transfer_a_editar is None:
        col_btn_g, col_btn_t = st.columns(2)
        if col_btn_g.button("🛒  Registrar Gasto", type="primary", use_container_width=True):
            st.session_state.modo_registro = "gasto"
            st.rerun()
        if col_btn_t.button("💸  Registrar Transferencia", use_container_width=True):
            st.session_state.modo_registro = "transferencia"
            st.rerun()
        st.markdown("<div style='margin-bottom:6px;'></div>", unsafe_allow_html=True)

    # =========================================================
    # VISTA 1: FORMULARIO DE NUEVO GASTO
    # =========================================================
    if st.session_state.modo_registro == "gasto":
        st.markdown('<div class="section-title">Registrar Compra o Pago</div>', unsafe_allow_html=True)
        with st.container():
            fecha = st.date_input("Fecha", datetime.date.today())
            concepto = st.text_input("Concepto / Descripción breve")
            col1, col2 = st.columns(2)
            moneda = col1.selectbox("Moneda", ["UYU", "USD"])
            monto = col2.number_input(f"Monto Total", min_value=0.0, value=None, format="%.2f")
            
            tasa_cambio = 1.0
            if moneda == "USD":
                tasa_cambio = st.number_input("Tasa de cambio a aplicar", min_value=1.0, value=float(obtener_tasa_usd_uyu()), format="%.2f")
            
            lista_usuarios = usuarios_df["Usuario"].tolist()
            pagado_por = st.selectbox("¿Quién puso el dinero?", lista_usuarios, index=lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0)
            categoria = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"])
            archivo_adjunto = st.file_uploader("Adjuntar Factura/Boleta", type=["pdf", "png", "jpg", "jpeg"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            col_save, col_cancel = st.columns(2)
            if col_save.button("Guardar", type="primary", use_container_width=True):
                if monto and concepto:
                    monto_uyu = monto * tasa_cambio
                    nombre_archivo = "Sin adjunto"
                    if archivo_adjunto:
                        file_bytes = bytes(archivo_adjunto.getbuffer())
                        nombre_archivo = f"GASTO_{fecha}_{archivo_adjunto.name}"
                        if USE_GSHEETS:
                            try:
                                nombre_archivo = upload_comprobante(file_bytes, nombre_archivo, archivo_adjunto.type)
                            except Exception as e:
                                st.warning(f"No se pudo subir a Drive: {e}")
                        else:
                            with open(os.path.join(DIR_COMPROBANTES, nombre_archivo), "wb") as f: f.write(file_bytes)
                    
                    nuevo_dato = pd.DataFrame([{"ID": uuid.uuid4().hex, "Fecha": fecha, "Concepto": concepto, "Moneda": moneda, "Monto_Original": monto, "Tasa_Cambio": tasa_cambio, "Monto_UYU": monto_uyu, "Pagado_por": pagado_por, "Categoria": categoria, "Archivo_Adjunto": nombre_archivo, "Modificado_por_Admin": False}])
                    save_data(pd.concat([df_gastos, nuevo_dato], ignore_index=True), DATA_FILE)
                    st.session_state.modo_registro = None
                    st.rerun()
                else: st.error("Falta monto o concepto.")
            if col_cancel.button("Cancelar", use_container_width=True):
                st.session_state.modo_registro = None
                st.rerun()

    # =========================================================
    # VISTA 2: FORMULARIO DE NUEVA TRANSFERENCIA
    # =========================================================
    elif st.session_state.modo_registro == "transferencia":
        st.markdown('<div class="section-title">Rendición y Giros</div>', unsafe_allow_html=True)
        lista_usuarios = [u for u in usuarios_df["Usuario"].tolist() if u.lower() != "admin"]
        if len(lista_usuarios) < 2:
            st.info("Necesitas 2 socios para esto.")
            if st.button("Volver"): st.session_state.modo_registro = None; st.rerun()
        else:
            fecha_transf = st.date_input("Fecha de envío", datetime.date.today())
            col1, col2 = st.columns(2)
            origen = col1.selectbox("Quién envía", lista_usuarios, index=lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0)
            destino = col2.selectbox("Quién recibe", [u for u in lista_usuarios if u != origen])
            
            col_m1, col_m2 = st.columns(2)
            moneda_transf = col_m1.selectbox("Moneda", ["UYU", "USD"])
            monto_transf = col_m2.number_input(f"Monto", min_value=0.0, value=None, format="%.2f")
            
            tasa_cambio_transf = 1.0
            if moneda_transf == "USD":
                tasa_cambio_transf = st.number_input("Tasa de cambio", min_value=1.0, value=float(obtener_tasa_usd_uyu()), format="%.2f")

            st.markdown("<br>", unsafe_allow_html=True)
            col_save, col_cancel = st.columns(2)
            if col_save.button("Registrar", type="primary", use_container_width=True):
                if monto_transf:
                    monto_uyu_transf = monto_transf * tasa_cambio_transf
                    nuevo_dato_transf = pd.DataFrame([{"ID": uuid.uuid4().hex, "Fecha": fecha_transf, "Origen": origen, "Destino": destino, "Moneda": moneda_transf, "Monto_Original": monto_transf, "Tasa_Cambio": tasa_cambio_transf, "Monto_UYU": monto_uyu_transf, "Archivo_Adjunto": "Sin adjunto", "Modificado_por_Admin": False}])
                    save_data(pd.concat([df_transfers, nuevo_dato_transf], ignore_index=True), TRANSFERS_FILE)
                    st.session_state.modo_registro = None
                    st.rerun()
                else: st.error("Ingresa un monto.")
            if col_cancel.button("Cancelar", use_container_width=True):
                st.session_state.modo_registro = None
                st.rerun()

    # =========================================================
    # VISTA 3: PANTALLA DE EDICIÓN DE GASTOS (OVERLAY)
    # =========================================================
    elif st.session_state.gasto_a_editar is not None:
        id_seleccionado = st.session_state.gasto_a_editar
        fila_actual = df_gastos[df_gastos["ID"] == id_seleccionado].iloc[0]
        
        st.markdown(f'<div class="section-title">Editando: {fila_actual["Concepto"]}</div>', unsafe_allow_html=True)
        
        with st.container():
            fecha_obj = pd.to_datetime(fila_actual["Fecha"]).date()
            edit_fecha = st.date_input("Fecha", fecha_obj)
            edit_concepto = st.text_input("Concepto", fila_actual["Concepto"])
            
            col1, col2 = st.columns(2)
            idx_moneda = ["UYU", "USD"].index(fila_actual["Moneda"]) if fila_actual["Moneda"] in ["UYU", "USD"] else 0
            edit_moneda = col1.selectbox("Moneda", ["UYU", "USD"], index=idx_moneda)
            edit_monto = col2.number_input("Monto Original", min_value=0.0, value=float(fila_actual["Monto_Original"]), format="%.2f")
            
            edit_tasa = float(fila_actual["Tasa_Cambio"])
            if edit_moneda == "USD":
                edit_tasa = st.number_input("Tasa aplicada", min_value=1.0, value=float(fila_actual["Tasa_Cambio"]), format="%.2f")
            
            categorias = ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"]
            idx_cat = categorias.index(fila_actual["Categoria"]) if fila_actual["Categoria"] in categorias else 0
            edit_categoria = st.selectbox("Categoría", categorias, index=idx_cat)

            if es_admin:
                lista_usuarios = usuarios_df["Usuario"].tolist()
                idx_paga = lista_usuarios.index(fila_actual["Pagado_por"]) if fila_actual["Pagado_por"] in lista_usuarios else 0
                edit_pagado_por = st.selectbox("Pagado por", lista_usuarios, index=idx_paga)
            else:
                edit_pagado_por = fila_actual["Pagado_por"]

            adjunto_actual = str(fila_actual.get("Archivo_Adjunto", "Sin adjunto"))
            if adjunto_actual.startswith("https://"):
                st.markdown(f"📎 Comprobante actual: [ver archivo]({adjunto_actual})")
            edit_archivo = st.file_uploader("Reemplazar comprobante", type=["pdf", "png", "jpg", "jpeg"])

            st.markdown("<br>", unsafe_allow_html=True)
            col_save, col_del, col_cancel = st.columns(3)

            if col_save.button("Guardar", type="primary", use_container_width=True):
                idx_general = df_gastos[df_gastos["ID"] == id_seleccionado].index[0]
                df_gastos.at[idx_general, "Fecha"] = edit_fecha
                df_gastos.at[idx_general, "Concepto"] = edit_concepto
                df_gastos.at[idx_general, "Moneda"] = edit_moneda
                df_gastos.at[idx_general, "Monto_Original"] = edit_monto
                df_gastos.at[idx_general, "Tasa_Cambio"] = edit_tasa
                df_gastos.at[idx_general, "Monto_UYU"] = edit_monto * edit_tasa
                df_gastos.at[idx_general, "Categoria"] = edit_categoria
                df_gastos.at[idx_general, "Pagado_por"] = edit_pagado_por
                if edit_archivo:
                    file_bytes = bytes(edit_archivo.getbuffer())
                    nombre_archivo = f"GASTO_{edit_fecha}_{edit_archivo.name}"
                    if USE_GSHEETS:
                        try:
                            nombre_archivo = upload_comprobante(file_bytes, nombre_archivo, edit_archivo.type)
                        except Exception as e:
                            st.warning(f"No se pudo subir a Drive: {e}")
                    else:
                        with open(os.path.join(DIR_COMPROBANTES, nombre_archivo), "wb") as f: f.write(file_bytes)
                    df_gastos.at[idx_general, "Archivo_Adjunto"] = nombre_archivo
                save_data(df_gastos, DATA_FILE)
                st.session_state.gasto_a_editar = None
                st.rerun()

            if col_del.button("🗑️ Eliminar", use_container_width=True):
                df_gastos = df_gastos[df_gastos["ID"] != id_seleccionado]
                save_data(df_gastos, DATA_FILE)
                st.session_state.gasto_a_editar = None
                st.rerun()
                
            if col_cancel.button("Cancelar", use_container_width=True):
                st.session_state.gasto_a_editar = None
                st.rerun()

    # =========================================================
    # VISTA 4: PANTALLA DE EDICIÓN DE TRANSFERENCIAS (OVERLAY)
    # =========================================================
    elif st.session_state.transfer_a_editar is not None:
        id_transf = st.session_state.transfer_a_editar
        fila_transf = df_transfers[df_transfers["ID"] == id_transf].iloc[0]
        st.markdown('<div class="section-title">Gestionar Transferencia</div>', unsafe_allow_html=True)
        st.warning("Para modificar montos u origen/destino, eliminá este registro y creá uno nuevo.")

        adjunto_transf = str(fila_transf.get("Archivo_Adjunto", "Sin adjunto"))
        if adjunto_transf.startswith("https://"):
            st.markdown(f"📎 Comprobante actual: [ver archivo]({adjunto_transf})")
        edit_archivo_transf = st.file_uploader("Adjuntar comprobante", type=["pdf", "png", "jpg", "jpeg"])

        if edit_archivo_transf:
            if st.button("Guardar comprobante", type="primary", use_container_width=True):
                file_bytes = bytes(edit_archivo_transf.getbuffer())
                nombre_archivo = f"TRANSF_{edit_archivo_transf.name}"
                if USE_GSHEETS:
                    try:
                        nombre_archivo = upload_comprobante(file_bytes, nombre_archivo, edit_archivo_transf.type)
                    except Exception as e:
                        st.warning(f"No se pudo subir a Drive: {e}")
                else:
                    with open(os.path.join(DIR_COMPROBANTES, nombre_archivo), "wb") as f: f.write(file_bytes)
                idx_t = df_transfers[df_transfers["ID"] == id_transf].index[0]
                df_transfers.at[idx_t, "Archivo_Adjunto"] = nombre_archivo
                save_data(df_transfers, TRANSFERS_FILE)
                st.session_state.transfer_a_editar = None
                st.rerun()

        st.markdown("<br>", unsafe_allow_html=True)
        col_del, col_cancel = st.columns(2)
        if col_del.button("🗑️ Eliminar Transferencia", use_container_width=True):
            df_transfers = df_transfers[df_transfers["ID"] != id_transf]
            save_data(df_transfers, TRANSFERS_FILE)
            st.session_state.transfer_a_editar = None
            st.rerun()
        if col_cancel.button("Cancelar", use_container_width=True):
            st.session_state.transfer_a_editar = None
            st.rerun()

    # =========================================================
    # VISTA 5: PESTAÑAS PRINCIPALES (VISTA NORMAL DE NAVEGACIÓN)
    # =========================================================
    else:
        opciones_menu = ["📊 Dashboard", "🕰️ Historial", "⚖️ Balance"]
        if es_admin: opciones_menu.append("⚙️ Admin")
        tabs = st.tabs(opciones_menu)

        # --- PESTAÑA 1: DASHBOARD ---
        with tabs[0]:
            if not df_gastos.empty:
                df_dash = df_gastos.copy()
                df_dash['Fecha'] = pd.to_datetime(df_dash['Fecha'])
                total_uyu = df_dash["Monto_UYU"].sum()
                tasa_actual = obtener_tasa_usd_uyu()
                
                kpi1, kpi2, kpi3 = st.columns(3)
                with kpi1: st.markdown(f'<div class="kpi-card kpi-card-primary"><span class="kpi-icon">🏗️</span><div class="kpi-label">Inversión Total</div><div class="kpi-value">${total_uyu:,.0f}</div><div class="kpi-sub">pesos uruguayos</div></div>', unsafe_allow_html=True)
                with kpi2: st.markdown(f'<div class="kpi-card kpi-card-success"><span class="kpi-icon">💵</span><div class="kpi-label">Equivalente USD</div><div class="kpi-value">U$S {total_uyu/tasa_actual:,.0f}</div><div class="kpi-sub">TC: ${tasa_actual:,.1f}</div></div>', unsafe_allow_html=True)
                with kpi3: st.markdown(f'<div class="kpi-card kpi-card-amber"><span class="kpi-icon">🧾</span><div class="kpi-label">Registros</div><div class="kpi-value">{len(df_dash)}</div><div class="kpi-sub">gastos cargados</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    st.markdown('<div class="section-title">En qué se gastó</div>', unsafe_allow_html=True)
                    fig_pie = px.pie(df_dash.groupby("Categoria")["Monto_UYU"].sum().reset_index(), values='Monto_UYU', names='Categoria', hole=0.6, color_discrete_sequence=["#4F46E5","#7C3AED","#059669","#0EA5E9","#F59E0B"])
                    fig_pie.update_layout(margin=dict(t=10, b=30, l=0, r=0), showlegend=True, legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", font=dict(size=11)), paper_bgcolor="rgba(0,0,0,0)")
                    fig_pie.update_traces(textinfo='percent', textfont_size=12)
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                with col_chart2:
                    st.markdown('<div class="section-title">Gasto por socio</div>', unsafe_allow_html=True)
                    fig_bar = px.bar(df_dash.groupby("Pagado_por")["Monto_UYU"].sum().reset_index(), x='Pagado_por', y='Monto_UYU', text_auto='.3s', color='Pagado_por', color_discrete_sequence=["#4F46E5","#059669","#7C3AED"])
                    fig_bar.update_layout(margin=dict(t=10, b=0, l=0, r=0), showlegend=False, xaxis_title="", yaxis_title="UYU", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
                    fig_bar.update_traces(marker_line_width=0, textfont_size=12)
                    fig_bar.update_yaxes(showgrid=True, gridcolor="rgba(148,163,184,0.1)")
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})

                st.markdown("<hr class='divider'>", unsafe_allow_html=True)
                st.markdown('<div class="section-title">Evolución del gasto por tipo</div>', unsafe_allow_html=True)
                
                fechas_unicas = df_dash["Fecha"].dropna().unique()
                categorias_unicas = df_dash["Categoria"].dropna().unique()
                grid = pd.MultiIndex.from_product([fechas_unicas, categorias_unicas], names=["Fecha", "Categoria"]).to_frame(index=False)
                
                gastos_diarios = df_dash.groupby(["Fecha", "Categoria"])["Monto_UYU"].sum().reset_index()
                gastos_evolucion = pd.merge(grid, gastos_diarios, on=["Fecha", "Categoria"], how="left").fillna(0)
                
                gastos_evolucion = gastos_evolucion.sort_values("Fecha")
                gastos_evolucion["Gasto_Acumulado"] = gastos_evolucion.groupby("Categoria")["Monto_UYU"].cumsum()
                
                fig_area = px.area(gastos_evolucion, x='Fecha', y='Gasto_Acumulado', color='Categoria', color_discrete_sequence=["#4F46E5","#7C3AED","#059669","#0EA5E9","#F59E0B"])
                
                # Ajuste de layout general
                fig_area.update_layout(margin=dict(t=10, b=10, l=0, r=0), xaxis_title="", yaxis_title="Acumulado (UYU)", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", legend=dict(orientation="h", yanchor="bottom", y=-0.5, xanchor="center", x=0.5, title_text=""))
                
                # Ocultar las horas en el eje horizontal y en la etiqueta al pasar el ratón/dedo
                fig_area.update_xaxes(tickformat="%d/%m/%Y", hoverformat="%d/%m/%Y")
                
                st.plotly_chart(fig_area, use_container_width=True, config={'displayModeBar': False})
            else:
                st.markdown("""
                    <div style='text-align:center; padding:60px 20px;'>
                        <div style='font-size:3.5rem; margin-bottom:16px;'>🏗️</div>
                        <div style='font-size:1.1rem; font-weight:700; opacity:0.6; margin-bottom:8px;'>Sin registros aún</div>
                        <div style='font-size:0.85rem; opacity:0.35;'>Registrá el primer gasto usando el botón de arriba</div>
                    </div>
                """, unsafe_allow_html=True)

        # --- PESTAÑA 2: HISTORIAL (SOLO VISTA) ---
        with tabs[1]:
            subtab1, subtab2 = st.tabs(["🛒 Gastos", "💸 Transferencias"])

            CAT_BADGE = {
                "Materiales":       ("badge-mat",  "Materiales"),
                "Mano de Obra":     ("badge-mdo",  "Mano de Obra"),
                "Trámites/Permisos":("badge-tram", "Trámites"),
                "Terreno":          ("badge-ter",  "Terreno"),
                "Otros":            ("badge-otros","Otros"),
            }

            with subtab1:
                if not df_gastos.empty:
                    df_gastos["Fecha"] = pd.to_datetime(df_gastos["Fecha"])
                    for _, f in df_gastos.sort_values("Fecha", ascending=False).iterrows():
                        cat = str(f.get("Categoria","Otros"))
                        badge_cls, badge_lbl = CAT_BADGE.get(cat, ("badge-otros", cat))
                        adjunto = str(f.get("Archivo_Adjunto",""))
                        clip = "📎 " if adjunto.startswith("https://") else ""
                        title_html = (
                            f"<span style='font-weight:700;font-size:0.95rem;'>{f['Concepto']}</span>"
                            f"&nbsp;&nbsp;<span class='badge {badge_cls}'>{badge_lbl}</span>"
                        )
                        expander_label = f"{f['Fecha'].strftime('%d/%m/%y')}  ·  {f['Concepto']}  ·  ${f['Monto_Original']:,.0f} {f['Moneda']}"
                        with st.expander(expander_label):
                            st.markdown(
                                f"<div style='display:flex;gap:16px;align-items:center;flex-wrap:wrap;margin-bottom:8px;'>"
                                f"<span class='badge {badge_cls}'>{badge_lbl}</span>"
                                f"<span style='font-size:0.8rem;opacity:0.55;'>👤 {f['Pagado_por']}</span>"
                                f"<span style='font-size:0.8rem;opacity:0.55;'>📅 {f['Fecha'].strftime('%d/%m/%Y')}</span>"
                                f"{'<span style=\"font-size:0.8rem;opacity:0.55;\">📎 Comprobante</span>' if adjunto.startswith('https://') else ''}"
                                f"</div>",
                                unsafe_allow_html=True
                            )
                            col_a, col_b = st.columns([1, 1])
                            with col_a:
                                st.metric("Monto", f"${f['Monto_Original']:,.2f} {f['Moneda']}")
                            with col_b:
                                st.metric("En UYU", f"${f['Monto_UYU']:,.0f}")
                            if adjunto.startswith("https://"):
                                st.markdown(f"[📎 Ver comprobante]({adjunto})")
                            if st.button("✏️ Editar / Eliminar", key=f"e_{f['ID']}", use_container_width=True):
                                st.session_state.gasto_a_editar = f["ID"]
                                st.rerun()
                else:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("Sin gastos registrados todavía.")

            with subtab2:
                if not df_transfers.empty:
                    df_transfers["Fecha"] = pd.to_datetime(df_transfers["Fecha"])
                    for _, f in df_transfers.sort_values("Fecha", ascending=False).iterrows():
                        expander_label = f"{f['Fecha'].strftime('%d/%m/%y')}  ·  {f['Origen']} → {f['Destino']}  ·  ${f['Monto_Original']:,.0f} {f['Moneda']}"
                        with st.expander(expander_label):
                            col_a, col_b = st.columns(2)
                            with col_a:
                                st.metric("Enviado", f"${f['Monto_Original']:,.2f} {f['Moneda']}")
                            with col_b:
                                st.metric("En UYU", f"${f['Monto_UYU']:,.0f}")
                            if st.button("🗑️ Gestionar", key=f"t_{f['ID']}", use_container_width=True):
                                st.session_state.transfer_a_editar = f["ID"]
                                st.rerun()
                else:
                    st.markdown("<br>", unsafe_allow_html=True)
                    st.info("Sin transferencias registradas todavía.")

        # --- PESTAÑA 3: BALANCE ---
        with tabs[2]:
            usrs = [u for u in usuarios_df["Usuario"].tolist() if u.lower() != "admin"]
            if len(usrs) >= 2:
                u1, u2 = usrs[0], usrs[1]
                g1 = df_gastos[df_gastos["Pagado_por"] == u1]["Monto_UYU"].sum() if not df_gastos.empty else 0
                g2 = df_gastos[df_gastos["Pagado_por"] == u2]["Monto_UYU"].sum() if not df_gastos.empty else 0
                e1 = df_transfers[df_transfers["Origen"] == u1]["Monto_UYU"].sum() if not df_transfers.empty else 0
                r1 = df_transfers[df_transfers["Destino"] == u1]["Monto_UYU"].sum() if not df_transfers.empty else 0
                e2 = df_transfers[df_transfers["Origen"] == u2]["Monto_UYU"].sum() if not df_transfers.empty else 0
                r2 = df_transfers[df_transfers["Destino"] == u2]["Monto_UYU"].sum() if not df_transfers.empty else 0

                s1, s2 = g1 + e1 - r1, g2 + e2 - r2
                total_aportes = s1 + s2
                meta = total_aportes / 2
                dif = abs(s1 - meta)

                # Estado principal
                if dif < 1:
                    st.markdown('<div class="kpi-card kpi-card-success" style="text-align:center;"><span class="kpi-icon">✅</span><div class="kpi-label">Estado del balance</div><div class="kpi-value" style="font-size:1.5rem;">Cuentas Claras</div><div class="kpi-sub">Los aportes están igualados</div></div>', unsafe_allow_html=True)
                elif s1 > meta:
                    st.markdown(f'<div class="kpi-card kpi-card-primary" style="text-align:center;"><span class="kpi-icon">⚖️</span><div class="kpi-label">{u2} le debe a {u1}</div><div class="kpi-value">${dif:,.0f} <span style="font-size:1.1rem;opacity:0.6;">UYU</span></div><div class="kpi-sub">para igualar los aportes al 50/50</div></div>', unsafe_allow_html=True)
                else:
                    st.markdown(f'<div class="kpi-card kpi-card-primary" style="text-align:center;"><span class="kpi-icon">⚖️</span><div class="kpi-label">{u1} le debe a {u2}</div><div class="kpi-value">${dif:,.0f} <span style="font-size:1.1rem;opacity:0.6;">UYU</span></div><div class="kpi-sub">para igualar los aportes al 50/50</div></div>', unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Barra de proporción
                if total_aportes > 0:
                    pct1 = s1 / total_aportes * 100
                    pct2 = 100 - pct1
                    st.markdown(f"""
                        <div style='margin-bottom:6px; display:flex; justify-content:space-between; font-size:0.78rem; font-weight:700; opacity:0.6; text-transform:uppercase; letter-spacing:0.8px;'>
                            <span>{u1} · {pct1:.0f}%</span>
                            <span>{pct2:.0f}% · {u2}</span>
                        </div>
                        <div class='balance-bar-wrap'>
                            <div class='balance-bar-fill' style='width:{pct1:.1f}%; background:linear-gradient(90deg,#4F46E5,#7C3AED);'></div>
                        </div>
                        <div style='display:flex; justify-content:center; margin-top:6px; font-size:0.72rem; opacity:0.35;'>objetivo: 50% / 50%</div>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # KPIs individuales
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f'<div class="kpi-card kpi-card-neutral"><div class="kpi-label">{u1}</div><div class="kpi-value" style="font-size:1.6rem;">${s1:,.0f}</div><div class="kpi-sub" style="color:var(--text-color);">aportado neto</div></div>', unsafe_allow_html=True)
                with c2:
                    st.markdown(f'<div class="kpi-card kpi-card-neutral"><div class="kpi-label">{u2}</div><div class="kpi-value" style="font-size:1.6rem;">${s2:,.0f}</div><div class="kpi-sub" style="color:var(--text-color);">aportado neto</div></div>', unsafe_allow_html=True)

        # --- PESTAÑA 4: ADMIN ---
        if es_admin:
            with tabs[3]:
                st.markdown('<div class="section-title">Importar Gastos desde Google Sheet</div>', unsafe_allow_html=True)
                st.caption("Compartí la hoja origen con el `client_email` de tu cuenta de servicio antes de importar.")
                with st.form("import_form"):
                    src_id = st.text_input("ID del Google Sheet de origen", placeholder="1-GVRvZUUD9Tue1XYDW8jsiXlchyWQ47DYmHK1DjF_SM")
                    src_hoja = st.text_input("Nombre de la hoja", value="Gastos")
                    col_i1, col_i2 = st.columns(2)
                    fecha_import = col_i1.date_input("Fecha a asignar", datetime.date.today())
                    cat_import = col_i2.selectbox("Categoría por defecto", ["Trámites/Permisos", "Materiales", "Mano de Obra", "Terreno", "Otros"])
                    if st.form_submit_button("Importar", type="primary", use_container_width=True):
                        try:
                            src_ws = get_gspread_client().open_by_key(src_id.strip()).worksheet(src_hoja.strip())
                            all_values = src_ws.get_all_values()
                            header_row = next((i for i, r in enumerate(all_values) if "Concepto" in r), None)
                            if header_row is None:
                                st.error("No se encontró encabezado 'Concepto' en la hoja.")
                            else:
                                # Extraer todos los hyperlinks de la hoja
                                all_links = extraer_hyperlinks(src_id.strip(), src_hoja.strip())
                                headers = all_values[header_row]
                                df_src = pd.DataFrame(all_values[header_row+1:], columns=headers)
                                df_src = df_src[df_src["Concepto"].str.strip() != ""]
                                df_src = df_src[~df_src["Concepto"].str.upper().str.contains("TOTAL")]
                                df_src = df_src.reset_index(drop=True)
                                tasa = obtener_tasa_usd_uyu()
                                nuevos = []
                                for i, row in df_src.iterrows():
                                    moneda = str(row.get("Moneda", "UYU")).strip() or "UYU"
                                    try:
                                        monto = float(str(row.get("Monto", "0")).replace(",", ".").strip())
                                    except:
                                        continue
                                    if monto <= 0:
                                        continue
                                    tasa_row = tasa if moneda == "USD" else 1.0
                                    # Buscar hyperlinks en la fila (índice real en la hoja)
                                    sheet_row = header_row + 1 + i
                                    row_links = all_links.get(sheet_row, {})
                                    adjunto = next(iter(row_links.values()), "Sin adjunto")
                                    nuevos.append({
                                        "ID": uuid.uuid4().hex,
                                        "Fecha": fecha_import,
                                        "Concepto": row["Concepto"].strip(),
                                        "Moneda": moneda,
                                        "Monto_Original": monto,
                                        "Tasa_Cambio": tasa_row,
                                        "Monto_UYU": monto * tasa_row,
                                        "Pagado_por": str(row.get("Paga", "")).strip() or "admin",
                                        "Categoria": cat_import,
                                        "Archivo_Adjunto": adjunto,
                                        "Modificado_por_Admin": True
                                    })
                                if nuevos:
                                    save_data(pd.concat([df_gastos, pd.DataFrame(nuevos)], ignore_index=True), DATA_FILE)
                                    st.success(f"✅ {len(nuevos)} gastos importados.")
                                    st.rerun()
                                else:
                                    st.warning("No se encontraron filas con monto válido.")
                        except Exception as e:
                            st.error(f"Error: {e}")

                st.markdown("---")
                with st.expander("🔑 Diagnóstico de Secrets", expanded=False):
                    st.caption("Keys cargadas en st.secrets (sin mostrar valores):")
                    keys_top = list(st.secrets.keys())
                    st.code("\n".join(keys_top))
                    drive_ok = "drive_folder_id" in st.secrets
                    oauth_ok = "google_oauth_refresh_token" in st.secrets
                    st.write(f"- `drive_folder_id` encontrado: {'✅' if drive_ok else '❌'}")
                    st.write(f"- `google_oauth_refresh_token` encontrado: {'✅' if oauth_ok else '❌'}")
                    if drive_ok:
                        fid = str(st.secrets["drive_folder_id"]).strip()
                        st.write(f"- Valor de `drive_folder_id` (primeros 10 chars): `{fid[:10]}...`")

                st.markdown("---")
                st.markdown('<div class="section-title">Respaldo de Datos</div>', unsafe_allow_html=True)
                if st.button("Generar Respaldo Excel", type="primary", use_container_width=True):
                    ruta, nombre, datos = generar_respaldo_excel(df_gastos, df_transfers)
                    st.session_state["ultimo_respaldo"] = {"nombre": nombre, "datos": datos, "ruta": ruta}

                if "ultimo_respaldo" in st.session_state:
                    r = st.session_state["ultimo_respaldo"]
                    st.success(f"Respaldo guardado en: `{r['ruta']}`")
                    st.download_button("⬇️ Descargar", data=r["datos"], file_name=r["nombre"], mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

                st.markdown("---")
                st.dataframe(usuarios_df[["Usuario"]], use_container_width=True)
                st.markdown('<div class="section-title">Registrar Socio</div>', unsafe_allow_html=True)
                with st.form("nuevo_socio_form"):
                    nuevo_nombre = st.text_input("Nombre de Usuario")
                    nueva_clave = st.text_input("Contraseña", type="password")
                    if st.form_submit_button("Añadir Usuario", type="primary"): 
                        if nuevo_nombre and nueva_clave:
                            if nuevo_nombre in usuarios_df["Usuario"].values: st.error("Ese usuario ya existe.")
                            else:
                                save_data(pd.concat([usuarios_df, pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])], ignore_index=True), USERS_FILE)
                                st.rerun()
