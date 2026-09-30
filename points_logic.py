import os
from supabase import create_client

# Escala oficial para Carrera (Top 10)
ESCALA_CARRERA = [25, 18, 15, 12, 10, 8, 6, 4, 2, 1]
# Escala oficial para Sprint (Top 8)
ESCALA_SPRINT = [25, 18, 15, 12, 10, 8, 6, 4]

def calcular_puntos_sesion(pred_text, real_text, limite_puestos, es_sprint=False):
    """
    Motor EFEH TECH: Valida Top 3 perfecto obligatorio y extiende 
    puntos triples estrictamente hasta el puesto 5 si hay acierto exacto.
    """
    if not pred_text or not real_text or not str(real_text).strip():
        print(f"⚠️ [WARN] Texto vacío en predicción o resultado real. Pred: '{pred_text}' | Real: '{real_text}'")
        return 0
        
    # Limpieza robusta de cada piloto (minúsculas, sin espacios)
    p_arr = [p.strip().lower() for p in str(pred_text).split(",") if p.strip()]
    r_arr = [r.strip().lower() for r in str(real_text).split(",") if r.strip()]
    
    if not p_arr or not r_arr:
        return 0

    escala = ESCALA_SPRINT if es_sprint else ESCALA_CARRERA

    # 1. Validar podio perfecto obligatorio (P1, P2, P3 exactos)
    podio_perfecto = False
    if len(p_arr) >= 3 and len(r_arr) >= 3:
        if p_arr[0] == r_arr[0] and p_arr[1] == r_arr[1] and p_arr[2] == r_arr[2]:
            podio_perfecto = True

    pts = 0
    racha_triples_viva = podio_perfecto 

    for i in range(min(len(p_arr), limite_puestos)):
        piloto = p_arr[i]
        p_predicha = i + 1  
        
        # Buscar posición real de forma segura
        p_real = -1
        if piloto in r_arr:
            p_real = r_arr.index(piloto) + 1
        
        if p_real > 0 and p_real <= len(r_arr):
            puntos_base = escala[p_real - 1] if (p_real - 1) < len(escala) else 0
            
            # CASO A: Posición exacta
            if p_real == p_predicha:
                if (p_predicha <= 3 and podio_perfecto) or (p_predicha > 3 and racha_triples_viva):
                    pts += puntos_base * 3
                    print(f"    -> [TRIPLE] P{p_predicha} ({piloto}): {puntos_base} x 3 = {puntos_base * 3}")
                else:
                    pts += puntos_base * 2
                    print(f"    -> [DOBLE] P{p_predicha} ({piloto}): {puntos_base} x 2 = {puntos_base * 2}")
            # CASO B: Posición incorrecta pero dentro de los puntos
            else:
                pts += puntos_base  
                print(f"    -> [SIMPLE] P{p_predicha} ({piloto}) real en P{p_real}: {puntos_base}")
                if p_predicha > 3:
                    racha_triples_viva = False  
        else:
            print(f"    -> [FALLO] P{p_predicha} ({piloto}) no está en el top real.")
            if p_predicha > 3:
                racha_triples_viva = False  

    return pts

