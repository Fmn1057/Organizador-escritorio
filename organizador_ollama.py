"""
Módulo de integración con Ollama para comandos en lenguaje natural.
Requiere Ollama instalado y ejecutándose localmente: https://ollama.com
"""
import json
import urllib.request
import urllib.error
from PyQt5.QtCore import QThread, pyqtSignal

OLLAMA_BASE_URL = "http://localhost:11434"
DEFAULT_MODEL = "llama3.2"

SYSTEM_PROMPT = """Eres el asistente del Organizador de Escritorio, una app Windows que organiza archivos en "casillas" (carpetas flotantes).

Cuando el usuario te dé un comando en lenguaje natural, responde ÚNICAMENTE con JSON válido usando este esquema exacto:
{
  "entendido": "descripción breve de lo que harás",
  "acciones": [ ...lista de acciones... ]
}

Tipos de acciones disponibles:

  {"tipo": "crear_casilla", "nombre": "NombreCasilla"}
  {"tipo": "eliminar_casilla", "nombre": "NombreCasilla"}
  {"tipo": "renombrar_casilla", "nombre_actual": "NombreActual", "nuevo_nombre": "NuevoNombre"}
  {"tipo": "mover_archivo", "archivo": "nombre_exacto.ext", "casilla_origen": "Origen", "casilla_destino": "Destino"}
  {"tipo": "mover_tipo", "extension": ".rar", "casilla_origen": "Origen", "casilla_destino": "Destino"}
  {"tipo": "nada", "mensaje": "Explicación de por qué no se puede hacer"}

Reglas importantes:
- Para "mover_archivo": usa el nombre EXACTO del archivo como aparece en el contexto (incluyendo extensión y mayúsculas)
- Para "mover_tipo": extension debe incluir el punto, ej: ".rar", ".pdf", ".jpg"
- Para mover desde el escritorio: casilla_origen = "Escritorio"
- Para mover al escritorio: casilla_destino = "Escritorio"
- Si el archivo está en el escritorio, usa casilla_origen = "Escritorio" (nunca inventes un nombre de casilla)
- Si no entiendes el comando o no es posible: {"tipo": "nada", "mensaje": "..."}
- Puedes incluir múltiples acciones en la lista para satisfacer un comando
- SIEMPRE responde SOLO con JSON válido, sin texto adicional

Ejemplos:
Usuario: "crear casilla Juegos"
→ {"entendido": "Crearé la casilla Juegos", "acciones": [{"tipo": "crear_casilla", "nombre": "Juegos"}]}

Usuario: "mover todos los rar del escritorio a Archivos Comprimidos"
→ {"entendido": "Moveré todos los .rar del escritorio a Archivos Comprimidos", "acciones": [{"tipo": "mover_tipo", "extension": ".rar", "casilla_origen": "Escritorio", "casilla_destino": "Archivos Comprimidos"}]}

Usuario: "renombrar casilla Trabajo a Proyectos"
→ {"entendido": "Renombraré la casilla Trabajo a Proyectos", "acciones": [{"tipo": "renombrar_casilla", "nombre_actual": "Trabajo", "nuevo_nombre": "Proyectos"}]}"""


class OllamaWorker(QThread):
    """Ejecuta la llamada a Ollama en un hilo separado para no bloquear la UI."""
    resultado = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, client, texto, contexto):
        super().__init__()
        self.client = client
        self.texto = texto
        self.contexto = contexto

    def run(self):
        try:
            result = self.client.procesar_comando(self.texto, self.contexto)
            self.resultado.emit(result)
        except Exception as e:
            self.error.emit(str(e))


class OllamaClient:
    """Cliente HTTP para comunicarse con la API local de Ollama."""

    def __init__(self, model=DEFAULT_MODEL, base_url=OLLAMA_BASE_URL):
        self.model = model
        self.base_url = base_url

    def is_available(self):
        """Verifica si Ollama está corriendo."""
        try:
            req = urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3)
            return req.status == 200
        except Exception:
            return False

    def get_models(self):
        """Retorna la lista de modelos instalados en Ollama."""
        try:
            req = urllib.request.urlopen(f"{self.base_url}/api/tags", timeout=3)
            data = json.loads(req.read().decode("utf-8"))
            return [m["name"] for m in data.get("models", [])]
        except Exception:
            return []

    def procesar_comando(self, texto, contexto_casillas):
        """
        Envía un comando en lenguaje natural a Ollama y retorna las acciones parseadas.
        Retorna un dict con keys 'entendido' y 'acciones'.
        """
        context_str = self._build_context(contexto_casillas)
        user_msg = f"Estado actual del organizador:\n{context_str}\n\nComando del usuario: {texto}"

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_msg}
            ],
            "stream": False,
            "format": "json"
        }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=90) as response:
            result = json.loads(response.read().decode("utf-8"))
            content = result["message"]["content"]
            return json.loads(content)

    def _build_context(self, contexto_casillas):
        """Construye el string de contexto mostrando archivos y carpetas de cada ubicación."""
        if not contexto_casillas:
            return "No hay casillas creadas y el escritorio está vacío."
        lines = []
        for nombre, entradas in contexto_casillas.items():
            if not entradas:
                lines.append(f"- {nombre}: (vacío)")
            else:
                lines.append(f"- {nombre}: {', '.join(entradas)}")
        return "\n".join(lines)
