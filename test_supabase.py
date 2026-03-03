from supabase import create_client
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Obtener credenciales
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print(f"URL: {supabase_url}")
print(f"Key presente: {'Sí' if supabase_key else 'No'}")

# Crear cliente
try:
    supabase = create_client(supabase_url, supabase_key)
    print("✅ Cliente de Supabase creado exitosamente!")
    print(f"✅ Conexión establecida con: {supabase_url}")
    
except Exception as e:
    print(f"❌ Error al conectar: {e}")