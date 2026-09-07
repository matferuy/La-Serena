# La Serena

Una sola app Streamlit con login compartido y dos secciones independientes, seleccionables desde la cabecera:

| Sección | Archivo | Para qué |
|---------|---------|----------|
| 🏗️ **Obra** | `obra.py` | Contabilidad compartida de la construcción: gastos por etapa, presupuesto vs. real, avances, planos, balance entre socios. |
| 🏠 **Copropiedad** | `copropiedad.py` | Gestión de la casa entre hermanos: gastos fijos/mantenimiento vs. gastos de uso, calendario de uso (Google Calendar), alquileres y otros ingresos, cuentas bancarias compartidas, balance por moneda. |

- `App.py` es el punto de entrada (`st.navigation`): configura la página, los estilos, hace el login una sola vez y muestra el selector Obra / Copropiedad.
- `common.py` contiene la infraestructura compartida (estilos, Google Sheets, Drive, Calendar, login, comprobantes múltiples, tipo de cambio).

URLs directas: `/obra` y `/copropiedad`.

## Cómo funciona la Copropiedad

- **Gastos**: cada gasto es *Fijo / Mantenimiento* o *de Uso*, y se reparte entre los hermanos con una de tres modalidades:
  - *Partes iguales* (según la participación configurada, 50/50 por defecto): gastos fijos recurrentes.
  - *Porcentaje ad hoc*: gastos excepcionales, con un porcentaje definido para ese gasto (puede ser 100% de uno).
  - *Proporcional al uso*: gastos recurrentes asociados al uso (UTE, OSE, gas), repartidos por días de estadía de cada uno en un período; los días de alquiler cuentan como compartidos.

  Puede pagarlo un hermano o una cuenta compartida.
- **Uso de la casa**: estadías propias, alquileres, mantenimiento o bloqueos en un calendario mensual. Si se configura `google_calendar_id` (y el token OAuth tiene permiso de Calendar) cada estadía crea/actualiza/borra un evento en Google Calendar. Avisa si dos estadías se superponen.
- **Ingresos**: alquileres u otros, cobrados por un hermano o depositados en una cuenta compartida. Se pueden vincular a la estadía.
- **Cuentas**: cuentas bancarias compartidas con aportes y retiros por socio, ajustes (intereses/comisiones) y saldo calculado.
- **Balance**: por moneda (UYU y USD). Para cada hermano: *aporte neto* (lo que pagó + aportes a cuentas − retiros − ingresos que cobró ± pagos entre hermanos) menos *lo que le corresponde* (su % de los gastos compartidos + sus gastos de uso − su % de los ingresos) menos su parte del pozo en cuentas compartidas. Saldo positivo → le deben.

Los datos de Copropiedad viven en la misma planilla de Google Sheets, en pestañas `Copro_Gastos`, `Copro_Ingresos`, `Copro_Usos`, `Copro_Cuentas`, `Copro_Movimientos`, `Copro_Transferencias` y `Copro_Config`, que se crean solas.

## Deploy en Streamlit Cloud

Una sola app con *Main file path* = `App.py`. Secrets según `.streamlit/secrets.toml.example`.

## Google Drive y Calendar (OAuth)

Los comprobantes se suben a Drive y las estadías al calendario con un token OAuth de usuario (las service accounts no tienen cuota en Drive personal):

```bash
pip install google-auth-oauthlib
python get_drive_token.py   # pide los scopes de Drive y Calendar y muestra las 3 claves para los Secrets
```

Sin Python: [OAuth Playground](https://developers.google.com/oauthplayground) con las credenciales propias y los scopes `.../auth/drive` y `.../auth/calendar`. La app OAuth debe estar **En producción** para que el token no expire a los 7 días.

## Local

```bash
pip install -r requirements.txt
streamlit run App.py
```

Sin `secrets.toml` la app funciona con archivos CSV locales (sin Drive ni Calendar). Con Docker: `docker compose up`.
