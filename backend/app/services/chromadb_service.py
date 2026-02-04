import chromadb
from app.config import get_settings

settings = get_settings()


class ChromaDBService:
    def __init__(self):
        self.client = chromadb.HttpClient(host=settings.chromadb_host, port=settings.chromadb_port)
        self._collection = None

    @property
    def collection(self):
        if self._collection is None:
            self._collection = self.client.get_or_create_collection(
                name="patients",
                metadata={"hnsw:space": "cosine"},
            )
        return self._collection

    def add_patient(self, patient_id: str, document: str, metadata: dict, embedding: list[float]):
        self.collection.upsert(
            ids=[patient_id],
            documents=[document],
            metadatas=[metadata],
            embeddings=[embedding],
        )

    def search(self, query_embedding: list[float], n_results: int = 5) -> dict:
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        return results

    def get_all_ids(self) -> list[str]:
        result = self.collection.get(include=[])
        return result["ids"]

    def get_by_id(self, patient_id: str) -> dict:
        result = self.collection.get(
            ids=[patient_id],
            include=["documents", "metadatas"],
        )
        return result

    def delete(self, patient_id: str):
        self.collection.delete(ids=[patient_id])

    def count(self) -> int:
        return self.collection.count()

    def is_available(self) -> bool:
        try:
            self.client.heartbeat()
            return True
        except Exception:
            return False


chromadb_service = ChromaDBService()
