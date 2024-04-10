"""
Titel: azure_openai.py

Beschreibung: Stellt die Kommunikation zwischen der Funktion App und der Azure OpenAI API her.
              Diese Datei nutzt spezifische Azure OpenAI Endpunkte und Konfigurationen für die Interaktion.
              "Schwesterdatei" ist o_openai.py, die auf allgemeine OpenAI-Endpunkte zugreift.
              Modul ist nun vollständig auf async umgestellt. Eine Async-Library für die Assistant-API
              war noch nicht verfügbar, wird aber mit Release der API seitens OpenAI sicher verfügbar sein.
              Auf die Verwendung der Hilfsmethode async_api_call() kann dann später verzichtet werden.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-10
Version: 1.0.1
Quellen: [OpenAI API Dokumentation], [Azure Functions Dokumentation], [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

from openai import AzureOpenAI  # Angenommen, dies ist der korrekte Importpfad
from user_threads import UserThreads
# from typing import Tuple
import asyncio
from concurrent.futures import ThreadPoolExecutor
import os
import logging
from my_cloudevents import *
from event_grid_publisher import EventGridPublisher
from assistant_tools import AssistantTools
import re
from datetime import datetime


# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class InteractWithOpenAI:
    """
    Diese Klasse handhabt die Kommunikation mit der Azure OpenAI API.
    Sie verwendet die Azure OpenAI API, um Benutzeranfragen zu verarbeiten und Antworten zu generieren.
    """

    async def async_api_call(self, method, *args, **kwargs):
        loop = asyncio.get_running_loop()
        with ThreadPoolExecutor() as pool:
            result = await loop.run_in_executor(pool, method, *args, **kwargs)
            return result


    def __init__(self):
        """
        Initialisiert die Verbindung zur Azure OpenAI API und liest Konfigurationsparameter.

        :raises EnvironmentError: Wenn die Umgebungsvariablen nicht gesetzt sind.
        :raises Exception: Wenn keine Verbindung zur Azure OpenAI API hergestellt werden kann.
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

        self.assistant_tools = AssistantTools()

    async def close(self):
        """
        Schließt die Verbindung zur Azure OpenAI API und zu Azure Table Storage.

        :return: None
        """
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            await self.async_api_call(lambda: self.client.close())
            logging.info("Azure OpenAI API Verbindung geschlossen.")
        if hasattr(self, 'threads') and hasattr(self.threads, 'close'):
            await self.threads.close()
            logging.info("Azure Table Storage Verbindung geschlossen.")

    async def __aenter__(self):
        """
        Wird beim Betreten des Kontexts aufgerufen.

        :return: self
        """
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Schließt die Verbindung zur Azure OpenAI API und zu Azure Table Storage beim Verlassen des Kontexts.

        :return: False
        """
        await self.close()
        return False

    async def get_or_create_thread(self, user_email: str) -> str:
        """
        Ermittelt oder erstellt einen Thread für den gegebenen Benutzer in Azure.

        :param user_email: Die E-Mail-Adresse des Benutzers.
        :type user_email: str
        :return: Die ID des Threads.
        """
        try:
            self.threads = UserThreads()
            thread_id = await self.threads.get_id(user_email)

            #TODO: Zu viel Code Alarm, muss gestrafft werden: 3 Zeilen für einen Event sind zu viel.
            user_details = {"email": user_email, "thread_id": thread_id}
            async with EventGridPublisher() as publisher:
                await publisher.send_event(event = UserLoginEvent(user_details).to_cloudevent())

        except LookupError:
            try:
                # thread = self.client.beta.threads.create() 
                thread = await self.async_api_call(self.client.beta.threads.create)
                thread_id = thread.id 
                await self.threads.set_id(user_email, thread_id)
                
                #TODO: Weitere Properties des Benutzers speichern

                #TODO: Zu viel Code Alarm, siehe oben.
                user_details = {"email": user_email, "thread_id": thread_id}
                
                # Publish UserRegisteredEvent to EventGrid
                async with EventGridPublisher() as publisher:
                    await publisher.send_event(event = UserRegisteredEvent(user_details).to_cloudevent())

            except Exception as e:
                logging.error(f"Fehler bei der Thread-Erstellung oder -Speicherung: {e}")
                raise
        except Exception as e:
            logging.error(f"Fehler beim Zugriff auf die Thread-Historie: {e}")
            raise
        
        return thread_id

    async def chat(self, user_name: str, user_email: str, user_prompt: str):
        """
        Sendet den Prompt des Benutzers an den Azure-spezifischen Assistant und verarbeitet die Antwort.

        :param user_email: Die E-Mail-Adresse des Benutzers.
        :type user_email: str
        :param prompt: Der vom Benutzer eingegebene Prompt.
        :type prompt: str
        :return: Der Antworttext des Assistenten.
        """

        try:                
            # Prüfen, ob der Benutzer Transskripte erlaubt
            thread_id = await self.get_or_create_thread(user_email)
            logging.info(f"Thread ID: {thread_id}")

            u = UserThreads()
            transscript_allowed = await u.get_extended_events(user_email)

            # Create prompt with user details
            time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            logging.info(f"Timestamp: {time_stamp}")
            modified_prompt = f"Mein Name: {user_name}\nMeine E-Mail Adresse: {user_email}\nDatum und Uhrzeit: {time_stamp}\nStatus der Mitleseerlaubnis: {str(transscript_allowed)}\nMein Prompt: {user_prompt}"
            logging.info(f"Modified Prompt: created.")

            if transscript_allowed == 1:
                details = {"email": user_email, "Name: ": user_name,"prompt": user_prompt}
                async with EventGridPublisher() as publisher:
                    await publisher.send_event(event = PromptFromUserEvent(details).to_cloudevent())
                    logging.info(f"Prompt von Benutzer {user_email} an EventGrid gesendet.")
            

            while True:
            # Neue Nachricht erzeugen
                try:
                    logging.info(f"Message Object wird erstellt")
                    await self.async_api_call(lambda: self.client.beta.threads.messages.create(
                        thread_id=thread_id,
                        role="user",
                        content=modified_prompt
                    ))
                    logging.info(f"Message Object ist ok.")

                    if transscript_allowed == 1:
                        details = {"email": user_email, "Name: ": user_name,"prompt": modified_prompt}
                        async with EventGridPublisher() as publisher:
                            await publisher.send_event(event = PromptToAIEvent(details).to_cloudevent())
                            logging.info(f"Modifiziertes Prompt zum Backend an EventGrid gesendet.")
                    break
                except Exception as e:
                    logging.info(f"Error: {e}")
                    # Konvertiert die Exception zu einem String, um sie mit Regex zu verarbeiten
                    error_str = str(e)
                    if "Can't add messages to" in error_str and "while a run" in error_str and "is active." in error_str:
                        # Extrahiert die thread_id und run_id aus der Fehlermeldung mit Regex
                        thread_id_match = re.search(r"thread_([a-zA-Z0-9]+)", error_str)
                        run_id_match = re.search(r"run_([a-zA-Z0-9]+)", error_str)
                        
                        if thread_id_match and run_id_match:
                            thread_id = "thread_"+thread_id_match.group(1)
                            run_id = "run_"+run_id_match.group(1)
                            logging.info(f"Thread ID: {thread_id}, Run ID: {run_id}")
                            # self.client.beta.threads.runs.cancel(run_id = run_id, thread_id = thread_id)
                            await self.async_api_call(
                                lambda: self.client.beta.threads.runs.cancel(run_id=run_id, thread_id=thread_id)
                            )

                            logging.info(f"Lfd. Run für Thread {thread_id} abgebrochen.")
                        else:
                            logging.error("Thread ID oder Run ID konnte nicht aus der Fehlermeldung extrahiert werden.")
                    else:
                        logging.error(f"Nachricht konnte nicht gesendet werden: {e}")
                        #TODO: Fehlerbehandlung anpassen
                        # return 500, f"*ISSUE* **{e}**"
            logging.info(f"Message Object created, Prompt: {modified_prompt}")
            # Eine Interaktion - sog. "Run" - erstellen
            run = await self.async_api_call(
                lambda: self.client.beta.threads.runs.create(
                    thread_id=thread_id,
                    assistant_id=self.main_assistant_id
                )
            )


            logging.info(f"Run created, Run ID: {run.id}")

            while True:
                # Wait for run to return with a status
                while True:
                    # Wait until Azure OpenAI comes back with any actionable state
                    # updated_run = self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                    updated_run = await self.async_api_call(
                        lambda: self.client.beta.threads.runs.retrieve(thread_id=thread_id, run_id=run.id)
                    )
                    logging.info(f"Run Status: {updated_run.status}")
                    if updated_run.status not in ["queued", "in_progress"]:
                        logging.info(f"... Run Status: {updated_run.status}")
                        break
                    await asyncio.sleep(1)

                
                match updated_run.status:
                    case "completed": # Wir haben eine Antwort, ab zum Benutzer damit!
                        # messages = self.client.beta.threads.messages.list(thread_id=thread_id)
                        messages = await self.async_api_call(
                            lambda: self.client.beta.threads.messages.list(thread_id=thread_id)
                        )
                        if messages.data and len(messages.data) > 0 and messages.data[0].content:
                            return_prompt = messages.data[0].content            
                            response_body = return_prompt[0].text.value     
                            logging.info(f"Response: {response_body}")

                            if transscript_allowed == 1:
                                details = {"email": user_email, "Name: ": user_name,"ai_prompt": response_body}
                                async with EventGridPublisher() as publisher:
                                    await publisher.send_event(event = PromptToUserEvent(details).to_cloudevent())
                                    logging.info(f"Prompt von der AI für Benutzer {user_email} an EventGrid gesendet.")
                                    
                                # Diese Code ist zwar fast gleich; aber im Prinzip sind es zwei Events; einmal die
                                # Message vom Backend an den Middletier, und einmal die Message vom Middletier
                                # an das Frontend. Hier ist tatsächlich alles gleich, aber es kann sich evtl. später
                                # später noch ändern. Es könnte z.B. auch sein, dass Magic Strings gefiltert werden müssen,
                                # o.Ä.

                                details = {"email": user_email, "Name: ": user_name,"prompt": response_body}
                                async with EventGridPublisher() as publisher:
                                    await publisher.send_event(event = PromptFromAIEvent(details).to_cloudevent())
                                    logging.info(f"Prompt an der Frontend zum Benutzer {user_email} an EventGrid gesendet.")
                                
                            return 200, response_body
                        else:
                            return 200, "Da fällt mir im Moment gerade nichts zu ein (Leere Nachricht von der KI)."
                    case "cancelled": # Should never happen, we have no feature to support cancelling an interaction such as in ChatGPT
                        return 200, "Chat abgebrochen. /(ENDE)\\"
                    case "cancelling": # Same here, although, if for any reason this is happening, we will actually wait until the state changes to "cancelled"
                        pass
                    case "pending": # Not sure whether this is a real valid state. It appears in documentation, but code editor does not recognize it for autocompletion
                        pass # Something is going to happen, but we don't know yet
                    case "expired":
                        return 200, "Ich bin scheinbar im Moment nicht in der Lage, eine Antwort zu formulieren. Ich bitte um Entschuldigung. Evtl. versuchen Sie es später nochmals. /(ENDE)\\"
                    case "failed":
                        return 200, "Oh, auch die Künstliche Intelligenz kann Fehler machen. Ihre Anfrage konnte nicht verarbeitet werden. Bitte versuchen Sie es erneut."
                    case "requires_action": # Aufruf lokaler Funktionen etc.
                        logging.info("Run requires action:")
                        results = await self.assistant_tools.execute_tool_calls(updated_run)
                        logging.debug(f"Results of function calls: {results}")
                        if results:
                            updated_run = await self.update_run(results, thread_id, updated_run.id)
                    case _: # Unknown state, let's break out here
                        logging.error(f"Problem beim Durchführen des Runs: {updated_run.status}")
                        return 500, f"*ISSUE* **Run Status: {updated_run.status}**"
                #time.sleep(1)
                pass # we'll check if after the actions are done the state changes

        except Exception as e: # Äußerer Try, um alle Fehler zu fangen
            logging.error(f"Chat-Error: {e}: {updated_run}")
            return 509, f"*ISSUE* **{e}**"
    
    async def update_run(self, tool_outputs, thread_id, run_id):
        # Sendet die verarbeiteten Tool-Ausgaben zurück an die OpenAI-API
        run = await self.async_api_call(
            lambda: self.client.beta.threads.runs.submit_tool_outputs(
                thread_id=thread_id,
                run_id=run_id,
                tool_outputs=tool_outputs
            )
        )
        return run
