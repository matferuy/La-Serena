"""
Ejecutá este script UNA SOLA VEZ para obtener el refresh_token de Google Drive.

Pasos previos:
1. GCP Console → APIs y servicios → Credenciales → Crear credencial → ID de cliente OAuth 2.0
2. Tipo: Aplicación de escritorio
3. Descargar el JSON y guardarlo como 'oauth_credentials.json' en esta carpeta
4. Correr: python get_drive_token.py

El script abre el navegador para que autorices el acceso.
Al final imprime el refresh_token para pegar en los Secrets de Streamlit.
"""

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/drive"]

flow = InstalledAppFlow.from_client_secrets_file("oauth_credentials.json", SCOPES)
creds = flow.run_local_server(port=0)

print("\n✅ Autenticación exitosa. Pegá esto en los Secrets de Streamlit Cloud:\n")
print(f'google_oauth_client_id = "{creds.client_id}"')
print(f'google_oauth_client_secret = "{creds.client_secret}"')
print(f'google_oauth_refresh_token = "{creds.refresh_token}"')
