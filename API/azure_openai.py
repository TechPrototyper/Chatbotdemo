"""
Titel: azure_openai.py

Beschreibung: Stellt die Kommunikation zwischen der Funktion App und der Azure OpenAI API her.
              Diese Datei nutzt spezifische Azure OpenAI Endpunkte und Konfigurationen für die Interaktion.
              "Schwesterdatei" ist o_openai.py, die auf allgemeine OpenAI-Endpunkte zugreift.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-03
Version: 1.0.0
Quellen: [OpenAI API Dokumentation], [Azure Functions Dokumentation], [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

from openai import AzureOpenAI  # Angenommen, dies ist der korrekte Importpfad
from user_threads import UserThreads
from typing import Tuple
import time
import os
import logging
from my_cloudevents import UserRegisteredEvent
from event_grid_publisher import EventGridPublisher

# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InteractWithOpenAI:
    """
    Diese Klasse handhabt die Kommunikation mit der Azure OpenAI API.
    """

    def __init__(self):
        """
        Initialisiert die Verbindung zur Azure OpenAI API und liest Konfigurationsparameter.
        """
        api_key = os.getenv("AZURE_OPENAI_API_KEY")
        endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        self.main_assistant_id = os.getenv("AZURE_OPENAI_MAIN_ASSISTANT_ID")
        api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        
        if not api_key or not endpoint:
            logging.error("AZURE_OPENAI_API_KEY oder AZURE_OPENAI_ENDPOINT ist nicht gesetzt.")
            raise EnvironmentError("AZURE_OPENAI_API_KEY oder AZURE_OPENAI_ENDPOINT Umgebungsvariable ist nicht gesetzt.")
        
        try:
            self.client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=endpoint)
        except Exception as e:
            logging.error(f"Konnte keine Verbindung zur Azure OpenAI API herstellen: {e}")
            raise

    def close(self):
        """
        Schließt die Verbindung zur Azure OpenAI API und zu Azure Table Storage.
        """
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            self.client.close()
            logging.info("Azure OpenAI API Verbindung geschlossen.")
        if hasattr(self, 'threads') and hasattr(self.threads, 'close'):
            self.threads.close()
            logging.info("Azure Table Storage Verbindung geschlossen.")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False

    def get_or_create_thread(self, user_email: str) -> str:
        """
        Ermittelt oder erstellt einen Thread für den gegebenen Benutzer in Azure.
        """
        try:
            self.threads = UserThreads()
            thread_id = self.threads.get_id(user_email)
        except LookupError:
            try:
                thread = self.client.beta.threads.create()  # Angenommen, dies ist die korrekte Methode
                print(thread)
                thread_id = thread.id  # Annahme über die Struktur der Antwort
                self.threads.set_id(user_email, thread_id)
                
                #TODO: Weitere Properties des Benutzers speichern
                user_details = {"email": user_email, "thread_id": thread_id}
                
                # Publish UserRegisteredEvent to EventGrid
                with EventGridPublisher() as publisher:
                    publisher.send_event(event = UserRegisteredEvent(user_details).to_cloudevent())

            except Exception as e:
                logging.error(f"Fehler bei der Thread-Erstellung oder -Speicherung: {e}")
                raise
        except Exception as e:
            logging.error(f"Fehler beim Zugriff auf die Thread-Historie: {e}")
            raise
        
        return thread_id

    def chat(self, user_email: str, prompt: str) -> Tuple[int, str]:
        """
        Sendet den Prompt des Benutzers an den Azure-spezifischen Assistant und verarbeitet die Antwort.
        """
        try:                
            thread_id = self.get_or_create_thread(user_email)
            logging.info(f"Thread ID: {thread_id}")

            self.client.beta.threads.messages.create(
                thread_id=thread_id,
                role="user",
                content=prompt
            )

            run = self.client.beta.threads.runs.create(
                thread_id=thread_id,
                assistant_id=self.main_assistant_id
            )

            while True:
                updated_run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                if updated_run.status in ["completed", "failed", "cancelled", "expired"]:
                    break
                time.sleep(1)

            if updated_run.status == "completed":
                messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                if messages.data and len(messages.data) > 0 and messages.data[0].content:
                    return 200, messages.data[0].content[0].text.value
                else:
                    return 200, "No response message found."
            else:
                logging.error(f"Problem beim Durchführen des Runs: {updated_run.status}")
                return 500, f"*ISSUE* **Run Status: {updated_run.status}**"
        except Exception as e:
            logging.error(f"Chat-Error: {e}")
            return 509, f"*ISSUE* **{e}**"

