import base64
import json

import streamlit as st
import streamlit.components.v1 as components
from dotenv import load_dotenv

from core.database import (
    add_option,
    delete_option,
    delete_utm,
    get_all_options,
    get_all_utms,
    get_existing_utm_ids,
    save_utm,
)
from core.supabase_client import create_custom_client
from core.utm_generator import (
    MAX_UTM_VALUE_LENGTH,
    collect_utm_field_errors,
    generate_utm_url,
    normalize_utm_param,
    prepare_utm_record,
    validate_utm_data,
)

load_dotenv()

st.set_page_config(
    page_title="UTM Master Builder",
    page_icon="🔗",
    layout="wide",
)


@st.cache_resource
def init_supabase():
    return create_custom_client()


def is_missing_config_value(value):
    if value is None:
        return True
    if isinstance(value, str) and value.strip().lower() in {"", "none", "null"}:
        return True
    return False


def has_valid_supabase_client(client):
    if client is None:
        return False

    url = getattr(client, "supabase_url", None)
    key = getattr(client, "supabase_key", None)
    return not is_missing_config_value(url) and not is_missing_config_value(key)


supabase = None
supabase_error = None
supabase_connected = False

try:
    supabase = init_supabase()
    if not has_valid_supabase_client(supabase):
        init_supabase.clear()
        raise ValueError(
            "Faltan credenciales válidas de Supabase. Reinicia con `SUPABASE_URL` y "
            "`SUPABASE_KEY`, o usa el modo local sin conexión."
        )
    supabase_connected = True
except Exception as error:
    supabase_error = str(error)
    supabase = None


@st.cache_data(ttl=300)
def load_all_options(_supabase):
    """Una sola llamada a Supabase para todas las opciones. Cacheada 5 min."""
    if _supabase is None:
        return {}
    return get_all_options(_supabase)


def get_cached_options(field_name):
    if not supabase_connected:
        return []
    all_opts = load_all_options(supabase)
    return [row["value"] for row in all_opts.get(field_name, [])]


def invalidate_options_cache():
    load_all_options.clear()


def first_value(row, *keys):
    for key in keys:
        value = row.get(key)
        if value not in (None, ""):
            return value
    return None


def row_value(row, field_name):
    field_map = {
        "utm_id": ("utm_id",),
        "utm_zc": ("utm_zc", "utm_sc"),
        "utm_name": ("utm_name", "campaign_name"),
        "utm_source": ("utm_source", "campaign_source"),
        "utm_medium": ("utm_medium", "campaign_medium"),
        "utm_intent": ("utm_intent",),
        "utm_business": ("utm_business",),
        "utm_campaign_id": ("utm_campaign_id", "campaign_id"),
        "utm_asset_id": ("utm_asset_id",),
        "utm_term": ("utm_term", "campaign_term"),
        "utm_content": ("utm_content", "campaign_content"),
        "utm_created": ("utm_created", "created_at"),
        "owner": ("owner",),
        "description": ("description",),
        "template_name": ("template_name",),
        "generated_url": ("generated_url",),
        "website_url": ("website_url",),
    }
    return first_value(row, *field_map.get(field_name, (field_name,)))


def is_row_seasonal(row):
    if row.get("is_seasonal") is not None:
        return bool(row.get("is_seasonal"))
    return bool(row_value(row, "utm_zc"))


def format_datetime_label(value):
    if not value:
        return "-"
    if isinstance(value, str):
        return value[:19].replace("T", " ")
    return str(value)


def get_option_list(field_name, current_value=None):
    options = get_cached_options(field_name)
    if current_value and current_value not in options:
        options = [current_value] + options
    return options


def get_option_index(options, value):
    try:
        return options.index(value) if value else None
    except ValueError:
        return None


def build_record_from_row(row):
    return {
        "template_name": row_value(row, "template_name") or "",
        "website_url": row_value(row, "website_url") or "",
        "utm_source": row_value(row, "utm_source"),
        "utm_medium": row_value(row, "utm_medium"),
        "utm_name": row_value(row, "utm_name") or "",
        "utm_intent": row_value(row, "utm_intent"),
        "utm_business": row_value(row, "utm_business"),
        "utm_campaign_id": row_value(row, "utm_campaign_id") or "",
        "utm_asset_id": row_value(row, "utm_asset_id") or "",
        "utm_term": row_value(row, "utm_term") or "",
        "utm_content": row_value(row, "utm_content") or "",
        "utm_zc": row_value(row, "utm_zc") or "",
        "owner": row_value(row, "owner") or "",
        "description": row_value(row, "description") or "",
        "is_seasonal": is_row_seasonal(row),
    }


def save_error_message(error):
    message = str(error)
    lowered = message.lower()
    if "column" in lowered or "schema cache" in lowered:
        return (
            "La tabla `utms` en Supabase todavía no tiene el esquema del maestro. "
            "Aplica `utm_master_migration.sql` y vuelve a intentar."
        )
    return f"Error al guardar: {error}"


def render_catalog_input(
    label,
    field_name,
    options,
    help_text,
    placeholder,
    value=None,
    key=None,
):
    if supabase_connected and options:
        return st.selectbox(
            label,
            options=options,
            index=get_option_index(options, value),
            placeholder=placeholder,
            help=help_text,
            key=key,
        )

    local_help = help_text
    if supabase_connected and not options:
        local_help += (
            "\n\nTodavía no hay catálogo cargado para este campo. "
            "Puedes escribir un valor temporal o agregarlo en Catálogos."
        )
    else:
        local_help += "\n\nModo local sin Supabase: escribe el valor manualmente."

    return st.text_input(
        label,
        value=value or "",
        placeholder=placeholder.replace(
            "Selecciona una o créala en Catálogos",
            "Escribe un valor",
        ),
        max_chars=MAX_UTM_VALUE_LENGTH,
        help=local_help,
        key=key,
    )


CREATE_WIDGET_KEYS = {
    "template_name": "create_template_name",
    "website_url": "create_website_url",
    "owner": "create_owner",
    "description": "create_description",
    "utm_zc": "create_utm_zc",
    "utm_source": "create_utm_source",
    "utm_medium": "create_utm_medium",
    "utm_name": "create_utm_name",
    "utm_intent": "create_utm_intent",
    "utm_business": "create_utm_business",
    "utm_campaign_id": "create_utm_campaign_id",
    "utm_asset_id": "create_utm_asset_id",
    "utm_term": "create_utm_term",
    "utm_content": "create_utm_content",
}

