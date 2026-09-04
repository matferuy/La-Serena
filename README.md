# La Serena

Dos aplicativos Streamlit que comparten login, planilla de Google Sheets y carpeta de Drive:

| App | Archivo | Para qué |
|-----|---------|----------|
| 🏗️ **Obra** | `App.py` | Contabilidad compartida de la construcción: gastos por etapa, presupuesto vs. real, avances, planos, balance entre socios. |
| 🏠 **Copropiedad** | `Copropiedad.py` | Gestión de la casa entre hermanos: gastos fijos/mantenimiento vs. gastos de uso, calendario de uso (Google Calendar), alquileres y otros ingresos, cuentas bancarias compartidas, balance por moneda. |

`common.py` contiene la infraestructura compartida (estilos, Google Sheets, Drive, Calendar, login, comprobantes múltiples, tipo de cambio).

## Cómo funciona la Copropiedad

- **Gastos**: cada gasto es *Fijo / Mantenimiento* (se reparte según la participación configurada, 50/50 por defecto) o *de Uso* (se atribuye al hermano que usó la casa, a ambos, o al alquiler). Puede pagarlo un hermano o una cuenta compartida.
- **Uso de la casa**: estadías propias, alquileres, mantenimiento o bloqueos en un calendario mensual. Si se configura `google_calendar_id` (y el token OAuth tiene permiso de Calendar) cada estadía crea/actualiza/borra un evento en Google Calendar. Avisa si dos estadías se superponen.
- **Ingresos**: alquileres u otros, cobrados por un hermano o depositados en una cuenta compartida. Se pueden vincular a la estadía.
- **Cuentas**: cuentas bancarias compartidas con aportes y retiros por socio, ajustes (intereses/comisiones) y saldo calculado.
- **Balance**: por moneda (UYU y USD). Para cada hermano: *aporte neto* (lo que pagó + aportes a cuentas − retiros − ingresos que cobró ± pagos entre hermanos) menos *lo que le corresponde* (su % de los gastos compartidos + sus gastos de uso − su % de los ingresos) menos su parte del pozo en cuentas compartidas. Saldo positivo → le deben.

## Deploy en Streamlit Cloud

Crear **dos apps** desde el mismo repositorio, cambiando solo el *Main file path*:

1. `App.py` → Obra
2. `Copropiedad.py` → Copropiedad

Ambas usan los mismos Secrets (ver `.streamlit/secrets.toml.example`). La app de Copropiedad crea automáticamente en la misma planilla las pestañas `Copro_Gastos`, `Copro_Ingresos`, `Copro_Usos`, `Copro_Cuentas`, `Copro_Movimientos`, `Copro_Transferencias` y `Copro_Config`.

Opcional: `url_app_obra` y `url_app_copropiedad` en los Secrets agregan un link cruzado en la cabecera de cada app.

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
streamlit run App.py            # Obra en :8501
streamlit run Copropiedad.py    # Copropiedad
```

Sin `secrets.toml` las apps funcionan con archivos CSV locales (sin Drive ni Calendar).

Con Docker: `docker compose up` levanta Obra en `:8501` y Copropiedad en `:8502`.
