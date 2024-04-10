"""
Titel: my_cloudevents.py
Beschreibung:   Implementiert eine Basisklasse für CloudEvents, die in Azure verwendet werden können.
Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-04
Version: 1.0.0
Quellen: [Azure Event Grid], [CloudEvents Spezifikation]
Kontakt: projekte@tim-walter.net
"""

"""
Vorläufiges Design; zu viel Boilerplate Code, aber so sehr flexibel.

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


class UserRegisteredEvent(BaseCloudEvent):
    def __init__(self, user_details: dict) -> None:

        type = "user.registered"

        super().__init__(
            source="",
            type=type,
            data=user_details
        )

class UserLoginEvent(BaseCloudEvent):
    def __init__(self, user_details: dict) -> None:
        
        type="user.login"
        
        super().__init__(
            source="",
            type=type,
            data=user_details
        )

class PromptFromUserEvent(BaseCloudEvent):
    def __init__(self, prompt_details: dict) -> None:
        
        type="user.prompt"
        
        super().__init__(
            source="",
            type=type,
            data=prompt_details
        )

class PromptToUserEvent(BaseCloudEvent):
    def __init__(self, prompt_details: dict) -> None:
        
        type="user.response"
        
        super().__init__(
            source="",
            type=type,
            data=prompt_details
        )

class PromptToAIEvent(BaseCloudEvent):
    def __init__(self, prompt_details: dict) -> None:
        
        type="backend.prompt"
        
        super().__init__(
            source="",
            type=type,
            data=prompt_details
        )

class PromptFromAIEvent(BaseCloudEvent):
    def __init__(self, prompt_details: dict) -> None:
        
        type="backend.response"
        
        super().__init__(
            source="",
            type=type,
            data=prompt_details
        )

class ChatEndedEvent(BaseCloudEvent):
    def __init__(self, chat_summary_details: dict) -> None:
        
        type="user.chatended"
        
        super().__init__(
            source="",
            type=type,
            data=chat_summary_details
        )

class ErrorEvent(BaseCloudEvent):
    def __init__(self, error_details: dict) -> None:
        
        type="system.error"
        
        super().__init__(
            source="",
            type=type,
            data=error_details
        )