CREATE_STEP_FIELDS = {
    1: ["website_url", "owner"],
    2: [
        "utm_zc",
        "utm_source",
        "utm_medium",
        "utm_name",
        "utm_intent",
        "utm_business",
    ],
    3: ["utm_campaign_id", "utm_asset_id", "utm_term", "utm_content"],
}


def build_create_record_from_state():
    is_seasonal = st.session_state.get("create_is_seasonal", "No") == "Sí"
    return {
        "template_name": st.session_state.get(CREATE_WIDGET_KEYS["template_name"], ""),
        "website_url": st.session_state.get(CREATE_WIDGET_KEYS["website_url"], ""),
        "utm_source": st.session_state.get(CREATE_WIDGET_KEYS["utm_source"]),
        "utm_medium": st.session_state.get(CREATE_WIDGET_KEYS["utm_medium"]),
        "utm_name": st.session_state.get(CREATE_WIDGET_KEYS["utm_name"], ""),
        "utm_intent": st.session_state.get(CREATE_WIDGET_KEYS["utm_intent"]),
        "utm_business": st.session_state.get(CREATE_WIDGET_KEYS["utm_business"]),
        "utm_campaign_id": st.session_state.get(
            CREATE_WIDGET_KEYS["utm_campaign_id"], ""
        ),
        "utm_asset_id": st.session_state.get(CREATE_WIDGET_KEYS["utm_asset_id"], ""),
        "utm_term": st.session_state.get(CREATE_WIDGET_KEYS["utm_term"], ""),
        "utm_content": st.session_state.get(CREATE_WIDGET_KEYS["utm_content"], ""),
        "utm_zc": st.session_state.get(CREATE_WIDGET_KEYS["utm_zc"]) if is_seasonal else None,
        "owner": st.session_state.get(CREATE_WIDGET_KEYS["owner"], ""),
        "description": st.session_state.get(CREATE_WIDGET_KEYS["description"], ""),
        "is_seasonal": is_seasonal,
    }


