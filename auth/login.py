import streamlit as st
import traceback

def show_login_page(supabase):
    """Muestra la página de login - Diseño limpio"""
    
    # CSS personalizado (igual que antes)
    st.markdown("""
        <style>
        .block-container {
            padding-top: 0rem !important;
            padding-bottom: 3rem !important;
        }
        
        .custom-header {
            background-color: #2c3e50;
            padding: 1.5rem 3rem;
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin: 0;
            width: 100%;
        }
        
        .logo {
            font-size: 2rem;
            font-weight: 900;
            color: #fff;
            letter-spacing: 4px;
        }
        
        .header-subtitle {
            color: #fff;
            font-size: 0.95rem;
            font-weight: 400;
            letter-spacing: 1px;
        }
        
        .stApp {
            background-color: #e8edf2;
        }
        
        .login-container {
            max-width: 500px;
            margin: 4rem auto;
            padding: 3rem 3rem;
            background: #fff;
            border-radius: 8px;
            box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
        }
        
        .login-title {
            font-size: 2rem;
            font-weight: 600;
            color: #2c3e50;
            margin-bottom: 0.8rem;
            text-align: center;
        }
        
        .login-subtitle {
            font-size: 1rem;
            color: #64748b;
            margin-bottom: 2.5rem;
            text-align: center;
        }
        
        .stButton > button {
            background-color: #2c3e50 !important;
            color: #fff !important;
            border: none !important;
            font-weight: 600 !important;
            padding: 0.85rem 1.5rem !important;
            border-radius: 6px !important;
            font-size: 1rem !important;
        }
        
        .stButton > button:hover {
            background-color: #34495e !important;
        }
        
        .stTextInput > div > div > input {
            border: 1px solid #d1d5db !important;
            border-radius: 6px !important;
            font-size: 1rem !important;
            padding: 0.85rem !important;
        }
        
        .login-footer {
            text-align: center;
            color: #64748b;
            font-size: 0.9rem;
            margin-top: 2rem;
        }
        
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stDeployButton {display: none;}
        
        div[data-testid="stVerticalBlock"] > div:first-child {
            gap: 0rem !important;
        }
        </style>
    """, unsafe_allow_html=True)
    
    # Header
    st.markdown("""
        <div class="custom-header">
            <div class="logo">GBM</div>
            <div class="header-subtitle">UTM Generator by Martech</div>
        </div>
    """, unsafe_allow_html=True)
    
    # Login container
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    
    st.markdown('<h2 class="login-title">Iniciar sesión</h2>', unsafe_allow_html=True)
    st.markdown('<p class="login-subtitle">Ingresa tu email corporativo para acceder</p>', unsafe_allow_html=True)
    
    email = st.text_input(
        "Email",
        placeholder="tu@gbm.com",
        label_visibility="collapsed"
    )
    
    st.markdown("<div style='margin: 1.5rem 0;'></div>", unsafe_allow_html=True)
    
    if st.button("Enviar Magic Link 🔐", type="primary", use_container_width=True):
        if email:
            try:
                print(f"[LOG] Intentando enviar magic link a: {email}")
                print(f"[LOG] Usando cliente custom con requests")
                
                # Usar el cliente custom
                response = supabase.auth.sign_in_with_otp({"email": email})
                
                print(f"[LOG] Respuesta: {response}")
                st.success("✓ Magic Link enviado correctamente")
                st.info("📧 Revisa tu email. El link expira en 1 hora")
                
            except Exception as e:
                print(f"[ERROR] {type(e).__name__}: {str(e)}")
                traceback.print_exc()
                
                st.error(f"✗ Error al enviar email: {str(e)}")
                
                with st.expander("Ver detalles del error"):
                    st.code(traceback.format_exc())
        else:
            st.warning("⚠ Por favor ingresa tu email")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Footer
    st.markdown(
        '<p class="login-footer">¿Problemas para acceder? Contacta a soporte</p>',
        unsafe_allow_html=True
    )