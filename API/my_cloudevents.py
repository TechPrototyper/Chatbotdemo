"""
Titel: my_cloudevents.py
Beschreibung:   Implementiert eine Basisklasse für CloudEvents, die in Azure verwendet werden können.
Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-03
Version: 1.0.0
Quellen: [Azure Event Grid], [CloudEvents Spezifikation]
Kontakt: projekte@tim-walter.net
"""

from datetime import datetime, timezone
import uuid
from cloudevents.http import CloudEvent # cloudevents library contains Format and HTTP bindings for CloudEvents
from os import getenv

# Insert documentation here

class BaseCloudEvent:
    def __init__(self, source: str, type: str, data: dict) -> None:
        
        if source:
            self.source = source
        else:
            try:
                self.source = getenv("EVENT_GRID_APPLICATION_ID")
            except KeyError:
                raise ValueError("Error: source must be provided or set as environment variable EVENT_GRID_APPLICATION_ID")
        
        self.type = type
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
        try:
            type=getenv("APP_NAMESPACE")+"user.registered"
        except KeyError:
            raise ValueError("Error: App namespace  must be provided or set as environment variable APP_NAMESPACE")
        
        #TODO:
        # Let's check if the user_details are complete / valid
        # before passing them to the base class

        super().__init__(
            source="",
            type=type,
            data=user_details
        )