def render_invalid_widget_styles(widget_keys):
    if not widget_keys:
        return

    selectors = []
    label_selectors = []
    for key in widget_keys:
        base = f".st-key-{key}"
        selectors.extend(
            [
                f"{base} [data-testid='stTextInputRootElement']",
                f"{base} [data-testid='stTextAreaRootElement']",
                f"{base} div[data-baseweb='select'] > div",
                f"{base} [role='radiogroup']",
            ]
        )
        label_selectors.extend(
            [
                f"{base} label[data-testid='stWidgetLabel']",
                f"{base} label[data-testid='stWidgetLabel'] p",
            ]
        )

    st.markdown(
        f"""
        <style>
        {", ".join(selectors)} {{
            border-color: rgba(220, 38, 38, 0.42) !important;
            box-shadow: 0 0 0 1px rgba(220, 38, 38, 0.35),
                        0 0 0 4px rgba(220, 38, 38, 0.08) !important;
        }}

        {", ".join(label_selectors)} {{
            color: #dc2626 !important;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def render_field_error(field_name, field_errors):
    message = field_errors.get(field_name)
    if not message:
        return
    st.markdown(
        f'<div class="field-error-text">{message}</div>',
        unsafe_allow_html=True,
    )


def render_copy_url_button(url, label="Copiar UTM"):
    components.html(
        f"""
        <div class="copy-utm-shell">
            <button id="copy-utm-btn" type="button">{label}</button>
            <div id="copy-utm-status" class="copy-utm-status" aria-live="polite"></div>
        </div>
        <script>
        const textToCopy = {json.dumps(url)};
        const button = document.getElementById("copy-utm-btn");
        const status = document.getElementById("copy-utm-status");

        const syncFrameSize = () => {{
            if (window.frameElement) {{
                window.frameElement.style.width = "100%";
                window.frameElement.style.border = "none";
                window.frameElement.style.height = "88px";
            }}
        }};

        const fallbackCopy = (value) => {{
            const textarea = document.createElement("textarea");
            textarea.value = value;
            textarea.setAttribute("readonly", "");
            textarea.style.position = "absolute";
            textarea.style.left = "-9999px";
            document.body.appendChild(textarea);
            textarea.select();
            textarea.setSelectionRange(0, value.length);
            document.execCommand("copy");
            document.body.removeChild(textarea);
        }};

        syncFrameSize();
        window.addEventListener("load", syncFrameSize);

        button.addEventListener("click", async () => {{
            try {{
                if (navigator.clipboard && window.isSecureContext) {{
                    await navigator.clipboard.writeText(textToCopy);
                }} else {{
                    fallbackCopy(textToCopy);
                }}
                status.textContent = "UTM copiada al portapapeles";
                status.style.color = "#0f766e";
            }} catch (error) {{
                status.textContent = "No se pudo copiar automáticamente";
                status.style.color = "#dc2626";
            }}
        }});
        </script>
        <style>
        html, body {{
            margin: 0;
            padding: 0;
            background: transparent;
            font-family: 'Manrope', sans-serif;
        }}

        .copy-utm-shell {{
            width: 100%;
            padding-top: 0.2rem;
        }}

        #copy-utm-btn {{
            width: 100%;
            min-height: 3.2rem;
            border-radius: 18px;
            border: none;
            background: #111827;
            color: #ffffff;
            font-size: 1rem;
            font-weight: 800;
            letter-spacing: 0.01em;
            cursor: pointer;
            box-shadow: 0 16px 32px rgba(17, 24, 39, 0.14);
            transition: transform 0.18s ease, background-color 0.18s ease;
        }}

        #copy-utm-btn:hover {{
            transform: translateY(-1px);
            background: #0b1220;
        }}

        .copy-utm-status {{
            min-height: 1.1rem;
            margin-top: 0.45rem;
            font-size: 0.82rem;
            font-weight: 700;
        }}
        </style>
        """,
        height=88,
    )


def render_section_intro(step, title, copy):
    st.markdown(
        f"""
        <div class="section-step-title">PASO {step} - {title}</div>
        <div class="section-title">{title}</div>
        <div class="section-copy">{copy}</div>
        """,
        unsafe_allow_html=True,
    )


def render_metric_card(title, value, caption):
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{title}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-caption">{caption}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_status_card(title, body, tone="default"):
    st.markdown(
        f"""
        <div class="status-card status-{tone}">
            <div class="status-title">{title}</div>
            <div class="status-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_inline_banner(title, body, tone="default"):
    st.markdown(
        f"""
        <div class="inline-banner inline-{tone}">
            <div class="inline-banner-title">{title}</div>
            <div class="inline-banner-body">{body}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def format_history_label(row):
    utm_id = row_value(row, "utm_id") or "sin_id"
    name = row_value(row, "utm_name") or "Sin nombre"
    source = row_value(row, "utm_source") or "-"
    medium = row_value(row, "utm_medium") or "-"
    template_name = row_value(row, "template_name")
    prefix = f"🏷️ {template_name} · " if template_name else ""
    return f"{prefix}`{utm_id}` · {name} · {source} / {medium}"


def history_matches_query(row, query):
    haystack = " ".join(
        str(value or "")
        for value in [
            row_value(row, "utm_id"),
            row_value(row, "utm_name"),
            row_value(row, "utm_source"),
            row_value(row, "utm_medium"),
            row_value(row, "utm_intent"),
            row_value(row, "utm_business"),
            row_value(row, "owner"),
            row_value(row, "template_name"),
            row_value(row, "utm_zc"),
        ]
    ).lower()
    return query.lower() in haystack


if "utm_success" not in st.session_state:
    st.session_state.utm_success = False
if "last_generated_url" not in st.session_state:
    st.session_state.last_generated_url = None
if "last_generated_record" not in st.session_state:
    st.session_state.last_generated_record = None
if "last_generated_saved" not in st.session_state:
    st.session_state.last_generated_saved = None
if "duplicate_utm" not in st.session_state:
    st.session_state.duplicate_utm = None
if "create_show_validation" not in st.session_state:
    st.session_state.create_show_validation = False

st.markdown(
    f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=Manrope:wght@400;500;600;700;800&display=swap');

    :root {{
        --bg-top: #f4f1e8;
        --bg-bottom: #f7fbf9;
        --paper: rgba(255, 255, 255, 0.82);
        --paper-strong: #ffffff;
        --ink: #121826;
        --muted: #5b6472;
        --line: rgba(18, 24, 38, 0.10);
        --brand: #0f766e;
        --brand-soft: #d9f2ed;
        --accent: #c79f5c;
        --shadow: 0 24px 70px rgba(18, 24, 38, 0.08);
        --radius-xl: 28px;
        --radius-lg: 22px;
        --radius-md: 16px;
    }}

    html, body, [class*="css"], .stTextInput, .stTextArea, .stButton, .stTabs,
    .stExpander, .stMarkdown, .stCaption, h1, h2, h3, p, label {{
        font-family: 'Manrope', sans-serif !important;
        color: var(--ink);
    }}

    .stApp {{
        background:
            radial-gradient(circle at top left, rgba(199, 159, 92, 0.12), transparent 30%),
            linear-gradient(180deg, var(--bg-top) 0%, #fbfbf8 34%, var(--bg-bottom) 100%);
    }}

    .block-container {{
        padding-top: 1.4rem;
        padding-bottom: 2.8rem;
    }}

    .custom-header {{
        background:
            linear-gradient(135deg, rgba(17, 24, 39, 0.97), rgba(17, 24, 39, 0.90));
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: var(--radius-xl);
        padding: 1.2rem 1.5rem;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 1.4rem;
        box-shadow: var(--shadow);
    }}

    .custom-header img {{
        height: 38px;
    }}

    .header-subtitle {{
        color: rgba(255, 255, 255, 0.82);
        font-size: 0.92rem;
        letter-spacing: 0.06em;
        text-transform: uppercase;
        font-weight: 700;
    }}

    .status-card {{
        background: rgba(255,255,255,0.72);
        border: 1px solid var(--line);
        border-radius: 16px;
        padding: 0.85rem 0.95rem;
        box-shadow: 0 8px 22px rgba(18, 24, 38, 0.04);
        margin-bottom: 0.7rem;
    }}

    .status-default {{
        border-left: 3px solid #1f2937;
    }}

    .status-success {{
        border-left: 3px solid var(--brand);
    }}

    .status-warning {{
        border-left: 3px solid var(--accent);
    }}

    .status-title {{
        font-size: 0.88rem;
        font-weight: 800;
        margin-bottom: 0.22rem;
    }}

    .status-body {{
        color: var(--muted);
        font-size: 0.83rem;
        line-height: 1.55;
    }}

    .inline-banner {{
        background: rgba(255,255,255,0.72);
        border: 1px solid rgba(18, 24, 38, 0.08);
        border-radius: 16px;
        padding: 0.8rem 0.95rem;
        margin-bottom: 0.7rem;
    }}

    .inline-default {{
        border-left: 3px solid #111827;
    }}

    .inline-success {{
        border-left: 3px solid var(--brand);
    }}

    .inline-warning {{
        border-left: 3px solid var(--accent);
    }}

    .inline-banner-title {{
        font-size: 0.86rem;
        font-weight: 800;
        margin-bottom: 0.2rem;
    }}

    .inline-banner-body {{
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.55;
    }}

    .section-step-title {{
        display: inline-block;
        margin-top: 0;
        margin-bottom: 0.55rem;
        color: var(--brand);
        font-size: 0.9rem;
        font-weight: 800;
        letter-spacing: 0.05em;
        text-transform: uppercase;
    }}

    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background: #ffffff;
        border: 1px solid rgba(18, 24, 38, 0.08) !important;
        border-radius: 28px !important;
        padding: 1.25rem 1.35rem 1.15rem 1.35rem;
        box-shadow: 0 16px 36px rgba(18, 24, 38, 0.05);
        margin: 1rem 0 1.15rem 0;
    }}

    div[data-testid="stLayoutWrapper"] {{
        background: #ffffff !important;
    }}

    .section-title {{
        display: none;
    }}

    .section-copy {{
        color: var(--muted);
        font-size: 0.96rem;
        line-height: 1.7;
        margin-bottom: 0;
    }}

    .field-error-text {{
        color: #dc2626;
        font-size: 0.82rem;
        font-weight: 700;
        line-height: 1.45;
        margin-top: 0.35rem;
        margin-bottom: 0.15rem;
    }}

    .metric-card {{
        background: rgba(255,255,255,0.82);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 0.9rem 0.95rem 0.88rem 0.95rem;
        box-shadow: 0 10px 24px rgba(18, 24, 38, 0.05);
        margin-bottom: 0.8rem;
    }}

    .metric-label {{
        color: var(--muted);
        font-size: 0.8rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        margin-bottom: 0.45rem;
    }}

    .metric-value {{
        font-size: 1.42rem;
        font-weight: 800;
        line-height: 1.05;
        margin-bottom: 0.18rem;
    }}

    .metric-caption {{
        color: var(--muted);
        font-size: 0.82rem;
        line-height: 1.5;
    }}

    .result-shell {{
        background: linear-gradient(135deg, rgba(15,118,110,0.10), rgba(255,255,255,0.84));
        border: 1px solid rgba(15,118,110,0.14);
        border-radius: var(--radius-lg);
        padding: 1.15rem 1.2rem;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }}

    .result-title {{
        font-weight: 800;
        font-size: 1rem;
        margin-bottom: 0.25rem;
    }}

    .result-copy {{
        color: var(--muted);
        font-size: 0.88rem;
        line-height: 1.6;
        margin: 0;
    }}

    div[data-testid="stForm"] {{
        background: transparent;
        border: none;
        border-radius: 0;
        padding: 0;
        box-shadow: none;
        backdrop-filter: none;
    }}

    div[data-testid="stExpander"] {{
        background: rgba(255,255,255,0.86);
        border: 1px solid var(--line);
        border-radius: 20px;
        box-shadow: 0 14px 36px rgba(18, 24, 38, 0.06);
    }}

    .stTextInput label,
    .stTextArea label,
    .stSelectbox label,
    .stRadio label,
    .stCheckbox label {{
        font-size: 1rem !important;
        font-weight: 700 !important;
    }}

    .stTextInput input,
    .stTextArea textarea {{
        font-size: 1rem !important;
        padding-top: 0.8rem !important;
        padding-bottom: 0.8rem !important;
    }}

    .stTextArea textarea {{
        line-height: 1.55 !important;
    }}

    div[data-baseweb="select"] > div,
    div[data-baseweb="select"] span {{
        font-size: 0.98rem !important;
    }}

    .stCaption {{
        font-size: 0.88rem !important;
    }}

    [data-testid="stCodeBlock"] pre,
    code {{
        font-family: 'IBM Plex Mono', monospace !important;
        font-size: 0.85rem !important;
    }}

    .stTabs [data-baseweb="tab-list"] {{
        gap: 0.45rem;
        background: rgba(255,255,255,0.60);
        border: 1px solid var(--line);
        border-radius: 18px;
        padding: 0.35rem;
    }}

    .stTabs [data-baseweb="tab"] {{
        border-radius: 14px;
        padding: 0.65rem 1rem;
        font-weight: 700;
        color: #111827 !important;
    }}

    .stButton > button,
    div[data-testid="stFormSubmitButton"] > button {{
        background-color: #111827 !important;
        border: none !important;
        color: #fff !important;
        font-weight: 800 !important;
        font-size: 1rem !important;
        min-height: 3.2rem !important;
        border-radius: 18px !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0.8rem 1.15rem !important;
        letter-spacing: 0.01em;
        transition: transform 0.18s ease, box-shadow 0.18s ease, background-color 0.18s ease;
        box-shadow: 0 16px 32px rgba(17, 24, 39, 0.14);
    }}

    .stButton > button *,
    div[data-testid="stFormSubmitButton"] > button * {{
        color: #ffffff !important;
        fill: #ffffff !important;
        opacity: 1 !important;
        font-weight: 800 !important;
    }}

    .stButton > button:hover,
    div[data-testid="stFormSubmitButton"] > button:hover {{
        transform: translateY(-1px);
        background-color: #0b1220 !important;
    }}

    .stTabs [aria-selected="true"] {{
        background: #111827 !important;
        color: #ffffff !important;
    }}

    .stTabs [data-baseweb="tab"] *,
    .stTabs [data-baseweb="tab"] span,
    .stTabs [data-baseweb="tab"] p,
    .stTabs [data-baseweb="tab"] div {{
        color: #111827 !important;
    }}

    .stTabs [aria-selected="true"] *,
    .stTabs [aria-selected="true"] span,
    .stTabs [aria-selected="true"] p,
    .stTabs [aria-selected="true"] div {{
        color: #ffffff !important;
    }}

    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    header {{visibility: hidden;}}
    .stDeployButton {{display: none;}}

    button[data-testid="tooltipHoverTarget"] {{
        opacity: 1 !important;
    }}

    button[data-testid="tooltipHoverTarget"] svg {{
        stroke: #111827 !important;
        width: 16px !important;
        height: 16px !important;
    }}

    button[data-testid="tooltipHoverTarget"]:hover svg {{
        stroke: var(--brand) !important;
    }}

    @media (max-width: 980px) {{
        .block-container {{
            padding-left: 0.85rem;
            padding-right: 0.85rem;
        }}

        .custom-header {{
            gap: 1rem;
            flex-direction: column;
            align-items: flex-start;
        }}

        div[data-testid="stVerticalBlockBorderWrapper"] {{
            padding: 1rem 1rem 0.95rem 1rem;
            border-radius: 22px !important;
        }}

        [data-testid="column"] {{
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }}

        .stTabs [data-baseweb="tab-list"] {{
            flex-wrap: wrap;
        }}
    }}
    </style>
    """,
    unsafe_allow_html=True,
)

