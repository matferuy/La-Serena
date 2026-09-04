"""
La Serena · Copropiedad
Gestión de la copropiedad del inmueble entre hermanos:
  - Gastos fijos / de mantenimiento (compartidos por participación) y gastos de uso (atribuidos a quien usó)
  - Calendario de uso de la casa (con sincronización opcional a Google Calendar)
  - Ingresos por alquileres u otros
  - Cuentas bancarias compartidas y sus movimientos
  - Balance por moneda entre hermanos
"""
import streamlit as st
import pandas as pd
import datetime
import calendar
import uuid
import io
import plotly.express as px
import streamlit.components.v1 as components
from common import (
    inject_css, USE_GSHEETS, has_secret, get_secret,
    load_table, save_table, parse_adjuntos, subir_comprobantes, links_adjuntos_md,
    obtener_tasa_usd_uyu, a_usd, load_users, save_users, socios as _socios,
    init_session, render_login, render_header, restaurar_tab, kpi, fmt_monto, hoy,
    get_calendar_service,
)

# =========================================================
# CONFIGURACIÓN
# =========================================================
st.set_page_config(page_title="La Serena · Copropiedad", page_icon="🏠", layout="wide", initial_sidebar_state="collapsed")
inject_css("copro")

SH_GASTOS, CSV_GASTOS     = "Copro_Gastos",         "copro_gastos.csv"
SH_INGRESOS, CSV_INGRESOS = "Copro_Ingresos",       "copro_ingresos.csv"
SH_USOS, CSV_USOS         = "Copro_Usos",           "copro_usos.csv"
SH_CUENTAS, CSV_CUENTAS   = "Copro_Cuentas",        "copro_cuentas.csv"
SH_MOVS, CSV_MOVS         = "Copro_Movimientos",    "copro_movimientos.csv"
SH_TRANSF, CSV_TRANSF     = "Copro_Transferencias", "copro_transferencias.csv"
SH_CONFIG, CSV_CONFIG     = "Copro_Config",         "copro_config.csv"

