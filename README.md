# Instagram Followers — OCI Function

Función que pega directo al endpoint JSON interno de Instagram
`web_profile_info` (`api/v1/users/web_profile_info/?username=solamentedeya.m`)
mandando el header público `x-ig-app-id` que el propio front de Instagram usa
en esa llamada, y extrae `data.user.edge_followed_by.count`. Sin browser: un
`GET` HTTP normal con `requests`.

**Por qué no usa Playwright/Chromium (a diferencia de Spotify):** la primera
versión de este scraper replicaba el enfoque de
[`guacha-records-spotify-scraper`](../guacha-records-spotify-scraper) —
Chromium headless interceptando la respuesta de red. Anduvo bien en local,
pero desplegado en OCI Functions Chromium se caía consistentemente (`502
function failed`, sin excepción de Python — el contenedor moría antes de que
nuestro propio `try/except` pudiera loguear nada) incluso subiendo la memoria
a 2048MB y bloqueando imágenes/fuentes. Todo indica que Instagram es mucho
más agresivo que Spotify detectando/bloqueando Chromium headless desde IPs de
datacenter. Como el dato que necesitamos (seguidores) sale del mismo endpoint
JSON que Chromium terminaba disparando de todas formas, pegarle directo por
HTTP evita el problema de raíz y de paso deja la imagen Docker mucho más
liviana (sin Chromium ni sus ~100 paquetes de sistema).

Este repo es independiente del de
[`guacha-records-spotify-scraper`](../guacha-records-spotify-scraper): su
propia Application de OCI Functions, su propio repo/deploy de GitHub Actions
y su propio path en el registry (`guacha-instagram-scraper`). La idea es que
si uno de los dos scrapers falla no tumbe al otro — antes compartían
flujo/pestañas y una falla arrastraba a la otra.

⚠️ **Riesgo conocido:** este endpoint es interno/no documentado — Instagram
puede cambiarlo o empezar a exigir headers adicionales (cookies de sesión,
u otro `x-ig-app-id`) en cualquier momento. Si `followers` empieza a salir
`null`/error de forma consistente, revisá primero si el endpoint sigue
respondiendo igual con una request manual (`curl` con los mismos headers)
antes de asumir que hay que volver a un browser real.

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
la función. Al no llevar Chromium, la imagen es chica y el build es rápido.

## 3. Probar directo (sin API Gateway todavía)
```bash
fn invoke instagram-scraper instagram-followers-solamentedeya
```
Debería devolver algo como:
```json
{"profile_username": "solamentedeya.m", "followers": 1234, "ok": true}
```
Si `followers` sale `null`, revisa los logs (`fn logs` o el log de la
Application en la consola OCI) — probablemente Instagram cambió el endpoint
o los headers que exige.

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