with open("assets/Logo_GBM_2.png", "rb") as file_handle:
    logo_b64 = base64.b64encode(file_handle.read()).decode()

st.markdown(
    f"""
    <div class="custom-header">
        <img src="data:image/png;base64,{logo_b64}" alt="GBM" />
        <div class="header-subtitle">UTM Master Builder by Martech</div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab_create, tab_history, tab_config = st.tabs(
    ["Crear Maestro", "Historial", "Catálogos"]
)


with tab_create:
    st.subheader("UTM Master Builder")
    st.caption("Un flujo más limpio para capturar campañas con contexto, consistencia y trazabilidad.")

    source_opts = get_cached_options("source")
    medium_opts = get_cached_options("medium")
    intent_opts = get_cached_options("intent")
    business_opts = get_cached_options("business")
    zc_opts = get_cached_options("zc")

    create_state_record = build_create_record_from_state()
    create_field_errors = (
        collect_utm_field_errors(create_state_record)
        if st.session_state.create_show_validation
        else {}
    )
    render_invalid_widget_styles(
        [
            CREATE_WIDGET_KEYS[field_name]
            for field_name in create_field_errors
            if field_name in CREATE_WIDGET_KEYS
        ]
    )

    with st.container(border=True):
        render_section_intro(
            1,
            "Contexto",
            "URL, responsable y contexto operativo para que cualquiera entienda el registro rápido.",
        )

        base_col1, base_col2 = st.columns(2, gap="large")
        with base_col1:
            template_name = st.text_input(
                "Nombre de plantilla",
                placeholder="newsletter_q2, pauta_meta_bf, webinar_advisory…",
                help="Etiqueta reusable para encontrar este patrón más adelante en el historial.",
                key=CREATE_WIDGET_KEYS["template_name"],
            )
            website_url = st.text_input(
                "URL destino *",
                placeholder="https://www.gbm.com",
                help="URL final a la que quieres enviar tráfico. Si no escribes esquema, el sistema usará `https://`.",
                key=CREATE_WIDGET_KEYS["website_url"],
            )
            render_field_error("website_url", create_field_errors)
        with base_col2:
            owner = st.text_input(
                "Responsable *",
                placeholder="Nico",
                help="Persona responsable de esta campaña o regla.",
                key=CREATE_WIDGET_KEYS["owner"],
            )
            render_field_error("owner", create_field_errors)
            description = st.text_area(
                "Contexto / descripción",
                placeholder="Qué se está lanzando, para quién, y qué lógica especial debería recordar el equipo.",
                help="No viaja en la URL. Sirve para documentar decisiones y contexto operativo.",
                height=130,
                key=CREATE_WIDGET_KEYS["description"],
            )

    with st.container(border=True):
        render_section_intro(
            2,
            "Clasificación",
            "Source, medium, intent y business para mantener consistencia en reporting.",
        )

        type_col1, type_col2 = st.columns(2, gap="large")
        with type_col1:
            st.markdown("**Tipo de campaña**")
            is_seasonal_answer = st.radio(
                "¿Esta campaña es de estacionalidad?",
                options=["No", "Sí"],
                horizontal=True,
                help="Si eliges Sí, aparecerá el campo `utm_sc` y será obligatorio.",
                key="create_is_seasonal",
            )
        with type_col2:
            utm_zc = None
            if is_seasonal_answer == "Sí":
                utm_zc = render_catalog_input(
                    "Clave estacional (utm_sc) *",
                    "zc",
                    zc_opts,
                    "Identificador de estacionalidad. Ej: buen_fin, mundial, ppr.",
                    "Selecciona una o créala en Catálogos",
                    key=CREATE_WIDGET_KEYS["utm_zc"],
                )
                render_field_error("utm_zc", create_field_errors)

        class_col1, class_col2 = st.columns(2, gap="large")
        with class_col1:
            utm_source = render_catalog_input(
                "Plataforma / origen (utm_source) *",
                "source",
                source_opts,
                "De dónde viene el tráfico. Ej: meta, google, newsletter.",
                "Selecciona una o créala en Catálogos",
                key=CREATE_WIDGET_KEYS["utm_source"],
            )
            render_field_error("utm_source", create_field_errors)
            utm_medium = render_catalog_input(
                "Canal (utm_medium) *",
                "medium",
                medium_opts,
                "Canal macro de adquisición. Ej: paid_social, email, paid_search.",
                "Selecciona una o créala en Catálogos",
                key=CREATE_WIDGET_KEYS["utm_medium"],
            )
            render_field_error("utm_medium", create_field_errors)
            utm_name = st.text_input(
                "Nombre de campaña (utm_name) *",
                placeholder="advisory_leads_q2",
                max_chars=MAX_UTM_VALUE_LENGTH,
                help="También se enviará como `utm_campaign` para mantener compatibilidad estándar.",
                key=CREATE_WIDGET_KEYS["utm_name"],
            )
            render_field_error("utm_name", create_field_errors)
        with class_col2:
            utm_intent = render_catalog_input(
                "Objetivo (utm_intent) *",
                "intent",
                intent_opts,
                "Etapa del funnel. Ej: awareness, consideration, leads, conversion.",
                "Selecciona una o créala en Catálogos",
                key=CREATE_WIDGET_KEYS["utm_intent"],
            )
            render_field_error("utm_intent", create_field_errors)
            utm_business = render_catalog_input(
                "Línea de negocio (utm_business) *",
                "business",
                business_opts,
                "Producto o unidad de negocio. Ej: advisory, wealth, trading.",
                "Selecciona una o créala en Catálogos",
                key=CREATE_WIDGET_KEYS["utm_business"],
            )
            render_field_error("utm_business", create_field_errors)

    with st.container(border=True):
        render_section_intro(
            3,
            "Activación",
            "IDs técnicos, creativo y una URL lista para compartir o guardar.",
        )

        tech_col1, tech_col2 = st.columns(2, gap="large")
        with tech_col1:
            utm_campaign_id = st.text_input(
                "ID de campaña (utm_campaign_id)",
                placeholder="111",
                max_chars=MAX_UTM_VALUE_LENGTH,
                help="ID de la campaña en Meta, Google Ads o la plataforma de origen.",
                key=CREATE_WIDGET_KEYS["utm_campaign_id"],
            )
            render_field_error("utm_campaign_id", create_field_errors)
            utm_asset_id = st.text_input(
                "ID de asset (utm_asset_id)",
                placeholder="55555",
                max_chars=MAX_UTM_VALUE_LENGTH,
                help="Identificador del asset creativo, anuncio o pieza.",
                key=CREATE_WIDGET_KEYS["utm_asset_id"],
            )
            render_field_error("utm_asset_id", create_field_errors)
        with tech_col2:
            utm_term = st.text_input(
                "Keyword / targeting (utm_term)",
                placeholder="credito",
                max_chars=MAX_UTM_VALUE_LENGTH,
                help="Keyword o criterio principal de segmentación.",
                key=CREATE_WIDGET_KEYS["utm_term"],
            )
            render_field_error("utm_term", create_field_errors)
            utm_content = st.text_input(
                "Creativo / variante (utm_content)",
                placeholder="video",
                max_chars=MAX_UTM_VALUE_LENGTH,
                help="Formato, concepto o variación creativa.",
                key=CREATE_WIDGET_KEYS["utm_content"],
            )
            render_field_error("utm_content", create_field_errors)

    raw_record = {
        "template_name": template_name,
        "website_url": website_url,
        "utm_source": utm_source,
        "utm_medium": utm_medium,
        "utm_name": utm_name,
        "utm_intent": utm_intent,
        "utm_business": utm_business,
        "utm_campaign_id": utm_campaign_id,
        "utm_asset_id": utm_asset_id,
        "utm_term": utm_term,
        "utm_content": utm_content,
        "utm_zc": utm_zc,
        "owner": owner,
        "description": description,
        "is_seasonal": is_seasonal_answer == "Sí",
    }

    submit_col, _ = st.columns([0.38, 0.62], gap="large")
    with submit_col:
        submitted = st.button(
            "Generar y guardar utm",
            type="primary",
            use_container_width=True,
        )

    preview_existing_ids = get_existing_utm_ids(supabase) if supabase_connected else []

    if submitted:
        st.session_state.utm_success = False
        st.session_state.create_show_validation = True
        errors = validate_utm_data(raw_record)
        if errors:
            st.rerun()
        else:
            st.session_state.create_show_validation = False
            utm_record = prepare_utm_record(
                raw_record,
                preview_existing_ids,
            )
            utm_record["generated_url"] = generate_utm_url(
                utm_record["website_url"],
                utm_record,
            )

            if supabase_connected:
                try:
                    save_utm(supabase, None, utm_record)
                    st.session_state.utm_success = True
                    st.session_state.last_generated_url = utm_record["generated_url"]
                    st.session_state.last_generated_record = utm_record
                    st.session_state.last_generated_saved = True
                    st.rerun()
                except Exception as error:
                    st.error(f"❌ {save_error_message(error)}")
            else:
                st.session_state.utm_success = True
                st.session_state.last_generated_url = utm_record["generated_url"]
                st.session_state.last_generated_record = utm_record
                st.session_state.last_generated_saved = False
                st.rerun()

    if st.session_state.last_generated_url:
        saved = bool(st.session_state.last_generated_saved)
        record = st.session_state.last_generated_record or {}
        result_title = (
            "Maestro UTM generado y guardado"
            if saved
            else "Maestro UTM generado en modo local"
        )
        result_copy = (
            "La configuración ya quedó registrada en el historial compartido."
            if saved
            else "La URL está lista para revisión, pero no se guardó porque no hay conexión con Supabase."
        )

        st.markdown(
            f"""
            <div class="result-shell">
                <div class="result-title">{result_title}</div>
                <p class="result-copy">{result_copy}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

        result_col1, result_col2, result_col3 = st.columns(3)
        with result_col1:
            render_metric_card("UTM ID", record.get("utm_id", "-"), "Asignado automáticamente")
        with result_col2:
            render_metric_card(
                "Fecha",
                record.get("utm_created", "-"),
                "Valor generado por el sistema",
            )
        with result_col3:
            render_metric_card(
                "Estacionalidad",
                "Sí" if record.get("is_seasonal") else "No",
                record.get("utm_zc") or "Sin clave estacional",
            )

        st.markdown("#### URL generada")
        st.code(st.session_state.last_generated_url, language=None)
        copy_col, _ = st.columns([0.38, 0.62], gap="large")
        with copy_col:
            render_copy_url_button(st.session_state.last_generated_url)


with tab_history:
    st.subheader("Historial de maestros UTM")
    st.caption("Revisa, filtra y reutiliza configuraciones sin tener que reconstruirlas desde cero.")

    if not supabase_connected:
        render_status_card(
            "Historial no disponible en modo local",
            "Conecta Supabase para consultar campañas guardadas, duplicarlas o limpiar registros que ya no uses.",
            tone="warning",
        )
    else:
        try:
            utms = get_all_utms(supabase)
        except Exception as error:
            utms = []
            st.error(f"Error al cargar historial: {error}")

        total_records = len(utms)
        total_templates = sum(1 for row in utms if row_value(row, "template_name"))
        total_seasonal = sum(1 for row in utms if is_row_seasonal(row))

        history_metrics = st.columns(3)
        with history_metrics[0]:
            render_metric_card("Registros", total_records, "Total de campañas guardadas")
        with history_metrics[1]:
            render_metric_card("Plantillas", total_templates, "Patrones reutilizables")
        with history_metrics[2]:
            render_metric_card("Estacionales", total_seasonal, "Con `utm_sc` activo")

        filter_col1, filter_col2, filter_col3, filter_col4 = st.columns([2, 1, 1, 1])
        with filter_col1:
            search_query = st.text_input(
                "Buscar",
                placeholder="Busca por ID, nombre, source, owner, plantilla o clave estacional…",
            )
        with filter_col2:
            only_seasonal = st.checkbox("Solo estacionales")
        with filter_col3:
            only_templates = st.checkbox("Solo plantillas")
        with filter_col4:
            if st.button("Actualizar", use_container_width=True):
                st.rerun()

        filtered_utms = []
        for row in utms:
            if search_query and not history_matches_query(row, search_query):
                continue
            if only_seasonal and not is_row_seasonal(row):
                continue
            if only_templates and not row_value(row, "template_name"):
                continue
            filtered_utms.append(row)

        if not filtered_utms:
            render_status_card(
                "No encontramos resultados",
                "Prueba con otro término de búsqueda o desactiva alguno de los filtros.",
            )

        for utm in filtered_utms:
            with st.expander(format_history_label(utm)):
                top_col1, top_col2 = st.columns([1.25, 1])
                with top_col1:
                    st.markdown("**URL destino**")
                    st.write(row_value(utm, "website_url"))
                    st.markdown("**URL generada**")
                    st.code(row_value(utm, "generated_url"), language=None)
                with top_col2:
                    st.markdown("**Plantilla**")
                    st.write(row_value(utm, "template_name") or "-")
                    st.markdown("**Responsable**")
                    st.write(row_value(utm, "owner") or "-")
                    st.markdown("**Descripción**")
                    st.write(row_value(utm, "description") or "-")

                detail_col1, detail_col2, detail_col3 = st.columns(3)
                with detail_col1:
                    render_metric_card(
                        "Clasificación",
                        row_value(utm, "utm_name") or "-",
                        f"{row_value(utm, 'utm_source') or '-'} / {row_value(utm, 'utm_medium') or '-'}",
                    )
                with detail_col2:
                    render_metric_card(
                        "Objetivo",
                        row_value(utm, "utm_intent") or "-",
                        row_value(utm, "utm_business") or "-",
                    )
                with detail_col3:
                    render_metric_card(
                        "Estacionalidad",
                        "Sí" if is_row_seasonal(utm) else "No",
                        row_value(utm, "utm_zc") or "Sin clave",
                    )

                st.caption(
                    " | ".join(
                        [
                            f"utm_id: {row_value(utm, 'utm_id') or '-'}",
                            f"utm_created: {format_datetime_label(row_value(utm, 'utm_created'))}",
                            f"campaign_id: {row_value(utm, 'utm_campaign_id') or '-'}",
                            f"asset_id: {row_value(utm, 'utm_asset_id') or '-'}",
                            f"term: {row_value(utm, 'utm_term') or '-'}",
                            f"content: {row_value(utm, 'utm_content') or '-'}",
                        ]
                    )
                )

                action_col1, action_col2, action_col3 = st.columns([2, 1, 1])
                with action_col1:
                    st.caption(
                        f"Creado: {format_datetime_label(first_value(utm, 'created_at', 'utm_created'))}"
                    )
                with action_col2:
                    if st.button("Duplicar", key=f"dup_btn_{utm['id']}", use_container_width=True):
                        st.session_state.duplicate_utm = utm
                with action_col3:
                    if st.button("Eliminar", key=f"del_{utm['id']}", use_container_width=True):
                        delete_utm(supabase, utm["id"])
                        if (
                            st.session_state.duplicate_utm
                            and st.session_state.duplicate_utm.get("id") == utm["id"]
                        ):
                            st.session_state.duplicate_utm = None
                        st.rerun()

                if (
                    st.session_state.duplicate_utm
                    and st.session_state.duplicate_utm.get("id") == utm["id"]
                ):
                    pre = build_record_from_row(st.session_state.duplicate_utm)
                    dup_seasonal_key = f"dup_is_seasonal_{utm['id']}"
                    if dup_seasonal_key not in st.session_state:
                        st.session_state[dup_seasonal_key] = (
                            "Sí" if pre["is_seasonal"] else "No"
                        )

                    st.divider()
                    st.markdown("### Duplicar configuración")
                    dup_is_seasonal_answer = st.radio(
                        "¿Esta campaña es de estacionalidad?",
                        options=["No", "Sí"],
                        horizontal=True,
                        key=dup_seasonal_key,
                    )

                    with st.form(key=f"dup_form_{utm['id']}"):
                        render_section_intro(
                            1,
                            "Ajusta lo necesario",
                            "El duplicado conserva los datos del original, pero generará un `utm_id` nuevo al guardar.",
                        )

                        dup_col1, dup_col2 = st.columns(2)
                        with dup_col1:
                            dup_template = st.text_input(
                                "Nombre de plantilla",
                                value=pre["template_name"],
                            )
                            dup_url = st.text_input(
                                "URL destino *",
                                value=pre["website_url"],
                            )
                            dup_source = render_catalog_input(
                                "Plataforma / origen (utm_source) *",
                                "source",
                                get_option_list("source", pre["utm_source"]),
                                "De dónde viene el tráfico.",
                                "Selecciona una o créala en Catálogos",
                                value=pre["utm_source"],
                                key=f"dup_source_{utm['id']}",
                            )
                            dup_medium = render_catalog_input(
                                "Canal (utm_medium) *",
                                "medium",
                                get_option_list("medium", pre["utm_medium"]),
                                "Canal macro de adquisición.",
                                "Selecciona una o créala en Catálogos",
                                value=pre["utm_medium"],
                                key=f"dup_medium_{utm['id']}",
                            )
                            dup_name = st.text_input(
                                "Nombre de campaña (utm_name) *",
                                value=pre["utm_name"],
                                max_chars=MAX_UTM_VALUE_LENGTH,
                            )
                        with dup_col2:
                            dup_owner = st.text_input(
                                "Responsable *",
                                value=pre["owner"],
                            )
                            dup_intent = render_catalog_input(
                                "Objetivo (utm_intent) *",
                                "intent",
                                get_option_list("intent", pre["utm_intent"]),
                                "Etapa del funnel.",
                                "Selecciona una o créala en Catálogos",
                                value=pre["utm_intent"],
                                key=f"dup_intent_{utm['id']}",
                            )
                            dup_business = render_catalog_input(
                                "Línea de negocio (utm_business) *",
                                "business",
                                get_option_list("business", pre["utm_business"]),
                                "Producto o unidad de negocio.",
                                "Selecciona una o créala en Catálogos",
                                value=pre["utm_business"],
                                key=f"dup_business_{utm['id']}",
                            )
                            dup_zc = None
                            if dup_is_seasonal_answer == "Sí":
                                dup_zc = render_catalog_input(
                                    "Clave estacional (utm_sc) *",
                                    "zc",
                                    get_option_list("zc", pre["utm_zc"]),
                                    "Identificador de estacionalidad.",
                                    "Selecciona una o créala en Catálogos",
                                    value=pre["utm_zc"],
                                    key=f"dup_zc_{utm['id']}",
                                )
                            dup_desc = st.text_area(
                                "Contexto / descripción",
                                value=pre["description"],
                            )

                        render_section_intro(
                            2,
                            "IDs técnicos",
                            "Solo cambia estos campos si la plataforma, el asset o el targeting también cambian.",
                        )

                        tech_col1, tech_col2 = st.columns(2)
                        with tech_col1:
                            dup_campaign_id = st.text_input(
                                "ID de campaña (utm_campaign_id)",
                                value=pre["utm_campaign_id"],
                                max_chars=MAX_UTM_VALUE_LENGTH,
                            )
                            dup_asset_id = st.text_input(
                                "ID de asset (utm_asset_id)",
                                value=pre["utm_asset_id"],
                                max_chars=MAX_UTM_VALUE_LENGTH,
                            )
                        with tech_col2:
                            dup_term = st.text_input(
                                "Keyword / targeting (utm_term)",
                                value=pre["utm_term"],
                                max_chars=MAX_UTM_VALUE_LENGTH,
                            )
                            dup_content = st.text_input(
                                "Creativo / variante (utm_content)",
                                value=pre["utm_content"],
                                max_chars=MAX_UTM_VALUE_LENGTH,
                            )

                        submit_dup_col, cancel_dup_col = st.columns(2)
                        with submit_dup_col:
                            dup_submitted = st.form_submit_button(
                                "Guardar duplicado",
                                type="primary",
                                use_container_width=True,
                            )
                        with cancel_dup_col:
                            dup_cancelled = st.form_submit_button(
                                "Cancelar",
                                use_container_width=True,
                            )

                        if dup_submitted:
                            raw_record = {
                                "template_name": dup_template,
                                "website_url": dup_url,
                                "utm_source": dup_source,
                                "utm_medium": dup_medium,
                                "utm_name": dup_name,
                                "utm_intent": dup_intent,
                                "utm_business": dup_business,
                                "utm_campaign_id": dup_campaign_id,
                                "utm_asset_id": dup_asset_id,
                                "utm_term": dup_term,
                                "utm_content": dup_content,
                                "utm_zc": dup_zc,
                                "owner": dup_owner,
                                "description": dup_desc,
                                "is_seasonal": dup_is_seasonal_answer == "Sí",
                            }

                            errors = validate_utm_data(raw_record)
                            if errors:
                                for error in errors:
                                    st.error(f"❌ {error}")
                            else:
                                dup_record = prepare_utm_record(
                                    raw_record,
                                    get_existing_utm_ids(supabase),
                                )
                                dup_record["generated_url"] = generate_utm_url(
                                    dup_record["website_url"],
                                    dup_record,
                                )
                                try:
                                    save_utm(supabase, None, dup_record)
                                    st.session_state.duplicate_utm = None
                                    st.session_state.utm_success = True
                                    st.session_state.last_generated_url = dup_record[
                                        "generated_url"
                                    ]
                                    st.session_state.last_generated_record = dup_record
                                    st.session_state.last_generated_saved = True
                                    st.session_state.pop(dup_seasonal_key, None)
                                    st.rerun()
                                except Exception as error:
                                    st.error(f"❌ {save_error_message(error)}")

                        if dup_cancelled:
                            st.session_state.duplicate_utm = None
                            st.session_state.pop(dup_seasonal_key, None)
                            st.rerun()


with tab_config:
    st.subheader("Catálogos controlados")
    st.caption("Gestiona las opciones compartidas que aparecen en el formulario principal.")

    if not supabase_connected:
        render_status_card(
            "Catálogos no disponibles en modo local",
            "Conecta Supabase para administrar listas compartidas de `source`, `medium`, `intent`, `business` y `sc`.",
            tone="warning",
        )
    else:
        render_status_card(
            "Qué puedes hacer aquí",
            "Mantener catálogos limpios ayuda a que el equipo capture campañas más rápido y con mejor consistencia. Los cambios impactan a todos los usuarios.",
        )

        try:
            all_options_export = get_all_options(supabase)
            export_data = {}
            for field_key, rows in all_options_export.items():
                export_data[field_key] = [
                    {"value": row["value"], "created_at": row.get("created_at", "")}
                    for row in rows
                ]
            json_str = json.dumps(export_data, ensure_ascii=False, indent=2)
            download_col, _ = st.columns([1, 4])
            with download_col:
                st.download_button(
                    "Exportar JSON",
                    data=json_str,
                    file_name="utm_options.json",
                    mime="application/json",
                    use_container_width=True,
                )
        except Exception as error:
            st.error(f"Error al preparar exportación: {error}")

        field_meta = {
            "source": {
                "label": "UTM Source",
                "icon": "🌐",
                "desc": "Origen o proveedor del tráfico. Ej: meta, google, newsletter.",
            },
            "medium": {
                "label": "UTM Medium",
                "icon": "📡",
                "desc": "Canal de adquisición. Ej: paid_social, paid_search, email.",
            },
            "intent": {
                "label": "UTM Intent",
                "icon": "🎯",
                "desc": "Etapa del funnel. Ej: awareness, consideration, leads, conversion.",
            },
            "business": {
                "label": "UTM Business",
                "icon": "💼",
                "desc": "Línea de negocio o producto. Ej: advisory, wealth, trading.",
            },
            "zc": {
                "label": "UTM SC",
                "icon": "🗂️",
                "desc": "Clave de estacionalidad. Ej: buen_fin, mundial, ppr.",
            },
        }

        try:
            all_options = get_all_options(supabase)
            for field_key, meta in field_meta.items():
                rows = all_options.get(field_key, [])
                st.markdown("### " + f"{meta['icon']} {meta['label']}")
                st.caption(meta["desc"])

                count_col, help_col = st.columns([1, 3])
                with count_col:
                    render_metric_card("Opciones", len(rows), "Valores activos")
                with help_col:
                    render_status_card(
                        "Buenas prácticas",
                        "Usa valores cortos, consistentes y fáciles de reconocer. Todo se normaliza automáticamente al formato UTM.",
                    )

                if rows:
                    for row in rows:
                        value_col, created_col, action_col = st.columns([4, 2, 1])
                        with value_col:
                            st.markdown(
                                f"""
                                <div class="metric-card" style="margin-bottom:0.4rem;">
                                    <div class="metric-value" style="font-size:1rem;">{row['value']}</div>
                                </div>
                                """,
                                unsafe_allow_html=True,
                            )
                        with created_col:
                            created = row.get("created_at", "")
                            if created:
                                st.caption(f"Creado: {created[:19].replace('T', ' ')}")
                        with action_col:
                            if st.button(
                                "Quitar",
                                key=f"del_opt_{row['id']}",
                                use_container_width=True,
                            ):
                                delete_option(supabase, row["id"])
                                invalidate_options_cache()
                                st.rerun()
                else:
                    render_status_card(
                        "Aún sin opciones",
                        "Agrega la primera para que este catálogo aparezca como desplegable compartido en el formulario.",
                    )

                config_msg = st.session_state.pop(f"_config_msg_{field_key}", None)
                if config_msg:
                    st.success(config_msg)

                with st.form(key=f"add_opt_{field_key}"):
                    input_col, button_col = st.columns([4, 1])
                    with input_col:
                        new_val = st.text_input(
                            f"Nuevo valor para {meta['label']}",
                            placeholder="Escribe el valor y presiona Agregar…",
                            label_visibility="collapsed",
                            max_chars=MAX_UTM_VALUE_LENGTH,
                        )
                    with button_col:
                        submitted_opt = st.form_submit_button(
                            "Agregar",
                            use_container_width=True,
                        )

                    if submitted_opt:
                        if not new_val.strip():
                            st.warning("Escribe un valor antes de agregar.")
                        else:
                            normalized = normalize_utm_param(new_val.strip())
                            if not normalized:
                                st.error(
                                    f"❌ **'{new_val}'** no es un valor UTM válido tras normalizar."
                                )
                            elif len(normalized) > MAX_UTM_VALUE_LENGTH:
                                st.error(
                                    f"❌ **'{normalized}'** excede el máximo de {MAX_UTM_VALUE_LENGTH} caracteres."
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
                                except Exception as error:
                                    st.error(f"❌ Ya existe o hubo un error: {error}")

                st.divider()
        except Exception as error:
            st.error(f"Error al cargar configuración: {error}")
