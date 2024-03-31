"""
Titel: user_threads.py

Beschreibung:   Implementiert die Verwaltung der Zuordnung zwischen Benutzern und ihren Threads in Azure Table Storage.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-03-28
Version: 1.0.0
Quellen: [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net
"""

import os
import logging
from azure.data.tables import TableServiceClient

# Konfiguration des Loggings
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class UserThreads:
    """
    Verwaltet die Zuordnung zwischen Benutzern und ihren Threads in Azure Table Storage.
    """
    
    def __init__(self):
        """
        Initialisiert die Verbindung zu Azure Table Storage und prüft die Umgebungsvariable.
        """
        self.connection_string = os.getenv("AZURE_STORAGE_CONNECTION_STRING")
        if not self.connection_string:
            logging.error("AZURE_STORAGE_CONNECTION_STRING Umgebungsvariable ist nicht gesetzt.")
            raise EnvironmentError("AZURE_STORAGE_CONNECTION_STRING Umgebungsvariable ist nicht gesetzt. Function App muss konfiguriert werden.")
        
        self.table_name = "UserThreads"
        self.table_service = TableServiceClient.from_connection_string(conn_str=self.connection_string)
        self.table_client = self.table_service.get_table_client(table_name=self.table_name)
        logging.info("Verbindung zu Azure Table Service hergestellt.")

    def get_id(self, user_id: str) -> str:
        """
        Ruft die Thread-ID für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Die ID des Threads.
        """
        try:
            user = self.table_client.get_entity(partition_key="Chat", row_key=user_id)
            return user["ThreadId"]
        except Exception as e:
            logging.error(f"Thread für Benutzer {user_id} nicht gefunden.")
            raise LookupError("ThreadNotFound") from e

    def set_id(self, user_id: str, thread_id: str) -> bool:
        """
        Speichert oder aktualisiert die Thread-ID für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param thread_id: Die zu speichernde Thread-ID.
        :return: True, wenn die Operation erfolgreich war, sonst False.
        """
        try:
            user = {
                "PartitionKey": "Chat",
                "RowKey": user_id,
                "ThreadId": thread_id
            }
            self.table_client.upsert_entity(entity=user)
            logging.info(f"Thread-ID {thread_id} für Benutzer {user_id} gesetzt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Thread-ID für Benutzer {user_id}.")
            raise IOError("ThreadPersistenceFailed") from e
    
    def close(self):
        """
        Schließt die Verbindung zum Azure Table Service.
        """
        self.table_service.close()
        logging.info("Verbindung zu Azure Table Service geschlossen.")
