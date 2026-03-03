# Guía de Despliegue — UTM Generator by Martech

## Plataforma objetivo

**Streamlit Community Cloud** (gratuito)
- URL: https://share.streamlit.io
- Repositorio fuente: GitHub (ya configurado)
- Límite free tier: 1 app activa por cuenta

---

## Pre-requisitos

- [x] Repositorio en GitHub con el código (`utm-generator`)
- [x] Cuenta en Streamlit Cloud (puede ser la misma cuenta de GitHub)
- [x] Proyecto en Supabase con la tabla `utms` configurada
- [x] `requirements.txt` en la raíz del repo

---

## Paso 1 — Ajuste de código: Secrets

En local usamos `.env` con `python-dotenv`. En Streamlit Cloud **no existe el `.env`** — las credenciales se gestionan desde el dashboard y se leen con `st.secrets`.

### Cambio requerido en `core/supabase_client.py`

Reemplazar en la función `create_custom_client()`:

```python
# ANTES (solo funciona en local)
def create_custom_client():
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return CustomSupabaseClient(url, key)
```

```python
# DESPUÉS (funciona en local Y en Streamlit Cloud)
def create_custom_client():
    try:
        import streamlit as st
        url = st.secrets["SUPABASE_URL"]
        key = st.secrets["SUPABASE_KEY"]
    except Exception:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_KEY")
    return CustomSupabaseClient(url, key)
```

---

## Paso 2 — Configurar Secrets en Streamlit Cloud

Una vez creada la app en Streamlit Cloud:

1. Ir a **App settings → Secrets**
2. Pegar el siguiente bloque (con los valores reales):

```toml
SUPABASE_URL = "https://xxxxxxxxxxxxxxxxxxx.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

> Los valores los encuentras en tu proyecto de Supabase en:
> **Project Settings → API → Project URL y anon public key**

---

## Paso 3 — Desplegar en Streamlit Cloud

1. Ir a https://share.streamlit.io
2. Click en **New app**
3. Configurar:
   - **Repository**: `eguzmanc-cmyk/utm-generator`
   - **Branch**: `main`
   - **Main file path**: `app.py`
4. Click **Deploy**

El despliegue tarda entre 1 y 3 minutos. Streamlit instala automáticamente las dependencias de `requirements.txt`.

---

## Paso 4 — Verificar en Supabase

Confirmar que estas configuraciones estén activas en el proyecto de Supabase:

| Configuración | Estado requerido |
|---|---|
| RLS en tabla `utms` | Desactivado (`DISABLE ROW LEVEL SECURITY`) |
| Columna `created_by` | Permite `NULL` |
| `created_at` / `updated_at` | Con valor por defecto `now()` |

---

## Limitaciones conocidas

### Streamlit Cloud free tier
- **1 app activa** por cuenta
- La app **se duerme** tras 7 días de inactividad (se reactiva al entrar)
- Los recursos son compartidos — puede haber latencia en horas pico
- No soporta variables de entorno del sistema (solo `st.secrets`)

### Supabase free tier
- **500 MB** de base de datos
- **2 GB** de transferencia mensual
- El proyecto **se pausa** tras 7 días sin actividad en el free tier
  - Solución: entrar al dashboard de Supabase periódicamente o upgradar
- La clave `anon` es pública por naturaleza — cualquiera con acceso a la URL de la app puede leer/escribir UTMs si conoce el endpoint de la API

### Seguridad a considerar
- Sin autenticación, cualquier persona con la URL puede crear y eliminar UTMs
- Recomendación futura: agregar al menos autenticación básica o restringir el acceso por dominio si la herramienta es solo para uso interno

---

## Post-despliegue

Una vez desplegada, la URL pública será algo como:
```
https://utm-generator-xxxx.streamlit.app
```

Compartir esa URL con el equipo de Martech. No requiere instalación ni configuración adicional por parte del usuario.

---

## Actualizar la app tras cambios

Cualquier `git push` a `main` dispara un redespliegue automático en Streamlit Cloud.

```bash
git add .
git commit -m "descripción del cambio"
git push origin main
```

Streamlit Cloud detecta el push y redespliega en ~1 minuto.
