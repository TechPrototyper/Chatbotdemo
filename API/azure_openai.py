"""
Titel: azure_openai.py

Beschreibung: Stellt die Kommunikation zwischen der Funktion App und der Azure OpenAI API her.
              Diese Datei nutzt spezifische Azure OpenAI Endpunkte und Konfigurationen für die Interaktion.
              "Schwesterdatei" ist o_openai.py, die auf allgemeine OpenAI-Endpunkte zugreift.
              Modul ist nun vollständig auf async umgestellt. Eine Async-Library für die Assistant-API
              war noch nicht verfügbar, wird aber mit Release der API seitens OpenAI sicher verfügbar sein.
              Auf die Verwendung der Hilfsmethode async_api_call() kann dann später verzichtet werden.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-11
Version: 1.1.0
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
from event_grid_publisher import EventGridPublisher
from assistant_tools import AssistantTools
import re
from datetime import datetime


# Configure logging
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

            user_details = {"email": user_email, "thread_id": thread_id}

            # That's not precisely right, because we'not only coming here on login,
            # but in fact on every prompt. Hence, we should not send this event here:
            # async with EventGridPublisher() as publisher:
            #     await publisher.send_event("user.login", user_details)

        except LookupError: # No known conversation for this user as of now
            try:
                thread = await self.async_api_call(self.client.beta.threads.create)
                thread_id = thread.id 
                await self.threads.set_id(user_email, thread_id)
                # After we're done, we'll let the world know that a user has registered...
                user_details = {"email": user_email, "thread_id": thread_id}                
                async with EventGridPublisher() as publisher:
                    await publisher.send_event("user.registered", user_details)

            except Exception as e:
                logging.error(f"Fehler bei der Thread-Erstellung oder -Speicherung: {e}")
                raise
        except Exception as e:
            logging.error(f"Ein unbekannter Fehler beim Zugriff auf die Thread-Historie ist aufgetreten: {e}")
            raise

        # ... and return the Thread-Id for further processing
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
            # Did we chat already? If so, let's continue, if not, let's start:
            thread_id = await self.get_or_create_thread(user_email)

            # Is the user ok with us reading the conversation?
            transscript_allowed = await self.check_transscript_permission(user_email)

            # GDPR: Are we allowed to read the conversation?
            # If so, we will send the prompt typed in to the EventGrid to whom it may concern
            if transscript_allowed == 1:
                details = {"email": user_email, "Name: ": user_name,"prompt": user_prompt}
                async with EventGridPublisher() as publisher:
                    await publisher.send_event("prompt.from.user", details)            

            # Let's embed the user's input into some information block for the LLM:
            modified_prompt = await self.create_modified_prompt(user_name, user_email, user_prompt, transscript_allowed)        

            # Prepare the message to be sent to the Azure OpenAI API
            await self.prepare_message(thread_id, user_name, user_email, modified_prompt)

            if transscript_allowed == 1: # If we're allowed...
                details = {"email": user_email, "Name: ": user_name,"prompt": modified_prompt}
                async with EventGridPublisher() as publisher: # we let the world know that we've sent the prompt to the AI
                    await publisher.send_event("prompt.to.ai", details)   

            # We've added a message to the thread, and now we'll order the LLM to work on the dialog by starting a run
            # We may have to do things in between such as executing local functions etc.
            http_status, response_body = await self.create_and_monitor_run(thread_id, user_name, user_email, transscript_allowed)

            # And return hopefully something that makes sense to the user
            return http_status, response_body

        except Exception as e: # Outer try, just for safety reasons
            logging.error(f"Chat-Error: {e}")
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
    
    async def check_transscript_permission(self, user_email: str) -> bool:
        u = UserThreads()
        transscript_allowed = await u.get_extended_events(user_email)
        logging.info(f"Transscript allowance checked for {user_email}: Value is {str(transscript_allowed)}")
        return transscript_allowed
    
    async def create_modified_prompt(self, user_name: str, user_email: str, user_prompt: str, transscript_allowed: int) -> str:
        time_stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        modified_prompt = f"Mein Name: {user_name}\nMeine E-Mail Adresse: {user_email}\nDatum und Uhrzeit: {time_stamp}\nStatus der Mitleseerlaubnis: {str(transscript_allowed)}\nMein Prompt: {user_prompt}"
        logging.info(f"Modified prompt created: {modified_prompt}")
        return modified_prompt
    
    async def prepare_message(self, thread_id: str, user_name: str, user_email: str, modified_prompt: str):

        while True: # We have to loop because we may find the thread being in a run;
                    # in this case we have to cancel it first and then go again
            try:
                await self.async_api_call(lambda: self.client.beta.threads.messages.create(
                    thread_id=thread_id,
                    role="user",
                    content=modified_prompt
                ))
                logging.info(f"Prepare Message: Object created successfully.")
                break
            except Exception as e: # Message could not be created/sent, let's check the run status
                logging.info(f"Prepare Message Error: {e}")
                
                # If the message is rejected because the thread has an active run,
                # the error message from OpenAI will contain the thread_id and run_id - we can extract them:
                error_str = str(e) # From a string
                if "Can't add messages to" in error_str and "while a run" in error_str and "is active." in error_str:
                    # I love regex... 
                    thread_id_match = re.search(r"thread_([a-zA-Z0-9]+)", error_str)
                    run_id_match = re.search(r"run_([a-zA-Z0-9]+)", error_str)
                    
                    if thread_id_match and run_id_match: # And indeed, we found'em:
                        thread_id = "thread_"+thread_id_match.group(1)
                        run_id = "run_"+run_id_match.group(1)
                        logging.info(f"Prepare message: Error reports Thread ID: {thread_id}, Run ID: {run_id}")

                        # Let's cancel the run and try again

                        await self.async_api_call(
                            lambda: self.client.beta.threads.runs.cancel(run_id=run_id, thread_id=thread_id)
                        )

                        logging.info(f"Prepare Message: Run {run_id} cancelled.")

                    else:
                        logging.info("Prepare message: Unknown error, no Id's could be extracted.")
                else:
                    logging.error(f"Prepare Message: Unknown error: {e}")
                    #TODO: Fehlerbehandlung anpassen
                    # return 500, f"*ISSUE* **{e}**"

    async def create_and_monitor_run(self, thread_id: str, user_name: str, user_email: str, transscript_allowed: int) -> str:

            # We've added a message to the thread, and now we'll order the LLM to work on the dialog by starting a run
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

                
                match updated_run.status: # Let's see where we got with the run so far...
                    case "completed": # We got a reply for the user from the LLM - this is what we want.
                        # So let's get it out of the thread ...
                        messages = await self.async_api_call(
                            lambda: self.client.beta.threads.messages.list(thread_id=thread_id)
                        )
                        # Well, a message should be longer then zero and contain something, right?
                        if messages.data and len(messages.data) > 0 and messages.data[0].content:
                            # Yeah, we got something, let's get it out of the JSON structure
                            return_prompt = messages.data[0].content
                            # And extract the text value from the JSON            
                            response_body = return_prompt[0].text.value     
                            logging.info(f"Response: {response_body}")

                            # If we're allowed to read the conversation, we'll send the response from the LLM to the EventGrid
                            if transscript_allowed == 1:
                                details = {"email": user_email, "Name: ": user_name,"prompt": response_body}                                
                                async with EventGridPublisher() as publisher:
                                    await publisher.send_event("prompt.from.ai", details)            

                                # Don't be surprised we're doing the same thing twice;
                                # This is due to envisioned future changes
                                # We may have to unwind magic strings here, or check for some trigger
                                # words, or whatever.
                                # In the future, the response from the AI may well be different to what we're
                                # sending to the user. Of course that is not the case right now, so it may look
                                # a bit redundant. But it's not :-)

                                details = {"email": user_email, "Name: ": user_name,"ai_prompt": response_body}
                                async with EventGridPublisher() as publisher:
                                    await publisher.send_event("prompt.to.user", details)            
                            
                            # Off we go:
                            return 200, response_body
                        else:
                            # Well, we got a message, but it's empty. That's bizarre. Wonder if that ever happens.
                            return 200, "Da fällt mir im Moment gerade nichts zu ein (Leere Nachricht von der KI)."
                    case "cancelled": # Should never happen, we have no feature to support cancelling an interaction such as in ChatGPT
                        # Watch the magic string here that tells the Frontend to finish the chat
                        return 200, "Chat abgebrochen. /(ENDE)\\"
                    case "cancelling": # Same here, although, if for any reason this is happening, we will actually wait until the state changes to "cancelled"
                        pass
                    case "pending": # Not sure whether this is a real valid state. It appears in documentation, but code editor does not recognize it for autocompletion
                        pass # Something is going to happen, but we don't know yet
                    case "expired":
                        return 200, "Ich bin scheinbar im Moment nicht in der Lage, eine Antwort zu formulieren. Ich bitte um Entschuldigung. Evtl. versuchen Sie es später nochmals. /(ENDE)\\"
                    case "failed":
                        return 200, "Oh, auch künstliche Intelligenz ist nicht unfehlbar, so wie Gott. Ihre Anfrage konnte nicht verarbeitet werden. Bitte versuchen Sie es erneut."
                    case "requires_action": # The AI wants to act autonomously, let's let it do so_
                        logging.info("In Run: Action required.")
                        # This nice function here will execute all known local functions simultaneously
                        # wait for all functions to finish, and settle the results; once we got'em, we'll
                        # be reporting them back to the LLM:
                        results = await self.assistant_tools.execute_tool_calls(updated_run)
                        logging.debug(f"In Run: Results from local function calls: {results}")
                        if results:
                            updated_run = await self.update_run(results, thread_id, updated_run.id)

                    case _: # Unknown state, let's break out here
                        logging.error(f"Problem beim Durchführen des Runs: {updated_run.status}")
                        return 500, f"*ISSUE* **Run Status: {updated_run.status}**"
                    
