import streamlit as st
import pandas as pd
import os

# --- SISTEMA DE LOGIN BÁSICO ---
# Aquí defines los usuarios y contraseñas para ti y tu hermano
USUARIOS = {"admin": "casa2024", "hermano": "serena2024"}

if "logueado" not in st.session_state:
    st.session_state.logueado = False

# Pantalla de Login
if not st.session_state.logueado:
    st.set_page_config(page_title="Login - Casa La Serena", page_icon="🔒")
    st.title("🔒 Acceso al Proyecto")
    st.write("Por favor, ingresa tus credenciales para ver la contabilidad.")
    
    usuario = st.text_input("Usuario")
    clave = st.text_input("Contraseña", type="password")
    
    if st.button("Entrar"):
        if usuario in USUARIOS and USUARIOS[usuario] == clave:
            st.session_state.logueado = True
            st.rerun() # Recarga la página para entrar a la app
        else:
            st.error("Usuario o contraseña incorrectos. Intenta de nuevo.")

# --- CÓDIGO DE LA APP (Solo se ve si el login es exitoso) ---
else:
    DATA_FILE = "contabilidad_casa.csv"

    def load_data():
        if os.path.exists(DATA_FILE):
            return pd.read_csv(DATA_FILE)
        else:
            return pd.DataFrame(columns=["Fecha", "Concepto", "Monto", "Pagado_por", "Categoria"])

    def save_data(df):
        df.to_csv(DATA_FILE, index=False)

    st.title("🏡 Proyecto Casa La Serena")
    
    # Botón para cerrar sesión
    st.sidebar.button("Cerrar Sesión", on_click=lambda: st.session_state.update(logueado=False))
    st.sidebar.markdown("---")
    
    menu = st.sidebar.selectbox("Navegación", ["Registrar Gasto", "Balance General"])

    df = load_data()

    if menu == "Registrar Gasto":
        st.header("📝 Nuevo Registro")
        with st.form("registro_form"):
            fecha = st.date_input("Fecha")
            concepto = st.text_input("Concepto")
            monto = st.number_input("Monto ($)", min_value=0)
            pagado_por = st.selectbox("¿Quién lo pagó?", ["Yo", "Mi Hermano"])
            categoria = st.selectbox("Categoría", ["Materiales", "Mano de Obra", "Trámites", "Otros"])
            
            if st.form_submit_button("Guardar Gasto"):
                nuevo_dato = pd.DataFrame([{"Fecha": fecha, "Concepto": concepto, "Monto": monto, "Pagado_por": pagado_por, "Categoria": categoria}])
                df = pd.concat([df, nuevo_dato], ignore_index=True)
                save_data(df)
                st.success("¡Gasto registrado con éxito!")

    elif menu == "Balance General":
        st.header("⚖️ Balance de Cuentas")
        if not df.empty:
            st.dataframe(df, use_container_width=True)
            total_yo = df[df["Pagado_por"] == "Yo"]["Monto"].sum()
            total_hermano = df[df["Pagado_por"] == "Mi Hermano"]["Monto"].sum()
            
            st.markdown("---")
            col1, col2 = st.columns(2)
            col1.metric("Total tuyo", f"${total_yo:,.0f}")
            col2.metric("Total tu hermano", f"${total_hermano:,.0f}")
            
            diferencia = abs(total_yo - total_hermano)
            deuda = diferencia / 2
            
            st.subheader("💡 Estado:")
            if total_yo > total_hermano:
                st.info(f"Tu hermano te debe: **${deuda:,.0f}**")
            elif total_hermano > total_yo:
                st.info(f"Tú le debes a tu hermano: **${deuda:,.0f}**")
            else:
                st.success("¡Están al día!")
        else:
            st.write("Aún no hay gastos.")
