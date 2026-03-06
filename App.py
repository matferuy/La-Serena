import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import uuid

# --- CONFIGURACIÓN INICIAL ---
st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide", initial_sidebar_state="collapsed")

# --- MAGIA CSS: DISEÑO UI/UX MODERNO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    
    /* Ocultar elementos de desarrollador de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem;
        max-width: 800px; /* Ancho máximo para que parezca app móvil incluso en PC */
    }

    /* Estilo del Tab Bar (Menú Superior) */
    div.stRadio > div[role="radiogroup"] {
        background-color: #F3F4F6;
        padding: 5px;
        border-radius: 12px;
        display: flex;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: 5px;
    }
    div.stRadio > div[role="radiogroup"] > label {
        background-color: transparent;
        padding: 8px 12px;
        border-radius: 8px;
        flex: 1;
        text-align: center;
        transition: all 0.2s ease;
    }
    div.stRadio > div[role="radiogroup"] > label[data-checked="true"] {
        background-color: #FFFFFF;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        color: #2563EB !important;
        font-weight: 600;
    }

    /* Estilo de Botones */
    .stButton>button {
        border-radius: 10px;
        font-weight: 600;
        height: 3rem;
        transition: all 0.3s ease;
    }
    .stButton>button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8);
        border: none;
        box-shadow: 0 4px 6px rgba(37, 99, 235, 0.2);
    }
    .stButton>button[kind="primary"]:hover {
        box-shadow: 0 6px 8px rgba(37, 99, 235, 0.3);
        transform: translateY(-1px);
    }

    /* Tarjetas del Historial (Expanders) */
    div[data-testid="stExpander"] {
        background-color: #FFFFFF;
        border-radius: 12px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 1px 3px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    
    /* Tarjetas Custom para KPIs (HTML inyectado) */
    .kpi-card-blue {
        background: linear-gradient(135deg, #1E3A8A, #3B82F6);
        color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(59, 130, 246, 0.3);
        margin-bottom: 15px;
    }
    .kpi-card-green {
        background: linear-gradient(135deg, #064E3B, #10B981);
        color: white;
        padding: 20px;
        border-radius: 16px;
        box-shadow: 0 4px 10px rgba(16, 185, 129, 0.3);
        margin-bottom: 15px;
    }
    .kpi-card-white {
        background: #FFFFFF;
        color: #1F2937;
        padding: 15px;
        border-radius: 16px;
        border: 1px solid #E5E7EB;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
        margin-bottom: 10px;
    }
    .kpi-title { font-size: 0.9rem; opacity: 0.9; margin-bottom: 5px; font-weight: 400; }
    .kpi-value { font-size: 2rem; font-weight: 800; margin: 0; line-height: 1.2;}
    .kpi-subtitle { font-size: 0.8rem; opacity: 0.7; margin-top: 5px;}
    
    /* Inputs */
    div[data-baseweb="input"], div[data-baseweb="select"] {
        border-radius: 8px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_FILE = "contabilidad_casa.csv"
USERS_FILE = "usuarios.csv"
LOG_FILE = "log_modificaciones.csv"
TRANSFERS_FILE = "transferencias.csv"
DIR_COMPROBANTES = "comprobantes"

if not os.path.exists(DIR_COMPROBANTES):
    os.makedirs(DIR_COMPROBANTES)

# --- FUNCIÓN: OBTENER TIPO DE CAMBIO AUTOMÁTICO ---
@st.cache_data(ttl=3600)
def obtener_tasa_usd_uyu():
    try:
        url = "https://open.er-api.com/v6/latest/USD"
        response = requests.get(url, timeout=5)
        data = response.json()
        return round(data["rates"]["UYU"], 2)
    except:
        return 39.00

# --- FUNCIONES DE DATOS Y LOGS ---
def load_users():
    if os.path.exists(USERS_FILE):
        return pd.read_csv(USERS_FILE, dtype={"Usuario": str, "Clave": str})
    else:
        default_users = pd.DataFrame([{"Usuario": "admin", "Clave": "1234"}])
        default_users.to_csv(USERS_FILE, index=False)
        return default_users

def load_data():
    if os.path.exists(DATA_FILE):
        df = pd.read_csv(DATA_FILE)
        if "ID" not in df.columns:
            df["ID"] = [uuid.uuid4().hex for _ in range(len(df))]
        if "Modificado_por_Admin" not in df.columns:
            df["Modificado_por_Admin"] = False
        save_data(df, DATA_FILE)
        return df
    else:
        return pd.DataFrame(columns=[
            "ID", "Fecha", "Concepto", "Moneda", "Monto_Original", "Tasa_Cambio", 
            "Monto_UYU", "Pagado_por", "Categoria", "Archivo_Adjunto", "Modificado_por_Admin"
        ])

def load_transfers():
    if os.path.exists(TRANSFERS_FILE):
        return pd.read_csv(TRANSFERS_FILE)
    else:
        return pd.DataFrame(columns=[
            "ID", "Fecha", "Origen", "Destino", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Archivo_Adjunto"
        ])

def load_logs():
    if os.path.exists(LOG_FILE):
        return pd.read_csv(LOG_FILE)
    else:
        return pd.DataFrame(columns=["Timestamp", "ID_Gasto", "Usuario", "Detalle_Cambios"])

def registrar_log(id_gasto, usuario, detalle):
    logs_df = load_logs()
    nuevo_log = pd.DataFrame([{
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "ID_Gasto": id_gasto,
        "Usuario": usuario,
        "Detalle_Cambios": detalle
    }])
    logs_df = pd.concat([logs_df, nuevo_log], ignore_index=True)
    logs_df.to_csv(LOG_FILE, index=False)

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- INICIALIZACIÓN DE SESIÓN ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""
if "gasto_a_editar" not in st.session_state:
    st.session_state.gasto_a_editar = None

usuarios_df = load_users()

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.markdown("<h1 style='text-align: center; color: #1E3A8A; font-weight: 800; margin-bottom: 0;'>🏡 La Serena</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #6B7280; margin-bottom: 30px;'>Gestión y Contabilidad 50/50</p>", unsafe_allow_html=True)
    
    with st.container():
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            clave = st.text_input("Contraseña", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            submit_login = st.form_submit_button("Ingresar Seguro", type="primary", use_container_width=True)
            
            if submit_login:
                user_match = usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"].astype(str) == str(clave))]
                if not user_match.empty:
                    st.session_state.logueado = True
                    st.session_state.usuario_actual = usuario
                    st.rerun()
                else:
                    st.error("Credenciales incorrectas. Inténtalo nuevamente.")

# --- APLICACIÓN PRINCIPAL ---
else:
    # --- MENÚ LATERAL (Solo para ajustes rápidos) ---
    st.sidebar.title("🏡 La Serena")
    st.sidebar.write(f"👤 Conectado como: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
        st.session_state.logueado = False
        st.session_state.usuario_actual = ""
        st.session_state.gasto_a_editar = None
        st.rerun()
        
    # --- MENÚ SUPERIOR DE NAVEGACIÓN ---
    opciones_menu = ["📊 Dashboard", "📝 Gasto", "💸 Transf.", "📋 Historial", "⚖️ Balance"]
    
    # Si es admin, le agregamos la pestaña de usuarios
    if st.session_state.usuario_actual.lower() == "admin":
        opciones_menu.append("👥 Admin")
    
    menu = st.radio("Navegación", opciones_menu, horizontal=True, label_visibility="collapsed")
    st.markdown("<br>", unsafe_allow_html=True)

    if menu != "📋 Historial":
        st.session_state.gasto_a_editar = None

    df_gastos = load_data()
    df_transfers = load_transfers()

    # --- MÓDULO 1: DASHBOARD ---
    if menu == "📊 Dashboard":
        if not df_gastos.empty:
            df_dash = df_gastos.copy()
            df_dash['Fecha'] = pd.to_datetime(df_dash['Fecha'])
            
            total_invertido = df_dash["Monto_UYU"].sum()
            total_gastos = len(df_dash)
            
            # Tarjeta Premium HTML Inyectada
            st.markdown(f"""
                <div class="kpi-card-blue">
                    <div class="kpi-title">INVERSIÓN TOTAL EN LA OBRA</div>
                    <div class="kpi-value">${total_invertido:,.0f} <span style="font-size: 1rem; font-weight: 400;">UYU</span></div>
                    <div class="kpi-subtitle">Basado en {total_gastos} comprobantes registrados.</div>
                </div>
            """, unsafe_allow_html=True)
            
            st.markdown("### 📈 Distribución del Presupuesto")
            gastos_cat = df_dash.groupby("Categoria")["Monto_UYU"].sum().reset_index()
            fig_pie = px.pie(gastos_cat, values='Monto_UYU', names='Categoria', hole=0.5, 
                             color_discrete_sequence=px.colors.qualitative.Pastel)
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0), showlegend=True)
            st.plotly_chart(fig_pie, use_container_width=True, config={'displayModeBar': False})
            
            st.markdown("### 🗓️ Ritmo de Gastos")
            gastos_fecha = df_dash.groupby("Fecha")["Monto_UYU"].sum().reset_index()
            gastos_fecha = gastos_fecha.sort_values("Fecha")
            gastos_fecha["Gasto_Acumulado"] = gastos_fecha["Monto_UYU"].cumsum()
            fig_line = px.line(gastos_fecha, x='Fecha', y='Gasto_Acumulado', markers=True, 
                               color_discrete_sequence=["#2563EB"])
            fig_line.update_layout(margin=dict(t=10, b=0, l=0, r=0), xaxis_title="", yaxis_title="Monto (UYU)")
            st.plotly_chart(fig_line, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("👋 ¡Bienvenido! Registra tu primer gasto para ver los indicadores de la obra.")

    # --- MÓDULO 2: REGISTRAR GASTO ---
    elif menu == "📝 Gasto":
        st.markdown("### 🛒 Registrar Compra o Pago")
        
        with st.container():
            fecha = st.date_input("Fecha", datetime.date.today())
            concepto = st.text_input("Concepto / Descripción breve")
            
            col1, col2 = st.columns(2)
            moneda = col1.selectbox("Moneda", ["UYU", "USD"])
            monto = col2.number_input(f"Monto Total ({moneda})", min_value=0.0, value=None, placeholder="Ej: 15000", format="%.2f")
            
            tasa_cambio = 1.0
            if moneda == "USD":
                tasa_sugerida = obtener_tasa_usd_uyu()
                st.caption(f"ℹ️ Cotización referencial automática: ${tasa_sugerida}")
                tasa_cambio = st.number_input("Tasa de cambio a aplicar", min_value=1.0, value=float(tasa_sugerida), format="%.2f")
            
            lista_usuarios = usuarios_df["Usuario"].tolist()
            indice_usuario = lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0
            pagado_por = st.selectbox("¿Quién puso el dinero?", lista_usuarios, index=indice_usuario)
            
            categoria = st.selectbox("Categoría contable", ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            archivo_adjunto = st.file_uploader("📸 Adjuntar Factura/Boleta", type=["pdf", "png", "jpg", "jpeg"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Guardar Gasto", type="primary", use_container_width=True):
                if monto is None or monto <= 0:
                    st.error("Por favor, ingresa un monto válido mayor a 0.")
                elif not concepto:
                    st.error("Por favor, ingresa un concepto para el gasto.")
                else:
                    monto_uyu = monto * tasa_cambio
                    nombre_archivo = "Sin adjunto"
                    
                    if archivo_adjunto is not None:
                        nombre_archivo = f"{fecha}_{archivo_adjunto.name}"
                        ruta_guardado = os.path.join(DIR_COMPROBANTES, nombre_archivo)
                        with open(ruta_guardado, "wb") as f:
                            f.write(archivo_adjunto.getbuffer())
                    
                    id_unico = uuid.uuid4().hex
                    nuevo_dato = pd.DataFrame([{
                        "ID": id_unico,
                        "Fecha": fecha, 
                        "Concepto": concepto, 
                        "Moneda": moneda, 
                        "Monto_Original": monto, 
                        "Tasa_Cambio": tasa_cambio, 
                        "Monto_UYU": monto_uyu, 
                        "Pagado_por": pagado_por, 
                        "Categoria": categoria,
                        "Archivo_Adjunto": nombre_archivo,
                        "Modificado_por_Admin": False
                    }])
                    
                    df_gastos = pd.concat([df_gastos, nuevo_dato], ignore_index=True)
                    save_data(df_gastos, DATA_FILE)
                    st.toast(f"¡Gasto de ${monto_uyu:,.0f} guardado con éxito!", icon="✅")

    # --- MÓDULO 3: TRANSFERENCIAS ---
    elif menu == "💸 Transf.":
        st.markdown("### 💸 Rendición y Giros")
        
        lista_usuarios = [u for u in usuarios_df["Usuario"].tolist() if str(u).lower().strip() != "admin"]
        
        if len(lista_usuarios) < 2:
            st.info("Necesitas crear al menos 2 cuentas de socios para registrar transferencias.")
        else:
            fecha = st.date_input("Fecha de envío", datetime.date.today())
            
            col1, col2 = st.columns(2)
            idx_origen = lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0
            origen = col1.selectbox("¿Quién envía?", lista_usuarios, index=idx_origen)
            
            opciones_destino = [u for u in lista_usuarios if u != origen]
            destino = col2.selectbox("¿Quién recibe?", opciones_destino)
            
            col_m1, col_m2 = st.columns(2)
            moneda = col_m1.selectbox("Moneda", ["UYU", "USD"])
            monto = col_m2.number_input(f"Monto a enviar", min_value=0.0, value=None, placeholder="Ej: 5000", format="%.2f")
            
            tasa_cambio = 1.0
            if moneda == "USD":
                tasa_cambio = st.number_input("Tasa de cambio", min_value=1.0, value=float(obtener_tasa_usd_uyu()), format="%.2f")

            archivo_adjunto = st.file_uploader("📸 Comprobante bancario", type=["pdf", "png", "jpg", "jpeg"])
            
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Registrar Transferencia", type="primary", use_container_width=True):
                if monto is None or monto <= 0:
                    st.error("Ingresa un monto válido mayor a 0.")
                else:
                    monto_uyu = monto * tasa_cambio
                    nombre_archivo = "Sin adjunto"
                    
                    if archivo_adjunto is not None:
                        nombre_archivo = f"TRANSF_{fecha}_{archivo_adjunto.name}"
                        ruta_guardado = os.path.join(DIR_COMPROBANTES, nombre_archivo)
                        with open(ruta_guardado, "wb") as f:
                            f.write(archivo_adjunto.getbuffer())
                    
                    nuevo_dato = pd.DataFrame([{
                        "ID": uuid.uuid4().hex,
                        "Fecha": fecha, 
                        "Origen": origen, 
                        "Destino": destino, 
                        "Moneda": moneda, 
                        "Monto_Original": monto, 
                        "Tasa_Cambio": tasa_cambio, 
                        "Monto_UYU": monto_uyu, 
                        "Archivo_Adjunto": nombre_archivo
                    }])
                    
                    df_transfers = pd.concat([df_transfers, nuevo_dato], ignore_index=True)
                    save_data(df_transfers, TRANSFERS_FILE)
                    st.toast(f"¡Transferencia a {destino} guardada!", icon="✅")

    # --- MÓDULO 4: HISTORIAL ---
    elif menu == "📋 Historial":
        st.markdown("### 📋 Libro Mayor")
        
        if not df_gastos.empty:
            if st.session_state.gasto_a_editar is None:
                df_ordenado = df_gastos.sort_values(by="Fecha", ascending=False)
                es_admin = str(st.session_state.usuario_actual).strip().lower() == "admin"
                
                for _, fila in df_ordenado.iterrows():
                    es_dueno = str(fila["Pagado_por"]).strip().lower() == str(st.session_state.usuario_actual).strip().lower()
                    icono = "💳" if es_dueno else "🧾"
                    
                    titulo_tarjeta = f"{icono} **{fila['Concepto']}** —  ${fila['Monto_Original']:,.2f} {fila['Moneda']}"
                    
                    with st.expander(titulo_tarjeta):
                        if fila.get("Modificado_por_Admin", False):
                            st.caption("⚠️ *Aviso: Modificado por Administrador*")

                        st.markdown(f"""
                        <div style="font-size: 0.9rem; color: #4B5563;">
                            <b>Fecha:</b> {fila['Fecha']}<br>
                            <b>Socio:</b> {fila['Pagado_por']}<br>
                            <b>Categoría:</b> {fila['Categoria']}<br>
                            <b>Impacto Balance:</b> ${fila['Monto_UYU']:,.2f} UYU
                        </div>
                        """, unsafe_allow_html=True)
                        st.markdown("<br>", unsafe_allow_html=True)
                        
                        if fila['Archivo_Adjunto'] != "Sin adjunto":
                            ruta_img = os.path.join(DIR_COMPROBANTES, fila['Archivo_Adjunto'])
                            if os.path.exists(ruta_img) and ruta_img.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(ruta_img, use_container_width=True)
                            else:
                                st.write(f"📎 **Documento adjunto:** {fila['Archivo_Adjunto']}")
                        else:
                            st.caption("📄 *No hay comprobantes adjuntos*")
                        
                        if es_dueno or es_admin:
                            if st.button("✏️ Editar", key=f"btn_edit_{fila['ID']}", use_container_width=True):
                                st.session_state.gasto_a_editar = fila["ID"]
                                st.rerun()
                        else:
                            st.caption("🔒 Solo el dueño o el Administrador pueden editar.")

            # VISTA DE EDICIÓN
            else:
                id_seleccionado = st.session_state.gasto_a_editar
                fila_actual = df_gastos[df_gastos["ID"] == id_seleccionado].iloc[0]
                
                es_admin = str(st.session_state.usuario_actual).strip().lower() == "admin"
                es_dueno = str(fila_actual["Pagado_por"]).strip().lower() == str(st.session_state.usuario_actual).strip().lower()

                if st.button("🔙 Volver", use_container_width=True):
                    st.session_state.gasto_a_editar = None
                    st.rerun()
                
                st.markdown(f"### ✏️ Editando: {fila_actual['Concepto']}")
                if es_admin and not es_dueno:
                    st.warning("⚠️ Modo Admin: Quedará registro de esta modificación externa.")
                
                with st.container():
                    fecha_obj = datetime.datetime.strptime(str(fila_actual["Fecha"]), "%Y-%m-%d").date() if isinstance(fila_actual["Fecha"], str) else fila_actual["Fecha"]
                    edit_fecha = st.date_input("Fecha", fecha_obj)
                    edit_concepto = st.text_input("Concepto", fila_actual["Concepto"])
                    
                    col1, col2 = st.columns(2)
                    idx_moneda = ["UYU", "USD"].index(fila_actual["Moneda"]) if fila_actual["Moneda"] in ["UYU", "USD"] else 0
                    edit_moneda = col1.selectbox("Moneda", ["UYU", "USD"], index=idx_moneda)
                    edit_monto = col2.number_input("Monto", min_value=0.0, value=float(fila_actual["Monto_Original"]), format="%.2f")
                    
                    edit_tasa = 1.0
                    if edit_moneda == "USD":
                        edit_tasa = st.number_input("Tasa aplicada", min_value=1.0, value=float(fila_actual["Tasa_Cambio"]), format="%.2f")
                    
                    categorias = ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"]
                    idx_cat = categorias.index(fila_actual["Categoria"]) if fila_actual["Categoria"] in categorias else 0
                    edit_categoria = st.selectbox("Categoría", categorias, index=idx_cat)
                    
                    st.write(f"📁 Documento actual: **{fila_actual['Archivo_Adjunto']}**")
                    nuevo_archivo = st.file_uploader("Reemplazar foto", type=["pdf", "png", "jpg", "jpeg"])
                    
                    st.markdown("<br>", unsafe_allow_html=True)
                    col_save, col_del = st.columns(2)
                    
                    if col_save.button("💾 Guardar", type="primary", use_container_width=True):
                        cambios_log = []
                        if str(edit_fecha) != str(fila_actual["Fecha"]): cambios_log.append("Fecha")
                        if edit_concepto != fila_actual["Concepto"]: cambios_log.append("Concepto")
                        if edit_moneda != fila_actual["Moneda"]: cambios_log.append("Moneda")
                        if float(edit_monto) != float(fila_actual["Monto_Original"]): cambios_log.append("Monto")
                        if edit_categoria != fila_actual["Categoria"]: cambios_log.append("Categoría")
                        
                        nombre_archivo_final = fila_actual["Archivo_Adjunto"]
                        if nuevo_archivo is not None:
                            nombre_archivo_final = f"{edit_fecha}_{nuevo_archivo.name}"
                            ruta_guardado = os.path.join(DIR_COMPROBANTES, nombre_archivo_final)
                            with open(ruta_guardado, "wb") as f:
                                f.write(nuevo_archivo.getbuffer())
                            cambios_log.append("Archivo adjuntado")

                        nuevo_monto_uyu = edit_monto * edit_tasa
                        idx_general = df_gastos[df_gastos["ID"] == id_seleccionado].index[0]
                        
                        df_gastos.at[idx_general, "Fecha"] = edit_fecha
                        df_gastos.at[idx_general, "Concepto"] = edit_concepto
                        df_gastos.at[idx_general, "Moneda"] = edit_moneda
                        df_gastos.at[idx_general, "Monto_Original"] = edit_monto
                        df_gastos.at[idx_general, "Tasa_Cambio"] = edit_tasa
                        df_gastos.at[idx_general, "Monto_UYU"] = nuevo_monto_uyu
                        df_gastos.at[idx_general, "Categoria"] = edit_categoria
                        df_gastos.at[idx_general, "Archivo_Adjunto"] = nombre_archivo_final
                        
                        if es_admin and not es_dueno:
                            df_gastos.at[idx_general, "Modificado_por_Admin"] = True
                        
                        save_data(df_gastos, DATA_FILE)
                        registrar_log(id_seleccionado, st.session_state.usuario_actual, f"Editado: {','.join(cambios_log)}")
                        
                        st.toast("¡Cambios guardados!", icon="✅")
                        st.session_state.gasto_a_editar = None
                        st.rerun()

                    if col_del.button("🗑️ Eliminar", use_container_width=True):
                        df_gastos = df_gastos[df_gastos["ID"] != id_seleccionado]
                        save_data(df_gastos, DATA_FILE)
                        registrar_log(id_seleccionado, st.session_state.usuario_actual, "ELIMINADO COMPLETAMENTE")
                        st.toast("Registro eliminado definitivamente.", icon="🗑️")
                        st.session_state.gasto_a_editar = None
                        st.rerun()
        else:
            st.info("Aún no hay movimientos en el libro mayor.")

    # --- MÓDULO 5: BALANCE 50/50 ---
    elif menu == "⚖️ Balance":
        st.markdown("### ⚖️ Balance 50/50")
        
        usuarios_socios = [u for u in usuarios_df["Usuario"].tolist() if str(u).lower().strip() != "admin"]
        if len(usuarios_socios) < 2:
            st.info("⚠️ Crea al menos 2 cuentas de socios para ver el cálculo matemático.")
        else:
            usuario_1 = usuarios_socios[0]
            usuario_2 = usuarios_socios[1]
            
            gastos_1 = df_gastos[df_gastos["Pagado_por"] == usuario_1]["Monto_UYU"].sum() if not df_gastos.empty else 0.0
            gastos_2 = df_gastos[df_gastos["Pagado_por"] == usuario_2]["Monto_UYU"].sum() if not df_gastos.empty else 0.0
            total_proyecto = gastos_1 + gastos_2
            meta_individual = total_proyecto / 2
            
            enviado_1 = df_transfers[df_transfers["Origen"] == usuario_1]["Monto_UYU"].sum() if not df_transfers.empty else 0.0
            recibido_1 = df_transfers[df_transfers["Destino"] == usuario_1]["Monto_UYU"].sum() if not df_transfers.empty else 0.0
            
            enviado_2 = df_transfers[df_transfers["Origen"] == usuario_2]["Monto_UYU"].sum() if not df_transfers.empty else 0.0
            recibido_2 = df_transfers[df_transfers["Destino"] == usuario_2]["Monto_UYU"].sum() if not df_transfers.empty else 0.0
            
            saldo_1 = gastos_1 + enviado_1 - recibido_1
            saldo_2 = gastos_2 + enviado_2 - recibido_2
            
            diferencia = abs(saldo_1 - meta_individual)

            # Tarjeta de Veredicto Principal (Diseño Custom HTML)
            if diferencia < 1: 
                color_card = "kpi-card-green"
                titulo_alerta = "¡CUENTAS CLARAS!"
                mensaje_alerta = "Ambos socios están al día. Nadie debe dinero."
            elif saldo_1 > meta_individual:
                color_card = "kpi-card-blue"
                titulo_alerta = f"ACCIONES REQUERIDAS"
                mensaje_alerta = f"{usuario_2} debe enviar a {usuario_1}:<br><span style='font-size: 2.5rem; font-weight: 800;'>${diferencia:,.0f}</span> <span style='font-size:1rem'>UYU</span>"
            else:
                color_card = "kpi-card-blue"
                titulo_alerta = f"ACCIONES REQUERIDAS"
                mensaje_alerta = f"{usuario_1} debe enviar a {usuario_2}:<br><span style='font-size: 2.5rem; font-weight: 800;'>${diferencia:,.0f}</span> <span style='font-size:1rem'>UYU</span>"

            st.markdown(f"""
                <div class="{color_card}" style="text-align: center; margin-bottom: 30px;">
                    <div class="kpi-title" style="font-weight: 600; letter-spacing: 1px;">{titulo_alerta}</div>
                    <div style="font-size: 1.2rem; margin-top: 10px;">{mensaje_alerta}</div>
                </div>
            """, unsafe_allow_html=True)
            
            # Tarjetas individuales de resumen
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"""
                    <div class="kpi-card-white">
                        <div style="color:#2563EB; font-weight:800; font-size:1.1rem; margin-bottom:10px;">👤 {usuario_1}</div>
                        <div style="font-size: 0.9rem; color: #4B5563;">
                            Gastos en Obra: <b style="float:right;">${gastos_1:,.0f}</b><br>
                            Girado: <span style="float:right; color:#10B981;">+${enviado_1:,.0f}</span><br>
                            Recibido: <span style="float:right; color:#EF4444;">-${recibido_1:,.0f}</span><br>
                            <hr style="margin: 8px 0;">
                            <b>Aporte Neto: <span style="float:right; color:#111827;">${saldo_1:,.0f}</span></b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)
                
            with col2:
                st.markdown(f"""
                    <div class="kpi-card-white">
                        <div style="color:#2563EB; font-weight:800; font-size:1.1rem; margin-bottom:10px;">👤 {usuario_2}</div>
                        <div style="font-size: 0.9rem; color: #4B5563;">
                            Gastos en Obra: <b style="float:right;">${gastos_2:,.0f}</b><br>
                            Girado: <span style="float:right; color:#10B981;">+${enviado_2:,.0f}</span><br>
                            Recibido: <span style="float:right; color:#EF4444;">-${recibido_2:,.0f}</span><br>
                            <hr style="margin: 8px 0;">
                            <b>Aporte Neto: <span style="float:right; color:#111827;">${saldo_2:,.0f}</span></b>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

    # --- MÓDULO 6: ADMIN (USUARIOS) ---
    elif menu == "👥 Admin":
        st.header("👥 Gestión Interna")
        st.dataframe(usuarios_df[["Usuario"]], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Registrar Socio")
        with st.container():
            nuevo_nombre = st.text_input("Nombre de Usuario")
            nueva_clave = st.text_input("Contraseña", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("Crear Usuario", type="primary", use_container_width=True):
                if nuevo_nombre in usuarios_df["Usuario"].values:
                    st.error("Ese usuario ya existe.")
                elif nuevo_nombre and nueva_clave:
                    nuevo_usr = pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])
                    usuarios_df = pd.concat([usuarios_df, nuevo_usr], ignore_index=True)
                    save_data(usuarios_df, USERS_FILE)
                    st.toast(f"Usuario '{nuevo_nombre}' habilitado.", icon="✅")
                    st.rerun()
