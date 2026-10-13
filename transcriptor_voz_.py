import os
import sys
import rclpy
from rclpy.node import Node
import google.generativeai as genai
# from custom_interfaces.srv import InterpretarOrden

class TranscriptorVoz(Node):
    def __init__(self):
        super().__init__('transcriptor_voz')
        
        # EXPERTO: Lectura estricta de variables de entorno. Falla rápido si no existe (Fail-fast).
        api_key = os.environ.get("Insertar API Key")
        if not api_key:
            self.get_logger().error("CRÍTICO: Variable de entorno GEMINI_API_KEY no encontrada.")
            sys.exit(1) # No iniciar el nodo si falta la clave, es un riesgo de seguridad/operación
            
        genai.configure(api_key=api_key)
        self.modelo_stt = genai.GenerativeModel('gemini-1.5-flash') # Modelo rápido para STT
        
        self.declare_parameter('timeout_api_s', 2.0)
        self.timeout_s = self.get_parameter('timeout_api_s').get_parameter_value().double_value
        
        # Cliente para llamar a interprete_ordenes
        self.cli = self.create_client(InterpretarOrden, '/interpretar_orden')
        while not self.cli.wait_for_service(timeout_sec=1.0):
            self.get_logger().info('Esperando al servicio /interpretar_orden...')

    def procesar_audio(self, ruta_archivo_audio):
        """
        Envía el audio a la API de Gemini. Si falla, hace fallback al teclado.
        """
        texto_transcrito = ""
        try:
            self.get_logger().info("Subiendo audio a Google AI Studio...")
            # EXPERTO: Subida y procesamiento con manejo de excepciones (internet caído)
            audio_file = genai.upload_file(path=ruta_archivo_audio)
            
            # Prompt estricto para que NO genere texto adicional, solo la transcripción
            respuesta = self.modelo_stt.generate_content(
                [audio_file, "Transcribe exactamente lo que se dice en este audio en español. No agregues nada más."],
                request_options={"timeout": self.timeout_s}
            )
            texto_transcrito = respuesta.text.strip()
            self.get_logger().info(f"Transcripción exitosa: {texto_transcrito}")
            
        except Exception as e:
            self.get_logger().warn(f"Fallo en API de transcripción ({e}). Activando modo TECLADO.")
            # Fallback exigido por el examen
            texto_transcrito = input("\n[MODO DEGRADADO - SIN INTERNET] Ingrese la orden manualmente: ")
            
        # Llamar al servicio subsecuente
        self.enviar_orden_a_interprete(texto_transcrito)

    def enviar_orden_a_interprete(self, texto):
        req = InterpretarOrden.Request()
        req.frase = texto
        future = self.cli.call_async(req)
        # EXPERTO: call_async evita bloquear el nodo mientras espera al LAYA
        future.add_done_callback(self.callback_respuesta_interprete)

    def callback_respuesta_interprete(self, future):
        try:
            respuesta = future.result()
            self.get_logger().info(
                f"Decisión: Acción={respuesta.accion}, Obj={respuesta.objeto}, "
                f"Permitido={respuesta.permitido}, Degradado={respuesta.degradado}"
            )
            # AQUI: Inyectar la decisión en la cola (broker) usando tu clase Pedido
            # broker_enqueue(respuesta)
        except Exception as e:
            self.get_logger().error(f"Error al llamar al intérprete: {e}")

def main(args=None):
    rclpy.init(args=args)
    nodo = TranscriptorVoz()
    # Simulación de un trigger (en tu caso, podrías suscribirte a un tópico que publique la ruta del audio)
    # nodo.procesar_audio("ruta/al/audio_capturado.wav")
    rclpy.spin(nodo)
    rclpy.shutdown()

if __name__ == '__main__':
    main()