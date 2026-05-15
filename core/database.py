def _build_utm_payload(utm_record, zc_column):
    return {
        "website_url": utm_record["website_url"],
        "generated_url": utm_record["generated_url"],
        "template_name": utm_record.get("template_name") or None,
        "description": utm_record.get("description") or None,
        "owner": utm_record.get("owner") or None,
        "utm_id": utm_record.get("utm_id"),
        zc_column: utm_record.get("utm_zc") or None,
        "utm_name": utm_record.get("utm_name"),
        "utm_source": utm_record.get("utm_source"),
        "utm_medium": utm_record.get("utm_medium"),
        "utm_intent": utm_record.get("utm_intent"),
        "utm_business": utm_record.get("utm_business"),
        "utm_campaign_id": utm_record.get("utm_campaign_id") or None,
        "utm_asset_id": utm_record.get("utm_asset_id") or None,
        "utm_term": utm_record.get("utm_term") or None,
        "utm_content": utm_record.get("utm_content") or None,
        "utm_created": utm_record.get("utm_created") or None,
        "is_seasonal": utm_record.get("is_seasonal", False),
        # Compatibilidad hacia atrás con el historial actual.
        "campaign_source": utm_record.get("utm_source"),
        "campaign_medium": utm_record.get("utm_medium"),
        "campaign_name": utm_record.get("utm_name"),
        "campaign_id": utm_record.get("utm_campaign_id") or None,
        "campaign_term": utm_record.get("utm_term") or None,
        "campaign_content": utm_record.get("utm_content") or None,
    }


def save_utm(supabase, user_id, utm_record):
    """Guarda una fila del maestro UTM en Supabase."""
    primary_data = _build_utm_payload(utm_record, "utm_zc")
    primary_data = {
        key: value
        for key, value in primary_data.items()
        if value is not None
    }

    if user_id:
        primary_data["created_by"] = user_id

    try:
        return supabase.table("utms").insert(primary_data).execute()
    except Exception as error:
        message = str(error).lower()
        if "utm_zc" not in message:
            raise

        legacy_data = _build_utm_payload(utm_record, "utm_sc")
        legacy_data = {
            key: value
            for key, value in legacy_data.items()
            if value is not None
        }
        if user_id:
            legacy_data["created_by"] = user_id

        return supabase.table("utms").insert(legacy_data).execute()


def get_all_utms(supabase):
    """Obtiene todas las UTMs (historial compartido)."""
    response = supabase.table("utms").select("*").order("created_at", desc=True).execute()
    return response.data


def get_existing_utm_ids(supabase):
    """Obtiene los utm_id ya usados para calcular el siguiente incremental."""
    return [
        row.get("utm_id")
        for row in get_all_utms(supabase)
        if row.get("utm_id")
    ]


def get_user_utms(supabase, user_id):
    """Obtiene solo las UTMs del usuario."""
    response = (
        supabase.table("utms")
        .select("*")
        .eq("created_by", user_id)
        .order("created_at", desc=True)
        .execute()
    )
    return response.data


def delete_utm(supabase, utm_id):
    """Elimina una UTM."""
    response = supabase.table("utms").delete().eq("id", utm_id).execute()
    return response


def get_options(supabase, field_name):
    """Obtiene las opciones de un campo específico."""
    response = (
        supabase.table("utm_options")
        .select("*")
        .eq("field_name", field_name)
        .order("value")
        .execute()
    )
    return [row["value"] for row in response.data]


def add_option(supabase, field_name, value):
    """Agrega una opción a un campo."""
    response = supabase.table("utm_options").insert(
        {"field_name": field_name, "value": value}
    ).execute()
    return response


def delete_option(supabase, option_id):
    """Elimina una opción por ID."""
    response = supabase.table("utm_options").delete().eq("id", option_id).execute()
    return response


def get_all_options(supabase):
    """Obtiene todas las opciones agrupadas por field_name."""
    response = supabase.table("utm_options").select("*").order("field_name").execute()
    grouped = {}
    for row in response.data:
        field = row["field_name"]
        if field not in grouped:
            grouped[field] = []
        grouped[field].append(row)
    return grouped
