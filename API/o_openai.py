"""
Titel: o_openai.py

Beschreibung:   Stellt die Kommunikation zwischen der Funktion App und der OpenAI API her.
                OpenAI Backend.
                "Schwesterdatei" ist azure_openai.py, die auf OpenAI-Endpunkte in Azure zugreift.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-03-28
Version: 1.0.0
Quellen: [OpenAI API Dokumentation], [Azure Functions Dokumentation], [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

from openai import OpenAI
from user_threads import UserThreads
from typing import Tuple
import time
import os
import logging

# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InteractWithOpenAI:
    """
    Diese Klasse handhabt die Kommunikation mit der OpenAI API.
    """

    def __init__(self):
        """
        Initialisiert die Verbindung zur OpenAI API und liest Konfigurationsparameter.
        """
        api_key = os.getenv("OPENAI_API_KEY")
        self.main_assistant_id = os.getenv("OPENAI_MAIN_ASSISTANT_ID")
        
        if not api_key:
            logging.error("OPENAI_API_KEY ist nicht gesetzt.")
            raise EnvironmentError("OPENAI_API_KEY Umgebungsvariable ist nicht gesetzt.")
        
        try:
            self.client = OpenAI(api_key=api_key)
        except Exception as e:
            logging.error(f"Konnte keine Verbindung zur OpenAI API herstellen: {e}")
            raise

    def close(self):
        """
        Schließt die Verbindung zur OpenAI API und zu Azure Table Storage.
        """
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            self.client.close()
            logging.info("OpenAI API Verbindung geschlossen.")
        if hasattr(self, 'threads') and hasattr(self.threads, 'close'):
            self.threads.close()
            logging.info("Azure Table Storage Verbindung geschlossen.")

    def __enter__(self):
        # Beim Betreten des Kontexts, bleibt unverändert
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Beim Verlassen des Kontexts, Ressourcenfreigabe
        self.close()

        return False

    def get_or_create_thread(self, user_email: str) -> str:
        """
        Ermittelt oder erstellt einen Thread für den gegebenen Benutzer.
        
        :param user_email: E-Mail-Adresse des Benutzers.
        :return: Thread-ID
        """
        try:
            self.threads = UserThreads()
            thread_id = self.threads.get_id(user_email)
        except LookupError:
            try:
                thread = self.client.beta.threads.create()
                thread_id = thread.id
                self.threads.set_id(user_email, thread_id)
            except Exception as e:
                logging.error(f"Fehler bei der Thread-Erstellung oder -Speicherung: {e}")
                raise
        except Exception as e:
            logging.error(f"Fehler beim Zugriff auf die Thread-Historie: {e}")
            raise
        
        return thread_id

    def chat(self, user_email: str, prompt: str) -> Tuple[int, str]:
        """
        Sendet den Prompt des Benutzers an den Assistant und verarbeitet die Antwort.

        :param user_email: E-Mail-Adresse des Benutzers.
        :param prompt: Der Prompt des Benutzers.
        :return: Antwort des Assistants.
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
                if messages.data and messages.data[0].content and len(messages.data[0].content) > 0:
                    return 200, messages.data[0].content[0].text.value
                else:
                    return 200, "No response message found."
            else:
                logging.error(f"Problem beim Durchführen des Runs: {updated_run.status}")
                return 500, f"*ISSUE* **Run Status: {updated_run.status}**"
        
        except Exception as e:
            logging.error(f"Chat-Error: {e}")
            return 509, f"*ISSUE* **{e}**"
                
