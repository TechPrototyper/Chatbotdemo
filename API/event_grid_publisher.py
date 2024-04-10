"""
Titel:          event_grid_publisher.py
Beschreibung:   Sendet Events ans Azure Event Grid.
                Umstellung auf async an 04.04.2024.
Autor:          Tim Walter (TechPrototyper)
Datum:          2024-04-10
Version:        1.0.1
Quellen:        [Azure Event Grid]
Kontakt:        projekte@tim-walter.net
"""

from azure.eventgrid.aio import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential
import os
# from typing import Optional
import logging
import asyncio

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

from azure.eventgrid.aio import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential
import os
import asyncio
import logging

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

    async def send_event(self, event):
        await self.client.send([event])
