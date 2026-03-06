import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px
import requests
import uuid

# --- CONFIGURACIÓN INICIAL Y UI DE "APP NATIVA" ---
st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide", initial_sidebar_state="collapsed")

st.markdown("""
    <style>
    /* Ocultar menú por defecto y footer para ganar espacio en celular */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    /* Reducir el margen superior blanco */
    .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    /* Estilizar las pestañas superiores para que parezcan botones de app */
    div.stRadio > div[role="radiogroup"] > label {
        background-color: #f0f2f6;
        padding: 5px 10px;
        border-radius: 8px;
        margin-right: 5px;
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
    st.title("🏡 Casa La Serena")
    st.write("Por favor, inicia sesión para continuar.")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Ingresar al Proyecto")
        
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
    # --- MENÚ LATERAL DE PERFIL ---
    st.sidebar.title("🏡 La Serena")
    st.sidebar.write(f"👤 Conectado como: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("🚪 Cerrar Sesión"):
        st.session_state.logueado = False
        st.session_state.usuario_actual = ""
        st.session_state.gasto_a_editar = None
        st.rerun()
        
    # --- MENÚ SUPERIOR DE NAVEGACIÓN ---
    opciones_menu = ["📊 Dashboard", "📝 Gasto", "💸 Transf.", "📋 Historial", "⚖️ Balance", "👥 Perfiles"]
    
    menu = st.radio(
        "Navegación", 
        opciones_menu, 
        horizontal=True, 
        label_visibility="collapsed"
    )
    st.markdown("---")

    if menu != "📋 Historial":
        st.session_state.gasto_a_editar = None

    df_gastos = load_data()
    df_transfers = load_transfers()

    # --- MÓDULO 1: MONITOREO DE GASTOS (DASHBOARD) ---
    if menu == "📊 Dashboard":
        st.header("📊 Resumen de la Obra")
        if not df_gastos.empty:
            df_dash = df_gastos.copy()
            df_dash['Fecha'] = pd.to_datetime(df_dash['Fecha'])
            
            # KPI Cards Rápidas Arriba
            total_invertido = df_dash["Monto_UYU"].sum()
            col1, col2 = st.columns(2)
            col1.metric("Inversión Total", f"${total_invertido:,.0f} UYU")
            col2.metric("Total Registros", f"{len(df_dash)} Gastos")
            st.markdown("---")
            
            st.subheader("Distribución por Categoría")
            gastos_cat = df_dash.groupby("Categoria")["Monto_UYU"].sum().reset_index()
            fig_pie = px.pie(gastos_cat, values='Monto_UYU', names='Categoria', hole=0.5)
            # Quitar márgenes al gráfico para que ocupe menos espacio en móvil
            fig_pie.update_layout(margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig_pie, use_container_width=True)
            
            st.subheader("Evolución del Costo Acumulado")
            gastos_fecha = df_dash.groupby("Fecha")["Monto_UYU"].sum().reset_index()
            gastos_fecha = gastos_fecha.sort_values("Fecha")
            gastos_fecha["Gasto_Acumulado"] = gastos_fecha["Monto_UYU"].cumsum()
            fig_line = px.line(gastos_fecha, x='Fecha', y='Gasto_Acumulado', markers=True)
            fig_line.update_layout(margin=dict(t=10, b=0, l=0, r=0))
            st.plotly_chart(fig_line, use_container_width=True)
        else:
            st.info("Aún no hay datos para mostrar gráficos. ¡Registra el primer gasto!")

    # --- MÓDULO 2: REGISTRAR GASTO ---
    elif menu == "📝 Gasto":
        st.header("📝 Registrar Nuevo Gasto")
        
        with st.container():
            fecha = st.date_input("Fecha", datetime.date.today())
            concepto = st.text_input("Concepto (Ej. Cemento, Honorarios)")
            
            col1, col2 = st.columns(2)
            moneda = col1.selectbox("Moneda", ["UYU", "USD"])
            monto = col2.number_input(f"Monto ({moneda})", min_value=0.0, value=None, placeholder="Ej: 1500", format="%.2f")
            
            tasa_cambio = 1.0
            if moneda == "USD":
                tasa_sugerida = obtener_tasa_usd_uyu()
                st.caption("ℹ️ Tipo de cambio referencial automático.")
                tasa_cambio = st.number_input("Tasa de cambio", min_value=1.0, value=float(tasa_sugerida), format="%.2f")
            
            lista_usuarios = usuarios_df["Usuario"].tolist()
            indice_usuario = lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0
            pagado_por = st.selectbox("¿Quién lo pagó?", lista_usuarios, index=indice_usuario)
            
            categoria = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"])
            archivo_adjunto = st.file_uploader("Adjuntar Foto/Boleta (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
            
            if st.button("💾 Guardar Registro", type="primary", use_container_width=True):
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
                    
                    # Notificación nativa tipo pop-up
                    st.toast(f"¡Gasto de ${monto_uyu:,.0f} guardado con éxito!", icon="✅")

    # --- MÓDULO 3: REGISTRAR TRANSFERENCIA ---
    elif menu == "💸 Transf.":
        st.header("💸 Rendición de Cuentas")
        
        lista_usuarios = [u for u in usuarios_df["Usuario"].tolist() if str(u).lower().strip() != "admin"]
        
        if len(lista_usuarios) < 2:
            st.info("Necesitas crear al menos 2 cuentas de socios para registrar transferencias.")
        else:
            fecha = st.date_input("Fecha", datetime.date.today())
            
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

            archivo_adjunto = st.file_uploader("Adjuntar comprobante bancario (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
            
            if st.button("📤 Guardar Transferencia", type="primary", use_container_width=True):
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

    # --- MÓDULO 4: LISTADO DE GASTOS E HISTORIAL ---
    elif menu == "📋 Historial":
        st.header("📋 Historial de Movimientos")
        
        if not df_gastos.empty:
            if st.session_state.gasto_a_editar is None:
                df_ordenado = df_gastos.sort_values(by="Fecha", ascending=False)
                es_admin = str(st.session_state.usuario_actual).strip().lower() == "admin"
                
                for _, fila in df_ordenado.iterrows():
                    es_dueno = str(fila["Pagado_por"]).strip().lower() == str(st.session_state.usuario_actual).strip().lower()
                    icono_socio = "🟢" if es_dueno else "🔵"
                    
                    titulo_tarjeta = f"{icono_socio} {fila['Fecha']} | {fila['Concepto']} | ${fila['Monto_Original']:,.2f} {fila['Moneda']}"
                    
                    with st.expander(titulo_tarjeta):
                        if fila.get("Modificado_por_Admin", False):
                            st.caption("⚠️ *Modificado por Admin*")

                        col_a, col_b = st.columns(2)
                        col_a.write(f"**Pagó:** {fila['Pagado_por']}")
                        col_b.write(f"**Cat:** {fila['Categoria']}")
                        st.write(f"**Base:** ${fila['Monto_UYU']:,.2f} UYU")
                        
                        # MEJORA UX: Visualizador de imágenes integrado
                        if fila['Archivo_Adjunto'] != "Sin adjunto":
                            ruta_img = os.path.join(DIR_COMPROBANTES, fila['Archivo_Adjunto'])
                            if os.path.exists(ruta_img) and ruta_img.lower().endswith(('.png', '.jpg', '.jpeg')):
                                st.image(ruta_img, caption="Comprobante Adjunto", use_container_width=True)
                            else:
                                st.write(f"📎 **Documento:** {fila['Archivo_Adjunto']}")
                        else:
                            st.write("📄 *Sin foto adjunta*")
                        
                        st.markdown("---")
                        if es_dueno or es_admin:
                            if st.button("✏️ Editar Gasto", key=f"btn_edit_{fila['ID']}", use_container_width=True):
                                st.session_state.gasto_a_editar = fila["ID"]
                                st.rerun()
                        else:
                            st.caption("🔒 Solo el dueño o el Administrador pueden editar este gasto.")

            # VISTA DE EDICIÓN
            else:
                id_seleccionado = st.session_state.gasto_a_editar
                fila_actual = df_gastos[df_gastos["ID"] == id_seleccionado].iloc[0]
                
                es_admin = str(st.session_state.usuario_actual).strip().lower() == "admin"
                es_dueno = str(fila_actual["Pagado_por"]).strip().lower() == str(st.session_state.usuario_actual).strip().lower()

                if st.button("🔙 Volver a la lista"):
                    st.session_state.gasto_a_editar = None
                    st.rerun()
                
                st.subheader(f"Editando: {fila_actual['Concepto']}")
                
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
                
                st.markdown("---")
                col_save, col_del = st.columns(2)
                
                # Botón Guardar
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
                    
                    st.toast("¡Modificaciones guardadas exitosamente!", icon="✅")
                    st.session_state.gasto_a_editar = None
                    st.rerun()

                # Botón Eliminar
                if col_del.button("🗑️ Eliminar Gasto", use_container_width=True):
                    df_gastos = df_gastos[df_gastos["ID"] != id_seleccionado]
                    save_data(df_gastos, DATA_FILE)
                    registrar_log(id_seleccionado, st.session_state.usuario_actual, "ELIMINADO COMPLETAMENTE")
                    st.toast("Registro eliminado.", icon="🗑️")
                    st.session_state.gasto_a_editar = None
                    st.rerun()
                    
        else:
            st.info("Aún no hay gastos registrados en el proyecto.")

    # --- MÓDULO 5: BALANCE 50/50 ---
    elif menu == "⚖️ Balance":
        st.header("⚖️ Estado de Cuentas")
        
        usuarios_socios = [u for u in usuarios_df["Usuario"].tolist() if str(u).lower().strip() != "admin"]
        if len(usuarios_socios) < 2:
            st.info("⚠️ Se necesitan 2 socios creados para calcular el balance.")
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

            # Tarjeta visual destacada del veredicto final
            if diferencia < 1: 
                st.success("🎉 **¡Están perfectamente al día! Nadie debe nada.**")
            elif saldo_1 > meta_individual:
                st.error(f"👉 **{usuario_2}** debe transferirle a **{usuario_1}**: \n\n ### ${diferencia:,.0f} UYU")
            else:
                st.error(f"👉 **{usuario_1}** debe transferirle a **{usuario_2}**: \n\n ### ${diferencia:,.0f} UYU")

            st.markdown("---")
            st.write(f"**Costo total acumulado:** ${total_proyecto:,.0f} UYU")
            st.write(f"*(Aporte ideal por socio: ${meta_individual:,.0f} UYU)*")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown(f"#### 👤 {usuario_1}")
                st.caption(f"Pagó en obra: ${gastos_1:,.0f}")
                st.caption(f"Transferencias: ${(enviado_1 - recibido_1):,.0f}")
                st.write(f"**Aporte Neto:** ${saldo_1:,.0f}")
                
            with col2:
                st.markdown(f"#### 👤 {usuario_2}")
                st.caption(f"Pagó en obra: ${gastos_2:,.0f}")
                st.caption(f"Transferencias: ${(enviado_2 - recibido_2):,.0f}")
                st.write(f"**Aporte Neto:** ${saldo_2:,.0f}")

    # --- MÓDULO 6: GESTIONAR USUARIOS ---
    elif menu == "👥 Perfiles":
        st.header("👥 Usuarios")
        st.dataframe(usuarios_df[["Usuario"]], use_container_width=True)
        
        st.markdown("---")
        st.subheader("Agregar Nuevo Socio")
        with st.form("nuevo_usuario"):
            nuevo_nombre = st.text_input("Nombre de Usuario")
            nueva_clave = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Crear Usuario", use_container_width=True):
                if nuevo_nombre in usuarios_df["Usuario"].values:
                    st.error("Ese usuario ya existe.")
                elif nuevo_nombre and nueva_clave:
                    nuevo_usr = pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])
                    usuarios_df = pd.concat([usuarios_df, nuevo_usr], ignore_index=True)
                    save_data(usuarios_df, USERS_FILE)
                    st.toast(f"Usuario '{nuevo_nombre}' creado.", icon="✅")
                    st.rerun()