GASTOS_COLS   = ["ID", "Fecha", "Concepto", "Tipo", "Categoria", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Pagado_por", "Atribuido_a", "Uso_ID", "Archivo_Adjunto", "Notas", "Registrado_por"]
INGRESOS_COLS = ["ID", "Fecha", "Concepto", "Tipo", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Cobrado_por", "Uso_ID", "Archivo_Adjunto", "Notas", "Registrado_por"]
USOS_COLS     = ["ID", "Fecha_Inicio", "Fecha_Fin", "Tipo", "Usuario", "Titulo", "Personas", "Notas", "GCal_Event_ID", "Registrado_por"]
CUENTAS_COLS  = ["ID", "Nombre", "Banco", "Moneda", "Saldo_Inicial", "Fecha_Apertura", "Notas", "Activa"]
MOVS_COLS     = ["ID", "Fecha", "Cuenta_ID", "Tipo", "Socio", "Moneda", "Monto", "Concepto", "Archivo_Adjunto", "Registrado_por"]
TRANSF_COLS   = ["ID", "Fecha", "Origen", "Destino", "Moneda", "Monto_Original", "Tasa_Cambio", "Monto_UYU", "Archivo_Adjunto", "Notas"]
CONFIG_COLS   = ["Clave", "Valor"]

TIPO_FIJO, TIPO_USO = "Fijo / Mantenimiento", "Uso"
CATS_FIJO = ["Contribución Inmobiliaria", "Impuesto Primaria", "UTE (cargo fijo)", "OSE (cargo fijo)", "Internet / TV",
             "Seguro", "Mantenimiento", "Jardín / Piscina", "Mejoras", "Alarma / Seguridad", "Otros fijos"]
CATS_USO  = ["UTE (consumo)", "OSE (consumo)", "Gas / Leña", "Limpieza", "Consumibles", "Reparación por uso",
             "Comisión alquiler", "Otros de uso"]
TIPOS_USO_CASA = ["Uso propio", "Alquiler", "Mantenimiento", "Bloqueo"]
TIPOS_INGRESO  = ["Alquiler", "Otro"]
TIPOS_MOV      = ["Aporte", "Retiro", "Ajuste"]
ATRIB_AMBOS, ATRIB_ALQ = "Ambos", "Alquiler"
COLORES_SOCIO = ["#0D9488", "#0EA5E9", "#8B5CF6"]
PALETA_CATS = ["#0D9488", "#0EA5E9", "#F59E0B", "#EF4444", "#8B5CF6", "#EC4899", "#84CC16", "#F97316", "#14B8A6", "#6366F1", "#A16207"]

# =========================================================
# CARGA / GUARDADO
# =========================================================
NUM_COLS = ["Monto_Original", "Tasa_Cambio", "Monto_UYU", "Monto", "Saldo_Inicial"]

def load_copro(sheet, csv, cols):
    df = load_table(sheet, csv, cols)
    for c in NUM_COLS:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    if "ID" in df.columns:
        df["ID"] = df["ID"].astype(str)
    return df

def load_config():
    df = load_table(SH_CONFIG, CSV_CONFIG, CONFIG_COLS)
    return {str(r["Clave"]): str(r["Valor"]) for _, r in df.iterrows() if str(r.get("Clave", "")).strip()}

def save_config(cfg):
    df = pd.DataFrame([{"Clave": k, "Valor": v} for k, v in cfg.items()], columns=CONFIG_COLS)
    save_table(df, SH_CONFIG, CSV_CONFIG)

def fecha_col(df, col):
    """Convierte una columna a datetime (NaT si inválido)."""
    if col in df.columns:
        df[col] = pd.to_datetime(df[col], errors="coerce")
    return df

def nuevo_id():
    return uuid.uuid4().hex

# =========================================================
# HELPERS DE NEGOCIO
# =========================================================
def participacion(cfg, lista_socios):
    """Dict {socio: fracción}. Por defecto partes iguales."""
    if not lista_socios:
        return {}
    base = 100.0 / len(lista_socios)
    shares = {}
    for s in lista_socios:
        try: shares[s] = float(cfg.get(f"share_{s}", base))
        except ValueError: shares[s] = base
    total = sum(shares.values()) or 100.0
    return {s: v / total for s, v in shares.items()}

def es_cuenta(val):
    return str(val).startswith("cta:")

def id_cuenta(val):
    return str(val)[4:] if es_cuenta(val) else ""

def nombre_pagador(val, df_cuentas):
    if es_cuenta(val):
        cid = id_cuenta(val)
        fila = df_cuentas[df_cuentas["ID"] == cid]
        return f"🏦 {fila.iloc[0]['Nombre']}" if not fila.empty else "🏦 Cuenta"
    return str(val)

def opciones_pagador(lista_socios, df_cuentas, moneda=None):
    """(labels, values) para 'Pagado por' / 'Cobrado por': socios + cuentas compartidas activas."""
    labels, values = list(lista_socios), list(lista_socios)
    if not df_cuentas.empty:
        activas = df_cuentas[df_cuentas["Activa"].astype(str).str.lower().isin(["true", "1", "si", "sí", ""])]
        if moneda:
            activas = activas[activas["Moneda"].astype(str).str.upper() == str(moneda).upper()]
        for _, c in activas.iterrows():
            labels.append(f"🏦 {c['Nombre']} ({c['Moneda']})")
            values.append(f"cta:{c['ID']}")
    return labels, values

def saldo_cuenta(cid, df_cuentas, df_movs, df_gastos, df_ingresos):
    """Saldo actual de una cuenta compartida (en su moneda)."""
    fila = df_cuentas[df_cuentas["ID"] == cid]
    if fila.empty: return 0.0
    saldo = float(fila.iloc[0]["Saldo_Inicial"] or 0)
    m = df_movs[df_movs["Cuenta_ID"].astype(str) == cid] if not df_movs.empty else pd.DataFrame()
    if not m.empty:
        saldo += m[m["Tipo"] == "Aporte"]["Monto"].sum()
        saldo -= m[m["Tipo"] == "Retiro"]["Monto"].sum()
        saldo += m[m["Tipo"] == "Ajuste"]["Monto"].sum()
    if not df_ingresos.empty:
        saldo += df_ingresos[df_ingresos["Cobrado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum()
    if not df_gastos.empty:
        saldo -= df_gastos[df_gastos["Pagado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum()
    return saldo

def calc_balance(moneda, lista_socios, shares, df_gastos, df_ingresos, df_movs, df_transf, df_cuentas):
    """
    Balance entre socios para una moneda. Devuelve dict {socio: {...componentes, 'saldo': x}}.
    saldo > 0 → el socio aportó de más (le deben); saldo < 0 → debe.
    """
    M = str(moneda).upper()
    g = df_gastos[df_gastos["Moneda"].astype(str).str.upper() == M] if not df_gastos.empty else pd.DataFrame(columns=GASTOS_COLS)
    ing = df_ingresos[df_ingresos["Moneda"].astype(str).str.upper() == M] if not df_ingresos.empty else pd.DataFrame(columns=INGRESOS_COLS)
    mv = df_movs[df_movs["Moneda"].astype(str).str.upper() == M] if not df_movs.empty else pd.DataFrame(columns=MOVS_COLS)
    tr = df_transf[df_transf["Moneda"].astype(str).str.upper() == M] if not df_transf.empty else pd.DataFrame(columns=TRANSF_COLS)

    gastos_compartidos = g[g["Atribuido_a"].isin([ATRIB_AMBOS, ATRIB_ALQ, "", "nan"])]["Monto_Original"].sum()
    ingresos_total = ing["Monto_Original"].sum()
    # Pool compartido: lo que entró/salió de las cuentas por aportes, retiros, ingresos y gastos
    pool = 0.0
    if not df_cuentas.empty:
        for _, c in df_cuentas[df_cuentas["Moneda"].astype(str).str.upper() == M].iterrows():
            cid = str(c["ID"])
            mc = mv[mv["Cuenta_ID"].astype(str) == cid]
            pool += mc[mc["Tipo"] == "Aporte"]["Monto"].sum() - mc[mc["Tipo"] == "Retiro"]["Monto"].sum()
            pool += ing[ing["Cobrado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum()
            pool -= g[g["Pagado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum()

    res = {}
    for s in lista_socios:
        sh = shares.get(s, 0)
        pagado_fijo = g[(g["Pagado_por"] == s) & (g["Tipo"] == TIPO_FIJO)]["Monto_Original"].sum()
        pagado_uso  = g[(g["Pagado_por"] == s) & (g["Tipo"] != TIPO_FIJO)]["Monto_Original"].sum()
        aportes = mv[(mv["Tipo"] == "Aporte") & (mv["Socio"] == s)]["Monto"].sum()
        retiros = mv[(mv["Tipo"] == "Retiro") & (mv["Socio"] == s)]["Monto"].sum()
        cobrado = ing[ing["Cobrado_por"] == s]["Monto_Original"].sum()
        env = tr[tr["Origen"] == s]["Monto_Original"].sum()
        rec = tr[tr["Destino"] == s]["Monto_Original"].sum()
        aporte_neto = pagado_fijo + pagado_uso + aportes - retiros - cobrado + env - rec
        uso_propio = g[g["Atribuido_a"] == s]["Monto_Original"].sum()
        corresponde = sh * gastos_compartidos + uso_propio - sh * ingresos_total
        saldo = aporte_neto - corresponde - sh * pool
        res[s] = dict(pagado_fijo=pagado_fijo, pagado_uso=pagado_uso, aportes=aportes, retiros=retiros,
                      cobrado=cobrado, env=env, rec=rec, aporte_neto=aporte_neto, uso_propio=uso_propio,
                      corresponde=corresponde, pool_share=sh * pool, saldo=saldo, share=sh)
    return res

def noches(ini, fin):
    try: return max((fin - ini).days, 0) + 1
    except Exception: return 0

def color_uso(u, lista_socios):
    t = str(u.get("Tipo", ""))
    if t == "Alquiler": return "#D97706"
    if t == "Mantenimiento": return "#475569"
    if t == "Bloqueo": return "#E11D48"
    usr = str(u.get("Usuario", ""))
    return COLORES_SOCIO[lista_socios.index(usr) % len(COLORES_SOCIO)] if usr in lista_socios else "#64748B"

def etiqueta_uso(u):
    t = str(u.get("Tipo", ""))
    if t == "Uso propio": return str(u.get("Usuario", ""))
    tit = str(u.get("Titulo", "")).strip()
    return f"{t}" + (f": {tit}" if tit and t == "Alquiler" else "")

def render_mes(year, month, df_usos, lista_socios):
    cal = calendar.Calendar(firstweekday=0)
    weeks = cal.monthdatescalendar(year, month)
    html = '<div class="cal-grid">' + "".join(f'<div class="cal-head">{d}</div>' for d in ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"])
    usos = []
    if not df_usos.empty:
        for _, u in df_usos.iterrows():
            if pd.isna(u["Fecha_Inicio"]) or pd.isna(u["Fecha_Fin"]): continue
            usos.append((u["Fecha_Inicio"].date(), u["Fecha_Fin"].date(), color_uso(u, lista_socios), etiqueta_uso(u)))
    for week in weeks:
        for d in week:
            if d.month != month:
                html += '<div class="cal-day empty"></div>'
                continue
            tags = "".join(f'<span class="cal-tag" style="background:{c}">{lab}</span>' for ini, fin, c, lab in usos if ini <= d <= fin)
            cls = "cal-day today" if d == hoy() else "cal-day"
            html += f'<div class="{cls}"><span class="cal-num">{d.day}</span>{tags}</div>'
    html += "</div>"
    st.markdown(html, unsafe_allow_html=True)

def solapamientos(df_usos, ini, fin, excluir_id=None):
    """Usos (propio/alquiler) que se superponen con [ini, fin]."""
    if df_usos.empty: return pd.DataFrame(columns=USOS_COLS)
    d = df_usos[df_usos["Tipo"].isin(["Uso propio", "Alquiler"])].copy()
    if excluir_id: d = d[d["ID"] != excluir_id]
    d = d.dropna(subset=["Fecha_Inicio", "Fecha_Fin"])
    return d[(d["Fecha_Inicio"].dt.date <= fin) & (d["Fecha_Fin"].dt.date >= ini)]

# --- Google Calendar ---
def calendar_id(cfg):
    if has_secret("google_calendar_id"): return str(get_secret("google_calendar_id")).strip()
    return str(cfg.get("google_calendar_id", "")).strip()

def gcal_disponible(cfg):
    return bool(calendar_id(cfg)) and has_secret("google_oauth_refresh_token")

def gcal_crear_evento(cal_id, titulo, ini, fin, descripcion=""):
    svc = get_calendar_service()
    body = {"summary": titulo, "description": descripcion,
            "start": {"date": ini.isoformat()}, "end": {"date": (fin + datetime.timedelta(days=1)).isoformat()}}
    return svc.events().insert(calendarId=cal_id, body=body).execute()["id"]

def gcal_actualizar_evento(cal_id, event_id, titulo, ini, fin, descripcion=""):
    svc = get_calendar_service()
    body = {"summary": titulo, "description": descripcion,
            "start": {"date": ini.isoformat()}, "end": {"date": (fin + datetime.timedelta(days=1)).isoformat()}}
    svc.events().patch(calendarId=cal_id, eventId=event_id, body=body).execute()

def gcal_borrar_evento(cal_id, event_id):
    svc = get_calendar_service()
    svc.events().delete(calendarId=cal_id, eventId=event_id).execute()

def titulo_evento(tipo, usuario, titulo):
    if tipo == "Uso propio": return f"🏠 {usuario} en La Serena"
    if tipo == "Alquiler": return f"🔑 Alquiler" + (f" · {titulo}" if titulo else "")
    if tipo == "Mantenimiento": return f"🔧 Mantenimiento" + (f" · {titulo}" if titulo else "")
    return f"⛔ Bloqueo" + (f" · {titulo}" if titulo else "")

def generar_respaldo(tablas):
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nombre = f"respaldo_copropiedad_{timestamp}.xlsx"
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        for hoja, df in tablas.items():
            df.to_excel(writer, sheet_name=hoja[:31], index=False)
    return nombre, buffer.getvalue()

def selector_categoria(tipo, existentes, key, actual=None):
    base = CATS_FIJO if tipo == TIPO_FIJO else CATS_USO
    extra = sorted(set(existentes) - set(base) - {""})
    opciones = base + extra
    nueva = st.checkbox("Crear nueva categoría", key=f"{key}_chk")
    if nueva:
        return st.text_input("Nombre de la nueva categoría", key=f"{key}_txt")
    idx = opciones.index(actual) if actual in opciones else 0
    return st.selectbox("Categoría", opciones, index=idx, key=f"{key}_sel")

def campos_monto(key, moneda_actual="UYU", monto_actual=None, tasa_actual=None):
    c1, c2 = st.columns(2)
    moneda = c1.selectbox("Moneda", ["UYU", "USD"], index=["UYU", "USD"].index(moneda_actual) if moneda_actual in ["UYU", "USD"] else 0, key=f"{key}_mon")
    monto = c2.number_input("Monto", min_value=0.0, value=monto_actual, format="%.2f", key=f"{key}_monto")
    tasa = 1.0
    if moneda == "USD":
        tasa = st.number_input("Tasa de cambio (UYU por USD)", min_value=1.0,
                               value=float(tasa_actual) if tasa_actual and tasa_actual > 1 else float(obtener_tasa_usd_uyu()),
                               format="%.2f", key=f"{key}_tasa")
    return moneda, monto, tasa

def anio_selector(df, col, key):
    anios = sorted({int(y) for y in pd.to_datetime(df[col], errors="coerce").dt.year.dropna().unique()} | {hoy().year}, reverse=True) if not df.empty else [hoy().year]
    opciones = ["Todos"] + [str(a) for a in anios]
    sel = st.selectbox("Año", opciones, index=1 if len(opciones) > 1 else 0, key=key)
    return None if sel == "Todos" else int(sel)

# =========================================================
# SESIÓN Y LOGIN
# =========================================================
init_session({"copro_modo": None, "copro_edit_id": None, "cal_year": hoy().year, "cal_month": hoy().month})
usuarios_df = load_users()

if not st.session_state.logueado:
    render_login(usuarios_df, "🏠", "La Serena", "Copropiedad · Hermanos",
                 "Gastos, uso de la casa, alquileres y cuentas compartidas", paleta="copro")
    st.stop()

# =========================================================
# DATOS
# =========================================================
df_gastos   = fecha_col(load_copro(SH_GASTOS, CSV_GASTOS, GASTOS_COLS), "Fecha")
df_ingresos = fecha_col(load_copro(SH_INGRESOS, CSV_INGRESOS, INGRESOS_COLS), "Fecha")
df_usos     = fecha_col(fecha_col(load_copro(SH_USOS, CSV_USOS, USOS_COLS), "Fecha_Inicio"), "Fecha_Fin")
df_cuentas  = load_copro(SH_CUENTAS, CSV_CUENTAS, CUENTAS_COLS)
df_movs     = fecha_col(load_copro(SH_MOVS, CSV_MOVS, MOVS_COLS), "Fecha")
df_transf   = fecha_col(load_copro(SH_TRANSF, CSV_TRANSF, TRANSF_COLS), "Fecha")
cfg         = load_config()
lista_socios = _socios(usuarios_df)
shares = participacion(cfg, lista_socios)
usuario = st.session_state.usuario_actual
es_admin = usuario.lower() == "admin"
tasa_actual = obtener_tasa_usd_uyu()

def guardar_gastos(df):   save_table(df[GASTOS_COLS].copy().assign(Fecha=lambda d: d["Fecha"].dt.strftime("%Y-%m-%d")), SH_GASTOS, CSV_GASTOS)
def guardar_ingresos(df): save_table(df[INGRESOS_COLS].copy().assign(Fecha=lambda d: d["Fecha"].dt.strftime("%Y-%m-%d")), SH_INGRESOS, CSV_INGRESOS)
def guardar_usos(df):
    d = df[USOS_COLS].copy()
    d["Fecha_Inicio"] = pd.to_datetime(d["Fecha_Inicio"]).dt.strftime("%Y-%m-%d")
    d["Fecha_Fin"] = pd.to_datetime(d["Fecha_Fin"]).dt.strftime("%Y-%m-%d")
    save_table(d, SH_USOS, CSV_USOS)
def guardar_cuentas(df):  save_table(df[CUENTAS_COLS], SH_CUENTAS, CSV_CUENTAS)
def guardar_movs(df):     save_table(df[MOVS_COLS].copy().assign(Fecha=lambda d: pd.to_datetime(d["Fecha"]).dt.strftime("%Y-%m-%d")), SH_MOVS, CSV_MOVS)
def guardar_transf(df):   save_table(df[TRANSF_COLS].copy().assign(Fecha=lambda d: pd.to_datetime(d["Fecha"]).dt.strftime("%Y-%m-%d")), SH_TRANSF, CSV_TRANSF)

def agregar_fila(df, fila):
    return pd.concat([df, pd.DataFrame([fila])], ignore_index=True)

def cerrar_form():
    st.session_state.copro_modo = None
    st.session_state.copro_edit_id = None
    st.rerun()

def abrir_form(modo, edit_id=None, tab=0):
    st.session_state.copro_modo = modo
    st.session_state.copro_edit_id = edit_id
    st.session_state.tab_activa = tab
    st.rerun()

# =========================================================
# CABECERA
# =========================================================
def _logout():
    st.session_state.copro_modo = None
    st.session_state.copro_edit_id = None
_link_obra = ("🏗️ Obra", get_secret("url_app_obra")) if has_secret("url_app_obra") else None
render_header("🏠", "La Serena · Copropiedad", f"TC U$S {tasa_actual:,.2f}", paleta="copro", link_otro=_link_obra, on_logout=_logout)

if len(lista_socios) < 2:
    st.info("Se necesitan al menos 2 socios (usuarios no admin) para gestionar la copropiedad. Agregalos en ⚙️ Config.")

modo = st.session_state.copro_modo
edit_id = st.session_state.copro_edit_id

# =========================================================
# FORMULARIOS (OVERLAY)
# =========================================================
if modo == "gasto":
    editando = edit_id is not None and not df_gastos[df_gastos["ID"] == edit_id].empty
    fila = df_gastos[df_gastos["ID"] == edit_id].iloc[0] if editando else None
    st.markdown(f'<div class="section-title">{"Editar gasto" if editando else "Nuevo gasto de la casa"}</div>', unsafe_allow_html=True)
    with st.container():
        fecha = st.date_input("Fecha", fila["Fecha"].date() if editando and not pd.isna(fila["Fecha"]) else hoy())
        concepto = st.text_input("Concepto", fila["Concepto"] if editando else "", placeholder="Ej: Contribución inmobiliaria 2026 · Limpieza fin de semana")
        tipo = st.radio("Tipo de gasto", [TIPO_FIJO, TIPO_USO], horizontal=True,
                        index=[TIPO_FIJO, TIPO_USO].index(fila["Tipo"]) if editando and fila["Tipo"] in [TIPO_FIJO, TIPO_USO] else 0,
                        help="Fijo / Mantenimiento se reparte según participación. Uso se atribuye a quien usó la casa.")
        categoria = selector_categoria(tipo, df_gastos["Categoria"].astype(str).tolist(), "g_cat", fila["Categoria"] if editando else None)
        moneda, monto, tasa = campos_monto("g", fila["Moneda"] if editando else "UYU",
                                           float(fila["Monto_Original"]) if editando else None,
                                           float(fila["Tasa_Cambio"]) if editando else None)
        labels_p, values_p = opciones_pagador(lista_socios, df_cuentas, moneda)
        actual_p = fila["Pagado_por"] if editando else (usuario if usuario in values_p else (values_p[0] if values_p else ""))
        pagado_por = st.selectbox("¿Quién pagó?", labels_p, index=values_p.index(actual_p) if actual_p in values_p else 0) if labels_p else ""
        pagado_por = values_p[labels_p.index(pagado_por)] if labels_p else ""
        if tipo == TIPO_USO:
            opc_atr = lista_socios + [ATRIB_AMBOS, ATRIB_ALQ]
            help_atr = "A quién se le atribuye el gasto: al hermano que usó la casa, a ambos, o al alquiler (compartido)."
            default_atr = fila["Atribuido_a"] if editando and fila["Atribuido_a"] in opc_atr else (usuario if usuario in opc_atr else ATRIB_AMBOS)
        else:
            opc_atr = [ATRIB_AMBOS] + lista_socios
            help_atr = "Los gastos fijos normalmente son de ambos (según participación)."
            default_atr = fila["Atribuido_a"] if editando and fila["Atribuido_a"] in opc_atr else ATRIB_AMBOS
        atribuido = st.selectbox("Atribuido a", opc_atr, index=opc_atr.index(default_atr), help=help_atr)
        uso_id = ""
        if tipo == TIPO_USO and not df_usos.empty:
            recientes = df_usos.dropna(subset=["Fecha_Inicio"]).sort_values("Fecha_Inicio", ascending=False).head(30)
            lab_u = ["(Sin vincular)"] + [f"{r['Fecha_Inicio'].strftime('%d/%m/%y')} · {etiqueta_uso(r)}" for _, r in recientes.iterrows()]
            val_u = [""] + recientes["ID"].tolist()
            cur_u = fila["Uso_ID"] if editando and fila["Uso_ID"] in val_u else ""
            sel_u = st.selectbox("Vincular a una estadía (opcional)", lab_u, index=val_u.index(cur_u))
            uso_id = val_u[lab_u.index(sel_u)]
        notas = st.text_input("Notas (opcional)", fila["Notas"] if editando else "")
        if editando and parse_adjuntos(fila["Archivo_Adjunto"]):
            st.markdown("📎 Comprobantes actuales: " + links_adjuntos_md(fila["Archivo_Adjunto"], "ver"))
        archivos = st.file_uploader("Adjuntar comprobantes", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, key="g_files")

        st.markdown("<br>", unsafe_allow_html=True)
        c_save, c_del, c_cancel = st.columns(3)
        if c_save.button("Guardar", type="primary", use_container_width=True):
            if not monto or not concepto or not str(categoria).strip():
                st.error("Falta monto, concepto o categoría.")
            else:
                adj_actual = parse_adjuntos(fila["Archivo_Adjunto"]) if editando else []
                if archivos:
                    urls, errs = subir_comprobantes(archivos, "COPRO_GASTO", str(fecha))
                    for e in errs: st.warning(f"No se pudo subir un comprobante: {e}")
                    adj_actual += parse_adjuntos(urls)
                registro = {"ID": fila["ID"] if editando else nuevo_id(), "Fecha": pd.Timestamp(fecha), "Concepto": concepto, "Tipo": tipo,
                            "Categoria": str(categoria).strip(), "Moneda": moneda, "Monto_Original": monto, "Tasa_Cambio": tasa,
                            "Monto_UYU": monto * tasa, "Pagado_por": pagado_por, "Atribuido_a": atribuido, "Uso_ID": uso_id,
                            "Archivo_Adjunto": " ||| ".join(adj_actual) if adj_actual else "Sin adjunto", "Notas": notas,
                            "Registrado_por": fila["Registrado_por"] if editando else usuario}
                if editando:
                    df_gastos = df_gastos[df_gastos["ID"] != edit_id]
                guardar_gastos(agregar_fila(df_gastos, registro))
                cerrar_form()
        if editando and c_del.button("🗑️ Eliminar", use_container_width=True):
            guardar_gastos(df_gastos[df_gastos["ID"] != edit_id])
            cerrar_form()
        if c_cancel.button("Cancelar", use_container_width=True):
            cerrar_form()

elif modo == "ingreso":
    editando = edit_id is not None and not df_ingresos[df_ingresos["ID"] == edit_id].empty
    fila = df_ingresos[df_ingresos["ID"] == edit_id].iloc[0] if editando else None
    st.markdown(f'<div class="section-title">{"Editar ingreso" if editando else "Nuevo ingreso"}</div>', unsafe_allow_html=True)
    with st.container():
        fecha = st.date_input("Fecha", fila["Fecha"].date() if editando and not pd.isna(fila["Fecha"]) else hoy())
        tipo_i = st.radio("Tipo", TIPOS_INGRESO, horizontal=True, index=TIPOS_INGRESO.index(fila["Tipo"]) if editando and fila["Tipo"] in TIPOS_INGRESO else 0)
        concepto = st.text_input("Concepto", fila["Concepto"] if editando else "", placeholder="Ej: Alquiler semana de Carnaval")
        moneda, monto, tasa = campos_monto("i", fila["Moneda"] if editando else "USD",
                                           float(fila["Monto_Original"]) if editando else None,
                                           float(fila["Tasa_Cambio"]) if editando else None)
        labels_p, values_p = opciones_pagador(lista_socios, df_cuentas, moneda)
        actual_p = fila["Cobrado_por"] if editando else (usuario if usuario in values_p else (values_p[0] if values_p else ""))
        cobrado_por = st.selectbox("¿Quién lo cobró / dónde entró?", labels_p, index=values_p.index(actual_p) if actual_p in values_p else 0) if labels_p else ""
        cobrado_por = values_p[labels_p.index(cobrado_por)] if labels_p else ""
        uso_id = ""
        alqs = df_usos[df_usos["Tipo"] == "Alquiler"].dropna(subset=["Fecha_Inicio"]).sort_values("Fecha_Inicio", ascending=False) if not df_usos.empty else pd.DataFrame()
        if tipo_i == "Alquiler" and not alqs.empty:
            lab_u = ["(Sin vincular)"] + [f"{r['Fecha_Inicio'].strftime('%d/%m/%y')} → {r['Fecha_Fin'].strftime('%d/%m/%y')} · {r['Titulo']}" for _, r in alqs.iterrows()]
            val_u = [""] + alqs["ID"].tolist()
            cur_u = fila["Uso_ID"] if editando and fila["Uso_ID"] in val_u else ""
            sel_u = st.selectbox("Vincular al alquiler", lab_u, index=val_u.index(cur_u))
            uso_id = val_u[lab_u.index(sel_u)]
        notas = st.text_input("Notas (opcional)", fila["Notas"] if editando else "")
        if editando and parse_adjuntos(fila["Archivo_Adjunto"]):
            st.markdown("📎 Comprobantes actuales: " + links_adjuntos_md(fila["Archivo_Adjunto"], "ver"))
        archivos = st.file_uploader("Adjuntar comprobantes", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, key="i_files")

        st.markdown("<br>", unsafe_allow_html=True)
        c_save, c_del, c_cancel = st.columns(3)
        if c_save.button("Guardar", type="primary", use_container_width=True):
            if not monto or not concepto:
                st.error("Falta monto o concepto.")
            else:
                adj_actual = parse_adjuntos(fila["Archivo_Adjunto"]) if editando else []
                if archivos:
                    urls, errs = subir_comprobantes(archivos, "COPRO_INGRESO", str(fecha))
                    for e in errs: st.warning(f"No se pudo subir un comprobante: {e}")
                    adj_actual += parse_adjuntos(urls)
                registro = {"ID": fila["ID"] if editando else nuevo_id(), "Fecha": pd.Timestamp(fecha), "Concepto": concepto, "Tipo": tipo_i,
                            "Moneda": moneda, "Monto_Original": monto, "Tasa_Cambio": tasa, "Monto_UYU": monto * tasa,
                            "Cobrado_por": cobrado_por, "Uso_ID": uso_id,
                            "Archivo_Adjunto": " ||| ".join(adj_actual) if adj_actual else "Sin adjunto", "Notas": notas,
                            "Registrado_por": fila["Registrado_por"] if editando else usuario}
                if editando:
                    df_ingresos = df_ingresos[df_ingresos["ID"] != edit_id]
                guardar_ingresos(agregar_fila(df_ingresos, registro))
                cerrar_form()
        if editando and c_del.button("🗑️ Eliminar", use_container_width=True):
            guardar_ingresos(df_ingresos[df_ingresos["ID"] != edit_id])
            cerrar_form()
        if c_cancel.button("Cancelar", use_container_width=True):
            cerrar_form()

elif modo == "uso":
    editando = edit_id is not None and not df_usos[df_usos["ID"] == edit_id].empty
    fila = df_usos[df_usos["ID"] == edit_id].iloc[0] if editando else None
    st.markdown(f'<div class="section-title">{"Editar estadía" if editando else "Reservar la casa"}</div>', unsafe_allow_html=True)
    with st.container():
        tipo_u = st.radio("Tipo", TIPOS_USO_CASA, horizontal=True, index=TIPOS_USO_CASA.index(fila["Tipo"]) if editando and fila["Tipo"] in TIPOS_USO_CASA else 0)
        usuario_u = ATRIB_AMBOS
        if tipo_u == "Uso propio":
            usuario_u = st.selectbox("¿Quién la usa?", lista_socios, index=lista_socios.index(fila["Usuario"]) if editando and fila["Usuario"] in lista_socios else (lista_socios.index(usuario) if usuario in lista_socios else 0)) if lista_socios else ""
        elif tipo_u == "Alquiler":
            usuario_u = ATRIB_ALQ
        c1, c2 = st.columns(2)
        f_ini = c1.date_input("Desde", fila["Fecha_Inicio"].date() if editando and not pd.isna(fila["Fecha_Inicio"]) else hoy())
        f_fin = c2.date_input("Hasta (inclusive)", fila["Fecha_Fin"].date() if editando and not pd.isna(fila["Fecha_Fin"]) else hoy() + datetime.timedelta(days=2))
        titulo = st.text_input("Título / inquilino" if tipo_u == "Alquiler" else "Título (opcional)", fila["Titulo"] if editando else "")
        personas = st.number_input("Cantidad de personas", min_value=0, value=int(float(fila["Personas"] or 0)) if editando and str(fila["Personas"]).strip() not in ("", "nan") else 2, step=1)
        notas = st.text_input("Notas (opcional)", fila["Notas"] if editando else "")
        sync_gcal = False
        if gcal_disponible(cfg):
            sync_gcal = st.checkbox("Sincronizar con Google Calendar", value=True)
        else:
            st.caption("Google Calendar no configurado (ver ⚙️ Config).")

        if f_fin < f_ini:
            st.error("La fecha de fin debe ser posterior o igual a la de inicio.")
        conflictos = solapamientos(df_usos, f_ini, f_fin, excluir_id=edit_id if editando else None) if tipo_u in ["Uso propio", "Alquiler"] else pd.DataFrame()
        confirmar = True
        if not conflictos.empty:
            st.warning("⚠️ Se superpone con: " + " · ".join(f"{etiqueta_uso(r)} ({r['Fecha_Inicio'].strftime('%d/%m')}→{r['Fecha_Fin'].strftime('%d/%m')})" for _, r in conflictos.iterrows()))
            confirmar = st.checkbox("Confirmar de todos modos")

        st.markdown("<br>", unsafe_allow_html=True)
        c_save, c_del, c_cancel = st.columns(3)
        if c_save.button("Guardar", type="primary", use_container_width=True, disabled=(f_fin < f_ini or not confirmar)):
            ev_id = str(fila["GCal_Event_ID"]) if editando and str(fila["GCal_Event_ID"]).strip() not in ("", "nan") else ""
            tit_ev = titulo_evento(tipo_u, usuario_u, titulo)
            desc_ev = f"{notas}\nPersonas: {personas}\nRegistrado por {usuario} en La Serena · Copropiedad"
            if sync_gcal:
                try:
                    if ev_id: gcal_actualizar_evento(calendar_id(cfg), ev_id, tit_ev, f_ini, f_fin, desc_ev)
                    else: ev_id = gcal_crear_evento(calendar_id(cfg), tit_ev, f_ini, f_fin, desc_ev)
                except Exception as e:
                    st.warning(f"No se pudo sincronizar con Google Calendar: {e}")
            registro = {"ID": fila["ID"] if editando else nuevo_id(), "Fecha_Inicio": pd.Timestamp(f_ini), "Fecha_Fin": pd.Timestamp(f_fin),
                        "Tipo": tipo_u, "Usuario": usuario_u, "Titulo": titulo, "Personas": int(personas), "Notas": notas,
                        "GCal_Event_ID": ev_id, "Registrado_por": fila["Registrado_por"] if editando else usuario}
            if editando:
                df_usos = df_usos[df_usos["ID"] != edit_id]
            guardar_usos(agregar_fila(df_usos, registro))
            cerrar_form()
        if editando and c_del.button("🗑️ Eliminar", use_container_width=True):
            ev_id = str(fila["GCal_Event_ID"])
            if ev_id.strip() not in ("", "nan") and gcal_disponible(cfg):
                try: gcal_borrar_evento(calendar_id(cfg), ev_id)
                except Exception as e: st.warning(f"No se pudo borrar el evento de Google Calendar: {e}")
            guardar_usos(df_usos[df_usos["ID"] != edit_id])
            cerrar_form()
        if c_cancel.button("Cancelar", use_container_width=True):
            cerrar_form()

elif modo == "cuenta":
    editando = edit_id is not None and not df_cuentas[df_cuentas["ID"] == edit_id].empty
    fila = df_cuentas[df_cuentas["ID"] == edit_id].iloc[0] if editando else None
    st.markdown(f'<div class="section-title">{"Editar cuenta" if editando else "Nueva cuenta compartida"}</div>', unsafe_allow_html=True)
    with st.container():
        nombre = st.text_input("Nombre", fila["Nombre"] if editando else "", placeholder="Ej: Caja de ahorro Itaú USD")
        c1, c2 = st.columns(2)
        banco = c1.text_input("Banco / entidad", fila["Banco"] if editando else "")
        moneda_c = c2.selectbox("Moneda", ["UYU", "USD"], index=["UYU", "USD"].index(fila["Moneda"]) if editando and fila["Moneda"] in ["UYU", "USD"] else 0)
        c3, c4 = st.columns(2)
        saldo_ini = c3.number_input("Saldo inicial", value=float(fila["Saldo_Inicial"]) if editando else 0.0, format="%.2f",
                                    help="Saldo al momento de empezar a registrar. Se considera de ambos según participación.")
        f_ap = c4.date_input("Fecha de apertura / inicio", pd.to_datetime(fila["Fecha_Apertura"]).date() if editando and str(fila["Fecha_Apertura"]).strip() not in ("", "nan") else hoy())
        notas = st.text_input("Notas (titulares, nº de cuenta, etc.)", fila["Notas"] if editando else "")
        activa = st.checkbox("Cuenta activa", value=(str(fila["Activa"]).lower() in ("true", "1", "si", "sí", "")) if editando else True)
        st.markdown("<br>", unsafe_allow_html=True)
        c_save, c_del, c_cancel = st.columns(3)
        if c_save.button("Guardar", type="primary", use_container_width=True):
            if not nombre.strip():
                st.error("Falta el nombre de la cuenta.")
            else:
                registro = {"ID": fila["ID"] if editando else nuevo_id(), "Nombre": nombre.strip(), "Banco": banco, "Moneda": moneda_c,
                            "Saldo_Inicial": saldo_ini, "Fecha_Apertura": str(f_ap), "Notas": notas, "Activa": bool(activa)}
                if editando:
                    df_cuentas = df_cuentas[df_cuentas["ID"] != edit_id]
                guardar_cuentas(agregar_fila(df_cuentas, registro))
                cerrar_form()
        if editando and c_del.button("🗑️ Eliminar", use_container_width=True):
            guardar_cuentas(df_cuentas[df_cuentas["ID"] != edit_id])
            cerrar_form()
        if c_cancel.button("Cancelar", use_container_width=True):
            cerrar_form()

elif modo == "mov":
    st.markdown('<div class="section-title">Movimiento en cuenta compartida</div>', unsafe_allow_html=True)
    if df_cuentas.empty:
        st.info("Primero creá una cuenta compartida.")
        if st.button("Volver"): cerrar_form()
    else:
        with st.container():
            fecha = st.date_input("Fecha", hoy())
            lab_c = [f"{c['Nombre']} ({c['Moneda']})" for _, c in df_cuentas.iterrows()]
            val_c = df_cuentas["ID"].tolist()
            sel_c = st.selectbox("Cuenta", lab_c)
            cuenta_id = val_c[lab_c.index(sel_c)]
            moneda_c = str(df_cuentas[df_cuentas["ID"] == cuenta_id].iloc[0]["Moneda"])
            tipo_m = st.radio("Tipo", TIPOS_MOV, horizontal=True,
                              help="Aporte: un hermano deposita dinero propio. Retiro: un hermano retira para sí. Ajuste: intereses, comisiones u otros (+/−), sin socio.")
            socio_m = ""
            if tipo_m in ("Aporte", "Retiro"):
                socio_m = st.selectbox("Socio", lista_socios, index=lista_socios.index(usuario) if usuario in lista_socios else 0) if lista_socios else ""
            monto_m = st.number_input(f"Monto ({moneda_c})", value=None, format="%.2f", help="Para Ajuste podés usar valores negativos (ej: comisiones).")
            concepto = st.text_input("Concepto", placeholder="Ej: Aporte para pagar contribución · Intereses del mes")
            archivos = st.file_uploader("Adjuntar comprobantes", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, key="m_files")
            st.markdown("<br>", unsafe_allow_html=True)
            c_save, c_cancel = st.columns(2)
            if c_save.button("Guardar", type="primary", use_container_width=True):
                if monto_m is None or (tipo_m != "Ajuste" and monto_m <= 0):
                    st.error("Ingresá un monto válido.")
                else:
                    adj = ""
                    if archivos:
                        urls, errs = subir_comprobantes(archivos, "COPRO_MOV", str(fecha))
                        for e in errs: st.warning(f"No se pudo subir un comprobante: {e}")
                        adj = urls
                    registro = {"ID": nuevo_id(), "Fecha": pd.Timestamp(fecha), "Cuenta_ID": cuenta_id, "Tipo": tipo_m, "Socio": socio_m,
                                "Moneda": moneda_c, "Monto": abs(monto_m) if tipo_m != "Ajuste" else monto_m, "Concepto": concepto,
                                "Archivo_Adjunto": adj or "Sin adjunto", "Registrado_por": usuario}
                    guardar_movs(agregar_fila(df_movs, registro))
                    cerrar_form()
            if c_cancel.button("Cancelar", use_container_width=True):
                cerrar_form()

elif modo == "transf":
    st.markdown('<div class="section-title">Pago entre hermanos</div>', unsafe_allow_html=True)
    if len(lista_socios) < 2:
        st.info("Se necesitan 2 socios.")
        if st.button("Volver"): cerrar_form()
    else:
        with st.container():
            fecha = st.date_input("Fecha", hoy())
            c1, c2 = st.columns(2)
            origen = c1.selectbox("Quién paga", lista_socios, index=lista_socios.index(usuario) if usuario in lista_socios else 0)
            destino = c2.selectbox("Quién recibe", [s for s in lista_socios if s != origen])
            moneda, monto, tasa = campos_monto("t", "UYU", None, None)
            notas = st.text_input("Notas (opcional)", placeholder="Ej: Saldo de gastos del trimestre")
            archivos = st.file_uploader("Adjuntar comprobantes", type=["pdf", "png", "jpg", "jpeg"], accept_multiple_files=True, key="t_files")
            st.markdown("<br>", unsafe_allow_html=True)
            c_save, c_cancel = st.columns(2)
            if c_save.button("Registrar", type="primary", use_container_width=True):
                if not monto:
                    st.error("Ingresá un monto.")
                else:
                    adj = ""
                    if archivos:
                        urls, errs = subir_comprobantes(archivos, "COPRO_TRANSF", str(fecha))
                        for e in errs: st.warning(f"No se pudo subir un comprobante: {e}")
                        adj = urls
                    registro = {"ID": nuevo_id(), "Fecha": pd.Timestamp(fecha), "Origen": origen, "Destino": destino, "Moneda": moneda,
                                "Monto_Original": monto, "Tasa_Cambio": tasa, "Monto_UYU": monto * tasa,
                                "Archivo_Adjunto": adj or "Sin adjunto", "Notas": notas}
                    guardar_transf(agregar_fila(df_transf, registro))
                    cerrar_form()
            if c_cancel.button("Cancelar", use_container_width=True):
                cerrar_form()

# =========================================================
# VISTA PRINCIPAL
# =========================================================
else:
    restaurar_tab()
    b1, b2, b3, b4 = st.columns(4)
    if b1.button("💸 Gasto", type="primary", use_container_width=True): abrir_form("gasto", tab=1)
    if b2.button("📅 Reservar", use_container_width=True): abrir_form("uso", tab=2)
    if b3.button("💰 Ingreso", use_container_width=True): abrir_form("ingreso", tab=3)
    if b4.button("🏦 Movimiento", use_container_width=True): abrir_form("mov", tab=4)

    tabs = st.tabs(["📊 Resumen", "💸 Gastos", "📅 Uso de la casa", "💰 Ingresos", "🏦 Cuentas", "⚖️ Balance", "⚙️ Config"])

    # ---------- RESUMEN ----------
    with tabs[0]:
        anio = anio_selector(pd.concat([df_gastos[["Fecha"]], df_ingresos[["Fecha"]]]) if not (df_gastos.empty and df_ingresos.empty) else pd.DataFrame(columns=["Fecha"]), "Fecha", "res_anio")
        g = df_gastos if anio is None else df_gastos[df_gastos["Fecha"].dt.year == anio]
        ing = df_ingresos if anio is None else df_ingresos[df_ingresos["Fecha"].dt.year == anio]
        g = g.copy(); ing = ing.copy()
        g["USD"] = g.apply(lambda r: a_usd(r, tasa_actual), axis=1) if not g.empty else []
        ing["USD"] = ing.apply(lambda r: a_usd(r, tasa_actual), axis=1) if not ing.empty else []
        tot_fijo = g[g["Tipo"] == TIPO_FIJO]["USD"].sum() if not g.empty else 0
        tot_uso = g[g["Tipo"] != TIPO_FIJO]["USD"].sum() if not g.empty else 0
        tot_ing = ing["USD"].sum() if not ing.empty else 0
        resultado = tot_ing - tot_fijo - tot_uso

        k1, k2, k3, k4 = st.columns(4)
        kpi(k1, "kpi-card-primary", "🏠", "Gastos fijos", f"U$S {tot_fijo:,.0f}", "mantenimiento e impuestos")
        kpi(k2, "kpi-card-amber", "🔥", "Gastos de uso", f"U$S {tot_uso:,.0f}", "atribuidos a quien usó")
        kpi(k3, "kpi-card-success", "💰", "Ingresos", f"U$S {tot_ing:,.0f}", "alquileres y otros")
        kpi(k4, "kpi-card-slate" if resultado < 0 else "kpi-card-success", "📈", "Resultado", f"U$S {resultado:,.0f}", "ingresos − gastos")

        # Saldo entre hermanos (resumen)
        if len(lista_socios) >= 2:
            partes = []
            for M in ["UYU", "USD"]:
                bal = calc_balance(M, lista_socios, shares, df_gastos, df_ingresos, df_movs, df_transf, df_cuentas)
                acreedor = max(bal, key=lambda s: bal[s]["saldo"])
                deudor = min(bal, key=lambda s: bal[s]["saldo"])
                dif = bal[acreedor]["saldo"]
                if abs(dif) < 1: partes.append(f"{M}: ✅ igualado")
                else: partes.append(f"{M}: {deudor} → {acreedor} {fmt_monto(M, dif)}")
            st.markdown(f"<div style='font-size:0.95rem;opacity:0.75;margin:4px 0 12px 0;'>⚖️ <b>Balance entre hermanos</b> &nbsp;·&nbsp; {' &nbsp;·&nbsp; '.join(partes)}</div>", unsafe_allow_html=True)

        if not g.empty or not ing.empty:
            c1, c2 = st.columns(2)
            with c1:
                st.markdown('<div class="section-title">Gastos e ingresos por mes</div>', unsafe_allow_html=True)
                frames = []
                if not g.empty:
                    gm = g.assign(Mes=g["Fecha"].dt.to_period("M").dt.to_timestamp(), Serie=g["Tipo"].map(lambda t: "Fijo / Mant." if t == TIPO_FIJO else "Uso"))
                    frames.append(gm.groupby(["Mes", "Serie"])["USD"].sum().reset_index())
                if not ing.empty:
                    im = ing.assign(Mes=ing["Fecha"].dt.to_period("M").dt.to_timestamp(), Serie="Ingresos")
                    frames.append(im.groupby(["Mes", "Serie"])["USD"].sum().reset_index())
                dm = pd.concat(frames)
                fig = px.bar(dm, x="Mes", y="USD", color="Serie", barmode="group",
                             color_discrete_map={"Fijo / Mant.": "#0D9488", "Uso": "#F59E0B", "Ingresos": "#059669"})
                fig.update_layout(margin=dict(t=10, b=10, l=0, r=0), xaxis_title="", yaxis_title="U$S", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                                  legend=dict(orientation="h", y=-0.25, x=0.5, xanchor="center", title_text="", font=dict(size=12)))
                fig.update_xaxes(tickformat="%b %y")
                fig.update_traces(hovertemplate='%{x|%b %Y}<br>U$S %{y:,.0f}<extra></extra>')
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar": False})
            with c2:
                st.markdown('<div class="section-title">Gastos por categoría</div>', unsafe_allow_html=True)
                if not g.empty:
                    fig_pie = px.pie(g.groupby("Categoria")["USD"].sum().reset_index(), values="USD", names="Categoria", hole=0.6, color_discrete_sequence=PALETA_CATS)
                    fig_pie.update_layout(margin=dict(t=10, b=30, l=0, r=0), legend=dict(orientation="h", y=-0.1, x=0.5, xanchor="center", font=dict(size=11)), paper_bgcolor="rgba(0,0,0,0)")
                    fig_pie.update_traces(textinfo="percent", textfont_size=12, hovertemplate='%{label}<br>U$S %{value:,.0f}<extra></extra>')
                    st.plotly_chart(fig_pie, use_container_width=True, config={"displayModeBar": False})
                else:
                    st.info("Sin gastos en el período.")

        # Uso de la casa en el año
        if not df_usos.empty:
            st.markdown('<div class="section-title">Días de uso de la casa</div>', unsafe_allow_html=True)
            u = df_usos.dropna(subset=["Fecha_Inicio", "Fecha_Fin"]).copy()
            if anio is not None:
                u = u[(u["Fecha_Inicio"].dt.year == anio) | (u["Fecha_Fin"].dt.year == anio)]
            if not u.empty:
                u["Dias"] = u.apply(lambda r: noches(r["Fecha_Inicio"].date(), r["Fecha_Fin"].date()), axis=1)
                u["Quien"] = u.apply(lambda r: r["Usuario"] if r["Tipo"] == "Uso propio" else r["Tipo"], axis=1)
                du = u.groupby("Quien")["Dias"].sum().reset_index()
                du["label"] = du["Dias"].apply(lambda v: f"{int(v)} días")
                colores = {s: COLORES_SOCIO[i % len(COLORES_SOCIO)] for i, s in enumerate(lista_socios)}
                colores.update({"Alquiler": "#D97706", "Mantenimiento": "#475569", "Bloqueo": "#E11D48"})
                fig_u = px.bar(du, x="Quien", y="Dias", text="label", color="Quien", color_discrete_map=colores)
                fig_u.update_layout(margin=dict(t=10, b=0, l=0, r=0), showlegend=False, xaxis_title="", yaxis_title="días", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=280)
                fig_u.update_traces(marker_line_width=0, textfont_size=13, hovertemplate='%{x}<br>%{y} días<extra></extra>')
                st.plotly_chart(fig_u, use_container_width=True, config={"displayModeBar": False})

        # Cuentas
        if not df_cuentas.empty:
            st.markdown('<div class="section-title">Cuentas compartidas</div>', unsafe_allow_html=True)
            cols = st.columns(min(len(df_cuentas), 3))
            for i, (_, c) in enumerate(df_cuentas.iterrows()):
                s = saldo_cuenta(str(c["ID"]), df_cuentas, df_movs, df_gastos, df_ingresos)
                kpi(cols[i % len(cols)], "kpi-card-neutral", "🏦", c["Nombre"], fmt_monto(c["Moneda"], s), c["Banco"])

    # ---------- GASTOS ----------
    with tabs[1]:
        f1, f2, f3 = st.columns(3)
        with f1: anio_g = anio_selector(df_gastos, "Fecha", "g_anio")
        with f2: tipo_f = st.selectbox("Tipo", ["Todos", TIPO_FIJO, TIPO_USO], key="g_tipo")
        with f3: quien_f = st.selectbox("Pagado por", ["Todos"] + lista_socios + ["Cuentas compartidas"], key="g_quien")
        d = df_gastos.copy()
        if anio_g is not None: d = d[d["Fecha"].dt.year == anio_g]
        if tipo_f != "Todos": d = d[d["Tipo"] == tipo_f]
        if quien_f == "Cuentas compartidas": d = d[d["Pagado_por"].astype(str).str.startswith("cta:")]
        elif quien_f != "Todos": d = d[d["Pagado_por"] == quien_f]
        if d.empty:
            st.info("Sin gastos para mostrar.")
        else:
            d["USD"] = d.apply(lambda r: a_usd(r, tasa_actual), axis=1)
            st.markdown(f"<div style='opacity:0.6;font-size:0.9rem;margin-bottom:8px;'>{len(d)} gastos · total U$S {d['USD'].sum():,.0f}</div>", unsafe_allow_html=True)
            for _, f in d.sort_values("Fecha", ascending=False).iterrows():
                badge = "badge-fijo" if f["Tipo"] == TIPO_FIJO else "badge-uso"
                fecha_txt = f["Fecha"].strftime("%d/%m/%y") if not pd.isna(f["Fecha"]) else "?"
                with st.expander(f"{fecha_txt}  ·  {f['Concepto']}  ·  {fmt_monto(f['Moneda'], f['Monto_Original'])}"):
                    st.markdown(
                        f"<div style='display:flex;gap:14px;align-items:center;flex-wrap:wrap;margin-bottom:8px;'>"
                        f"<span class='badge {badge}'>{f['Tipo']}</span><span class='badge badge-otros'>{f['Categoria']}</span>"
                        f"<span style='font-size:0.85rem;opacity:0.6;'>👤 Pagó {nombre_pagador(f['Pagado_por'], df_cuentas)}</span>"
                        f"<span style='font-size:0.85rem;opacity:0.6;'>🎯 Atribuido a {f['Atribuido_a'] or ATRIB_AMBOS}</span>"
                        f"</div>", unsafe_allow_html=True)
                    ca, cb = st.columns(2)
                    ca.metric("Monto", fmt_monto(f["Moneda"], f["Monto_Original"]))
                    cb.metric("En USD" if f["Moneda"] == "UYU" else "En UYU", f"U$S {f['USD']:,.0f}" if f["Moneda"] == "UYU" else f"$ {f['Monto_UYU']:,.0f}")
                    if str(f["Notas"]).strip() not in ("", "nan"): st.caption(f"📝 {f['Notas']}")
                    md = links_adjuntos_md(f["Archivo_Adjunto"])
                    if md: st.markdown(md)
                    if st.button("✏️ Editar / Eliminar", key=f"eg_{f['ID']}", use_container_width=True):
                        abrir_form("gasto", f["ID"], tab=1)

    # ---------- USO DE LA CASA ----------
    with tabs[2]:
        cprev, cmes, cnext = st.columns([1, 3, 1])
        if cprev.button("◀", use_container_width=True, key="cal_prev"):
            m = st.session_state.cal_month - 1
            if m == 0: st.session_state.cal_month, st.session_state.cal_year = 12, st.session_state.cal_year - 1
            else: st.session_state.cal_month = m
            st.rerun()
        if cnext.button("▶", use_container_width=True, key="cal_next"):
            m = st.session_state.cal_month + 1
            if m == 13: st.session_state.cal_month, st.session_state.cal_year = 1, st.session_state.cal_year + 1
            else: st.session_state.cal_month = m
            st.rerun()
        meses_es = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]
        cmes.markdown(f"<div style='text-align:center;font-weight:900;font-size:1.25rem;padding-top:8px;'>{meses_es[st.session_state.cal_month-1]} {st.session_state.cal_year}</div>", unsafe_allow_html=True)
        render_mes(st.session_state.cal_year, st.session_state.cal_month, df_usos, lista_socios)
        leyenda = " ".join(f"<span class='cal-tag' style='display:inline-block;background:{COLORES_SOCIO[i % len(COLORES_SOCIO)]};margin-right:6px;'>{s}</span>" for i, s in enumerate(lista_socios))
        leyenda += "<span class='cal-tag' style='display:inline-block;background:#D97706;margin-right:6px;'>Alquiler</span><span class='cal-tag' style='display:inline-block;background:#475569;margin-right:6px;'>Mantenimiento</span><span class='cal-tag' style='display:inline-block;background:#E11D48;'>Bloqueo</span>"
        st.markdown(f"<div style='margin:10px 0 4px 0;'>{leyenda}</div>", unsafe_allow_html=True)

        if calendar_id(cfg):
            with st.expander("📆 Ver Google Calendar"):
                components.iframe(f"https://calendar.google.com/calendar/embed?src={calendar_id(cfg)}&ctz=America%2FMontevideo&mode=MONTH", height=520)

        st.markdown('<div class="section-title">Estadías</div>', unsafe_allow_html=True)
        if df_usos.empty:
            st.info("Todavía no hay estadías registradas. Usá 📅 Reservar.")
        else:
            solo_fut = st.checkbox("Solo próximas", value=True, key="usos_fut")
            u = df_usos.dropna(subset=["Fecha_Inicio", "Fecha_Fin"]).copy()
            if solo_fut: u = u[u["Fecha_Fin"].dt.date >= hoy()]
            for _, r in u.sort_values("Fecha_Inicio", ascending=bool(solo_fut)).iterrows():
                color = color_uso(r, lista_socios)
                n = noches(r["Fecha_Inicio"].date(), r["Fecha_Fin"].date())
                with st.expander(f"{r['Fecha_Inicio'].strftime('%d/%m/%y')} → {r['Fecha_Fin'].strftime('%d/%m/%y')}  ·  {etiqueta_uso(r)}  ·  {n} días"):
                    st.markdown(f"<span class='cal-tag' style='display:inline-block;background:{color};font-size:0.75rem;'>{r['Tipo']}</span> &nbsp;"
                                f"<span style='font-size:0.85rem;opacity:0.6;'>👥 {r['Personas']} personas</span>"
                                + (f" &nbsp;<span style='font-size:0.85rem;opacity:0.6;'>📆 en Google Calendar</span>" if str(r['GCal_Event_ID']).strip() not in ('', 'nan') else ""),
                                unsafe_allow_html=True)
                    if str(r["Titulo"]).strip() not in ("", "nan"): st.markdown(f"**{r['Titulo']}**")
                    if str(r["Notas"]).strip() not in ("", "nan"): st.caption(f"📝 {r['Notas']}")
                    # Gastos e ingresos vinculados
                    gv = df_gastos[df_gastos["Uso_ID"].astype(str) == str(r["ID"])] if not df_gastos.empty else pd.DataFrame()
                    iv = df_ingresos[df_ingresos["Uso_ID"].astype(str) == str(r["ID"])] if not df_ingresos.empty else pd.DataFrame()
                    if not gv.empty or not iv.empty:
                        ca, cb = st.columns(2)
                        ca.metric("Gastos vinculados", f"U$S {sum(a_usd(x, tasa_actual) for _, x in gv.iterrows()):,.0f}")
                        cb.metric("Ingresos vinculados", f"U$S {sum(a_usd(x, tasa_actual) for _, x in iv.iterrows()):,.0f}")
                    if st.button("✏️ Editar / Eliminar", key=f"eu_{r['ID']}", use_container_width=True):
                        abrir_form("uso", r["ID"], tab=2)

    # ---------- INGRESOS ----------
    with tabs[3]:
        anio_i = anio_selector(df_ingresos, "Fecha", "i_anio")
        d = df_ingresos.copy()
        if anio_i is not None: d = d[d["Fecha"].dt.year == anio_i]
        if d.empty:
            st.info("Sin ingresos para mostrar. Usá 💰 Ingreso para registrar un alquiler u otro ingreso.")
        else:
            d["USD"] = d.apply(lambda r: a_usd(r, tasa_actual), axis=1)
            st.markdown(f"<div style='opacity:0.6;font-size:0.9rem;margin-bottom:8px;'>{len(d)} ingresos · total U$S {d['USD'].sum():,.0f}</div>", unsafe_allow_html=True)
            for _, f in d.sort_values("Fecha", ascending=False).iterrows():
                fecha_txt = f["Fecha"].strftime("%d/%m/%y") if not pd.isna(f["Fecha"]) else "?"
                with st.expander(f"{fecha_txt}  ·  {f['Concepto']}  ·  {fmt_monto(f['Moneda'], f['Monto_Original'])}"):
                    st.markdown(f"<span class='badge badge-ing'>{f['Tipo']}</span> &nbsp;<span style='font-size:0.85rem;opacity:0.6;'>💳 Cobró {nombre_pagador(f['Cobrado_por'], df_cuentas)}</span>", unsafe_allow_html=True)
                    ca, cb = st.columns(2)
                    ca.metric("Monto", fmt_monto(f["Moneda"], f["Monto_Original"]))
                    cb.metric("En USD" if f["Moneda"] == "UYU" else "En UYU", f"U$S {f['USD']:,.0f}" if f["Moneda"] == "UYU" else f"$ {f['Monto_UYU']:,.0f}")
                    if str(f["Notas"]).strip() not in ("", "nan"): st.caption(f"📝 {f['Notas']}")
                    md = links_adjuntos_md(f["Archivo_Adjunto"])
                    if md: st.markdown(md)
                    if st.button("✏️ Editar / Eliminar", key=f"ei_{f['ID']}", use_container_width=True):
                        abrir_form("ingreso", f["ID"], tab=3)

    # ---------- CUENTAS ----------
    with tabs[4]:
        if st.button("➕ Nueva cuenta compartida", use_container_width=True):
            abrir_form("cuenta", tab=4)
        if df_cuentas.empty:
            st.info("Sin cuentas compartidas todavía.")
        else:
            for _, c in df_cuentas.iterrows():
                cid = str(c["ID"])
                s = saldo_cuenta(cid, df_cuentas, df_movs, df_gastos, df_ingresos)
                activa = str(c["Activa"]).lower() in ("true", "1", "si", "sí", "")
                with st.expander(f"🏦 {c['Nombre']}  ·  {fmt_monto(c['Moneda'], s)}" + ("" if activa else "  ·  (inactiva)")):
                    st.markdown(f"<span class='badge badge-cta'>{c['Moneda']}</span> &nbsp;<span style='font-size:0.85rem;opacity:0.6;'>{c['Banco']}</span>"
                                + (f" &nbsp;<span style='font-size:0.85rem;opacity:0.6;'>📝 {c['Notas']}</span>" if str(c['Notas']).strip() not in ('', 'nan') else ""), unsafe_allow_html=True)
                    m = df_movs[df_movs["Cuenta_ID"].astype(str) == cid] if not df_movs.empty else pd.DataFrame()
                    ap = m[m["Tipo"] == "Aporte"]["Monto"].sum() if not m.empty else 0
                    re_ = m[m["Tipo"] == "Retiro"]["Monto"].sum() if not m.empty else 0
                    ing_c = df_ingresos[df_ingresos["Cobrado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum() if not df_ingresos.empty else 0
                    gas_c = df_gastos[df_gastos["Pagado_por"].astype(str) == f"cta:{cid}"]["Monto_Original"].sum() if not df_gastos.empty else 0
                    k1, k2, k3, k4 = st.columns(4)
                    k1.metric("Saldo inicial", fmt_monto(c["Moneda"], c["Saldo_Inicial"]))
                    k2.metric("Aportes − retiros", fmt_monto(c["Moneda"], ap - re_))
                    k3.metric("Ingresos", fmt_monto(c["Moneda"], ing_c))
                    k4.metric("Gastos pagados", fmt_monto(c["Moneda"], gas_c))
                    if not m.empty:
                        st.markdown("<div style='font-weight:800;margin:8px 0 4px 0;'>Movimientos</div>", unsafe_allow_html=True)
                        for _, mv in m.sort_values("Fecha", ascending=False).head(50).iterrows():
                            signo = "+" if mv["Tipo"] == "Aporte" or (mv["Tipo"] == "Ajuste" and mv["Monto"] >= 0) else "−"
                            quien = f" · {mv['Socio']}" if str(mv["Socio"]).strip() not in ("", "nan") else ""
                            md = links_adjuntos_md(mv["Archivo_Adjunto"], "comprobante")
                            fecha_txt = mv["Fecha"].strftime("%d/%m/%y") if not pd.isna(mv["Fecha"]) else "?"
                            cm1, cm2 = st.columns([5, 1])
                            cm1.markdown(f"<div style='font-size:0.9rem;padding:4px 0;'>{fecha_txt} · <b>{mv['Tipo']}</b>{quien} · {signo}{fmt_monto(mv['Moneda'], abs(mv['Monto']))} <span style='opacity:0.55;'>{mv['Concepto']}</span> {md}</div>", unsafe_allow_html=True)
                            if cm2.button("🗑️", key=f"dm_{mv['ID']}"):
                                guardar_movs(df_movs[df_movs["ID"] != mv["ID"]])
                                st.session_state.tab_activa = 4
                                st.rerun()
                    if st.button("✏️ Editar cuenta", key=f"ec_{cid}", use_container_width=True):
                        abrir_form("cuenta", cid, tab=4)

    # ---------- BALANCE ----------
    with tabs[5]:
        if len(lista_socios) < 2:
            st.info("Se necesitan 2 socios para el balance.")
        else:
            if st.button("🔁 Registrar pago entre hermanos", use_container_width=True):
                abrir_form("transf", tab=5)
            st.markdown('<div class="section-title">Balances por moneda</div>', unsafe_allow_html=True)
            st.caption("Cada hermano aporta según su participación en los gastos compartidos, más los gastos de uso que se le atribuyen, menos su parte de los ingresos. "
                       "El saldo positivo indica quién puso de más.")
            filas_html = ""
            for M in ["UYU", "USD"]:
                bal = calc_balance(M, lista_socios, shares, df_gastos, df_ingresos, df_movs, df_transf, df_cuentas)
                acreedor = max(bal, key=lambda s: bal[s]["saldo"])
                deudor = min(bal, key=lambda s: bal[s]["saldo"])
                dif = bal[acreedor]["saldo"]
                if abs(dif) < 1:
                    filas_html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.15);"><span style="font-size:1.05rem;opacity:0.85;">{M}</span><span style="font-size:1.2rem;font-weight:700;">✅ Igualado</span></div>'
                else:
                    filas_html += f'<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid rgba(255,255,255,0.15);"><span style="font-size:1.05rem;opacity:0.85;">{M} · {deudor} → {acreedor}</span><span style="font-size:1.5rem;font-weight:900;">{fmt_monto(M, abs(dif))}</span></div>'
            st.markdown(f'<div class="kpi-card kpi-card-primary"><div class="kpi-label">Balances por moneda</div>{filas_html}</div>', unsafe_allow_html=True)

            for M in ["UYU", "USD"]:
                bal = calc_balance(M, lista_socios, shares, df_gastos, df_ingresos, df_movs, df_transf, df_cuentas)
                if all(abs(v["aporte_neto"]) < 0.01 and abs(v["corresponde"]) < 0.01 for v in bal.values()):
                    continue
                st.markdown(f'<div class="section-title">Detalle {M}</div>', unsafe_allow_html=True)
                cols = st.columns(len(lista_socios))
                for i, s in enumerate(lista_socios):
                    b = bal[s]
                    def _row(lab, val, bold=False, color=None):
                        stl = "font-weight:800;" if bold else "opacity:0.8;"
                        col = f"color:{color};" if color else ""
                        return f"<div style='display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid rgba(148,163,184,0.15);font-size:1rem;{stl}'><span>{lab}</span><span style='{col}'>{fmt_monto(M, val)}</span></div>"
                    html = f"<div class='etapa-card'><div style='font-size:1.3rem;font-weight:900;margin-bottom:8px;'>{s} <span style='font-size:0.8rem;opacity:0.5;font-weight:700;'>({b['share']*100:.0f}%)</span></div>"
                    html += _row("Pagó gastos fijos", b["pagado_fijo"]) + _row("Pagó gastos de uso", b["pagado_uso"])
                    if b["aportes"] or b["retiros"]: html += _row("Aportes a cuentas", b["aportes"]) + _row("Retiros de cuentas", -b["retiros"])
                    if b["cobrado"]: html += _row("Ingresos cobrados (a devolver al pozo)", -b["cobrado"])
                    if b["env"] or b["rec"]: html += _row("Pagos enviados al hermano", b["env"]) + _row("Pagos recibidos del hermano", -b["rec"])
                    html += _row("Aporte neto", b["aporte_neto"], bold=True)
                    html += _row("Le corresponde", b["corresponde"])
                    if abs(b["pool_share"]) > 0.01: html += _row("Su parte en cuentas compartidas", b["pool_share"])
                    color = "#059669" if b["saldo"] > 0.5 else ("#DC2626" if b["saldo"] < -0.5 else None)
                    html += _row("Saldo", b["saldo"], bold=True, color=color) + "</div>"
                    cols[i].markdown(html, unsafe_allow_html=True)

            if not df_transf.empty:
                st.markdown('<div class="section-title">Pagos entre hermanos</div>', unsafe_allow_html=True)
                for _, t in df_transf.sort_values("Fecha", ascending=False).iterrows():
                    fecha_txt = t["Fecha"].strftime("%d/%m/%y") if not pd.isna(t["Fecha"]) else "?"
                    ct1, ct2 = st.columns([5, 1])
                    md = links_adjuntos_md(t["Archivo_Adjunto"], "comprobante")
                    ct1.markdown(f"<div style='font-size:0.95rem;padding:6px 0;'>{fecha_txt} · <b>{t['Origen']} → {t['Destino']}</b> · {fmt_monto(t['Moneda'], t['Monto_Original'])} <span style='opacity:0.55;'>{t['Notas'] if str(t['Notas']).strip() not in ('', 'nan') else ''}</span> {md}</div>", unsafe_allow_html=True)
                    if ct2.button("🗑️", key=f"dt_{t['ID']}"):
                        guardar_transf(df_transf[df_transf["ID"] != t["ID"]])
                        st.session_state.tab_activa = 5
                        st.rerun()

    # ---------- CONFIG ----------
    with tabs[6]:
        st.markdown('<div class="section-title">Participación en la copropiedad</div>', unsafe_allow_html=True)
        st.caption("Porcentaje con el que cada hermano participa en los gastos fijos, gastos compartidos e ingresos.")
        with st.form("form_shares"):
            nuevos = {}
            cols = st.columns(max(len(lista_socios), 1))
            for i, s in enumerate(lista_socios):
                nuevos[s] = cols[i].number_input(f"{s} (%)", min_value=0.0, max_value=100.0, value=round(shares.get(s, 0) * 100, 2), step=0.5, key=f"sh_{s}")
            if st.form_submit_button("Guardar participación", type="primary", use_container_width=True):
                if abs(sum(nuevos.values()) - 100) > 0.01:
                    st.error("Los porcentajes deben sumar 100.")
                else:
                    for s, v in nuevos.items(): cfg[f"share_{s}"] = str(v)
                    save_config(cfg)
                    st.success("Participación guardada.")
                    st.rerun()

        st.markdown('<div class="section-title">Google Calendar</div>', unsafe_allow_html=True)
        st.caption("ID del calendario compartido (Configuración del calendario → Integrar calendario → ID). "
                   "Para crear eventos automáticamente el token OAuth debe incluir el permiso de Calendar (regenerar con get_drive_token.py).")
        if has_secret("google_calendar_id"):
            st.info(f"Configurado en secrets: `{calendar_id(cfg)}`")
        else:
            with st.form("form_gcal"):
                cal_in = st.text_input("Calendar ID", cfg.get("google_calendar_id", ""), placeholder="xxxx@group.calendar.google.com")
                if st.form_submit_button("Guardar calendario", use_container_width=True):
                    cfg["google_calendar_id"] = cal_in.strip()
                    save_config(cfg)
                    st.success("Guardado.")
                    st.rerun()
        st.write(f"- Sincronización de eventos: {'✅ disponible' if gcal_disponible(cfg) else '❌ no disponible (falta calendar ID o token OAuth)'}")

        st.markdown('<div class="section-title">Respaldo</div>', unsafe_allow_html=True)
        if st.button("Generar respaldo Excel", use_container_width=True):
            nombre, datos = generar_respaldo({"Gastos": df_gastos, "Ingresos": df_ingresos, "Usos": df_usos, "Cuentas": df_cuentas,
                                              "Movimientos": df_movs, "Transferencias": df_transf})
            st.download_button("⬇️ Descargar", data=datos, file_name=nombre, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

        if es_admin:
            st.markdown('<div class="section-title">Usuarios</div>', unsafe_allow_html=True)
            st.dataframe(usuarios_df[["Usuario"]], use_container_width=True)
            with st.form("nuevo_usuario_copro"):
                nuevo_nombre = st.text_input("Nombre de usuario")
                nueva_clave = st.text_input("Contraseña", type="password")
                if st.form_submit_button("Añadir usuario", type="primary"):
                    if nuevo_nombre and nueva_clave:
                        if nuevo_nombre in usuarios_df["Usuario"].values: st.error("Ese usuario ya existe.")
                        else:
                            save_users(pd.concat([usuarios_df, pd.DataFrame([{"Usuario": nuevo_nombre, "Clave": nueva_clave}])], ignore_index=True))
                            st.rerun()
        st.caption(f"Almacenamiento: {'Google Sheets' if USE_GSHEETS else 'archivos CSV locales'} · Comprobantes en Drive: {'✅' if has_secret('google_oauth_refresh_token') else '❌'}")
