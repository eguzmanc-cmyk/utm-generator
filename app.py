import streamlit as st
import base64
import os
from dotenv import load_dotenv
from core.utm_generator import generate_utm_url, validate_utm_data
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

if 'utm_success' not in st.session_state:
    st.session_state.utm_success = False
if 'last_generated_url' not in st.session_state:
    st.session_state.last_generated_url = None
if 'duplicate_utm' not in st.session_state:
    st.session_state.duplicate_utm = None

# Tipografía e estilos globales
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

    /* Tooltip ? más llamativo */
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

with tab1:
    st.subheader("Crear nuevo UTM")

    with st.form("utm_form"):
        template_name = st.text_input(
            "Nombre de plantilla (opcional)",
            placeholder="the-idea, the-story, newsletter-semanal…",
            help="Dale un nombre reutilizable a este UTM para encontrarlo fácil en el historial y duplicarlo."
        )

        col1, col2 = st.columns(2)

        source_options = get_options(supabase, "source")
        medium_options = get_options(supabase, "medium")

        with col1:
            website_url = st.text_input(
                "Website URL *",
                placeholder="https://www.gbm.com",
                help="URL de destino del enlace. Debe incluir http:// o https://.\nEj: https://www.gbm.com/blog/the-idea"
            )

            source_choice = st.selectbox(
                "Campaign Source *",
                options=source_options + ["Otro..."],
                help="Plataforma o remitente del tráfico. Identifica de dónde viene el usuario.\nEj: google · linkedin · newsletter · instagram · gbm_blog"
            )
            campaign_source = st.text_input("Especifica el source:", placeholder="mi_fuente") if source_choice == "Otro..." else source_choice

            medium_choice = st.selectbox(
                "Campaign Medium *",
                options=medium_options + ["Otro..."],
                help="Canal o tipo de tráfico. Describe cómo llega el usuario.\nEj: cpc · email · organic · banner · social · referral"
            )
            campaign_medium = st.text_input("Especifica el medium:", placeholder="mi_medium") if medium_choice == "Otro..." else medium_choice

            campaign_name = st.text_input(
                "Campaign Name",
                placeholder="spring_sale",
                help="Nombre de la campaña. Usa guiones bajos en vez de espacios.\nEj: lanzamiento_q1 · black_friday_2024 · the_idea_abril"
            )

        with col2:
            campaign_id = st.text_input(
                "Campaign ID",
                placeholder="abc123",
                help="Identificador único para vincular con plataformas de pauta (Google Ads, Meta, etc.).\nEj: 12345 · gbm_q1_2025 · meta_camp_003"
            )
            campaign_term = st.text_input(
                "Campaign Term",
                placeholder="palabras clave",
                help="Palabra clave de búsqueda pagada (SEM).\nEj: software_financiero · gbm_broker · inversion_mexico"
            )
            campaign_content = st.text_input(
                "Campaign Content",
                placeholder="variante del anuncio",
                help="Diferencia creatividades en pruebas A/B o cuando hay múltiples variantes.\nEj: banner_azul · cta_registrate · video_30s"
            )
            description = st.text_area(
                "Descripción",
                placeholder="¿Para qué es este UTM? ¿Quién lo pidió? ¿Dónde se usa?",
                help="Contexto interno — no aparece en la URL. Documenta el propósito para que el equipo lo entienda.\nEj: Banner de cierre para campaña Q1, solicitado por Valeria."
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
                # Etiqueta: prioriza nombre de plantilla si existe
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

                    # Form inline de duplicado
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
                                dup_url = st.text_input("Website URL *", value=pre.get('website_url') or '')
                                dup_source = st.text_input("Campaign Source *", value=pre.get('campaign_source') or '')
                                dup_medium = st.text_input("Campaign Medium *", value=pre.get('campaign_medium') or '')
                                dup_name = st.text_input("Campaign Name", value=pre.get('campaign_name') or '')
                            with dup_col2:
                                dup_id = st.text_input("Campaign ID", value=pre.get('campaign_id') or '')
                                dup_term = st.text_input("Campaign Term", value=pre.get('campaign_term') or '')
                                dup_content = st.text_input("Campaign Content", value=pre.get('campaign_content') or '')
                                dup_desc = st.text_area("Descripción", value=pre.get('description') or '')

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

with tab3:
    st.subheader("Gestionar opciones de desplegables")
    st.caption("Agrega o elimina valores que aparecen en los selectores de Source y Medium.")

    FIELD_LABELS = {
        "source": "Campaign Source",
        "medium": "Campaign Medium",
    }

    try:
        all_options = get_all_options(supabase)

        for field_key, field_label in FIELD_LABELS.items():
            st.markdown(f"### {field_label}")
            rows = all_options.get(field_key, [])

            if rows:
                for row in rows:
                    col_val, col_del = st.columns([5, 1])
                    with col_val:
                        st.text(row["value"])
                    with col_del:
                        if st.button("🗑️", key=f"del_opt_{row['id']}"):
                            delete_option(supabase, row["id"])
                            st.rerun()
            else:
                st.caption("Sin opciones aún.")

            with st.form(key=f"add_opt_{field_key}"):
                new_val = st.text_input(f"Nueva opción para {field_label}:", placeholder="nueva_opcion")
                if st.form_submit_button("➕ Agregar", use_container_width=False):
                    if new_val.strip():
                        try:
                            add_option(supabase, field_key, new_val.strip().lower())
                            st.success(f"✅ '{new_val.strip()}' agregado a {field_label}")
                            st.rerun()
                        except Exception as e:
                            st.error(f"❌ Error: {e}")
                    else:
                        st.warning("Escribe un valor antes de agregar.")

            st.divider()

    except Exception as e:
        st.error(f"Error al cargar opciones: {e}")
