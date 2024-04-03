from azure.eventgrid import EventGridPublisherClient
from azure.core.credentials import AzureKeyCredential
import os
from typing import Optional

class EventGridPublisher:

    def __init__(self, endpoint: Optional[str] = None) -> None:

        if endpoint:
            self.endpoint = endpoint
        else:
            try:
                self.endpoint = os.environ["EVENT_GRID_ENDPOINT"]
                self.credential = AzureKeyCredential(os.environ["EVENT_GRID_ACCESS_KEY"])
            except KeyError:
                raise KeyError("Error: endpoint must be provided or set as environment variable EVENT_GRID_ENDPOINT, access key must be provided or set as environment variable EVENT_GRID_ACCESS_KEY")
        
        try:
            self.client = EventGridPublisherClient(self.endpoint, self.credential)
        except:
            raise ConnectionError ("Error: could not create EventGridPublisherClient")

    def send_event(self, event: dict) -> bool:
        try:
            self.client.send([event])
            return True
        except Exception as e:
            raise ConnectionError(f"Error: could not send event to grid: {e}")
        
    def close(self) -> bool:
        if hasattr(self, 'client') and hasattr(self.client, 'close'):
            try:
                self.client.close()
                return True
            except Exception as e:
                raise ConnectionError(f"Error: could not close EventGridPublisherClient: {e}")
            
    def __enter__(self) -> "EventGridPublisher":
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> bool:
        self.close()
        return False
    
    