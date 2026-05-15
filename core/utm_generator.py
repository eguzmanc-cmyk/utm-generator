import re
from datetime import date
from urllib.parse import quote

MAX_UTM_VALUE_LENGTH = 30

MONTH_PREFIXES = {
    1: "ENE",
    2: "FEB",
    3: "MAR",
    4: "ABR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AGO",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DIC",
}

MASTER_FIELD_LABELS = {
    "utm_zc": "UTM SC",
    "utm_name": "UTM Name",
    "utm_source": "UTM Source",
    "utm_medium": "UTM Medium",
    "utm_intent": "UTM Intent",
    "utm_business": "UTM Business",
    "utm_campaign_id": "UTM Campaign ID",
    "utm_asset_id": "UTM Asset ID",
    "utm_term": "UTM Term",
    "utm_content": "UTM Content",
}

FIELDS_WITH_MAX_30 = tuple(MASTER_FIELD_LABELS.keys())


def normalize_utm_param(text):
    """
    Normaliza parámetros UTM:
    - minúsculas
    - espacios y guiones -> _
    - sin acentos
    - solo letras, números, _, -, .
    """
    if text is None:
        return None

    text = str(text).strip()
    if not text:
        return None

    text = text.lower()
    text = text.replace(" ", "_")
    text = text.replace("-", "_")

    replacements = {
        "á": "a",
        "é": "e",
        "í": "i",
        "ó": "o",
        "ú": "u",
        "à": "a",
        "è": "e",
        "ì": "i",
        "ò": "o",
        "ù": "u",
        "ä": "a",
        "ë": "e",
        "ï": "i",
        "ö": "o",
        "ü": "u",
        "â": "a",
        "ê": "e",
        "î": "i",
        "ô": "o",
        "û": "u",
        "ñ": "n",
        "ç": "c",
    }

    for old, new in replacements.items():
        text = text.replace(old, new)

    cleaned_chars = []
    for char in text:
        if char.isalnum() or char in ["_", "-", "."]:
            cleaned_chars.append(char)

    normalized = "".join(cleaned_chars)
    normalized = re.sub(r"_+", "_", normalized).strip("_.-")

    return normalized or None


def normalize_utm_record(record):
    """Normaliza el payload del maestro UTM antes de validar o guardar."""
    normalized = dict(record)

    for field_name in FIELDS_WITH_MAX_30:
        normalized[field_name] = normalize_utm_param(record.get(field_name))

    normalized["website_url"] = (record.get("website_url") or "").strip()
    normalized["owner"] = (record.get("owner") or "").strip() or None
    normalized["description"] = (record.get("description") or "").strip() or None
    normalized["template_name"] = (record.get("template_name") or "").strip() or None
    normalized["is_seasonal"] = bool(record.get("is_seasonal"))

    if not normalized["is_seasonal"]:
        normalized["utm_zc"] = None

    return normalized


def generate_master_utm_id(existing_ids, reference_date=None):
    """Genera el utm_id con formato MMMYY-##### por mes."""
    ref = reference_date or date.today()
    prefix = f"{MONTH_PREFIXES[ref.month]}{str(ref.year)[-2:]}"
    pattern = re.compile(rf"^{prefix}-(\d{{5}})$")

    max_sequence = 0
    for utm_id in existing_ids or []:
        if not utm_id:
            continue
        match = pattern.match(str(utm_id).upper())
        if match:
            max_sequence = max(max_sequence, int(match.group(1)))

    return f"{prefix}-{max_sequence + 1:05d}"


def prepare_utm_record(record, existing_ids, reference_date=None):
    """Completa los campos automáticos del maestro UTM."""
    ref = reference_date or date.today()
    normalized = normalize_utm_record(record)
    normalized["utm_id"] = generate_master_utm_id(existing_ids, ref)
    normalized["utm_created"] = ref.isoformat()
    return normalized


def generate_utm_url(base_url, utm_record):
    """Genera la URL con UTMs estándar y campos adicionales del maestro."""
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    param_order = [
        ("utm_source", utm_record.get("utm_source")),
        ("utm_medium", utm_record.get("utm_medium")),
        ("utm_campaign", utm_record.get("utm_name")),
        ("utm_id", utm_record.get("utm_id")),
        ("utm_term", utm_record.get("utm_term")),
        ("utm_content", utm_record.get("utm_content")),
        ("utm_zc", utm_record.get("utm_zc")),
        ("utm_name", utm_record.get("utm_name")),
        ("utm_intent", utm_record.get("utm_intent")),
        ("utm_business", utm_record.get("utm_business")),
        ("utm_campaign_id", utm_record.get("utm_campaign_id")),
        ("utm_asset_id", utm_record.get("utm_asset_id")),
    ]

    params = [
        f"{key}={quote(str(value))}"
        for key, value in param_order
        if value
    ]

    separator = "&" if "?" in base_url else "?"
    return f"{base_url}{separator}{'&'.join(params)}"


def collect_utm_field_errors(record):
    """Devuelve errores por campo para mostrar validación inline."""
    normalized = normalize_utm_record(record)
    errors = {}

    required_fields = {
        "website_url": "Website URL",
        "utm_source": "UTM Source",
        "utm_medium": "UTM Medium",
        "utm_name": "UTM Name",
        "utm_intent": "UTM Intent",
        "utm_business": "UTM Business",
        "owner": "Owner",
    }

    for field_name, label in required_fields.items():
        if not normalized.get(field_name):
            errors[field_name] = f"{label} es requerido"

    if normalized.get("is_seasonal") and not normalized.get("utm_zc"):
        errors["utm_zc"] = "UTM SC es requerido cuando la campaña es de estacionalidad"

    if normalized.get("website_url") and " " in normalized["website_url"]:
        errors["website_url"] = "Website URL no puede contener espacios"

    for field_name, label in MASTER_FIELD_LABELS.items():
        raw_value = record.get(field_name)
        value = normalized.get(field_name)

        if raw_value and not value:
            errors[field_name] = f"{label} no es válido después de normalizar"
            continue

        if value and len(value) > MAX_UTM_VALUE_LENGTH:
            errors[field_name] = (
                f"{label} no puede exceder {MAX_UTM_VALUE_LENGTH} caracteres"
            )

    return errors


def validate_utm_data(record):
    """Valida los datos del maestro UTM."""
    return list(collect_utm_field_errors(record).values())
