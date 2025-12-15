# test_assistant.py
import sys
import os
import time
from typing import List, Dict, Any

# Añadir el path para importar desde src/
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Importar las funciones de servicio necesarias
from src.assistant.assistant_client import send_message_to_assistant
from src.config.settings import settings
from src.utils.time_utils import get_current_time_info

# --- Funciones Auxiliares ---

def _build_conversation_history(system_text: str, user_input: str) -> List[Dict[str, Any]]:
    """Construye la estructura de entrada de la API."""
    # Nota: send_message_to_assistant espera una lista de turnos,
    # y ya se encarga de añadir el prompt del sistema.
    # Por simplicidad, este test envía solo el turno del usuario.
    return [
        {"role": "user", "content": [{"type": "input_text", "text": user_input}]},
    ]

def _get_runtime_context():
    """Define y construye el contexto de usuario (user_id, página, etc.)."""
    user_id = "test-user-worker"
    page = "simulacro-unal/ciencias-naturales"
    name = "Test User"
    email = "test@example.com"
    
    # Aquí podríamos construir el system_text si no lo hiciera send_message_to_assistant,
    # pero como send_message_to_assistant lo hace internamente, solo pasamos los metadatos.
    return user_id, page, name, email


def main():
    # Asegúrate de que los modelos Alpha y Omega están configurados en .env
    alpha_model = os.getenv("OPENAI_MODEL_ALPHA", "o1 (Default)")
    omega_model = os.getenv("OPENAI_MODEL_OMEGA", "gpt-4o-mini (Default)")
    
    print("\n===============================================")
    print("🔹 Test Interactivo del Worker (Alpha vs. Omega)")
    print(f"   Alpha (Razonamiento): {alpha_model}")
    print(f"   Omega (Velocidad): {omega_model}")
    print("===============================================\n")

    # 🔹 1. Bucle de selección de modo
    while True:
        mode_input = input("⚙️ Seleccione modo (A/Alpha, O/Omega, o 'exit'): ").strip().lower()

        if mode_input in ["exit", "e"]:
            print("👋 Sesión de pruebas finalizada.\n")
            break
        
        if mode_input in ["a", "alpha"]:
            mode = "alpha"
            print(f"✅ Modo seleccionado: ALPHA (Modelo: {alpha_model})")
        elif mode_input in ["o", "omega"]:
            mode = "omega"
            print(f"✅ Modo seleccionado: OMEGA (Modelo: {omega_model})")
        else:
            print("❌ Entrada inválida. Intente 'A' o 'O'.")
            continue

        # 🔹 2. Bucle de consulta
        while True:
            user_input = input(f"\n👤 You ({mode.upper()}): ").strip()
            
            if user_input.lower() in ["exit", "e"]:
                break
            if not user_input:
                continue

            # Obtener el contexto de usuario
            user_id, page, name, email = _get_runtime_context()
            
            # Construir la historia de la conversación (solo el último turno del usuario)
            conversation_history = _build_conversation_history("", user_input)
            
            print(f"\n🧠 Thinking with {mode.upper()}...")
            start_time = time.time()
            
            try:
                # 🔹 CRÍTICO: Usar la función de servicio que contiene la lógica de o1/max_completion_tokens
                ai_reply = send_message_to_assistant(
                    conversation_input=conversation_history,
                    user_id=user_id,
                    page=page,
                    name=name,
                    email=email,
                    mode=mode # Pasar el modo seleccionado
                )
                end_time = time.time()
                latency = end_time - start_time
                
                print(f"🤖 Roma AI ({mode.upper()} - {latency:.2f}s): {ai_reply}\n")
                
            except Exception as e:
                print(f"❌ Worker FAILED ({mode.upper()}): {e}\n")


if __name__ == "__main__":
    main()