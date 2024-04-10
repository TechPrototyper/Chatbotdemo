"""
Titel: function_app.py
Beschreibung:   Implementiert eine Azure Function App mit verschiedenen Routen bzw. Endpunkten.
                Programmiermodell Version 2, im "FastAPI-Style".
                Jetzt vollständig auf Async umgestellt.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-10
Version: 1.0.0
Quellen: [OpenAI API Dokumentation], [Azure Functions Dokumentation], [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

import azure.functions as func
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
import logging
from datetime import datetime
from azure_openai import InteractWithOpenAI
import aiohttp  
from event_grid_publisher import EventGridPublisher
from my_cloudevents import PromptToUserEvent


# Initialisierung der Funktion App
    
# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
configure_azure_monitor()

# Erstellen der Funktion App

app = func.FunctionApp(http_auth_level=func.AuthLevel.ANONYMOUS)

# Sektion für Endpunkte bzw. Routen

"""
Parameter Hilfsklasse:

Leider unterstützt Azure Functions V2 die Übergabe von
Parametern per Dekoratoren i.V.m. Dependency Injection nicht.

Andererseits hat für diese Anwendung die ASGI-Bridge keinen Mehrwert, im Gegenteil.
Deshalb behelfen wir uns mit einer kleinen Parameter-Klasse, um die Parameter zu isolieren.
"""

# Hilfsklasse für Parameter für mock und chat Endpunkte / Routen / Operations
class ChatRequestParams:
    """
    Hilfsklasse zur Extraktion und Speicherung von Anfrageparametern.
    """
    def __init__(self, request: func.HttpRequest):
        self.user_name = request.params.get("Name", "")
        self.user_email = request.params.get("email", "")
        self.user_prompt = request.params.get("prompt", "")
        if not self.user_name or not self.user_email or not self.user_prompt:
          logging.error("Fehlende Parameter: Name, E-Mail oder Prompt")
          raise Exception("One or more parameters missing")

@app.route(route="mock", methods=["GET", "POST"])
def mock(req: func.HttpRequest) -> func.HttpResponse:
    """
    Einfacher Mock-Endpoint zum Testen der Verbindung und Parametereingabe.
    """
    try: 
      params = ChatRequestParams(req)
    except Exception as e:
      return func.HttpResponse(f"An error has occured: {e}", status_code=400)

    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")               
    return func.HttpResponse(f"Hello, {params.user_name}! So you like to talk about {params.user_prompt}", status_code=200)

# Hauptendpunkt für den Chat
@app.route(route="chat", methods=["GET", "POST"])
async def chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Haupt-Chat-Endpoint, verbindet sich mit einem Backend-Service zur Verarbeitung der Anfragen.
    """
    # Parameter aus der Anfrage extrahieren.
    try:
      params = ChatRequestParams(req)
    except Exception as e:
      return func.HttpResponse(f"An error has occured: {e}", status_code=400)

    # async with InteractWithOpenAI() as interaction:
    #     logging.info(f"Chat-Endpoint: Calling... {params.user_email} mit Prompt: {prompt}")
    #     http_status, response = await interaction.chat(params.user_email, prompt)
    #     logging.info(f"Chat-Endpoint came back: Response: {http_status}: {response}")

    interaction = InteractWithOpenAI()
    try:
        logging.info(f"Chat-Endpoint: Calling... {params.user_email} mit Prompt: {params.user_prompt}")
        http_status, response = await interaction.chat(params.user_name, params.user_email, params.user_prompt)
        # logging.info(f"Chat-Endpoint came back: Response: {http_status}: {response}")
    finally:
        await interaction.close()

    logging.info("InteractWithOpenAI() Context left, About to Return data to Caller!"  )

    response_body = response[0].text.value

    details = {"email": params.user_email, "Name: ": params.user_name, "prompt": response_body}
    async with EventGridPublisher() as publisher:
        await publisher.send_event(event = PromptToUserEvent(details).to_cloudevent())
        logging.info(f"Antwort-Prompt an {params.user_email} an EventGrid gesendet.")
        
    try:
        return func.HttpResponse(response_body, status_code=http_status, headers={"Content-Type": "text/plain; charset=utf-8"})
    except Exception as e:
        logging.error(f"Error returning the response: {e}")
        return func.HttpResponse("Internal server error", status_code=500)

# Ping- und Status-Endpunkte, noch zu implementieren
# Ggf. separate Parameter-Klassen für Ping und Status implementieren
@app.route(route="ping", methods=["GET"])
def ping(req: func.HttpRequest) -> func.HttpResponse:
    """
    Ping-Endpoint zur Überprüfung der Erreichbarkeit.
    """
    #TODO: Implementierung der Ping-Logik
    logging.info('Ping function processed a request.')
    return func.HttpResponse("pong", status_code=200)


@app.route(route="status", methods=["GET"])
def alive(req: func.HttpRequest) -> func.HttpResponse:
    """
    Status-Endpoint zur Überprüfung der Gesundheit der Funktion und verbundener Dienste.
    """
    logging.info('Alive function processed a request.')
    #TODO: Implementierung der Status-Logik
    return func.HttpResponse('{"chat_service": {"openai": "good", "database": "good"}}', status_code=200, mimetype="application/json")



