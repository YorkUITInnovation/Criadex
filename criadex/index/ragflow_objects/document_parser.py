from criadex.index.ragflow_objects.schemas import RagflowBaseNode, RagflowTextNode, RagflowDocument

def default_id_func(i, document):
    return f"{document.doc_id}_{i}"

class RagflowDocumentParser:
    """
    Base parser for Ragflow documents.
    """
    @classmethod
    def class_name(cls):
        return "ragflow_document_parser"

    def get_nodes_from_documents(self, documents, show_progress=False, **kwargs):
        # Implement Ragflow document parsing logic
        return []

    @classmethod
    def build_nodes_from_document(cls, document: RagflowDocument):
        # Implement Ragflow node building logic
        return []

    def _parse_nodes(self, nodes, show_progress=False, **kwargs):
        # Not needed by this subclass
        raise NotImplementedError
