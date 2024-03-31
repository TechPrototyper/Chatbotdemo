"""
Titel: function_app.py
Beschreibung:   Implementiert eine Azure Function App mit verschiedenen Routen bzw. Endpunkten.
                Programmiermodell Version 2, im "FastAPI-Style".

Autor: Tim Walter (TechPrototyper)
Datum: 2024-03-28
Version: 1.0.0
Quellen: [OpenAI API Dokumentation], [Azure Functions Dokumentation], [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

import azure.functions as func
import logging
from datetime import datetime
from o_openai import InteractWithOpenAI



# Initialisierung der Funktion App
    
# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

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
    except:
        return func.HttpResponse(f"An error has occured: {e}", status_code=400)

    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")               
    return func.HttpResponse(f"Hello, {params.user_name}! So you like to talk about {params.user_prompt}", status_code=200)

# Hauptendpunkt für den Chat
@app.route(route="chat", methods=["GET", "POST"])
def chat(req: func.HttpRequest) -> func.HttpResponse:
    """
    Haupt-Chat-Endpoint, verbindet sich mit einem Backend-Service zur Verarbeitung der Anfragen.
    """
    # Parameter aus der Anfrage extrahieren.
    try:
      params = ChatRequestParams(req)
    except:
      return func.HttpResponse(f"An error has occured: {e}", status_code=400)

    # Timestamp für Prompt erstellen
    time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Prompt für OpenAI erstellen
    prompt = f"Mein Name: {params.user_name}\nDatum und Uhrzeit: {time_stamp}\nMein Prompt: {params.user_prompt}"

    with InteractWithOpenAI() as interaction:
        http_status, response = interaction.chat(params.user_email, prompt)

    return func.HttpResponse(response, status_code=http_status)


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



