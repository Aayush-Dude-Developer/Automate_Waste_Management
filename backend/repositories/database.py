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

    def query_collection(
        self,
        collection_path: str,
        filters: List[tuple[str, str, Any]] | None = None,
        order_by: tuple[str, str] | None = None,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        records = self.get_collection(collection_path)
        for field, operator, value in filters or []:
            if operator == "==":
                records = [record for record in records if record.get(field) == value]
            elif operator == ">=":
                records = [record for record in records if record.get(field) is not None and record[field] >= value]
            elif operator == "<":
                records = [record for record in records if record.get(field) is not None and record[field] < value]
            elif operator == "<=":
                records = [record for record in records if record.get(field) is not None and record[field] <= value]
            elif operator == "in":
                records = [record for record in records if record.get(field) in value]
            else:
                raise ValueError(f"Unsupported query operator: {operator}")
        if order_by:
            field, direction = order_by
            direction = direction.upper()
            if direction not in {"ASCENDING", "DESCENDING"}:
                raise ValueError(f"Unsupported sort direction: {direction}")
            records = sorted(
                records,
                key=lambda record: (record.get(field) is None, record.get(field)),
                reverse=direction == "DESCENDING",
            )
        if limit is not None:
            if limit < 1:
                raise ValueError("Query limit must be positive.")
            records = records[:limit]
        return records

    def count_collection(
        self,
        collection_path: str,
        filters: List[tuple[str, str, Any]] | None = None,
    ) -> int:
        return len(self.query_collection(collection_path, filters))

    def set_documents(self, documents: List[tuple[str, str, Dict[str, Any]]]):
        for collection_path, document_id, data in documents:
            collection = self._resolve_collection(collection_path)
            for idx, doc in enumerate(collection):
                if doc.get("id") == document_id:
                    collection[idx] = data
                    break
            else:
                collection.append(data)
        self._save()

    def create_documents(self, documents: List[tuple[str, str, Dict[str, Any]]]):
        if documents and self.get_document(documents[0][0], documents[0][1]):
            raise ValueError(f"Document {documents[0][1]} already exists.")
        self.set_documents(documents)

    def transition_document(
        self,
        collection_path: str,
        document_id: str,
        expected_status: str | None,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        current = self.get_document(collection_path, document_id)
        current_status = current.get("status") if current else None
        if current_status != expected_status:
            raise ValueError("Recommendation status changed; refresh and try again.")
        if current:
            self.add_document(collection_path, document_id, data)
        else:
            self.create_documents([(collection_path, document_id, data)])
        return data


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

    def query_collection(
        self,
        collection_path: str,
        filters: List[tuple[str, str, Any]] | None = None,
        order_by: tuple[str, str] | None = None,
        limit: int | None = None,
    ) -> List[Dict[str, Any]]:
        query = self.db.collection(collection_path)
        for field, operator, value in filters or []:
            query = query.where(field, operator, value)
        if order_by:
            direction = order_by[1].upper()
            if direction not in {"ASCENDING", "DESCENDING"}:
                raise ValueError(f"Unsupported sort direction: {direction}")
            query = query.order_by(order_by[0], direction=order_by[1].upper())
        if limit is not None:
            if limit < 1:
                raise ValueError("Query limit must be positive.")
            query = query.limit(limit)
        return [doc.to_dict() for doc in query.stream()]

    def count_collection(
        self,
        collection_path: str,
        filters: List[tuple[str, str, Any]] | None = None,
    ) -> int:
        query = self.db.collection(collection_path)
        for field, operator, value in filters or []:
            query = query.where(field, operator, value)
        results = query.count(alias="record_count").get()
        return int(results[0][0].value)

    def set_documents(self, documents: List[tuple[str, str, Dict[str, Any]]]):
        batch = self.db.batch()
        for collection_path, document_id, data in documents:
            batch.set(self.db.collection(collection_path).document(document_id), data)
        batch.commit()

    def create_documents(self, documents: List[tuple[str, str, Dict[str, Any]]]):
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import firestore

        if not documents:
            return
        transaction = self.db.transaction()

        @firestore.transactional
        def commit(transaction):
            for index, (collection_path, document_id, data) in enumerate(documents):
                reference = self.db.collection(collection_path).document(document_id)
                if index == 0:
                    transaction.create(reference, data)
                else:
                    transaction.set(reference, data)

        try:
            commit(transaction)
        except AlreadyExists as error:
            raise ValueError(f"Document {documents[0][1]} already exists.") from error

    def transition_document(
        self,
        collection_path: str,
        document_id: str,
        expected_status: str | None,
        data: Dict[str, Any],
    ) -> Dict[str, Any]:
        from google.cloud import firestore

        reference = self.db.collection(collection_path).document(document_id)
        transaction = self.db.transaction()

        @firestore.transactional
        def transition(transaction):
            snapshot = reference.get(transaction=transaction)
            current = snapshot.to_dict() if snapshot.exists else None
            current_status = current.get("status") if current else None
            if current_status != expected_status:
                raise ValueError("Recommendation status changed; refresh and try again.")
            if current:
                transaction.set(reference, data)
            else:
                transaction.create(reference, data)

        transition(transaction)
        return data


def get_db():
    if settings.DATABASE_BACKEND == "firestore":
        try:
            return FirestoreDatabase()
        except Exception as e:
            raise RuntimeError("Firestore is configured but could not be initialized.") from e
    else:
        return LocalDatabase()

# Singleton DB instance
db = get_db()
