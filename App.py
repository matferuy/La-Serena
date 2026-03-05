import streamlit as st
import pandas as pd
import os
import datetime
import plotly.express as px

# --- CONFIGURACIÓN DE ARCHIVOS Y CARPETAS ---
DATA_FILE = "contabilidad_casa.csv"
USERS_FILE = "usuarios.csv"
DIR_COMPROBANTES = "comprobantes"

# Crear carpeta para comprobantes si no existe
if not os.path.exists(DIR_COMPROBANTES):
    os.makedirs(DIR_COMPROBANTES)

# --- FUNCIONES DE DATOS ---
def load_users():
    if os.path.exists(USERS_FILE):
        # Forzamos a que lea los datos como texto para evitar errores con claves numéricas
        return pd.read_csv(USERS_FILE, dtype={"Usuario": str, "Clave": str})
    else:
        # Crea un usuario administrador por defecto si no existe
        default_users = pd.DataFrame([{"Usuario": "admin", "Clave": "1234"}])
        default_users.to_csv(USERS_FILE, index=False)
        return default_users

def load_data():
    if os.path.exists(DATA_FILE):
        return pd.read_csv(DATA_FILE)
    else:
        return pd.DataFrame(columns=[
            "Fecha", "Concepto", "Moneda", "Monto_Original", "Tasa_Cambio", 
            "Monto_UYU", "Pagado_por", "Categoria", "Archivo_Adjunto"
        ])

def save_data(df, file_name):
    df.to_csv(file_name, index=False)

# --- INICIALIZACIÓN DE SESIÓN ---
if "logueado" not in st.session_state:
    st.session_state.logueado = False
    st.session_state.usuario_actual = ""

usuarios_df = load_users()

# --- PANTALLA DE LOGIN ---
if not st.session_state.logueado:
    st.set_page_config(page_title="Login - Casa La Serena", page_icon="🏡", layout="centered")
    st.title("🔒 Acceso al Proyecto")
    st.write("Ingresa tus credenciales para continuar.")
    
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        clave = st.text_input("Contraseña", type="password")
        submit_login = st.form_submit_button("Entrar")
        
        if submit_login:
            # Comparamos asegurando que ambos lados sean texto (str)
            user_match = usuarios_df[(usuarios_df["Usuario"] == usuario) & (usuarios_df["Clave"].astype(str) == str(clave))]
            if not user_match.empty:
                st.session_state.logueado = True
                st.session_state.usuario_actual = usuario
                st.rerun()
            else:
                st.error("Credenciales incorrectas. Verifica tu usuario y contraseña.")

