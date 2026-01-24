from typing import Dict

class DocumentStore:
    def __init__(self):
        self._documents: Dict[str, dict] = {}
    
    def add(self, doc_id: str, title: str, pages: int) -> dict:
        doc = {
            "id": doc_id,
            "title": title,
            "pages": pages,
        }
        self._documents[doc_id] = doc
        return doc
    
    def get(self, doc_id: str) -> dict | None:
        return self._documents.get(doc_id)
    
    def exists(self, doc_id: str) -> bool:
        return doc_id in self._documents

documents = DocumentStore()
