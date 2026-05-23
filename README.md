# 🤖 Teen Bot — Bot Profesional de Discord

Bot premium para Discord con **180+ comandos**, dashboard web, sistema de moderación, economía, niveles, reputación, tickets, automod, anti-nuke, bienvenidas, logs, verificación, reaction roles, giveaways, sugerencias, reportes y más.

## ✨ Características

| Sistema | Comandos principales |
|---|---|
| 🛡️ **Moderación** | ban, unban, softban, kick, timeout, mute, warn, purge, slowmode, lock, lockdown, nick, role, voice, massban, hackban, clean |
| 🤖 **Automod** | Anti-spam, flood, links, invites, mentions, caps, emoji, zalgo, raid, alt, blacklist, whitelist |
| ☢️ **Anti-Nuke** | Protección contra borrado/creación masiva de canales, roles, bans, kicks. Sistema de confianza |
| ⭐ **Reputación** | give, remove, set, profile, leaderboard, history, reset, cooldown |
| 📊 **Niveles** | XP por mensajes y voz, rank, leaderboard, levelroles, levelconfig, admin commands |
| 💰 **Economía** | balance, daily, weekly, work, crime, pay, rob, deposit, withdraw, shop, buy, sell, inventory, slots, coinflip, roulette |
| 🎫 **Tickets** | Panel, crear, cerrar, reclamar, transcript, logs, stats |
| 👋 **Bienvenidas** | Mensajes personalizados, autoroles, despedidas, test |
| 📝 **Logs** | 12 módulos: mensajes, miembros, moderación, canales, roles, voz, etc. |
| 🛠️ **Utilidad** | help, ping, botinfo, serverinfo, userinfo, avatar, banner, roleinfo, channelinfo, poll, afk, remind, color, qr, timestamp, define |
| 🎮 **Diversión** | 8ball, meme, joke, cat, dog, hug, kiss, ship, rate, rps, trivia, choose, reverse |
| 💡 **Sugerencias** | Crear, aceptar, rechazar, comentar, votos |
| 📢 **Reportes** | Reportar usuarios con canal dedicado |
| 🛂 **Verificación** | Botón + captcha opcional, rol al verificar |
| 🎭 **Reaction Roles** | Crear, eliminar, listar. Button roles con panel |
| 🎉 **Giveaways** | Crear, terminar, reroll, listar, participación con botón |
| ⚙️ **Config** | view, prefix, language, reset, modules |

## 📋 Requisitos

- **Python 3.11+**
- **discord.py 2.3+**
- Token de bot de Discord
- Cliente OAuth2 para el dashboard (opcional)

## 🚀 Instalación Local

### 1. Clonar
```bash
git clone https://github.com/tuusuario/teen-bot.git
cd teen-bot
```

### 2. Entorno virtual
```bash
python3 -m venv .venv
source .venv/bin/activate  # Linux/macOS
# .venv\Scripts\activate   # Windows
```

### 3. Dependencias
```bash
pip install -r requirements.txt
```

### 4. Configurar .env
Copia `.env.example` a `.env` y edítalo:

```env
DISCORD_TOKEN=tu_token_aqui
CLIENT_ID=tu_client_id
CLIENT_SECRET=tu_client_secret  # Solo para dashboard
OWNER_ID=tu_id_de_discord
PREFIX=!
DASHBOARD_URL=http://localhost:5000
DASHBOARD_SECRET=clave_secreta_segura
```

### 5. Obtener Token
1. Ve a [Discord Developer Portal](https://discord.com/developers/applications)
2. Nueva aplicación → Bot → Reset Token
3. Copia el token a `DISCORD_TOKEN`

### 6. Activar Intents
En el Developer Portal, sección Bot:
- ✅ PRESENCE INTENT
- ✅ SERVER MEMBERS INTENT  
- ✅ MESSAGE CONTENT INTENT

### 7. Invitar el Bot
```
https://discord.com/oauth2/authorize?client_id=TU_CLIENT_ID&permissions=8&scope=bot%20applications.commands
```

### 8. Iniciar
```bash
python main.py
```

## 🌐 Dashboard Web

### Configurar OAuth2
1. En el Developer Portal → OAuth2 → General
2. Añadir redirect: `http://localhost:5000/callback`
3. Copiar Client ID y Client Secret al `.env`

### Iniciar Dashboard (opcional)
El dashboard es opcional. El bot funciona sin él.
```bash
python dashboard/app.py
```
Abrir `http://localhost:5000`

## ☁️ Desplegar en Discloud

### Opción 1: Subida directa
El archivo `discloud.config` ya está configurado:
```
NAME=Teen Bot
MAIN=main.py
TYPE=python
MEMORY=512
VERSION=3.11
```

1. Comprime la carpeta del bot en `.zip`
2. Súbela a [Discloud](https://discloud.com)
3. Configura las variables de entorno en el panel de Discloud

### Opción 2: Variables en Discloud
En el panel de Discloud, añade:
- `DISCORD_TOKEN`: tu token
- `OWNER_ID`: tu ID
- `CLIENT_ID`: opcional
- `CLIENT_SECRET`: opcional

## 📁 Estructura

```
Teen Bot/
├── main.py                 # Entry point
├── config.py               # Configuración global
├── .env                    # Variables de entorno
├── requirements.txt        # Dependencias
├── discloud.config         # Config para Discloud
├── README.md               # Este archivo
├── core/
│   └── bot.py              # Clase Bot personalizada
├── cogs/                   # Todos los módulos
│   ├── moderation.py       # 45+ comandos de moderación
│   ├── automod.py          # Automod completo
│   ├── antinuke.py         # Anti-nuke
│   ├── reputation.py       # Reputación
│   ├── levels.py           # Niveles y XP
│   ├── economy.py          # Economía y tienda
│   ├── tickets.py          # Tickets
│   ├── welcome.py          # Bienvenidas/autoroles
│   ├── logs.py             # Sistema de logs
│   ├── utility.py          # Utilidad
│   ├── fun.py              # Diversión
│   ├── suggestions.py      # Sugerencias
│   ├── reports.py          # Reportes
│   ├── verification.py     # Verificación
│   ├── reaction_roles.py   # Reaction/button roles
│   ├── giveaways.py        # Giveaways
│   ├── config_cog.py       # Configuración
│   └── events.py           # Eventos y errores
├── database/
│   ├── db.py               # Conexión SQLite
│   └── models.py           # Esquemas SQL
├── utils/
│   ├── embeds.py           # Embeds premium
│   ├── logger.py           # Logging
│   ├── checks.py           # Permisos
│   ├── helpers.py          # Funciones auxiliares
│   └── paginator.py        # Paginación
├── dashboard/              # Web dashboard
│   ├── app.py              # Flask app
│   ├── config.py           # Config dashboard
│   ├── templates/          # HTML
│   └── static/             # CSS/JS
├── data/                   # SQLite DB
├── logs/                   # Logs del bot
└── assets/                 # Recursos
```

## 🔧 Solución de Problemas

**Error: PrivilegedIntentsRequired**
→ Activa los 3 intents en el Developer Portal.

**Error: 403 Forbidden**
→ El bot no tiene permisos. Asegúrate de que su rol esté arriba.

**Error: Token inválido**
→ Regenera el token en el Developer Portal y actualiza `.env`.

**El dashboard no carga**
→ Verifica `CLIENT_ID`, `CLIENT_SECRET` y `DASHBOARD_URL` en `.env`.

**Los comandos slash no aparecen**
→ Pueden tardar hasta 1 hora. Usa `/help` para verificar.

## 📄 Licencia

MIT — Hecho con ❤️ para la comunidad de Discord
