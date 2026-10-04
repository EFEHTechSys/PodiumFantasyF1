import os
from supabase import create_client

# Escala oficial para Carrera (Top 10)
ESCALA_CARRERA = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
# Escala oficial para Sprint (Top 8 - Idéntica a carrera hasta el puesto 8)
ESCALA_SPRINT = [25, 18, 15, 12, 10, 8, 6, 4]

def calcular_puntos_sesion(pred_text, real_text, limite_puestos, es_sprint=False):
    """
    Motor de cálculo oficial de EFEH TECH:
    - Simples: Piloto en Top real pero posición incorrecta.
    - Dobles: Posición exacta acertada.
    - Triples: Requiere obligatoriamente P1, P2 y P3 exactos para activar la racha en el podio.
    """
    if not pred_text or not real_text or not real_text.strip():
        return 0
        
    p_arr = [p.strip().lower() for p in pred_text.split(",") if p.strip()]
    r_arr = [p.strip().lower() for p in real_text.split(",") if p.strip()]
    
    if not p_arr or not r_arr:
        return 0

    escala = ESCALA_SPRINT if es_sprint else ESCALA_CARRERA

    # 1. Validar podio perfecto obligatorio (P1, P2, P3 exactos) para racha de triples
    podio_perfecto = False
    if len(p_arr) >= 3 and len(r_arr) >= 3:
        if p_arr[0] == r_arr[0] and p_arr[1] == r_arr[1] and p_arr[2] == r_arr[2]:
            podio_perfecto = True

    pts = 0
    racha_triples_viva = podio_perfecto 

    for i in range(min(len(p_arr), limite_puestos)):
        piloto = p_arr[i]
        p_predicha = i + 1  
        
        p_real = r_arr.index(piloto) + 1 if piloto in r_arr else -1
        
        if p_real > 0 and p_real <= len(r_arr):
            puntos_base = escala[p_real - 1] if (p_real - 1) < len(escala) else 0
            
            # CASO A: Posición exacta
            if p_real == p_predicha:
                if (p_predicha <= 3 and podio_perfecto) or (p_predicha > 3 and racha_triples_viva):
                    pts += puntos_base * 3
                else:
                    pts += puntos_base * 2
            # CASO B: Posición incorrecta pero en zona de puntos real
            else:
                pts += puntos_base  
                if p_predicha > 3:
                    racha_triples_viva = False  
        else:
            # Fuera de la zona de puntos real
            if p_predicha > 3:
                racha_triples_viva = False  

    return pts

def procesar_todo(supabase):
    print("🚀 [EFEH TECH] Iniciando motor de cálculo oficial de puntos...")

    # 1. Obtener todas las predicciones registradas
    preds_res = supabase.table("predicciones").select("*").execute()
    if not preds_res.data:
        print("⚠️ No hay predicciones registradas en la base de datos.")
        return

    # Diccionario para acumular los puntos globales de cada usuario
    puntos_acumulados_usuarios = {}

    for pred in preds_res.data:
        usuario_id = pred['usuario_id']
        gran_premio = pred['gran_premio']
        pred_id = pred['id']

        puntos_quali = 0
        puntos_sprint = 0
        puntos_carrera = 0

        # --- A. QUALI (Valor fijo exacto: 5 puntos si acierta el poleman) ---
        poleman_predicho = pred.get('poleman')
        if poleman_predicho:
            res_q = supabase.table("resultados_quali").select("quali").eq("gran_premio", gran_premio).execute()
            if res_q.data:
                poleman_real = res_q.data[0]['quali']
                if poleman_predicho.strip().lower() == poleman_real.strip().lower():
                    puntos_quali = 5

        # --- B. SPRINT ---
        sprint_preds = [pred.get('sprint_p1'), pred.get('sprint_p2'), pred.get('sprint_p3')]
        if any(sprint_preds):
            pred_sprint_text = ",".join([str(p) for p in sprint_preds if p])
            res_s = supabase.table("resultados_sprint").select("sprint").eq("gran_premio", gran_premio).execute()
            if res_s.data:
                real_sprint_text = res_s.data[0]['sprint']
                puntos_sprint = calcular_puntos_sesion(pred_sprint_text, real_sprint_text, limite_puestos=8, es_sprint=True)

        # --- C. CARRERA OFICIAL ---
        carrera_preds = [
            pred.get('carrera_p1'), pred.get('carrera_p2'), pred.get('carrera_p3'), 
            pred.get('carrera_p4'), pred.get('carrera_p5')
        ]
        if any(carrera_preds):
            pred_carrera_text = ",".join([str(p) for p in carrera_preds if p])
            res_c = supabase.table("resultados_oficiales").select("carrera").eq("gran_premio", gran_premio).execute()
            if res_c.data:
                real_carrera_text = res_c.data[0]['carrera']
                puntos_carrera = calcular_puntos_sesion(pred_carrera_text, real_carrera_text, limite_puestos=10, es_sprint=False)

        puntos_total_fin_de_semana = puntos_quali + puntos_sprint + puntos_carrera

        # 2. Actualizar la tabla 'predicciones' con los parciales y el total (Estrategia funcional probada)
        supabase.table("predicciones").update({
            "puntos_qualy": puntos_quali,
            "puntos_sprint": puntos_sprint,
            "puntos_carrera": puntos_carrera,
            "total_fin_de_semana": puntos_total_fin_de_semana
        }).eq("id", pred_id).execute()

        # Acumular para el global del usuario
        if usuario_id not in puntos_acumulados_usuarios:
            puntos_acumulados_usuarios[usuario_id] = 0
        puntos_acumulados_usuarios[usuario_id] += puntos_total_fin_de_semana

        print(f"🎯 GP: {gran_premio} | Usuario: {usuario_id[:8]}... -> Q: {puntos_quali} | S: {puntos_sprint} | C: {puntos_carrera} | Total GP: {puntos_total_fin_de_semana}")

    # 3. Actualizar los puntos globales en la tabla 'usuarios' para cada participante
    for u_id, pts_glob in puntos_acumulados_usuarios.items():
        supabase.table("usuarios").update({
            "puntos_globales": pts_glob
        }).eq("id", u_id).execute()
        print(f"👤 Usuario {u_id[:8]}... actualizado con Puntos Globales: {pts_glob}")

if __name__ == "__main__":
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Error: Faltan las credenciales de Supabase en las variables de entorno.")
        exit(1)
        
    supabase = create_client(url, key)
    procesar_todo(supabase)
    print("🏁 [EFEH TECH] Cálculo y sincronización con Supabase finalizados correctamente.")
