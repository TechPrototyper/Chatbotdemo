"""
Titel: user_threads.py

Beschreibung:   Implementiert die Verwaltung der Zuordnung zwischen Benutzern und ihren Threads in Azure Table Storage.
                Umstellung auf asnychrone Methoden am 04.04.2024.

Autor: Tim Walter (TechPrototyper)
Datum: 2024-04-04
Version: 1.0.0
Quellen: [Azure Table Storage Dokumentation]
Kontakt: projekte@tim-walter.net

Todo: Umbenennung der Klasse in Users, da jetzt neben der User-Thread-Zuordnung auch weitere Benutzerdaten
      gespeichert werden.

"""

import os
import logging
from azure.data.tables.aio import TableServiceClient

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
        logging.info(f"UserThreads-Objekt erstellt.")

        # In der async-Variante haben wir keine dauerhaften Verbindungs-Objekte, sondern müssen die Connection per Request händeln:
        # self.table_service = TableServiceClient.from_connection_string(conn_str=self.connection_string)
        # self.table_client = self.table_service.get_table_client(table_name=self.table_name)
        # logging.info("Verbindung zu Azure Table Service hergestellt.")

    async def get_id(self, user_id: str) -> str:
        """
        Ruft die Thread-ID für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Die ID des Threads.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)
                user = await table_client.get_entity(partition_key="Chat", row_key=user_id)
            logging.info(f"Thread für Benutzer gefunden, ID: {user['ThreadId']}")
            return user["ThreadId"]
        except Exception as e:
            logging.info(f"Thread für Benutzer {user_id} nicht gefunden.")
            raise LookupError("ThreadNotFound") from e

    async def set_id(self, user_id: str, thread_id: str) -> int:
        """
        Speichert oder aktualisiert die Thread-ID für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param thread_id: Die zu speichernde Thread-ID.
        :return: True, wenn die Operation erfolgreich war, sonst False.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)
                user = {
                    "PartitionKey": "Chat",
                    "RowKey": user_id,
                    "ThreadId": thread_id,
                    "ExtendedEvents": "0"
                }
                await table_client.upsert_entity(entity=user)
            
            logging.info(f"Thread-ID {thread_id} für Benutzer {user_id} gesetzt.")
            return 1
        
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Thread-ID für Benutzer {user_id}.")
            raise IOError("ThreadPersistenceFailed") from e
        
    async def get_extended_events(self, user_id: str) -> int:
        """
        Ruft die Schalterstellung für erweiterte Events für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Schalterstellung; 0 für ausgeschaltet, 1 für eingeschaltet.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)
                user = await table_client.get_entity(partition_key="Chat", row_key=user_id)
            return int(user["ExtendedEvents"]) # Schalter ist 0 oder 1
        except Exception as e:
            logging.info(f"Erweiterte Events für Benutzer {user_id} nicht gefunden.")
            raise LookupError("ExtendedEventsNotFound") from e
        
    async def set_extended_events(self, user_id: str, extended_events: int) -> int:
        """
        Speichert oder aktualisiert die Schalterstellung für erweiterte Events für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param extended_events: Die zu speichernde Schalterstellung; True für eingeschaltet, False für ausgeschaltet.
        :return: 1, wenn die Operation erfolgreich war, sonst 0.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)            
                user = await table_client.get_entity(partition_key="Chat", row_key=user_id)
                user["ExtendedEvents"] = int(extended_events)
                await table_client.upsert_entity(entity=user)
            logging.info(f"Erweiterte Events für Benutzer {user_id} auf {int(extended_events)} gesetzt.")
            return 1
        except Exception as e:
            logging.error(f"Fehler beim Speichern der erweiterten Events für Benutzer {user_id}.")
            raise IOError("ExtendedEventsPersistenceFailed") from e
    
    async def get_user_data(self, user_id: str) -> dict:
        """
        Ruft die Benutzerdaten für einen gegebenen Benutzer ab.
        
        :param user_id: Die ID des Benutzers.
        :return: Die Benutzerdaten als Dictionary.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)
                user = await table_client.get_entity(partition_key="Chat", row_key=user_id)
            return user
        except Exception as e:
            logging.info(f"Benutzerdaten für Benutzer {user_id} nicht gefunden.")
            raise LookupError("UserDataNotFound") from e
        
    async def set_user_data(self, user_id: str, user_data: dict) -> int:
        """
        Speichert oder aktualisiert die Benutzerdaten für einen Benutzer.
        
        :param user_id: Die ID des Benutzers.
        :param user_data: Die zu speichernden Benutzerdaten.
        :return: 1, wenn die Operation erfolgreich war, sonst 0.
        """
        try:
            async with TableServiceClient.from_connection_string(self.connection_string) as table_service:
                table_client = table_service.get_table_client(table_name=self.table_name)
                user_data["PartitionKey"] = "Chat"
                user_data["RowKey"] = user_id
                await table_client.upsert_entity(entity=user_data)
            logging.info(f"Benutzerdaten für Benutzer {user_id} gesetzt.")
            return True
        except Exception as e:
            logging.error(f"Fehler beim Speichern der Benutzerdaten für Benutzer {user_id}.")
            raise IOError("UserDataPersistenceFailed") from e

    async def close(self):
        """
        Schließt die Verbindung zum Azure Table Service.
        """
        # await self.table_service.close()
        # logging.info("Verbindung zu Azure Table Service geschlossen.")

        # Hier gibt es wegen der Umstellung auf async nichts mehr zu tun,
        # da die Verbindung immer mit einem Kontext an Ort und Stelle in jeder Methode auf- und abgebaut wird.

        pass