def procesar_todo(supabase):
    print("🚀 [EFEH TECH] Iniciando motor de cálculo con datos manuales...")

    preds_res = supabase.table("predicciones").select("*").eq("estado", "pendiente").execute()
    if not preds_res.data:
        print("⚠️ No hay predicciones registradas en la base de datos.")
        return

    puntos_acumulados_usuarios = {}

    for pred in preds_res.data:
        usuario_id = pred['usuario_id']
        gran_premio = pred['gran_premio']
        pred_id = pred['id']

        puntos_quali = 0
        puntos_sprint = 0
        puntos_carrera = 0

        # --- A. QUALI ---
        poleman_predicho = pred.get('poleman')
        if poleman_predicho:
            res_q = supabase.table("resultados_quali").select("*").eq("gran_premio", gran_premio).execute()
            if res_q.data:
                # Busca de forma flexible cualquier columna que contenga el resultado
                row_q = res_q.data[0]
                poleman_real = row_q.get('quali') or row_q.get('resultado') or row_q.get('poleman')
                if poleman_real and poleman_predicho.strip().lower() == str(poleman_real).strip().lower():
                    puntos_quali = 5

        # --- B. SPRINT ---
        sprint_preds = [pred.get('sprint_p1'), pred.get('sprint_p2'), pred.get('sprint_p3')]
        if any(sprint_preds):
            pred_sprint_text = ",".join([str(p) for p in sprint_preds if p])
            res_s = supabase.table("resultados_sprint").select("*").eq("gran_premio", gran_premio).execute()
            if res_s.data:
                row_s = res_s.data[0]
                real_sprint_text = row_s.get('sprint') or row_s.get('resultado') or row_s.get('sprint_p1')
                if real_sprint_text:
                    puntos_sprint = calcular_puntos_sesion(pred_sprint_text, real_sprint_text, limite_puestos=8, es_sprint=True)

        # --- C. CARRERA OFICIAL ---
        carrera_preds = [
            pred.get('carrera_p1'), pred.get('carrera_p2'), pred.get('carrera_p3'), 
            pred.get('carrera_p4'), pred.get('carrera_p5')
        ]
        if any(carrera_preds):
            pred_carrera_text = ",".join([str(p) for p in carrera_preds if p])
            # Buscamos de forma flexible en resultados_oficiales
            res_c = supabase.table("resultados_oficiales").select("*").eq("gran_premio", gran_premio).execute()
            if res_c.data:
                row_c = res_c.data[0]
                # Revisa nombres comunes de columnas manuales
                real_carrera_text = row_c.get('carrera') or row_c.get('resultado') or row_c.get('carrera_oficial')
                print(f"\n🔍 Procesando GP: {gran_premio} | Predicción: {pred_carrera_text}")
                print(f"📋 Resultado Oficial leídos de BD: {real_carrera_text}")
                if real_carrera_text:
                    puntos_carrera = calcular_puntos_sesion(pred_carrera_text, real_carrera_text, limite_puestos=10, es_sprint=False)
                else:
                    print("❌ ALERTA: No se encontró el texto de resultados oficiales para este GP en la BD.")

        puntos_total_fin_de_semana = puntos_quali + puntos_sprint + puntos_carrera

        # Guardar parciales en predicciones y sellar como procesado
            supabase.table("predicciones").update({
                "puntos_qualy": puntos_quali,
                "puntos_sprint": puntos_sprint,
                "puntos_carrera": puntos_carrera,
                "total_fin_de_semana": puntos_total_fin_de_semana,
                "estado": "procesado"
            }).eq("id", pred_id).execute()

        # Upsert en puntuaciones_gp
        try:
            supabase.table("puntuaciones_gp").upsert({
                "usuario_id": usuario_id,
                "gran_premio": gran_premio,
                "puntos_quali": puntos_quali,
                "puntos_sprint": puntos_sprint,
                "puntos_carrera": puntos_carrera,
                "total": puntos_total_fin_de_semana
            }, on_conflict="usuario_id,gran_premio").execute()
        except Exception:
            pass

        if usuario_id not in puntos_acumulados_usuarios:
            puntos_acumulados_usuarios[usuario_id] = 0
        puntos_acumulados_usuarios[usuario_id] += puntos_total_fin_de_semana

        print(f"🎯 [RESUMEN] GP: {gran_premio} | Q: {puntos_quali} | S: {puntos_sprint} | C: {puntos_carrera} | Total GP: {puntos_total_fin_de_semana}\n" + "-"*50)

    for u_id, pts_glob in puntos_acumulados_usuarios.items():
        supabase.table("usuarios").update({
            "puntos_globales": pts_glob
        }).eq("id", u_id).execute()
        print(f"👤 Usuario ID {u_id[:8]}... actualizado con Puntos Globales: {pts_glob}")

if __name__ == "__main__":
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        print("❌ Error: Faltan las credenciales de Supabase en las variables de entorno.")
        exit(1)
        
    supabase = create_client(url, key)
    procesar_todo(supabase)
    print("🏁 [EFEH TECH] Cálculo manual finalizado.")
