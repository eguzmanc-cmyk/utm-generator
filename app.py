import streamlit as st
import base64
import json
import os
from dotenv import load_dotenv
from core.utm_generator import generate_utm_url, validate_utm_data, normalize_utm_param
from core.database import save_utm, get_all_utms, delete_utm, get_options, add_option, delete_option, get_all_options
from core.supabase_client import create_custom_client

load_dotenv()

st.set_page_config(
    page_title="Generador de UTMs",
    page_icon="🔗",
    layout="wide"
)

@st.cache_resource
def init_supabase():
    return create_custom_client()

supabase = init_supabase()

@st.cache_data(ttl=300)
def load_all_options(_supabase):
    """Una sola llamada a Supabase para todas las opciones. Cacheada 5 min."""
    return get_all_options(_supabase)

def get_cached_options(field_name):
    all_opts = load_all_options(supabase)
    return [r["value"] for r in all_opts.get(field_name, [])]

def invalidate_options_cache():
    load_all_options.clear()

if 'utm_success' not in st.session_state:
    st.session_state.utm_success = False
if 'last_generated_url' not in st.session_state:
    st.session_state.last_generated_url = None
if 'duplicate_utm' not in st.session_state:
    st.session_state.duplicate_utm = None

btn_color = "#16a34a" if st.session_state.utm_success else "#0d9488"

