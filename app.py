import streamlit as st
import base64
import os
from dotenv import load_dotenv
from core.utm_generator import generate_utm_url, validate_utm_data
from core.database import save_utm, get_all_utms, delete_utm
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

tab0, tab1, tab2 = st.tabs(["Instrucciones", "Crear UTM", "Historial"])

with tab0:
    st.markdown("""
        <style>
        .instr-hero {
            background-color: #000;
            border-radius: 8px;
            padding: 2.5rem 3rem;
            margin-bottom: 2rem;
        }
        .instr-hero h2 {
            color: #fff;
            font-size: 1.6rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            font-family: 'Inter', sans-serif !important;
        }
        .instr-hero p {
            color: #a3a3a3;
            font-size: 1rem;
            margin: 0;
            font-family: 'Inter', sans-serif !important;
        }
        .instr-card {
            background-color: #f9fafb;
            border-left: 4px solid #0d9488;
            border-radius: 4px;
            padding: 1.2rem 1.5rem;
            margin-bottom: 1rem;
        }
        .instr-card h4 {
            color: #111827;
            font-size: 0.95rem;
            font-weight: 600;
            margin-bottom: 0.3rem;
            font-family: 'Inter', sans-serif !important;
        }
        .instr-card p {
            color: #4b5563;
            font-size: 0.88rem;
            margin: 0;
            font-family: 'Inter', sans-serif !important;
        }
        .instr-section-title {
            font-size: 1rem;
            font-weight: 600;
            color: #111827;
            margin: 1.8rem 0 1rem 0;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-family: 'Inter', sans-serif !important;
        }
        .instr-rule {
            background-color: #f3f4f6;
            border-radius: 6px;
            padding: 1rem 1.5rem;
            margin-bottom: 0.6rem;
            display: flex;
            align-items: flex-start;
            gap: 0.8rem;
        }
        .instr-rule-num {
            background-color: #0d9488;
            color: white;
            font-size: 0.75rem;
            font-weight: 700;
            border-radius: 50%;
            min-width: 22px;
            height: 22px;
            display: flex;
            align-items: center;
            justify-content: center;
            margin-top: 1px;
        }
        .instr-rule p {
            color: #374151;
            font-size: 0.88rem;
            margin: 0;
            font-family: 'Inter', sans-serif !important;
        }
        </style>

        <div class="instr-hero">
            <h2>UTM Parameter Generator</h2>
            <p>Herramienta oficial del equipo de Martech para la gestión estandarizada de parámetros UTM.</p>
        </div>

        <p style="color:#374151; font-size:0.95rem; line-height:1.7;">
            Los <strong>parámetros UTM</strong> (Urchin Tracking Module) son etiquetas que se añaden a una URL
            para identificar el origen, medio y campaña que generó cada visita a tu sitio web.
            Permiten medir con precisión el rendimiento de cada esfuerzo de marketing dentro de
            herramientas de analítica como Google Analytics o GA4.
        </p>

        <p class="instr-section-title">Parámetros disponibles</p>

        <div class="instr-card">
            <h4>utm_source — Origen</h4>
            <p>Identifica de dónde proviene el tráfico. Ejemplos: <code>google</code>, <code>newsletter</code>, <code>facebook</code></p>
        </div>
        <div class="instr-card">
            <h4>utm_medium — Medio</h4>
            <p>Describe el canal o tipo de tráfico. Ejemplos: <code>cpc</code>, <code>email</code>, <code>banner</code>, <code>organic</code></p>
        </div>
        <div class="instr-card">
            <h4>utm_campaign — Campaña</h4>
            <p>Nombre de la campaña específica. Ejemplos: <code>lanzamiento_q1</code>, <code>black_friday_2024</code></p>
        </div>
        <div class="instr-card">
            <h4>utm_id — ID de campaña</h4>
            <p>Identificador único de la campaña, útil para vincular con plataformas de pauta.</p>
        </div>
        <div class="instr-card">
            <h4>utm_term — Término</h4>
            <p>Palabra clave asociada, principalmente en campañas de búsqueda pagada (SEM).</p>
        </div>
        <div class="instr-card">
            <h4>utm_content — Contenido</h4>
            <p>Diferencia variantes de un mismo anuncio. Útil en pruebas A/B.</p>
        </div>

        <p class="instr-section-title">Buenas prácticas</p>

        <div class="instr-rule">
            <div class="instr-rule-num">1</div>
            <p><strong>Usa siempre minúsculas.</strong> Google Analytics distingue entre mayúsculas y minúsculas. <code>Google</code> y <code>google</code> se registran como fuentes distintas. Esta herramienta normaliza automáticamente.</p>
        </div>
        <div class="instr-rule">
            <div class="instr-rule-num">2</div>
            <p><strong>Sé consistente con la nomenclatura.</strong> Define y respeta una convención de nombres dentro del equipo. El historial compartido de esta herramienta te ayuda a revisar cómo se han usado anteriormente.</p>
        </div>
        <div class="instr-rule">
            <div class="instr-rule-num">3</div>
            <p><strong>No uses UTMs en tráfico interno.</strong> Etiquetar enlaces dentro de tu propio sitio sobreescribe la fuente original del visitante y distorsiona los datos.</p>
        </div>
        <div class="instr-rule">
            <div class="instr-rule-num">4</div>
            <p><strong>Documenta siempre el propósito.</strong> Utiliza el campo Descripción para registrar el contexto de cada UTM. Facilita el análisis posterior y el trabajo en equipo.</p>
        </div>
        <div class="instr-rule">
            <div class="instr-rule-num">5</div>
            <p><strong>Evita información sensible en los parámetros.</strong> Los UTMs son visibles en la URL y en los reportes de analítica. No incluyas datos confidenciales.</p>
        </div>
    """, unsafe_allow_html=True)

