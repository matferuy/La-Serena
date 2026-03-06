import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import uuid

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide", initial_sidebar_state="collapsed")

# --- MAGIA CSS: DISEÑO UI/UX MEJORADO Y COMPATIBLE CON MODO OSCURO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;800&display=swap');
    
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container { padding-top: 1rem; max-width: 900px; }

    .stButton>button {
        border-radius: 10px; font-weight: 600; height: 3rem; transition: all 0.3s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8); border: none; color: white;
    }

    div[data-testid="stExpander"] {
        background-color: var(--secondary-background-color); border-radius: 12px;
        border: 1px solid var(--faded-text-05); margin-bottom: 10px;
    }
    
    .kpi-card-blue { background: linear-gradient(135deg, #1E3A8A, #3B82F6); color: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3); margin-bottom: 15px; }
    .kpi-card-green { background: linear-gradient(135deg, #064E3B, #10B981); color: white; padding: 20px; border-radius: 16px; box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3); margin-bottom: 15px; }
    .kpi-card-dynamic { background: var(--background-color); color: var(--text-color); padding: 15px; border-radius: 16px; border: 1px solid var(--faded-text-10); margin-bottom: 10px; }
    .kpi-title { font-size: 0.9rem; opacity: 0.9; margin-bottom: 5px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; }
    .kpi-value { font-size: 2rem; font-weight: 800; margin: 0; line-height: 1.2;}
    .kpi-subtitle { font-size: 0.8rem; opacity: 0.7; margin-top: 5px;}
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_FILE = "contabilidad_casa.csv"
USERS_FILE = "usuarios.csv"
LOG_FILE = "log_modificaciones.csv"
TRANSFERS_FILE = "transferencias.csv"
DIR_COMPROBANTES = "comprobantes"

if not os.path.exists(DIR_COMPROBANTES): os.makedirs(DIR_COMPROBANTES)

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
    if os.path.exists(USERS_FILE): return pd.read_csv(USERS_FILE, dtype={"Usuario": str, "Clave": str})
    default_users = pd.DataFrame([{"Usuario": "admin", "Clave": "1234"}])
    default_users.to_csv(USERS_FILE, index=False)
    return default_users

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
        if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
        save_data(df, DATA_FILE)
        return df
    return pd.DataFrame(columns=["ID", "Fecha", "Concepto", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Pagado_por", "Categoria", "Archivo_Adjunto", "Modificado_por_Admin"])

def load_transfers():
    if os.path.exists(TRANSFERS_FILE):
        df = pd.read_csv(TRANSFERS_FILE)
        if "ID" not in df.columns: df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
        if "Modificado_por_Admin" not in df.columns: df["Modificado_por_Admin"] = False
        save_data(df, TRANSFERS_FILE)
        return df
    return pd.DataFrame(columns=["ID", "Fecha", "Origen", "Destino", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Archivo_Adjunto", "Modificado_por_Admin"])

def save_data(df, file_name): df.to_csv(file_name, index=False)

# --- INICIALIZACIÓN DE SESIÓN ---
if "logueado" not in st.session_state: st.session_state.logueado = False
if "usuario_actual" not in st.session_state: st.session_state.usuario_actual = ""
if "gasto_a_editar" not in st.session_state: st.session_state.gasto_a_editar = None
if "transfer_a_editar" not in st.session_state: st.session_state.transfer_a_editar = None
if "modo_registro" not in st.session_state: st.session_state.modo_registro = None

usuarios_df = load_users()

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A; font-weight: 800; margin-bottom: 0;'>La Serena</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: var(--text-color); margin-bottom: 30px;'>Gestión y Contabilidad</p>", unsafe_allow_html=True)
    with st.container():
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            submit_login = st.form_submit_button("Ingresar", type="primary", use_container_width=True)
            if submit_login:
                if not usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"].astype(str) == str(clave))].empty:
                    st.session_state.logueado, st.session_state.usuario_actual = True, usuario
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas.")

# --- APLICACIÓN PRINCIPAL ---
else:
    df_gastos = load_data()
    df_transfers = load_transfers()
    es_admin = st.session_state.usuario_actual.lower() == "admin"

    # --- CABECERA MÓVIL (Reemplaza el menú lateral) ---
    col_perfil, col_salir = st.columns([3, 1])
    with col_perfil:
        st.markdown(f"<div style='padding-top: 15px; font-size: 1.1rem;'>👤 <b>{st.session_state.usuario_actual}</b></div>", unsafe_allow_html=True)
    with col_salir:
        if st.button("🚪 Salir", use_container_width=True):
            st.session_state.logueado = False
            st.session_state.modo_registro = None
            st.rerun()

    st.markdown("<hr style='margin: 5px 0px 15px 0px;'>", unsafe_allow_html=True)

    # --- BOTÓN DE ACCIÓN PRINCIPAL TIPO DROPDOWN ("+") ---
    # Solo se muestra si no estamos llenando o editando un formulario
    if st.session_state.modo_registro is None and st.session_state.gasto_a_editar is None and st.session_state.transfer_a_editar is None:
        with st.expander("➕ NUEVO REGISTRO", expanded=False):
            col_btn_g, col_btn_t = st.columns(2)
            if col_btn_g.button("🛒 Cargar Gasto", type="primary", use_container_width=True):
                st.session_state.modo_registro = "gasto"
                st.rerun()
            if col_btn_t.button("💸 Transferencia", type="primary", use_container_width=True):
                st.session_state.modo_registro = "transferencia"
                st.rerun()

    # =========================================================
    # VISTA 1: FORMULARIO DE NUEVO GASTO
    # =========================================================
    if st.session_state.modo_registro == "gasto":
        st.markdown("### 🛒 Registrar Compra o Pago")
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
            
            col_save, col_cancel = st.columns(2)
            if col_save.button("Guardar", type="primary", use_container_width=True):
                if monto and concepto:
                    monto_uyu = monto * tasa_cambio
                    nombre_archivo = "Sin adjunto"
                    if archivo_adjunto:
                        nombre_archivo = f"GASTO_{fecha}_{archivo_adjunto.name}"
                        with open(os.path.join(DIR_COMPROBANTES, nombre_archivo), "wb") as f: f.write(archivo_adjunto.getbuffer())
                    
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
        st.markdown("### 💸 Rendición y Giros")
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

            archivo_adjunto_transf = st.file_uploader("Comprobante bancario", type=["pdf", "png", "jpg", "jpeg"])
            
            col_save, col_cancel = st.columns(2)
            if col_save.button("Registrar", type="primary", use_container_width=True):
                if monto_transf:
                    monto_uyu_transf = monto_transf * tasa_cambio_transf
                    nombre_archivo_transf = "Sin adjunto"
                    if archivo_adjunto_transf:
                        nombre_archivo_transf = f"TRANSF_{fecha_transf}_{archivo_adjunto_transf.name}"
                        with open(os.path.join(DIR_COMPROBANTES, nombre_archivo_transf), "wb") as f: f.write(archivo_adjunto_transf.getbuffer())
                    
                    nuevo_dato_transf = pd.DataFrame([{"ID": uuid.uuid4().hex, "Fecha": fecha_transf, "Origen": origen, "Destino": destino, "Moneda": moneda_transf, "Monto_Original": monto_transf, "Tasa_Cambio": tasa_cambio_transf, "Monto_UYU": monto_uyu_transf, "Archivo_Adjunto": nombre_archivo_transf, "Modificado_por_Admin": False}])
                    save_data(pd.concat([df_transfers, nuevo_dato_transf], ignore_index=True), TRANSFERS_FILE)
                    st.session_state.modo_registro = None
                    st.rerun()
                else: st.error("Ingresa un monto.")
            if col_cancel.button("Cancelar", use_container_width=True):
                st.session_state.modo_registro = None
                st.rerun()

    # =========================================================
    # VISTA 3: PESTAÑAS PRINCIPALES (VISTA NORMAL)
    # =========================================================
    else:
        # Pestañas de navegación
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
                with kpi1: st.markdown(f'<div class="kpi-card-blue"><div class="kpi-title">Inversión</div><div class="kpi-value">${total_uyu:,.0f}</div></div>', unsafe_allow_html=True)
                with kpi2: st.markdown(f'<div class="kpi-card-green"><div class="kpi-title">Est. USD</div><div class="kpi-value">U$S {total_uyu/tasa_actual:,.0f}</div></div>', unsafe_allow_html=True)
                with kpi3: st.markdown(f'<div class="kpi-card-dynamic"><div class="kpi-title">Registros</div><div class="kpi-value">{len(df_dash)}</div></div>', unsafe_allow_html=True)

                col_chart1, col_chart2 = st.columns(2)
                with col_chart1:
                    fig_pie = px.pie(df_dash.groupby("Categoria")["Monto_UYU"].sum().reset_index(), values='Monto_UYU', names='Categoria', hole=0.5)
                    fig_pie.update_layout(margin=dict(t=10, b=0, l=0, r=0), showlegend=False, paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
                with col_chart2:
                    fig_bar = px.bar(df_dash.groupby("Pagado_por")["Monto_UYU"].sum().reset_index(), x='Pagado_por', y='Monto_UYU', text_auto='.2s')
                    fig_bar.update_layout(margin=dict(t=10, b=0, l=0, r=0), xaxis_title="", yaxis_title="", paper_bgcolor="rgba(0,0,0,0)")
                    st.plotly_chart(fig_bar, use_container_width=True, config={'displayModeBar': False})
            else:
                st.info("Sin registros aún.")

        # --- PESTAÑA 2: HISTORIAL ---
        with tabs[1]:
            if st.session_state.gasto_a_editar:
                # Flujo rápido de edición de gasto
                fila_actual = df_gastos[df_gastos["ID"] == st.session_state.gasto_a_editar].iloc[0]
                if st.button("⬅️ Cancelar Edición"): st.session_state.gasto_a_editar = None; st.rerun()
                st.markdown(f"**Editando:** {fila_actual['Concepto']}")
                if st.button("🗑️ Eliminar Definitivamente", type="primary"): 
                    save_data(df_gastos[df_gastos["ID"] != st.session_state.gasto_a_editar], DATA_FILE)
                    st.session_state.gasto_a_editar = None; st.rerun()
            elif st.session_state.transfer_a_editar:
                if st.button("⬅️ Cancelar Edición"): st.session_state.transfer_a_editar = None; st.rerun()
                if st.button("🗑️ Eliminar Transferencia", type="primary"): 
                    save_data(df_transfers[df_transfers["ID"] != st.session_state.transfer_a_editar], TRANSFERS_FILE)
                    st.session_state.transfer_a_editar = None; st.rerun()
            else:
                subtab1, subtab2 = st.tabs(["🛒 Gastos", "💸 Transferencias"])
                with subtab1:
                    if not df_gastos.empty:
                        df_gastos["Fecha"] = pd.to_datetime(df_gastos["Fecha"])
                        for _, f in df_gastos.sort_values("Fecha", ascending=False).iterrows():
                            with st.expander(f"{f['Fecha'].strftime('%d/%m/%Y')} | {f['Concepto']} | ${f['Monto_Original']:,.2f} {f['Moneda']}"):
                                st.write(f"**Por:** {f['Pagado_por']} | **Cat:** {f['Categoria']}")
                                if st.button("Editar / Eliminar", key=f"e_{f['ID']}"): st.session_state.gasto_a_editar = f["ID"]; st.rerun()
                with subtab2:
                    if not df_transfers.empty:
                        df_transfers["Fecha"] = pd.to_datetime(df_transfers["Fecha"])
                        for _, f in df_transfers.sort_values("Fecha", ascending=False).iterrows():
                            with st.expander(f"{f['Fecha'].strftime('%d/%m/%Y')} | {f['Origen']} ➡️ {f['Destino']} | ${f['Monto_Original']:,.2f} {f['Moneda']}"):
                                if st.button("Eliminar", key=f"t_{f['ID']}"): st.session_state.transfer_a_editar = f["ID"]; st.rerun()

        # --- PESTAÑA 3: BALANCE ---
        with tabs[2]:
            usrs = [u for u in usuarios_df["Usuario"].tolist() if u.lower() != "admin"]
            if len(usrs) >= 2:
                u1, u2 = usrs[0], usrs[1]
                g1, g2 = df_gastos[df_gastos["Pagado_por"] == u1]["Monto_UYU"].sum() if not df_gastos.empty else 0, df_gastos[df_gastos["Pagado_por"] == u2]["Monto_UYU"].sum() if not df_gastos.empty else 0
                e1, r1 = df_transfers[df_transfers["Origen"] == u1]["Monto_UYU"].sum() if not df_transfers.empty else 0, df_transfers[df_transfers["Destino"] == u1]["Monto_UYU"].sum() if not df_transfers.empty else 0
                e2, r2 = df_transfers[df_transfers["Origen"] == u2]["Monto_UYU"].sum() if not df_transfers.empty else 0, df_transfers[df_transfers["Destino"] == u2]["Monto_UYU"].sum() if not df_transfers.empty else 0
                
                s1, s2 = g1 + e1 - r1, g2 + e2 - r2
                meta = (g1 + g2) / 2
                dif = abs(s1 - meta)

                if dif < 1: st.markdown('<div class="kpi-card-green" style="text-align:center;">CUENTAS CLARAS</div>', unsafe_allow_html=True)
                elif s1 > meta: st.markdown(f'<div class="kpi-card-blue" style="text-align:center;">{u2} debe a {u1}:<br><b>${dif:,.0f} UYU</b></div>', unsafe_allow_html=True)
                else: st.markdown(f'<div class="kpi-card-blue" style="text-align:center;">{u1} debe a {u2}:<br><b>${dif:,.0f} UYU</b></div>', unsafe_allow_html=True)
                
                c1, c2 = st.columns(2)
                with c1: st.markdown(f'<div class="kpi-card-dynamic"><b>{u1}</b><br>Neto: ${s1:,.0f}</div>', unsafe_allow_html=True)
                with c2: st.markdown(f'<div class="kpi-card-dynamic"><b>{u2}</b><br>Neto: ${s2:,.0f}</div>', unsafe_allow_html=True)

        # --- PESTAÑA 4: ADMIN ---
        if es_admin:
            with tabs[3]:
                st.dataframe(usuarios_df[["Usuario"]], use_container_width=True)
                if st.button("Añadir Usuario de Prueba"): 
                    save_data(pd.concat([usuarios_df, pd.DataFrame([{"Usuario": f"Socio_{len(usuarios_df)}", "Clave": "123"}])], ignore_index=True), USERS_FILE)
                    st.rerun()
