"""
Titel: user_threads.py

Beschreibung:   Implementiert die Verwaltung der Zuordnung zwischen Benutzern und ihren Threads in Azure Table Storage.
                Siehe Bemerkung Todo unten.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-03-28
Version: 1.0.0
Quellen: [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net

Todo: Umbenennung der Klasse in Users, da jetzt neben der User-Thread-Zuordnung auch weitere Benutzerdaten
      gespeichert werden.

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
            logging.info(f"Thread für Benutzer {user_id} nicht gefunden.")
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
                "ThreadId": thread_id,
                "ExtendedEvents": "0"
            }
            self.table_client.upsert_entity(entity=user)
            logging.info(f"Thread-ID {thread_id} für Benutzer {user_id} gesetzt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Thread-ID für Benutzer {user_id}.")
            raise IOError("ThreadPersistenceFailed") from e
        
    def get_extended_events(self, user_id: str) -> bool:
        """
        Ruft die Schalterstellung für erweiterte Events für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Schalterstellung; 0 für ausgeschaltet, 1 für eingeschaltet.
        """
        try:
            user = self.table_client.get_entity(partition_key="Chat", row_key=user_id)
            return bool(int(user["ExtendedEvents"])) # Schalter ist 0 oder 1, aber hier als bool zurückgegeben
        except Exception as e:
            logging.info(f"Erweiterte Events für Benutzer {user_id} nicht gefunden.")
            raise LookupError("ExtendedEventsNotFound") from e
        
    def set_extended_events(self, user_id: str, extended_events: bool) -> bool:
        """
        Speichert oder aktualisiert die Schalterstellung für erweiterte Events für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param extended_events: Die zu speichernde Schalterstellung; True für eingeschaltet, False für ausgeschaltet.
        :return: True, wenn die Operation erfolgreich war, sonst False.
        """
        try:
            user = self.table_client.get_entity(partition_key="Chat", row_key=user_id)
            user["ExtendedEvents"] = "1" if extended_events else "0"
            self.table_client.upsert_entity(entity=user)
            logging.info(f"Erweiterte Events für Benutzer {user_id} auf {int(extended_events)} gesetzt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der erweiterten Events für Benutzer {user_id}.")
            raise IOError("ExtendedEventsPersistenceFailed") from e
    
    def get_user_data(self, user_id: str) -> dict:
        """
        Ruft die Benutzerdaten für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Die Benutzerdaten als Dictionary.
        """
        try:
            user = self.table_client.get_entity(partition_key="Chat", row_key=user_id)
            return user
        except Exception as e:
            logging.info(f"Benutzerdaten für Benutzer {user_id} nicht gefunden.")
            raise LookupError("UserDataNotFound") from e
        
    def set_user_data(self, user_id: str, user_data: dict) -> bool:
        """
        Speichert oder aktualisiert die Benutzerdaten für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param user_data: Die zu speichernden Benutzerdaten.
        :return: True, wenn die Operation erfolgreich war, sonst False.
        """
        try:
            user_data["PartitionKey"] = "Chat"
            user_data["RowKey"] = user_id
            self.table_client.upsert_entity(entity=user_data)
            logging.info(f"Benutzerdaten für Benutzer {user_id} gesetzt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Benutzerdaten für Benutzer {user_id}.")
            raise IOError("UserDataPersistenceFailed") from e

    def close(self):
        """
        Schließt die Verbindung zum Azure Table Service.
        """
        self.table_service.close()
        logging.info("Verbindung zu Azure Table Service geschlossen.")
