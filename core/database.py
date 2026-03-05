def save_utm(supabase, user_id, website_url, source, medium, generated_url,
             campaign_name=None, campaign_id=None, term=None, content=None,
             description=None, template_name=None):
    """Guarda UTM en Supabase"""

    data = {
        "website_url": website_url,
        "campaign_source": source,
        "campaign_medium": medium,
        "campaign_name": campaign_name or None,
        "campaign_id": campaign_id or None,
        "campaign_term": term or None,
        "campaign_content": content or None,
        "description": description or None,
        "generated_url": generated_url,
        "template_name": template_name or None,
    }
    # Quitar campos None para no enviarlos a Supabase
    data = {k: v for k, v in data.items() if v is not None}
    if user_id:
        data["created_by"] = user_id
    
    response = supabase.table("utms").insert(data).execute()
    return response


def get_all_utms(supabase):
    """Obtiene todas las UTMs (historial compartido)"""
    response = supabase.table("utms").select("*").order("created_at", desc=True).execute()
    return response.data


def get_user_utms(supabase, user_id):
    """Obtiene solo las UTMs del usuario"""
    response = supabase.table("utms").select("*").eq("created_by", user_id).order("created_at", desc=True).execute()
    return response.data


def delete_utm(supabase, utm_id):
    """Elimina una UTM"""
    response = supabase.table("utms").delete().eq("id", utm_id).execute()
    return response