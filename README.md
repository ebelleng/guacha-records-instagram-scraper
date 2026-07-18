# Instagram Followers — OCI Function

Función que abre `instagram.com/solamentedeya.m` con Chromium headless
(Playwright) e intercepta la llamada de red interna `web_profile_info`
(`api/v1/users/web_profile_info/?username=solamentedeya.m`) que Instagram
dispara al cargar el perfil, de la cual se extrae
`data.user.edge_followed_by.count`. Igual que en el scraper de Spotify, ese
número no está en el HTML servido de entrada (SEO/meta tags), sino que llega
vía una llamada propia del front — por eso hace falta un browser real y no
un simple `fetch`.

Este repo es una réplica **independiente** del de
[`guacha-records-spotify-scraper`](../guacha-records-spotify-scraper):
misma arquitectura (Fn Project / OCI Functions + Playwright), pero su propia
Application de OCI Functions, su propio repo/deploy de GitHub Actions y su
propio path en el registry (`guacha-instagram-scraper`). La idea es que si
uno de los dos scrapers falla (bloqueo del sitio, cambio de markup, límite
de tamaño de imagen, etc.) no tumbe al otro — antes compartían flujo/pestañas
y una falla arrastraba a la otra.

⚠️ **Sin probar en un tenancy real.** Igual que el de Spotify, esto está
armado en base a la documentación de Fn Project / OCI Functions sin poder
desplegarlo ni ejecutarlo desde acá. Instagram además es bastante más
agresivo que Spotify bloqueando tráfico de datacenters/IPs de nube y puede
pedir login para ciertas requests — si `followers` sale `null` de forma
consistente, puede que haga falta agregar cookies de sesión o un proxy
residencial.

## 1. Prerequisitos
- CLI de Fn Project instalado y configurado contra tu tenancy OCI
  (`fn list contexts` debería mostrar tu contexto de Oracle).
- Docker corriendo localmente (el build se hace con Docker).
- Un compartment y una **Application de Functions propia** (no reusar la de
  Spotify, justamente para mantenerlas independientes):
  ```
  fn create app instagram-scraper --annotation oracle.com/oci/subnetIds='["<subnet-ocid>"]'
  ```

## 2. Deploy
Desde esta carpeta:
```bash
fn -v deploy --app instagram-scraper
```
Esto hace el build de la imagen (Docker), la sube a OCIR, y crea/actualiza
la función. La primera build va a tardar varios minutos por el
`playwright install --with-deps chromium`.

**Riesgo conocido:** OCI Functions tiene un límite sobre el tamaño total
descomprimido de las imágenes de una Application. Una imagen con Chromium
puede rondar 500MB-1GB — por eso esta función vive en su propia Application,
separada de la de Spotify.

## 3. Probar directo (sin API Gateway todavía)
```bash
fn invoke instagram-scraper instagram-followers-solamentedeya
```
Debería devolver algo como:
```json
{"profile_username": "solamentedeya.m", "followers": 1234, "ok": true}
```
Si `followers` sale `null`, revisa los logs (`fn logs` o el log de la
Application en la consola OCI) — puede ser que Instagram haya pedido login,
que el `username` en la URL de `web_profile_info` no matchee a tiempo, o que
haya cambiado el endpoint interno.

## 4. Exponerla como endpoint HTTPS (para que n8n la llame)
Igual que con el scraper de Spotify, hace falta **API Gateway** adelante de
la función:

1. Consola OCI → API Gateway → Gateways → crear uno (o reusar) en la misma
   VCN/subnet que la Application de Functions.
2. Crear un **Deployment** con una ruta, ej. `/instagram-followers`, método
   `GET`, backend tipo "Oracle Functions" apuntando a esta función.
3. En la política de autenticación del deployment, configurá algo simple
   como un **Request Authorizer** o dejalo sin auth y agregá una ruta con
   un segmento random difícil de adivinar.
4. Guarda la URL pública que te da el Deployment.

## 5. GitHub Actions
El workflow (`.github/workflows/deploy.yml`) usa los mismos secrets que el
repo de Spotify (`OCI_CLI_USER`, `OCI_CLI_FINGERPRINT`, `OCI_CLI_TENANCY`,
`OCI_CLI_KEY_CONTENT`, `OCIR_AUTH_TOKEN`, `OCI_USERNAME`), pero al ser un
repo distinto hay que cargarlos de nuevo en **Settings → Secrets and
variables → Actions** de este repo — no se heredan del otro.

## 6. Conectar con n8n
Con la URL del Deployment, agregá un HTTP Request GET en el workflow de
n8n, en paralelo a los otros fetch de métricas, y juntá el valor de
`followers` junto con el resto antes de mandarlo al dashboard.
