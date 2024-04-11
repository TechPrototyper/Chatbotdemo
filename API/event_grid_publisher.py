"""
Titel:          event_grid_publisher.py
Beschreibung:   Sendet Events ans Azure Event Grid.
                Umstellung auf async an 04.04.2024.
                Umstellung auf Factory-Pattern an 11.04.2024.
Autor:          Tim Walter (TechPrototyper)
Datum:          2024-04-11
Version:        1.2.0
Quellen:        [Azure Event Grid]
Kontakt:        projekte@tim-walter.net
"""

"""
Refactored. Now uses Event-Factory in my_cloudevents.py
and identifies the correct factory method by using Python's reflection.
This keeps boiler plate code at a minimum and is very effective.
"""

from azure.eventgrid.aio import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential
import os
import asyncio
import logging
from my_cloudevents import BaseCloudEvent

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class EventGridPublisher:
    def __init__(self):
        try:
            self.endpoint = os.getenv("EVENT_GRID_ENDPOINT")
            self.credential = AzureKeyCredential(os.getenv("EVENT_GRID_ACCESS_KEY"))
        except KeyError as e:
            logging.error(f"Error: {e}")
            raise

    async def __aenter__(self):
        self.client = EventGridPublisherClient(self.endpoint, self.credential)
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            logging.error(f"Error: {exc_type}: {exc_val}")

        await self.client.close()


    async def send_event(self, event_type: str, details: dict):
        # Use reflection to get the correct factory method
        # First, convert "." to "_" in the event type to match the method name
        method_name = f"create_{event_type.replace('.', '_')}_event"

        # Now look the Method up in the BaseCloudEvent class
        event_factory_method = getattr(BaseCloudEvent, method_name, None)

        # No factroy for the event_type passed...
        if not event_factory_method:
            # ... leads to a ValueError:
            raise ValueError(f"EventGridPublisher: Event factory method for {event_type} not found.")
        
        # Otherwise, create the event...
        event = event_factory_method(details)

        try:
            # ... and send it
            await self.client.send([event])
            logging.info(f"EventGridPublisher: {event_type} Event sent to grid.")

        except Exception as e:
            logging.error(f"EventGridPublisher: {event_type} Event failed to publish: {e}")