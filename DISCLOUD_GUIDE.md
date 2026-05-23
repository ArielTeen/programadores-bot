# Guia Completa de Hosteo en Discloud

## Indice

1. [Requisitos](#1-requisitos)
2. [Estructura del Proyecto](#2-estructura-del-proyecto)
3. [Archivo discloud.config](#3-archivo-discloudconfig)
4. [Variables de Entorno](#4-variables-de-entorno)
5. [Preparar el Proyecto](#5-preparar-el-proyecto)
6. [Subir a GitHub](#6-subir-a-github)
7. [Desplegar en Discloud](#7-desplegar-en-discloud)
8. [Configurar Subdominio](#8-configurar-subdominio)
9. [Dashboard y Login](#9-dashboard-y-login)
10. [Mantenimiento](#10-mantenimiento)
11. [Solucion de Problemas](#11-solucion-de-problemas)
12. [Seguridad](#12-seguridad)

---

## 1. Requisitos

- Cuenta en [Discloud](https://discloud.com) (plan Platinum o superior para subdominio)
- Cuenta en [GitHub](https://github.com)
- Aplicacion de Discord creada en [Discord Developer Portal](https://discord.com/developers/applications)
- Token del bot generado

## 2. Estructura del Proyecto

```
/
├── discloud.config          # Configuracion de Discloud
├── .env                     # Variables de entorno (NO subir a GitHub)
├── .gitignore               # Archivos ignorados por git
├── requirements.txt         # Dependencias Python
├── main_discloud.py         # Entry point (bot + dashboard)
├── config.py                # Configuracion global del bot
├── core/
│   └── bot.py               # Clase principal del bot
├── cogs/                    # Modulos del bot (comandos slash)
│   ├── moderation.py
│   ├── automod.py
│   ├── reputation.py
│   ├── tickets.py
│   ├── utility.py
│   └── ...
├── dashboard/               # Servidor web Flask
│   ├── app.py               # Rutas y API
│   ├── config.py            # Config del dashboard
│   ├── templates/           # HTML templates
│   │   ├── base.html
│   │   ├── login.html
│   │   ├── dashboard.html
│   │   ├── servers.html
│   │   └── config.html
│   └── static/
│       ├── css/style.css
│       └── js/app.js
├── database/                # Modelos de base de datos
│   └── db.py
└── utils/                   # Utilidades
    ├── embeds.py
    ├── paginator.py
    └── logger.py
```

## 3. Archivo discloud.config

El archivo `discloud.config` le dice a Discloud como ejecutar tu aplicacion:

```ini
ID=programadores
NAME=programadores
MAIN=main_discloud.py
TYPE=site
MEMORY=1024
VERSION=3.11
AUTORESTART=true
```

### Explicacion de campos:

| Campo | Valor | Explicacion |
|-------|-------|-------------|
| `ID` | `programadores` | Nombre del subdominio (debe coincidir con el registrado) |
| `NAME` | `programadores` | Nombre interno de la app |
| `MAIN` | `main_discloud.py` | Archivo que inicia la aplicacion |
| `TYPE` | `site` | `site` para apps web, `python` para bots puros |
| `MEMORY` | `1024` | RAM en MB (min 512, recomendado 1024) |
| `VERSION` | `3.11` | Version de Python |
| `AUTORESTART` | `true` | Reinicio automatico si falla |

### Importante:
- `TYPE=site` es necesario para que el subdominio funcione
- El `MAIN` debe iniciar tanto el bot como el dashboard
- `MEMORY=1024` es suficiente, si ves errores de memoria subi a 2048

## 4. Variables de Entorno

Discloud permite configurar variables de entorno desde el dashboard web en:
**Aplicaciones > [tu app] > Variables de Entorno**

### Variables necesarias:

```
DISCORD_TOKEN=MTUwNjgxMzg2NTk0NDY4MjUzNg.xxxxx
CLIENT_ID=1506813865944682536
CLIENT_SECRET=wS7zVQbSIQA9RBLCEZahXL9dgXph-ZHZ
OWNER_ID=395719713558233088
DASHBOARD_URL=https://programadores.discloud.app
DASHBOARD_SECRET=your_strong_secret_here
```

### Explicacion:

| Variable | Donde obtenerla |
|----------|----------------|
| `DISCORD_TOKEN` | Discord Developer Portal > Bot > Token |
| `CLIENT_ID` | Discord Developer Portal > OAuth2 > Client ID |
| `CLIENT_SECRET` | Discord Developer Portal > OAuth2 > Client Secret |
| `OWNER_ID` | Tu ID de Discord (modo desarrollador > clic derecho en tu perfil) |
| `DASHBOARD_URL` | URL de tu dashboard (con subdominio) |
| `DASHBOARD_SECRET` | Clave secreta para sesiones (generala con `python3 -c "import secrets; print(secrets.token_hex(32))"`) |

### Archivo .env local (para desarrollo):

```ini
DISCORD_TOKEN=...
CLIENT_ID=...
CLIENT_SECRET=...
OWNER_ID=...
PREFIX=!
DATABASE_URL=sqlite:///data/bot.db
LOG_LEVEL=INFO
DASHBOARD_URL=https://programadores.discloud.app
DASHBOARD_SECRET=...
```

**.env NO se sube a GitHub** — esta en `.gitignore`.

## 5. Preparar el Proyecto

### requirements.txt

```txt
discord.py>=2.3.0,<3.0.0
python-dotenv>=1.0.0
aiosqlite>=0.20.0
aiohttp>=3.9.0
flask>=3.0.0
requests>=2.31.0
Pillow>=10.0.0
beautifulsoup4>=4.12.0
```

### main_discloud.py (entry point)

Este archivo inicia el bot de Discord y el dashboard Flask en hilos separados:

```python
#!/usr/bin/env python3
import asyncio
import threading
import os
import config
from core.bot import Bot
from utils.logger import setup_logger

logger = setup_logger("Main")

def run_dashboard():
    from dashboard.app import app
    port = int(os.getenv("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

async def run_bot():
    bot = Bot()
    try:
        await bot.start(config.TOKEN)
    except KeyboardInterrupt:
        await bot.close()
    except Exception as e:
        logger.error(f"Error fatal: {e}")
    finally:
        await bot.db.close()

def main():
    logger.info("Iniciando bot + dashboard")
    if not config.TOKEN:
        logger.error("Token no configurado")
        return
    t = threading.Thread(target=run_dashboard, daemon=True)
    t.start()
    try:
        asyncio.run(run_bot())
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()
```

### Puerto

Discloud asigna el puerto automaticamente via la variable `PORT`.
- Con `TYPE=site`, Discloud espera que escuches en el puerto indicado por `PORT` (tipicamente 8080)
- Dashboard y bot deben escuchar en el mismo puerto si usas `TYPE=site`

## 6. Subir a GitHub

### Configurar SSH key

```bash
ssh-keygen -t ed25519 -f ~/.ssh/github-key -N ""
```

Agrega la clave publica (`~/.ssh/github-key.pub`) en GitHub:
Settings > SSH and GPG keys > New SSH key

### Inicializar repositorio

```bash
git init
git add -A
git commit -m "Initial commit"
git remote add origin git@github.com:TU_USUARIO/TU_REPO.git
git push -u origin main
```

### .gitignore

```gitignore
.env
.venv/
__pycache__/
*.pyc
data/
*.db
logs/
.DS_Store
```

## 7. Desplegar en Discloud

### Metodo 1: Desde GitHub (recomendado)

1. Anda a [Discloud Dashboard](https://discloud.com/dashboard)
2. Clic en **Aplicaciones** > **Nueva Aplicacion**
3. Selecciona **GitHub**
4. Conecta tu cuenta de GitHub
5. Selecciona el repositorio `TU_USUARIO/TU_REPO`
6. Selecciona la rama `main`
7. Clic en **Deploy**

### Metodo 2: Subir ZIP

1. Empaqueta el proyecto: `zip -r bot.zip . -x ".venv/*" ".git/*" "__pycache__/*" "*.pyc"`
2. Anda a Discloud > Aplicaciones > Nueva Aplicacion > Upload ZIP
3. Selecciona el archivo y sube

### Despues del deploy

Discloud construye automaticamente:
1. Instala dependencias de `requirements.txt`
2. Ejecuta `main_discloud.py`
3. Expone el dashboard en el puerto especificado

### Logs

Para ver los logs de tu app:
1. Discloud > Aplicaciones > tu app > **Logs**
2. Ahi ves la salida del bot y el dashboard

### Redeploy

Para actualizar:
1. Pushea cambios a GitHub
2. Discloud > Aplicaciones > tu app > **Deploy** (o **Update**)
3. Discloud rebuild y redeploya automaticamente

## 8. Configurar Subdominio

### Registrar subdominio

1. Anda a [Discloud Dashboard](https://discloud.com/dashboard)
2. Selecciona tu app
3. Busca la seccion **Dominio** o **Subdominio** dentro de la app
4. Ingresa el nombre (ej: `programadores`)
5. Confirma — aparecera como **Disponible**

### Vincular a la app

- El `ID` en `discloud.config` debe coincidir con el nombre del subdominio
- `TYPE` debe ser `site`
- La app debe escuchar en el puerto indicado por Discloud

### DNS

El subdominio `programadores.discloud.app` apunta a Cloudflare.
Puede tardar unos minutos en propagarse.
Estado **Activo** = funcionando.
Estado **Disponible** = registrado pero sin app vinculada.

## 9. Dashboard y Login

### Requisitos para el login con Discord

1. En [Discord Developer Portal](https://discord.com/developers/applications):
   - Selecciona tu aplicacion
   - **OAuth2** > Redirects
   - Agrega: `https://programadores.discloud.app/callback`
   - Guarda

2. En Discloud > Variables de Entorno:
   - Agrega `CLIENT_ID`
   - Agrega `CLIENT_SECRET`
   - Agrega `DASHBOARD_URL`

### Como funciona el login

1. Usuario entra a `https://programadores.discloud.app`
2. Clic en "Iniciar sesion con Discord"
3. Discord pide autorizacion
4. Discord redirige a `/callback`
5. El dashboard intercambia el codigo por un token
6. El token se guarda en la sesion de Flask
7. Usuario redirigido al dashboard

### Permisos

El dashboard detecta automaticamente el nivel de permiso:
- **Owner** = dueno del servidor
- **Admin** = tiene permiso ADMINISTRATOR
- **Staff** = tiene KICK/BAN/MANAGE_GUILD/etc
- **Member** = sin permisos de administracion

## 10. Mantenimiento

### Actualizar archivos

1. Haces cambios localmente
2. `git add -A && git commit -m "descripcion" && git push`
3. En Discloud: **Deploy** (reconstruye desde GitHub)
4. Discloud rebuild y redeploya

### Sin perder datos

- La base de datos SQLite se almacena en `data/bot.db`
- Discloud usa almacenamiento EFIMERO — los datos se pierden al redeployar
- Para persistencia: migrar a PostgreSQL (Supabase, Neon, etc.)

### Migrar a PostgreSQL

1. Crea una base de datos en [Supabase](https://supabase.com) (gratis)
2. Actualiza `DATABASE_URL` en variables de entorno
3. Modifica `database/db.py` para usar `asyncpg` en vez de `aiosqlite`

### Verificar que corre

- Bot: envia `/ping` en Discord
- Dashboard: entra a `https://programadores.discloud.app`
- Logs: revisa en Discloud > Aplicaciones > Logs

### Comandos de mantenimiento

- `/ping` — verifica latencia del bot
- `/help` — lista todos los comandos
- Dashboard > General — exportar/importar configuracion

## 11. Solucion de Problemas

### Error: 502 Bad Gateway

**Causa:** La app no responde en el puerto esperado.
**Solucion:**
- Verifica que `main_discloud.py` escuche en `os.getenv("PORT", 8080)`
- Confirma `TYPE=site` en `discloud.config`
- Revisa logs en Discloud

### Error: Subdominio "Disponible" no "Activo"

**Causa:** Subdominio registrado pero no vinculado a ninguna app.
**Solucion:**
- `ID=programadores` en `discloud.config`
- `TYPE=site`
- Redeploy

### Error: DNS no resuelve

**Causa:** Propagacion DNS (puede tardar minutos).
**Solucion:** Espera 5-10 minutos. Si persiste, contacta soporte de Discloud.

### Error: "client_id is not snowflake"

**Causa:** `CLIENT_ID` no configurado en variables de entorno.
**Solucion:** Agrega `CLIENT_ID=123456789` en Discloud > Variables de Entorno.

### Error: Token invalido

**Causa:** Token expuesto y regenerado, o mal configurado.
**Solucion:** Regenera el token en Discord Developer Portal > Bot > Reset Token. Actualiza en variables de entorno.

### Error: Bot no responde comandos

- El bot tarda unos segundos en sincronizar comandos al iniciar
- Usa `/ping` para verificar
- Si no responde, revisa logs en Discloud

### Error: Base de datos corrupta

**Causa:** SQLite local se corrompio.
**Solucion:** Borra `data/bot.db` y redeploy. O migra a PostgreSQL.

## 12. Seguridad

### Tokens y credenciales

- **NUNCA** subas `.env` a GitHub
- **NUNCA** compartas el token del bot
- **NUNCA** compartas `CLIENT_SECRET`
- Usa variables de entorno en Discloud para credenciales

### Token expuesto

Si tu token se expone:

1. **URGENTE:** Regeneralo en Discord Developer Portal > Bot > Reset Token
2. Actualiza en Discloud > Variables de Entorno
3. Redeploy

### Buenas practicas

- Usa un `.env` local para desarrollo con tus credenciales
- No compartas pantallazos del dashboard con tokens visibles
- Usa `DASHBOARD_SECRET` fuerte (generalo con `secrets.token_hex(32)`)
- Mantene las dependencias actualizadas
- Revisa los logs periodicamente

### Rate Limits

- Discord API: 50 requests/segundo por endpoint
- El bot maneja rate limits automaticamente (discord.py)
- El dashboard usa cache de 60 segundos para guildas
- Evita hacer muchas requests desde el dashboard

---

## Checklist Rapido

- [ ] Token del bot generado y en variables de entorno
- [ ] CLIENT_ID y CLIENT_SECRET configurados
- [ ] Redirect URI en Discord Developer Portal
- [ ] discloud.config con ID, TYPE=site, MAIN correcto
- [ ] requirements.txt con todas las dependencias
- [ ] .gitignore creado
- [ ] Codigo en GitHub
- [ ] App creada en Discloud desde GitHub
- [ ] Subdominio registrado y vinculado
- [ ] DNS propagado (esperar minutos)
- [ ] Dashboard accesible via subdominio
- [ ] Bot responde comandos en Discord

---

*Documentacion generada para el Bot de Comunidad de Programadores*
*Hosteado en Discloud.com — Mayo 2026*