st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"], .stTextInput, .stTextArea, .stButton, .stTabs,
    .stExpander, .stMarkdown, .stCaption, h1, h2, h3, p, label {{
        font-family: 'Inter', sans-serif !important;
    }}

    /* Botón primario */
    .stButton > button[kind="primaryFormSubmit"],
    div[data-testid="stFormSubmitButton"] > button {{
        background-color: {btn_color} !important;
        border: none !important;
        color: #fff !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: background-color 0.3s ease;
    }}
    .stButton > button[kind="primaryFormSubmit"]:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {{
        background-color: {'#15803d' if st.session_state.utm_success else '#0f766e'} !important;
    }}

    /* Header */
    .custom-header {{
        background-color: #000000;
        padding: 1.2rem 2rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 2rem;
    }}
    .custom-header img {{ height: 40px; }}
    .header-subtitle {{
        color: #fff;
        font-size: 0.9rem;
        letter-spacing: 1px;
        font-family: 'Inter', sans-serif !important;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}

    button[data-testid="tooltipHoverTarget"] {{
        opacity: 1 !important;
    }}
    button[data-testid="tooltipHoverTarget"] svg {{
        stroke: #111827 !important;
        width: 16px !important;
        height: 16px !important;
    }}
    button[data-testid="tooltipHoverTarget"]:hover svg {{
        stroke: #0d9488 !important;
    }}
    </style>
""", unsafe_allow_html=True)

# Header con logo
with open("assets/Logo_GBM_2.png", "rb") as f:
    logo_b64 = base64.b64encode(f.read()).decode()

st.markdown(f"""
    <div class="custom-header">
        <img src="data:image/png;base64,{logo_b64}" alt="GBM" />
        <div class="header-subtitle">UTM Generator by Martech</div>
    </div>
""", unsafe_allow_html=True)

tab1, tab2, tab3 = st.tabs(["Crear UTM", "Historial", "⚙️ Configuración"])

# ─── TAB 1: CREAR UTM ────────────────────────────────────────────────────────
with tab1:
    st.subheader("Crear nuevo UTM")

    with st.form("utm_form"):
        template_name = st.text_input(
            "Nombre de plantilla (opcional)",
            placeholder="the-idea, the-story, newsletter-semanal…",
            help="Dale un nombre reutilizable a este UTM para encontrarlo fácil en el historial y duplicarlo."
        )

        col1, col2 = st.columns(2)

        source_opts  = get_cached_options("source")
        medium_opts  = get_cached_options("medium")
        name_opts    = get_cached_options("name")
        id_opts      = get_cached_options("id")
        term_opts    = get_cached_options("term")
        content_opts = get_cached_options("content")

        with col1:
            website_url = st.text_input(
                "Website URL *",
                placeholder="https://www.gbm.com",
                help="URL de destino del enlace. Debe incluir http:// o https://.\nEj: https://www.gbm.com/blog/the-idea"
            )
            campaign_source = st.selectbox(
                "Campaign Source *", options=source_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Plataforma o remitente del tráfico.\nEj: google · linkedin · newsletter · instagram"
            )
            campaign_medium = st.selectbox(
                "Campaign Medium *", options=medium_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Canal o tipo de tráfico.\nEj: cpc · email · organic · banner · social"
            )
            campaign_name = st.selectbox(
                "Campaign Name", options=name_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Nombre de la campaña.\nEj: lanzamiento_q1 · black_friday_2024 · the_idea_abril"
            )

        with col2:
            campaign_id = st.selectbox(
                "Campaign ID", options=id_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Identificador único para vincular con plataformas de pauta.\nEj: 12345 · gbm_q1_2025 · meta_camp_003"
            )
            campaign_term = st.selectbox(
                "Campaign Term", options=term_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Palabra clave de búsqueda pagada (SEM).\nEj: software_financiero · gbm_broker · inversion_mexico"
            )
            campaign_content = st.selectbox(
                "Campaign Content", options=content_opts,
                index=None, placeholder="Selecciona una o créala en ⚙️ Configuración",
                help="Diferencia creatividades en pruebas A/B.\nEj: banner_azul · cta_registrate · video_30s"
            )
            description = st.text_area(
                "Descripción",
                placeholder="¿Para qué es este UTM? ¿Quién lo pidió? ¿Dónde se usa?",
                help="Contexto interno — no aparece en la URL.\nEj: Banner de cierre para campaña Q1, solicitado por Valeria."
            )

        submitted = st.form_submit_button("Generar UTM", type="primary", use_container_width=True)

        if submitted:
            st.session_state.utm_success = False
            errors = validate_utm_data(website_url, campaign_source, campaign_medium,
                                       campaign_name, campaign_id)
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                generated_url = generate_utm_url(
                    website_url, campaign_source, campaign_medium,
                    campaign_name, campaign_id, campaign_term, campaign_content
                )
                try:
                    save_utm(supabase, None, website_url, campaign_source,
                             campaign_medium, generated_url, campaign_name, campaign_id,
                             campaign_term, campaign_content, description, template_name)
                    st.session_state.utm_success = True
                    st.session_state.last_generated_url = generated_url
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")

    if st.session_state.last_generated_url:
        st.success("✅ UTM generado y guardado en el historial")
        st.markdown("**Tu URL con UTM** (usa el botón 📋 para copiar):")
        st.code(st.session_state.last_generated_url, language=None)

# ─── TAB 2: HISTORIAL ────────────────────────────────────────────────────────
with tab2:
    st.subheader("Historial de UTMs")

    st.markdown("""
        <div style="background-color:#f0fdfa; border-left:4px solid #0d9488; border-radius:4px; padding:1rem 1.25rem; margin-bottom:1.25rem;">
            <p style="margin:0 0 0.4rem 0; font-weight:600; color:#0d9488; font-size:0.92rem;">¿Cómo reusar una UTM existente?</p>
            <p style="margin:0 0 0.6rem 0; color:#374151; font-size:0.88rem; line-height:1.6;">
                Abre cualquier UTM del historial → haz clic en <strong>📋 Duplicar</strong> → se abre un formulario pre-llenado con todos sus campos →
                cambia <em>solo lo que necesites</em> (por ejemplo la URL de destino o el nombre de campaña) → pulsa <strong>Guardar duplicado</strong>.
                El original queda intacto y el nuevo se añade al historial.
            </p>
            <p style="margin:0; color:#374151; font-size:0.88rem; line-height:1.6;">
                <strong>Tip:</strong> usa el campo <strong>Nombre de plantilla</strong> para etiquetar UTMs que el equipo reutiliza frecuentemente.
                Así puedes tener formatos establecidos como <code>the-idea</code> (blogpost), <code>the-story</code> (newsletter),
                <code>pauta-meta</code>, etc. — aparecen destacados en el historial y son fáciles de encontrar y duplicar.
            </p>
        </div>
    """, unsafe_allow_html=True)

    col_refresh, col_space = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Actualizar"):
            st.rerun()

    try:
        utms = get_all_utms(supabase)
        if utms:
            for utm in utms:
                if utm.get('template_name'):
                    label = f"🏷️ **{utm['template_name']}** — {utm['campaign_source']} / {utm['campaign_medium']}"
                else:
                    label = f"**{utm['campaign_source']}** / {utm['campaign_medium']}"
                    if utm.get('campaign_name'):
                        label += f" — {utm['campaign_name']}"

                with st.expander(label):
                    st.write(f"**URL Base:** {utm['website_url']}")
                    st.code(utm['generated_url'], language=None)
                    if utm.get('description'):
                        st.caption(f"📝 {utm['description']}")

                    col_date, col_dup, col_del = st.columns([3, 1, 1])
                    with col_date:
                        st.caption(f"Creado: {utm['created_at'][:19].replace('T', ' ')}")
                    with col_dup:
                        if st.button("📋 Duplicar", key=f"dup_btn_{utm['id']}"):
                            st.session_state.duplicate_utm = utm
                    with col_del:
                        if st.button("🗑️ Eliminar", key=f"del_{utm['id']}"):
                            delete_utm(supabase, utm['id'])
                            if st.session_state.duplicate_utm and st.session_state.duplicate_utm.get('id') == utm['id']:
                                st.session_state.duplicate_utm = None
                            st.rerun()

                    if st.session_state.duplicate_utm and st.session_state.duplicate_utm.get('id') == utm['id']:
                        pre = st.session_state.duplicate_utm
                        st.divider()
                        st.markdown("**Duplicar UTM** — edita solo los campos que necesites cambiar:")

                        with st.form(key=f"dup_form_{utm['id']}"):
                            dup_template = st.text_input(
                                "Nombre de plantilla (opcional)",
                                value=pre.get('template_name') or '',
                                placeholder="the-idea, the-story…"
                            )

                            dup_col1, dup_col2 = st.columns(2)
                            with dup_col1:
                                dup_url     = st.text_input("Website URL *",      value=pre.get('website_url') or '')
                                dup_source  = st.text_input("Campaign Source *",  value=pre.get('campaign_source') or '')
                                dup_medium  = st.text_input("Campaign Medium *",  value=pre.get('campaign_medium') or '')
                                dup_name    = st.text_input("Campaign Name",      value=pre.get('campaign_name') or '')
                            with dup_col2:
                                dup_id      = st.text_input("Campaign ID",        value=pre.get('campaign_id') or '')
                                dup_term    = st.text_input("Campaign Term",      value=pre.get('campaign_term') or '')
                                dup_content = st.text_input("Campaign Content",   value=pre.get('campaign_content') or '')
                                dup_desc    = st.text_area("Descripción",         value=pre.get('description') or '')

                            sub_col, cancel_col = st.columns(2)
                            with sub_col:
                                dup_submitted = st.form_submit_button("Guardar duplicado", type="primary", use_container_width=True)
                            with cancel_col:
                                dup_cancelled = st.form_submit_button("Cancelar", use_container_width=True)

                            if dup_submitted:
                                errors = validate_utm_data(dup_url, dup_source, dup_medium, dup_name, dup_id)
                                if errors:
                                    for err in errors:
                                        st.error(f"❌ {err}")
                                else:
                                    gen_url = generate_utm_url(
                                        dup_url, dup_source, dup_medium,
                                        dup_name, dup_id, dup_term, dup_content
                                    )
                                    try:
                                        save_utm(supabase, None, dup_url, dup_source, dup_medium,
                                                 gen_url, dup_name, dup_id, dup_term, dup_content,
                                                 dup_desc, dup_template)
                                        st.session_state.duplicate_utm = None
                                        st.session_state.utm_success = True
                                        st.session_state.last_generated_url = gen_url
                                        st.success("✅ UTM duplicado y guardado")
                                        st.code(gen_url, language=None)
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"❌ Error al guardar: {e}")

                            if dup_cancelled:
                                st.session_state.duplicate_utm = None
                                st.rerun()
        else:
            st.info("No hay UTMs guardados aún. ¡Crea el primero!")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")

# ─── TAB 3: CONFIGURACIÓN ────────────────────────────────────────────────────
with tab3:
    st.subheader("⚙️ Configuración de desplegables")

    st.markdown("""
        <div style="background-color:#f0fdfa; border-left:4px solid #0d9488; border-radius:4px; padding:1rem 1.25rem; margin-bottom:1.5rem;">
            <p style="margin:0 0 0.5rem 0; font-weight:600; color:#0d9488; font-size:0.95rem;">¿Para qué sirve esta sección?</p>
            <p style="margin:0 0 0.6rem 0; color:#374151; font-size:0.88rem; line-height:1.7;">
                Aquí defines qué opciones aparecen en los <strong>menús desplegables</strong> del formulario de creación de UTMs.
                Cada campo del generador (Source, Medium, Name, ID, Term y Content) tiene su propia lista de valores
                que tú y tu equipo gestionan desde aquí.
            </p>
            <p style="margin:0 0 0.4rem 0; color:#374151; font-size:0.88rem; line-height:1.7;">
                <strong>Puedes:</strong>
            </p>
            <ul style="margin:0 0 0.75rem 0; padding-left:1.2rem; color:#374151; font-size:0.88rem; line-height:1.9;">
                <li>➕ <strong>Agregar</strong> nuevas opciones que el equipo usará frecuentemente</li>
                <li>🗑️ <strong>Eliminar</strong> opciones que ya no son relevantes</li>
                <li>✏️ Los cambios son <strong>inmediatos y compartidos</strong> con todo el equipo</li>
            </ul>
            <p style="margin:0 0 0.4rem 0; font-weight:600; color:#0d9488; font-size:0.88rem;">✨ Escribe como quieras — el sistema normaliza solo</p>
            <p style="margin:0; color:#374151; font-size:0.88rem; line-height:1.7;">
                No te preocupes por mayúsculas, acentos ni espacios. El sistema convierte automáticamente cualquier valor
                al formato correcto para UTMs: <code>Mi Fuente</code> → <code>mi_fuente</code>,
                <code>Black Friday 2025</code> → <code>black_friday_2025</code>,
                <code>Lanzamiento Q1</code> → <code>lanzamiento_q1</code>.
                Si el mensaje de confirmación muestra un valor diferente al que escribiste, así es como quedó guardado.
            </p>
        </div>
    """, unsafe_allow_html=True)

    # Botón exportar JSON
    try:
        all_options_export = get_all_options(supabase)
        export_data = {}
        for fk, rows in all_options_export.items():
            export_data[fk] = [
                {"value": r["value"], "created_at": r.get("created_at", "")}
                for r in rows
            ]
        json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
        col_exp, _ = st.columns([1, 4])
        with col_exp:
            st.download_button(
                "📥 Exportar JSON",
                data=json_str,
                file_name="utm_options.json",
                mime="application/json",
                use_container_width=True
            )
    except Exception as e:
        st.error(f"Error al preparar exportación: {e}")

    FIELD_META = {
        "source":  {"label": "Campaign Source",  "icon": "🌐", "desc": "De dónde viene el tráfico. Ej: google, newsletter, instagram, linkedin"},
        "medium":  {"label": "Campaign Medium",  "icon": "📡", "desc": "Tipo de canal o formato. Ej: cpc, email, organic, banner, social"},
        "name":    {"label": "Campaign Name",    "icon": "🏷️", "desc": "Nombre de la campaña. Ej: lanzamiento_q1, black_friday, the_idea"},
        "id":      {"label": "Campaign ID",      "icon": "🔢", "desc": "Identificador único de campaña. Ej: gbm_q1_2025, meta_camp_001"},
        "term":    {"label": "Campaign Term",    "icon": "🔍", "desc": "Palabra clave SEM. Ej: software_financiero, gbm_broker, inversion_mexico"},
        "content": {"label": "Campaign Content", "icon": "🎨", "desc": "Variante de creatividad o A/B. Ej: banner_azul, cta_registrate, video_30s"},
    }

    try:
        all_options = get_all_options(supabase)

        for field_key, meta in FIELD_META.items():
            rows = all_options.get(field_key, [])
            count = len(rows)

            st.markdown(f"""
                <div style="margin-top:1.5rem; margin-bottom:0.25rem;">
                    <span style="font-size:1.1rem; font-weight:700; color:#111827;">{meta['icon']} {meta['label']}</span>
                    <span style="margin-left:0.6rem; background:#e5e7eb; color:#6b7280; font-size:0.75rem;
                                 font-weight:600; padding:2px 8px; border-radius:999px;">{count} opción{'es' if count != 1 else ''}</span>
                </div>
                <p style="margin:0 0 0.75rem 0; color:#6b7280; font-size:0.82rem;">{meta['desc']}</p>
            """, unsafe_allow_html=True)

            if rows:
                for row in rows:
                    col_val, col_date, col_del = st.columns([4, 3, 1])
                    with col_val:
                        st.markdown(f"""
                            <div style="background:#f9fafb; border:1px solid #e5e7eb; border-radius:6px;
                                        padding:0.4rem 0.75rem; font-size:0.88rem; color:#111827; font-family:'Inter',sans-serif;">
                                {row['value']}
                            </div>
                        """, unsafe_allow_html=True)
                    with col_date:
                        created = row.get('created_at', '')
                        if created:
                            st.caption(f"🕒 {created[:19].replace('T', ' ')}")
                    with col_del:
                        if st.button("🗑️", key=f"del_opt_{row['id']}", help=f"Eliminar '{row['value']}'"):
                            delete_option(supabase, row["id"])
                            invalidate_options_cache()
                            st.rerun()
            else:
                st.markdown("""
                    <div style="background:#fff7ed; border:1px dashed #fed7aa; border-radius:6px;
                                padding:0.6rem 1rem; color:#92400e; font-size:0.85rem; margin-bottom:0.5rem;">
                        Sin opciones aún — agrega la primera abajo.
                    </div>
                """, unsafe_allow_html=True)

            # Mensaje de éxito de la acción anterior (persiste tras st.rerun)
            config_msg = st.session_state.pop(f"_config_msg_{field_key}", None)
            if config_msg:
                st.success(config_msg)

            with st.form(key=f"add_opt_{field_key}"):
                col_input, col_btn = st.columns([4, 1])
                with col_input:
                    new_val = st.text_input(
                        "Nueva opción:",
                        placeholder="Escribe el valor y presiona Agregar…",
                        label_visibility="collapsed"
                    )
                with col_btn:
                    submitted_opt = st.form_submit_button("➕ Agregar", use_container_width=True)

                if submitted_opt:
                    if new_val.strip():
                        normalized = normalize_utm_param(new_val.strip())
                        if not normalized:
                            st.error(
                                f"❌ **'{new_val}'** no es un valor UTM válido tras normalizar. "
                                f"Solo se permiten letras, números, guión bajo (_) y puntos. "
                                f"Revisa lo que escribiste e inténtalo de nuevo."
                            )
                        else:
                            try:
                                add_option(supabase, field_key, normalized)
                                invalidate_options_cache()
                                if normalized != new_val.strip():
                                    st.session_state[f"_config_msg_{field_key}"] = (
                                        f"✅ **'{normalized}'** agregado a {meta['label']} "
                                        f"(normalizado desde '{new_val.strip()}')"
                                    )
                                else:
                                    st.session_state[f"_config_msg_{field_key}"] = (
                                        f"✅ **'{normalized}'** agregado a {meta['label']}"
                                    )
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ Ya existe o hubo un error: {e}")
                    else:
                        st.warning("Escribe un valor antes de agregar.")

            st.divider()

    except Exception as e:
        st.error(f"Error al cargar opciones: {e}")
