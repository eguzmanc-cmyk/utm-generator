import streamlit as st
import os
from dotenv import load_dotenv
from auth.login import show_login_page
from core.utm_generator import generate_utm_url, validate_utm_data
from core.database import save_utm, get_all_utms, get_user_utms, delete_utm
from core.supabase_client import create_custom_client

# Cargar variables de entorno
load_dotenv()

# LOGS DE DEBUG
print("="*50)
print("[LOG] Iniciando aplicación...")
print(f"[LOG] SUPABASE_URL: {os.getenv('SUPABASE_URL')}")
print(f"[LOG] SUPABASE_KEY presente: {bool(os.getenv('SUPABASE_KEY'))}")
print("="*50)

# Configurar página
st.set_page_config(
    page_title="Generador de UTMs",
    page_icon="🔗",
    layout="wide"
)

# Logo GBM en esquina superior derecha
st.markdown("""
    <style>
    .gbm-logo-header {
        position: fixed;
        right: 3rem;
        top: 1rem;
        font-size: 2rem;
        font-weight: 900;
        color: #2c3e50;
        letter-spacing: 4px;
        z-index: 999999;
        opacity: 0.3;
        transition: opacity 0.3s ease;
    }
    .gbm-logo-header:hover {
        opacity: 0.8;
    }
    </style>
    <div class="gbm-logo-header">GBM</div>
""", unsafe_allow_html=True)

# Inicializar cliente CUSTOM de Supabase
@st.cache_resource
def init_supabase():
    return create_custom_client()

supabase = init_supabase()

# ============================================
# TEMPORAL: SKIP AUTH PARA DESARROLLO
# ============================================
SKIP_AUTH = True  # Cambia a False cuando quieras activar auth

if SKIP_AUTH:
    st.warning("⚠️ MODO DESARROLLO: Autenticación desactivada")
    # Usuario fake para desarrollo
    class FakeUser:
        id = "00000000-0000-0000-0000-000000000000"
        email = "dev@gbm.com"
    
    user = FakeUser()
    session = True  # Simular sesión activa
else:
    # Verificar sesión real
    session = supabase.auth.get_session()
    
    if not session:
        show_login_page(supabase)
        st.stop()
    else:
        user = session.user
# ============================================

# Sidebar
with st.sidebar:
    st.write(f"👤 {user.email}")
    if not SKIP_AUTH:
        if st.button("Cerrar sesión"):
            supabase.auth.sign_out()
            st.rerun()

# Tabs
tab1, tab2, tab3 = st.tabs(["📝 Crear UTM", "📊 Historial Compartido", "🗂️ Mis UTMs"])

with tab1:
    st.subheader("Crear nuevo UTM")
    
    with st.form("utm_form"):
        col1, col2 = st.columns(2)
        
        with col1:
            website_url = st.text_input("Website URL *", placeholder="https://www.example.com")
            campaign_source = st.text_input("Campaign Source *", placeholder="google, newsletter")
            campaign_medium = st.text_input("Campaign Medium *", placeholder="cpc, banner, email")
            campaign_name = st.text_input("Campaign Name", placeholder="spring_sale")
        
        with col2:
            campaign_id = st.text_input("Campaign ID", placeholder="abc123")
            campaign_term = st.text_input("Campaign Term", placeholder="paid keywords")
            campaign_content = st.text_input("Campaign Content", placeholder="differentiate ads")
            description = st.text_area("Descripción/Comentarios", placeholder="Breve descripción del uso de este UTM")
        
        submitted = st.form_submit_button("Generar UTM", type="primary")
        
        if submitted:
            errors = validate_utm_data(website_url, campaign_source, campaign_medium, 
                                      campaign_name, campaign_id)
            
            if errors:
                for error in errors:
                    st.error(f"❌ {error}")
            else:
                # Generar URL
                generated_url = generate_utm_url(
                    website_url, campaign_source, campaign_medium,
                    campaign_name, campaign_id, campaign_term, campaign_content
                )
                
                # Guardar en BD
                try:
                    save_utm(supabase, user.id, website_url, campaign_source, 
                            campaign_medium, generated_url, campaign_name, campaign_id,
                            campaign_term, campaign_content, description)
                    
                    st.success("✅ UTM creado exitosamente!")
                    st.code(generated_url, language=None)
                    
                except Exception as e:
                    st.error(f"❌ Error al guardar: {e}")
                    import traceback
                    st.code(traceback.format_exc())

with tab2:
    st.subheader("Historial Compartido")
    try:
        utms = get_all_utms(supabase)
        
        if utms:
            for utm in utms:
                with st.expander(f"🔗 {utm['campaign_source']} / {utm['campaign_medium']} - {utm.get('campaign_name', utm.get('campaign_id', 'N/A'))}"):
                    st.write(f"**URL Base:** {utm['website_url']}")
                    st.code(utm['generated_url'], language=None)
                    if utm.get('description'):
                        st.write(f"📝 {utm['description']}")
                    st.caption(f"Creado: {utm['created_at']}")
        else:
            st.info("No hay UTMs creados aún")
    except Exception as e:
        st.error(f"Error al cargar UTMs: {e}")

with tab3:
    st.subheader("Mis UTMs")
    try:
        my_utms = get_user_utms(supabase, user.id)
        
        if my_utms:
            for utm in my_utms:
                col1, col2 = st.columns([4, 1])
                with col1:
                    with st.expander(f"🔗 {utm['campaign_source']} / {utm['campaign_medium']}"):
                        st.code(utm['generated_url'], language=None)
                        if utm.get('description'):
                            st.write(f"📝 {utm['description']}")
                with col2:
                    if st.button("🗑️", key=f"delete_{utm['id']}"):
                        delete_utm(supabase, utm['id'])
                        st.rerun()
        else:
            st.info("No has creado UTMs aún")
    except Exception as e:
        st.error(f"Error: {e}")