# --- APLICACIÓN PRINCIPAL ---
else:
    st.set_page_config(page_title="Casa La Serena", page_icon="🏡", layout="wide")
    st.title("🏡 Proyecto Casa La Serena")
    
    # Barra lateral
    st.sidebar.write(f"👤 Usuario activo: **{st.session_state.usuario_actual}**")
    if st.sidebar.button("Cerrar Sesión"):
        st.session_state.logueado = False
        st.session_state.usuario_actual = ""
        st.rerun()
        
    st.sidebar.markdown("---")
    menu = st.sidebar.selectbox("Navegación", [
        "Registrar Gasto", 
        "Balance General", 
        "Monitoreo de Gastos", 
        "Gestionar Usuarios"
    ])

    df_gastos = load_data()

    # --- MÓDULO 1: REGISTRAR GASTO ---
    if menu == "Registrar Gasto":
        st.header("📝 Nuevo Registro de Gasto")
        
        with st.form("registro_form", clear_on_submit=True):
            fecha = st.date_input("Fecha", datetime.date.today())
            concepto = st.text_input("Concepto (Ej. Pago arquitecto, Cemento, Honorarios)")
            
            col1, col2 = st.columns(2)
            moneda = col1.selectbox("Moneda", ["UYU", "USD"])
            monto = col2.number_input(f"Monto en {moneda}", min_value=0.0, format="%.2f")
            
            tasa_cambio = 1.0
            if moneda == "USD":
                tasa_cambio = st.number_input("Tasa de cambio (Pesos uruguayos por 1 USD hoy)", min_value=1.0, value=39.0)
            
            lista_usuarios = usuarios_df["Usuario"].tolist()
            indice_usuario = lista_usuarios.index(st.session_state.usuario_actual) if st.session_state.usuario_actual in lista_usuarios else 0
            pagado_por = st.selectbox("¿Quién pagó?", lista_usuarios, index=indice_usuario)
            
            categoria = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Trámites/Permisos", "Terreno", "Otros"])
            
            archivo_adjunto = st.file_uploader("Adjuntar Boleta/Factura (Opcional)", type=["pdf", "png", "jpg", "jpeg"])
            
            submit = st.form_submit_button("Guardar Gasto")
            
            if submit:
                monto_uyu = monto * tasa_cambio
                nombre_archivo = "Sin adjunto"
                
                if archivo_adjunto is not None:
                    nombre_archivo = f"{fecha}_{archivo_adjunto.name}"
                    ruta_guardado = os.path.join(DIR_COMPROBANTES, nombre_archivo)
                    with open(ruta_guardado, "wb") as f:
                        f.write(archivo_adjunto.getbuffer())
                
                nuevo_dato = pd.DataFrame([{
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
                st.success(f"¡Gasto registrado con éxito! Equivalente: ${monto_uyu:,.2f} UYU")

    # --- MÓDULO 2: BALANCE 50/50 ---
    elif menu == "Balance General":
        st.header("⚖️ Balance de Cuentas (Base UYU)")
        if not df_gastos.empty:
            st.dataframe(df_gastos, use_container_width=True)
            
            totales = df_gastos.groupby("Pagado_por")["Monto_UYU"].sum().reset_index()
            
            st.markdown("---")
            st.subheader("Resumen de Aportes")
            
            if len(totales) == 2:
                usuario_1, total_1 = totales.iloc[0]["Pagado_por"], totales.iloc[0]["Monto_UYU"]
                usuario_2, total_2 = totales.iloc[1]["Pagado_por"], totales.iloc[1]["Monto_UYU"]
                
                col1, col2 = st.columns(2)
                col1.metric(f"Total {usuario_1}", f"${total_1:,.2f} UYU")
                col2.metric(f"Total {usuario_2}", f"${total_2:,.2f} UYU")
                
                diferencia = abs(total_1 - total_2)
                deuda = diferencia / 2
                
                st.subheader("💡 Estado de Cuentas (50/50):")
                if total_1 > total_2:
                    st.info(f"**{usuario_2}** debe transferir a **{usuario_1}**: **${deuda:,.2f} UYU**")
                elif total_2 > total_1:
                    st.info(f"**{usuario_1}** debe transferir a **{usuario_2}**: **${deuda:,.2f} UYU**")
                else:
                    st.success("¡Están al día perfectamente equilibrados!")
            else:
                st.write("Aportes totales por usuario:")
                st.dataframe(totales)
                st.warning("El cálculo automático 50/50 se mostrará cuando haya exactamente 2 usuarios con registros de gastos.")
        else:
            st.write("Aún no hay gastos registrados.")

    # --- MÓDULO 3: MONITOREO DE GASTOS ---
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
                st.subheader("Evolución del Gasto Acumulado")
                gastos_fecha = df_gastos.groupby("Fecha")["Monto_UYU"].sum().reset_index()
                gastos_fecha = gastos_fecha.sort_values("Fecha")
                gastos_fecha["Gasto_Acumulado"] = gastos_fecha["Monto_UYU"].cumsum()
                fig_line = px.line(gastos_fecha, x='Fecha', y='Gasto_Acumulado', markers=True, 
                                   labels={'Gasto_Acumulado': 'Monto Total (UYU)', 'Fecha': 'Fecha'})
                st.plotly_chart(fig_line, use_container_width=True)
                
            st.markdown("---")
            st.subheader("Desglose Detallado")
            st.dataframe(gastos_cat.style.format({"Monto_UYU": "${:,.2f}"}), use_container_width=True)
        else:
            st.info("Registra algunos gastos primero para poder ver los gráficos.")

    # --- MÓDULO 4: GESTIONAR USUARIOS ---
    elif menu == "Gestionar Usuarios":
        st.header("👥 Gestión de Usuarios")
        st.write("Usuarios actuales con acceso a la plataforma:")
        st.dataframe(usuarios_df[["Usuario"]])
        
        st.markdown("---")
        st.subheader("Agregar Nuevo Usuario")
        with st.form("nuevo_usuario"):
            nuevo_nombre = st.text_input("Nombre de Usuario")
            nueva_clave = st.text_input("Contraseña", type="password")
            
            if st.form_submit_button("Crear Usuario"):
                if nuevo_nombre in usuarios_df["Usuario"].values:
                    st.error("Ese usuario ya existe. Elige otro nombre.")
                elif nuevo_nombre and nueva_clave:
                    nuevo_usr = pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])
                    usuarios_df = pd.concat([usuarios_df, nuevo_usr], ignore_index=True)
                    save_data(usuarios_df, USERS_FILE)
                    st.success(f"Usuario '{nuevo_nombre}' creado con éxito.")
                    st.rerun()
                else:
                    st.error("Debes ingresar un nombre y una contraseña válidos.")
