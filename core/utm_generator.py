from urllib.parse import quote
import unicodedata

def normalize_utm_param(text):
    """
    Normaliza parámetros UTM siguiendo las reglas de la fórmula Excel:
    - Convertir a minúsculas
    - Espacios → _
    - Acentos → sin acentos (á→a, é→e, etc)
    - ñ → n
    - Caracteres especiales → eliminar o normalizar
    """
    if not text:
        return text
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Reemplazar espacios por guión bajo
    text = text.replace(" ", "_")
    
    # Reemplazar guiones por guión bajo
    text = text.replace("-", "_")
    
    # Tabla de reemplazo manual para acentos y ñ
    replacements = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'à': 'a', 'è': 'e', 'ì': 'i', 'ò': 'o', 'ù': 'u',
        'ä': 'a', 'ë': 'e', 'ï': 'i', 'ö': 'o', 'ü': 'u',
        'â': 'a', 'ê': 'e', 'î': 'i', 'ô': 'o', 'û': 'u',
        'ñ': 'n',
        'ç': 'c'
    }
    
    for old, new in replacements.items():
        text = text.replace(old, new)
    
    # Eliminar otros caracteres especiales (mantener solo letras, números y _)
    cleaned = ''
    for char in text:
        if char.isalnum() or char in ['_', '-', '.']:
            cleaned += char
    
    return cleaned


def generate_utm_url(base_url, source, medium, campaign_name=None, campaign_id=None, 
                    term=None, content=None):
    """
    Genera URL completa con parámetros UTM normalizados
    Replica el comportamiento de la fórmula de Excel
    """
    
    # Validar que la URL tenga esquema
    if not base_url.startswith(('http://', 'https://')):
        base_url = 'https://' + base_url
    
    # Normalizar todos los parámetros
    source = normalize_utm_param(source)
    medium = normalize_utm_param(medium)
    
    if campaign_name:
        campaign_name = normalize_utm_param(campaign_name)
    if campaign_id:
        campaign_id = normalize_utm_param(campaign_id)
    if term:
        term = normalize_utm_param(term)
    if content:
        content = normalize_utm_param(content)
    
    # Construir parámetros UTM (ya normalizados, ahora URL encode)
    params = []
    params.append(f"utm_source={quote(source)}")
    params.append(f"utm_medium={quote(medium)}")
    
    if campaign_name:
        params.append(f"utm_campaign={quote(campaign_name)}")
    if campaign_id:
        params.append(f"utm_id={quote(campaign_id)}")
    if term:
        params.append(f"utm_term={quote(term)}")
    if content:
        params.append(f"utm_content={quote(content)}")
    
    # Determinar separador (? o &)
    separator = '&' if '?' in base_url else '?'
    
    # Construir URL final
    utm_string = '&'.join(params)
    
    return f"{base_url}{separator}{utm_string}"


def validate_utm_data(website_url, source, medium, campaign_name, campaign_id):
    """Valida los datos del formulario UTM"""
    errors = []
    
    if not website_url:
        errors.append("Website URL es requerido")
    
    if not source:
        errors.append("Campaign Source es requerido")
    
    if not medium:
        errors.append("Campaign Medium es requerido")
    
    if not campaign_name and not campaign_id:
        errors.append("Debes proporcionar Campaign Name o Campaign ID")
    
    return errors