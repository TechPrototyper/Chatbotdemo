"""
Titel: assistant_tools.py

Beschreibung:   Enthält Funktionen, die vom Assistenten verwendet werden, um verschiedene Aufgaben auszuführen.
                Zum einen enthält es diese von der KI aufgerufenen Funktionen selbst, als async Methoden, im zweiten Teil; im ersten
                Teil stehen noch die Methoden zum parallelen Ausführen der Hilfsfunktionen.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-04
Version: 1.0.0
Quellen: [OpenAI API Dokumentation]
Kontakt: projekte@tim-walter.net
"""

import logging
import asyncio
import json

# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

class AssistantTools:
    def __init__(self):
        pass

    #TODO: Objekttypen von run einfügen
    async def execute_tool_calls(self, run) -> list:
        """
        Führt eine Liste von Tool Calls aus und gibt die Ergebnisse zurück.

        :param run: Ein OpenAI/AzureOpenAI Run Objekt, das eine Liste von Tool Calls enthält, die ausgeführt werden sollen.
        :type tool_calls: list
        :return: Eine Liste von Ergebnissen der Tool Calls.
        :rtype: list
        """

        queue = asyncio.Queue()

        tasks = [self._handle_tool_call(tool_call, queue) for tool_call in run.required_action.submit_tool_outputs.tool_calls]
        await asyncio.gather(*tasks)

        tool_outputs = []
        while not queue.empty():
            tool_outputs.append(await queue.get())

        return tool_outputs

    #TODO: Objekttypen von tool_call einfügen
    async def _handle_tool_call(self, tool_call, queue: asyncio.Queue) -> None:
        """
        Führt einen einzelnen Tool Call aus und gibt das Ergebnis (threadsafe) in eine Queue.

        :param tool_call: Der Tool Call, der ausgeführt werden soll.
        :type tool_call: dict
        :param queue: Die Queue, in die das Ergebnis geschrieben wird.
        :type queue: asyncio.Queue
        """
        if tool_call.type == "function": # Other types not handled here yet
            function_name = tool_call.function.name
            args = json.loads(tool_call.function.arguments)
            logging.info(f"I shall call function {function_name} with arguments {args}")
            method = getattr(self, function_name, None)
            if method:
                logging.info(f"Method found in AssistantTools Class - calling {function_name} with arguments {args}")
                try:
                    logging.info(f"Calling {function_name} with arguments {args}")
                    output_value = await method(**args)
                    result = {"tool_call_id": tool_call.id, "output": output_value}
                except Exception as e:
                    logging.error(f"Error calling {function_name} with arguments {args}: {e}")
            else:
                logging.error(f"Function {function_name} not found.")

            await queue.put(result)
            logging.debug(f"Result of {function_name}, which is {result}, was added to the results queue.")
        else:
            logging.error(f"Tool Call type {tool_call.type} is not supported yet.")
            raise NotImplementedError(f"Tool Call type {tool_call.type} is not supported yet.")

    """
    Teil 2 der AssistantTools-Klasse
    
    Die folgenden Methoden sind die von der KI aufgerufenen Funktionen.
    Damit sie aufgerufen werden, müssen sie im Assistenten deklariert werden.
    Dies geschieht momentan noch manuell.
    """


    async def set_read_along(self, email: str, read_along: str) -> str:
        """
        Setzt den Read-Along-Modus für einen Benutzer.

        :param email: Die E-Mail-Adresse des Benutzers.
        :type email: str
        :param read_along: Der Status des Read-Along-Modus.
        :type read_along: str
        :return: Eine Bestätigungsmeldung.
        :rtype: str
        """

        from user_threads import UserThreads

        try:
            toggle = int(read_along)
        except ValueError:
            logging.error(f"Invalid value for read along: {read_along}")
            return "Invalid value for read along. Please use 0 or 1."
        
        #Todo: Man sollte sich überlegen, ob die Verbindung zum Storage Account bzw. zur dortigen Benutzer-
        #tabelle nicht während des gesamten Dialogschrittes offen gehalten wird, und die Verbindung
        #hier in Methoden injiziert wird, um unnötigen Verbindungsauf- und abbau zu vermeiden.

        #Todo: offenbar kennt UserThreads auch kein __enter__ und __exit__ für einen Kontext.
        #Wenn schon Verbindung aufbauen, dann bitte mit With-Clause. Ändern.

        #Todo: Die UserThreads() Klasse muss, so oder so, asynchron werden...
        # user_threads = await UserThreads.create_async()
        user_threads = UserThreads() #... ist sie aber noch nicht :-()

        current_read_along_setting = await user_threads.get_extended_events(email)

        if current_read_along_setting == toggle:
            logging.info(f"Read along for {email} is already set to {read_along}")
            ret_str = f"Es musste nichts gemacht werden, Mitlesen war für {email} bereits {'deaktiviert.' if toggle==0 else 'aktiviert.'}"
        else:
            await user_threads.set_extended_events(email, read_along)
            logging.info(f"Read along for {email} now set to {read_along}")
            ret_str = f"Mitlesen für {email} wurde erfolgreich {'deaktiviert' if toggle==0 else 'aktiviert'}"

        await user_threads.close()
        
        logging.info(f"Setting read along for {email} to {read_along}")

        return ret_str