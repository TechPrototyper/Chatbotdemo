"""
Titel: my_cloudevents.py
Beschreibung:   Implementiert eine Basisklasse für CloudEvents, die in Azure verwendet werden können.
Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-11
Version: 1.1.0
Quellen: [Azure Event Grid], [CloudEvents Spezifikation]
Kontakt: projekte@tim-walter.net
"""

"""
Version 1.1: Umstellung auf Factory Methoden
"""

from datetime import datetime, timezone
import uuid
from cloudevents.http import CloudEvent # cloudevents library contains Format and HTTP bindings for CloudEvents
from os import getenv

# Requires environment variables:
# - EVENT_GRID_APPLICATION_ID
# - APP_NAMESPACE

class BaseCloudEvent:
    def __init__(self, source: str, type: str, data: dict) -> None:
        
        if source:
            self.source = source
        else:
            try:
                self.source = getenv("EVENT_GRID_APPLICATION_ID")
            except KeyError:
                raise ValueError("Error: source must be provided or set as environment variable EVENT_GRID_APPLICATION_ID")
        
        try:
            self.type = getenv("APP_NAMESPACE")+type # APP_NAMESPACE is the namespace of the application; has been moved here from the UserRegisteredEvent class
        except KeyError:
            raise ValueError("Error: App namespace  must be provided or set as environment variable APP_NAMESPACE")
        
        self.specversion = '1.0'
        self.id = str(uuid.uuid4())
        self.time = datetime.now(timezone.utc).isoformat()
        self.data = data

    def to_cloudevent(self):
        attributes = {
            "specversion": self.specversion,
            "id": self.id,
            "source": self.source,
            "type": self.type,
            "time": self.time,
            "data": self.data
        }
        return CloudEvent(attributes, self.data)

    @classmethod
    def create_user_registered_event(cls, user_details: dict):
        return cls("", "user.registered", user_details).to_cloudevent()

    @classmethod
    def create_user_login_event(cls, user_details: dict):
        return cls("", "user.login", user_details).to_cloudevent()

    @classmethod
    def create_prompt_from_user_event(cls, prompt_details: dict):
        return cls("", "user.prompt", prompt_details).to_cloudevent()

    @classmethod
    def create_prompt_to_user_event(cls, prompt_details: dict):
        return cls("", "user.response", prompt_details).to_cloudevent()

    @classmethod
    def create_prompt_to_ai_event(cls, prompt_details: dict):
        return cls("", "backend.prompt", prompt_details).to_cloudevent()

    @classmethod
    def create_prompt_from_ai_event(cls, prompt_details: dict):
        return cls("", "backend.response", prompt_details).to_cloudevent()

    @classmethod
    def create_chat_ended_event(cls, chat_summary_details: dict):
        return cls("", "user.chatended", chat_summary_details).to_cloudevent()

    @classmethod
    def create_error_event(cls, error_details: dict):
        return cls("", "system.error", error_details).to_cloudevent()