with tab1:
    st.subheader("Crear nuevo UTM")

    with st.form("utm_form"):
        col1, col2 = st.columns(2)

        with col1:
            website_url = st.text_input("Website URL *", placeholder="https://www.gbm.com")
            campaign_source = st.text_input("Campaign Source *", placeholder="google, newsletter, facebook")
            campaign_medium = st.text_input("Campaign Medium *", placeholder="cpc, email, banner")
            campaign_name = st.text_input("Campaign Name", placeholder="spring_sale")

        with col2:
            campaign_id = st.text_input("Campaign ID", placeholder="abc123")
            campaign_term = st.text_input("Campaign Term", placeholder="palabras clave")
            campaign_content = st.text_input("Campaign Content", placeholder="variante del anuncio")
            description = st.text_area("Descripción", placeholder="¿Para qué es este UTM?")

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
                             campaign_term, campaign_content, description)
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

    col_refresh, col_space = st.columns([1, 5])
    with col_refresh:
        if st.button("🔄 Actualizar"):
            st.rerun()

    try:
        utms = get_all_utms(supabase)
        if utms:
            for utm in utms:
                label = f"**{utm['campaign_source']}** / {utm['campaign_medium']}"
                if utm.get('campaign_name'):
                    label += f" — {utm['campaign_name']}"
                with st.expander(label):
                    st.write(f"**URL Base:** {utm['website_url']}")
                    st.code(utm['generated_url'], language=None)
                    if utm.get('description'):
                        st.caption(f"📝 {utm['description']}")
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.caption(f"Creado: {utm['created_at'][:19].replace('T', ' ')}")
                    with col2:
                        if st.button("🗑️ Eliminar", key=f"del_{utm['id']}"):
                            delete_utm(supabase, utm['id'])
                            st.rerun()
        else:
            st.info("No hay UTMs guardados aún. ¡Crea el primero!")
    except Exception as e:
        st.error(f"Error al cargar historial: {e}")
