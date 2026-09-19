# f1_tracks.py (o calendar.py)

# 1. Diccionario de nombres y variaciones oficiales de los Grandes Premios (Temporada 2026)
MAPEO_GRANDES_PREMIOS = {
    "melbourne": ["Gran Premio de Australia", "Australian Grand Prix"],
    "shanghai": ["Gran Premio de China", "Chinese Grand Prix"],
    "suzuka": ["Gran Premio de Japón", "Japanese Grand Prix"],
    "miami": ["Gran Premio de Miami", "Miami Grand Prix"],
    "canada": ["Gran Premio de Canadá", "Canadian Grand Prix"],
    "monaco": ["Gran Premio de Mónaco", "Monaco Grand Prix"],
    "barcelona": ["Gran Premio de Catalunia", "Gran Premio de Barcelona-Catalunya"],
    "austria": ["Gran Premio de Austria", "Austrian Grand Prix"],
    "silverstone": ["Gran Premio de Gran Bretaña", "British Grand Prix"],
    "Spa- Francorschamps": ["Gran Premio de Bélgica", "Belgian Grand Prix"],
    "hungria": ["Gran Premio de Hungría", "Hungarian Grand Prix"],
    "paises bajos": ["Gran Premio de Países Bajos", "Dutch Grand Prix"],
    "Monza": ["Gran Premio de Italia", "Italian Grand Prix"],
    "madring": ["Gran Premio de Madrid", "Gran Premio de España"],
    "azerbaiyan": ["Gran Premio de Azerbaiyán", "Azerbaijan Grand Prix"],
    "singapur": ["Gran Premio de Singapur", "Singapore Grand Prix"],
    "austin": ["Gran Premio de Estados Unidos", "United States Grand Prix"],
    "mexico": ["Gran Premio de México", "Mexican Grand Prix"],
    "brasil": ["Gran Premio de Brasil", "Brazilian Grand Prix"],
    "las vegas": ["Gran Premio de Las Vegas", "Las Vegas Grand Prix"],
    "qatar": ["Gran Premio de Qatar", "Qatar Grand Prix"],
    "abu dabi": ["Gran Premio de Abu Dabi", "Abu Dhabi Grand Prix"]
}

# 2. Diccionario para identificar qué circuitos tienen formato Sprint
CALENDARIO_2026_SPRINT = {
    "china": True,
    "miami": True,
    "canada": True,
    "austin": True,
    "paises bajos": True,
    "singapur": True
}

def tiene_sprint(gran_premio):
    """
    Verifica si un circuito tiene formato Sprint de forma segura.
    """
    if not gran_premio:
        return False
    gp_limpio = gran_premio.strip().lower()
    return CALENDARIO_2026_SPRINT.get(gp_limpio, False)

def get_current_event(supabase):
    """
    Consulta a Supabase para obtener el GP activo y la sesión actual,
    integrando la gestión de datos en un solo lugar.
    """
    try:
        response = supabase.table("calendario") \
                           .select("*") \
                           .eq("es_activo", True) \
                           .single() \
                           .execute()
        
        if response.data:
            return {
                "id": response.data['id'],
                "name": response.data['gp_nombre'],
                "sesion": response.data['sesion_actual'],
                "url": response.data['url_motorsport']
            }
        else:
            print("❌ No hay ningún evento marcado como activo en la BD.")
            return None
    except Exception as e:
        print(f"❌ Error consultando el calendario en la BD: {e}")
        return None
