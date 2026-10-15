import os
import sys

# Añade la carpeta actual al path para que Python encuentre los módulos locales
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from supabase import create_client
import f1_tracks
import points_logic
import utils

def main():
    print("--- [EFEH TECH] Iniciando Orquestador con Resultados Globales ---")
    
    # 1. Configuración de Supabase
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    
    if not SUPABASE_URL or not SUPABASE_KEY:
        print("❌ Error: Credenciales de Supabase no configuradas en el entorno.")
        sys.exit(1)
        
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    try:
        # 2. Determinar evento activo usando el módulo calendar unificado
        evento = f1_tracks.get_current_event(supabase)
        if not evento:
            print("❌ No hay ningún evento marcado como activo en la BD.")
            return
            
        gp_nombre = evento['name']
        print(f"📡 Procesando Gran Premio activo: {gp_nombre}")

        # 3. Obtener los resultados oficiales directamente desde la tabla unificada 'resultados_globales'
        res_global = supabase.table("resultados_globales") \
                              .select("quali, sprint, carrera") \
                              .eq("gran_premio", gp_nombre) \
                              .execute()

        if not res_global.data or not res_global.data[0].get('carrera'):
            print(f"❌ No hay resultados oficiales cargados en 'resultados_globales' para {gp_nombre}. Abortando.")
            return
            
        resultados = res_global.data[0]
        poleman_real = resultados.get("quali")
        real_sprint_text = resultados.get("sprint")
        real_carrera_text = resultados.get("carrera")
        
        print(f"📋 Resultados oficiales recuperados de la tabla unificada para {gp_nombre}")

        # 4. Obtener las predicciones de los usuarios para este GP desde Supabase
        registros_predicciones = utils.get_user_predictions(supabase, gp_nombre)
        if not registros_predicciones:
            print("⚠️ No se encontraron predicciones de usuarios para este evento.")
            return

        print(f"📊 Procesando puntos para {len(registros_predicciones)} pronósticos...")

        puntos_acumulados_usuarios = {}

        # 5. Bucle de cálculo e inyección por cada usuario registrado
        for reg in registros_predicciones:
            usuario_id = reg.get("usuario_id")
            pred_id = reg.get("id")

            puntos_quali = 0
            puntos_sprint = 0
            puntos_carrera = 0

            # --- A. QUALI (Poleman) ---
            poleman_predicho = reg.get('poleman')
            if poleman_predicho and poleman_real:
                if poleman_predicho.strip().lower() == poleman_real.strip().lower():
                    puntos_quali = 5

            # --- B. SPRINT ---
            sprint_preds = [reg.get('sprint_p1'), reg.get('sprint_p2'), reg.get('sprint_p3')]
            if any(sprint_preds) and real_sprint_text:
                pred_sprint_text = ",".join([str(p) for p in sprint_preds if p])
                puntos_sprint = points_logic.calcular_puntos_sesion(pred_sprint_text, real_sprint_text, limite_puestos=8, es_sprint=True)

            # --- C. CARRERA OFICIAL ---
            carrera_preds = [
                reg.get('carrera_p1'), reg.get('carrera_p2'), reg.get('carrera_p3'), 
                reg.get('carrera_p4'), reg.get('carrera_p5')
            ]
            if any(carrera_preds) and real_carrera_text:
                pred_carrera_text = ",".join([str(p) for p in carrera_preds if p])
                puntos_carrera = points_logic.calcular_puntos_sesion(pred_carrera_text, real_carrera_text, limite_puestos=10, es_sprint=False)

            puntos_total_fin_de_semana = puntos_quali + puntos_sprint + puntos_carrera

            # 6. Actualizar la tabla 'predicciones' con los parciales, el total y marcar como 'procesado'
            supabase.table("predicciones").update({
                "puntos_qualy": puntos_quali,
                "puntos_sprint": puntos_sprint,
                "puntos_carrera": puntos_carrera,
                "total_fin_de_semana": puntos_total_fin_de_semana,
                "estado": "procesado"
            }).eq("id", reg['id']).execute()

            # Acumular para el global del usuario
            if usuario_id not in puntos_acumulados_usuarios:
                puntos_acumulados_usuarios[usuario_id] = 0
            puntos_acumulados_usuarios[usuario_id] += puntos_total_fin_de_semana

            print(f"👤 Usuario ID {usuario_id[:8]}... -> Q: {puntos_quali} | S: {puntos_sprint} | C: {puntos_carrera} | Total GP: {puntos_total_fin_de_semana} [PROCESADO]")

        # 7. Actualizar los puntos globales en la tabla 'usuarios' sumando lo nuevo a lo que ya tenían
        for u_id, pts_nuevos in puntos_acumulados_usuarios.items():
            user_res = supabase.table("usuarios").select("puntos_globales").eq("id", u_id).execute()
            puntos_actuales = 0
            if user_res.data and user_res.data[0].get("puntos_globales") is not None:
                puntos_actuales = user_res.data[0]["puntos_globales"]
            
            puntos_totales_globales = puntos_actuales + pts_nuevos

            supabase.table("usuarios").update({
                "puntos_globales": puntos_totales_globales
            }).eq("id", u_id).execute()
            print(f"🎯 Usuario {u_id[:8]}... actualizado con Puntos Globales Totales: {puntos_totales_globales}")

        print("🏁 [EFEH TECH] Orquestador ejecutado y sincronizado con éxito.")

    except Exception as e:
        print(f"❌ Error durante la ejecución del orquestador: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
