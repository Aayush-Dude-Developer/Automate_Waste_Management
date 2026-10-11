import json
import os
from typing import Dict, Any, List, Optional
from ..config import settings

class LocalDatabase:
    """Zero-dependency local JSON mock of Firestore for hackathon/development."""
    
    def __init__(self, storage_file: str = "local_db.json"):
        self.storage_file = storage_file
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Any]:
        if os.path.exists(self.storage_file):
            with open(self.storage_file, 'r') as f:
                return json.load(f)
        return {}

    def _save(self):
        with open(self.storage_file, 'w') as f:
            json.dump(self.data, f, indent=2)

    def _resolve_collection(self, collection_path: str) -> List[Dict]:
        if collection_path not in self.data:
            self.data[collection_path] = []
        return self.data[collection_path]

    def add_document(self, collection_path: str, document_id: str, data: Dict[str, Any]):
        collection = self._resolve_collection(collection_path)
        # update if exists
        for idx, doc in enumerate(collection):
            if doc.get("id") == document_id:
                collection[idx] = data
                self._save()
                return
        
        # append new
        collection.append(data)
        self._save()

    def get_document(self, collection_path: str, document_id: str) -> Optional[Dict[str, Any]]:
        collection = self._resolve_collection(collection_path)
        for doc in collection:
            if doc.get("id") == document_id:
                return doc
        return None

    def get_collection(self, collection_path: str) -> List[Dict[str, Any]]:
        return self._resolve_collection(collection_path)


class FirestoreDatabase:
    """Actual Google Cloud Firestore implementation placeholder."""
    def __init__(self):
        from google.cloud import firestore
        self.db = firestore.Client(
            project=settings.GOOGLE_CLOUD_PROJECT,
            database="default",
        )
        
    def add_document(self, collection_path: str, document_id: str, data: Dict[str, Any]):
        self.db.collection(collection_path).document(document_id).set(data)
        
    def get_document(self, collection_path: str, document_id: str) -> Optional[Dict[str, Any]]:
        doc = self.db.collection(collection_path).document(document_id).get()
        return doc.to_dict() if doc.exists else None

    def get_collection(self, collection_path: str) -> List[Dict[str, Any]]:
        docs = self.db.collection(collection_path).stream()
        return [doc.to_dict() for doc in docs]


def get_db():
    if settings.DATABASE_BACKEND == "firestore":
        try:
            return FirestoreDatabase()
        except Exception as e:
            print(f"Warning: Failed to initialize Firestore ({e}). Falling back to Local DB.")
            return LocalDatabase()
    else:
        return LocalDatabase()

# Singleton DB instance
db = get_db()
