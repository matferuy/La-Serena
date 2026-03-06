import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import uuid

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_FILE = "contabilidad_casa.csv"
USERS_FILE = "usuarios.csv"
LOG_FILE = "log_modificaciones.csv"
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
            save_data(df, DATA_FILE)
        return df
    else:
        return pd.DataFrame(columns=[
            "ID", "Fecha", "Concepto", "Moneda", "Monto_Original", "Tasa_Cambio", 
            "Monto_UYU", "Pagado_por", "Categoria", "Archivo_Adjunto"
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
    st.set_page_config(page_title="Login - Casa La Serena", page_icon="🏡", layout="centered")
    st.title("🔒 Acceso al Proyecto")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar")
        
        if submit_login:
            user_match = usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"].astype(str) == str(clave))]
            if not user_match.empty:
                st.session_state.logueado = True
                st.session_state.usuario_actual = usuario
                st.rerun()
            else:
                st.error("Credenciales incorrectas.")

# --- APLICACIÓN PRINCIPAL ---
else:
    st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide")
    st.title("🏡 Proyecto Casa La Serena")
    
    st.sidebar.write(f"👤 Usuario activo: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.session_state.usuario_actual = ""
        st.session_state.gasto_a_editar = None
        st.rerun()
        
    st.sidebar.markdown("---")
    menu = st.sidebar.selectbox("Navegación", [
        "Registrar Gasto", 
        "Listado de Gastos",
        "Balance General", 
        "Monitoreo de Gastos", 
        "Gestionar Usuarios"
    ])

    # Limpiamos el estado de edición si el usuario cambia de pestaña
    if menu != "Listado de Gastos":
        st.session_state.gasto_a_editar = None

    df_gastos = load_data()

    # --- MÓDULO 1: REGISTRAR GASTO ---
    if menu == "Registrar Gasto":
        st.header("📝 Nuevo Registro de Gasto")
        
        fecha = st.date_input("Fecha", datetime.date.today())
        concepto = st.text_input("Concepto (Ej. Pago arquitecto, Cemento)")
        
        col1, col2 = st.columns(2)
        moneda = col1.selectbox("Moneda", ["UYU", "USD"])
        monto = col2.number_input(f"Monto en {moneda}", min_value=0.0, format="%.2f")
        
        tasa_cambio = 1.0
        if moneda == "USD":
            tasa_sugerida = obtener_tasa_usd_uyu()
            st.info("🌐 Tipo de cambio interbancario referencial obtenido automáticamente.")
            tasa_cambio = st.number_input("Tasa de cambio a aplicar", min_value=1.0, value=float(tasa_sugerida), format="%.2f")
        
        lista_usuarios = usuarios_df["Usuario"].tolist()
        indice_usuario = lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0
        pagado_por = st.selectbox("¿Quién pagó?", lista_usuarios, index=indice_usuario)
        
        categoria = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"])
        
        archivo_adjunto = st.file_uploader("Adjuntar Boleta/Factura (Opcional - Puedes subirlo después)", type=["pdf", "png", "jpg", "jpeg"])
        
        if st.button("Guardar Gasto", type="primary"):
            if monto <= 0:
                st.error("El monto debe ser mayor a 0.")
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
                    "Archivo_Adjunto": nombre_archivo
                }])
                
                df_gastos = pd.concat([df_gastos, nuevo_dato], ignore_index=True)
                save_data(df_gastos, DATA_FILE)
                st.success(f"¡Gasto registrado con éxito! Equivalente: **${monto_uyu:,.2f} UYU**")

    # --- MÓDULO 2: LISTADO DE GASTOS (VISTA DE LISTA Y EDICIÓN) ---
    elif menu == "Listado de Gastos":
        st.header("📋 Historial del Proyecto")
        
        if not df_gastos.empty:
            # VISTA 1: LISTA ORDENADA PARA TODOS
            if st.session_state.gasto_a_editar is None:
                st.write("Historial completo. Solo puedes editar los gastos que tú hayas registrado (✏️).")
                
                df_ordenado = df_gastos.sort_values(by="Fecha", ascending=False)
                
                col1, col2, col3, col4, col5, col6 = st.columns([2, 3, 2, 1, 2, 1])
                col1.markdown("**Fecha**")
                col2.markdown("**Concepto**")
                col3.markdown("**Monto**")
                col4.markdown("**Moneda**")
                col5.markdown("**Socio**")
                col6.markdown("**Acción**")
                st.markdown("---")
                
                for _, fila in df_ordenado.iterrows():
                    c1, c2, c3, c4, c5, c6 = st.columns([2, 3, 2, 1, 2, 1])
                    c1.write(fila["Fecha"])
                    c2.write(fila["Concepto"])
                    c3.write(f"${fila['Monto_Original']:,.2f}")
                    c4.write(fila["Moneda"])
                    c5.write(fila["Pagado_por"])
                    
                    with c6:
                        # Validación de seguridad visual
                        if fila["Pagado_por"] == st.session_state.usuario_actual:
                            if st.button("✏️", key=f"btn_{fila['ID']}"):
                                st.session_state.gasto_a_editar = fila["ID"]
                                st.rerun()
                        else:
                            st.write("🔒")

            # VISTA 2: FORMULARIO DE EDICIÓN (SOLO PARA EL CREADOR)
            else:
                id_seleccionado = st.session_state.gasto_a_editar
                fila_actual = df_gastos[df_gastos["ID"] == id_seleccionado].iloc[0]
                
                # Segunda validación de seguridad (por si alguien fuerza el estado)
                if fila_actual["Pagado_por"] != st.session_state.usuario_actual:
                    st.error("No tienes permisos para editar este gasto.")
                    if st.button("🔙 Volver"):
                        st.session_state.gasto_a_editar = None
                        st.rerun()
                else:
                    if st.button("🔙 Volver a la lista de gastos"):
                        st.session_state.gasto_a_editar = None
                        st.rerun()
                    
                    st.markdown("---")
                    st.subheader(f"Editando: {fila_actual['Concepto']}")
                    
                    with st.form("form_edicion"):
                        fecha_obj = datetime.datetime.strptime(str(fila_actual["Fecha"]), "%Y-%m-%d").date() if isinstance(fila_actual["Fecha"], str) else fila_actual["Fecha"]
                        
                        edit_fecha = st.date_input("Fecha", fecha_obj)
                        edit_concepto = st.text_input("Concepto", fila_actual["Concepto"])
                        
                        col1, col2 = st.columns(2)
                        idx_moneda = ["UYU", "USD"].index(fila_actual["Moneda"]) if fila_actual["Moneda"] in ["UYU", "USD"] else 0
                        edit_moneda = col1.selectbox("Moneda", ["UYU", "USD"], index=idx_moneda)
                        edit_monto = col2.number_input("Monto", min_value=0.0, value=float(fila_actual["Monto_Original"]), format="%.2f")
                        
                        edit_tasa = 1.0
                        if edit_moneda == "USD":
                            edit_tasa = st.number_input("Tasa de cambio aplicada", min_value=1.0, value=float(fila_actual["Tasa_Cambio"]), format="%.2f")
                        
                        categorias = ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"]
                        idx_cat = categorias.index(fila_actual["Categoria"]) if fila_actual["Categoria"] in categorias else 0
                        edit_categoria = st.selectbox("Categoría", categorias, index=idx_cat)
                        
                        st.write(f"📁 Documento actual: **{fila_actual['Archivo_Adjunto']}**")
                        nuevo_archivo = st.file_uploader("Subir documento nuevo (Reemplaza al anterior)", type=["pdf", "png", "jpg", "jpeg"])
                        
                        guardar_cambios = st.form_submit_button("Guardar Modificaciones")
                        
                        if guardar_cambios:
                            cambios_log = []
                            
                            if str(edit_fecha) != str(fila_actual["Fecha"]): cambios_log.append(f"Fecha ({fila_actual['Fecha']} -> {edit_fecha})")
                            if edit_concepto != fila_actual["Concepto"]: cambios_log.append(f"Concepto ('{fila_actual['Concepto']}' -> '{edit_concepto}')")
                            if edit_moneda != fila_actual["Moneda"]: cambios_log.append(f"Moneda ({fila_actual['Moneda']} -> {edit_moneda})")
                            if edit_monto != fila_actual["Monto_Original"]: cambios_log.append(f"Monto ({fila_actual['Monto_Original']} -> {edit_monto})")
                            if edit_categoria != fila_actual["Categoria"]: cambios_log.append(f"Categoría ({fila_actual['Categoria']} -> {edit_categoria})")
                            
                            nombre_archivo_final = fila_actual["Archivo_Adjunto"]
                            if nuevo_archivo is not None:
                                nombre_archivo_final = f"{edit_fecha}_{nuevo_archivo.name}"
                                ruta_guardado = os.path.join(DIR_COMPROBANTES, nombre_archivo_final)
                                with open(ruta_guardado, "wb") as f:
                                    f.write(nuevo_archivo.getbuffer())
                                cambios_log.append(f"Archivo adjuntado ({nuevo_archivo.name})")

                            if cambios_log:
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
                                
                                save_data(df_gastos, DATA_FILE)
                                registrar_log(id_seleccionado, st.session_state.usuario_actual, " | ".join(cambios_log))
                                
                                st.success("¡Modificaciones guardadas!")
                                st.session_state.gasto_a_editar = None
                                st.rerun()
                            else:
                                st.info("No detecté ninguna modificación para guardar.")
        else:
            st.info("Aún no hay gastos registrados en el proyecto.")

    # --- MÓDULO 3: BALANCE 50/50 ---
    elif menu == "Balance General":
        st.header("⚖️ Balance de Cuentas (Base UYU)")
        
        usuarios_socios = [u for u in usuarios_df["Usuario"].tolist() if u != "admin"]
        if len(usuarios_socios) < 2:
            usuarios_socios = usuarios_df["Usuario"].tolist()

        if len(usuarios_socios) >= 2:
            usuario_1 = usuarios_socios[0]
            usuario_2 = usuarios_socios[1]
            
            total_1 = df_gastos[df_gastos["Pagado_por"] == usuario_1]["Monto_UYU"].sum() if not df_gastos.empty else 0.0
            total_2 = df_gastos[df_gastos["Pagado_por"] == usuario_2]["Monto_UYU"].sum() if not df_gastos.empty else 0.0
                
            st.subheader("Resumen de Aportes")
            col1, col2 = st.columns(2)
            col1.metric(f"Total {usuario_1}", f"${total_1:,.2f} UYU")
            col2.metric(f"Total {usuario_2}", f"${total_2:,.2f} UYU")
            
            diferencia = abs(total_1 - total_2)
            deuda = diferencia / 2
            
            st.markdown("---")
            st.subheader("💡 Estado de Cuentas (50/50):")
            if total_1 > total_2:
                st.info(f"👉 **{usuario_2}** debe transferir a **{usuario_1}**: **${deuda:,.2f} UYU**")
            elif total_2 > total_1:
                st.info(f"👉 **{usuario_1}** debe transferir a **{usuario_2}**: **${deuda:,.2f} UYU**")
            else:
                st.success("¡Están al día perfectamente equilibrados!")
                
        else:
            st.warning("⚠️ Ve a 'Gestionar Usuarios' y crea al menos 2 cuentas.")

    # --- MÓDULO 4: MONITOREO DE GASTOS ---
    elif menu == "Monitoreo de Gastos":
        st.header("📊 Dashboard de Gastos")
        if not df_gastos.empty:
            df_gastos['Fecha'] = pd.to_datetime(df_gastos['Fecha'])
            
            col1, col2 = st.columns(2)
            with col1:
                st.subheader("Distribución por Categoría")
                gastos_cat = df_gastos.groupby("Categoria")["Monto_UYU"].sum().reset_index()
                fig_pie = px.pie(gastos_cat, values='Monto_UYU', names='Categoria', hole=0.4)
                st.plotly_chart(fig_pie, use_container_width=True)
                
            with col2:
                st.subheader("Evolución del Gasto")
                gastos_fecha = df_gastos.groupby("Fecha")["Monto_UYU"].sum().reset_index()
                gastos_fecha = gastos_fecha.sort_values("Fecha")
                gastos_fecha["Gasto_Acumulado"] = gastos_fecha["Monto_UYU"].cumsum()
                fig_line = px.line(gastos_fecha, x='Fecha', y='Gasto_Acumulado', markers=True)
                st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Registra algunos gastos primero para poder ver los gráficos.")

    # --- MÓDULO 5: GESTIONAR USUARIOS ---
    elif menu == "Gestionar Usuarios":
        st.header("👥 Gestión de Usuarios")
        st.dataframe(usuarios_df[["Usuario"]])
        
        st.markdown("---")
        st.subheader("Agregar Nuevo Socio")
        with st.form("nuevo_usuario"):
            nuevo_nombre = st.text_input("Nombre de Usuario")
            nueva_clave = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Crear Usuario"):
                if nuevo_nombre in usuarios_df["Usuario"].values:
                    st.error("Ese usuario ya existe.")
                elif nuevo_nombre and nueva_clave:
                    nuevo_usr = pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])
                    usuarios_df = pd.concat([usuarios_df, nuevo_usr], ignore_index=True)
                    save_data(usuarios_df, USERS_FILE)
                    st.success(f"Usuario '{nuevo_nombre}' creado.")
                    st.rerun()
