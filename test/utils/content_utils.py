import uuid
from typing import Tuple

from criadex.index.index_api.document.index_objects import DocumentConfig, Element, ElementType
from criadex.index.index_api.question.index_objects import QuestionConfig, RelatedPrompt


def sample_document() -> DocumentConfig:
    """
    Test the document fixture to ensure it is loaded correctly.

    """

    return DocumentConfig(
        nodes=[
            Element(
                type=ElementType.NARRATIVE_TEXT,
                text="[PYTEST] This is a test document NarrativeText element.",
                metadata={
                    "test_metadata_key": "test_metadata_value"
                }
            ),
            Element(
                type=ElementType.IMAGE,
                text="[PYTEST] This is a test document Image element.",
            ),

            # Must be the last node
            Element(
                type=ElementType.NARRATIVE_TEXT,
                text="[PYTEST] This NarrativeText element should be updated.",
            )
        ]
    )


def sample_document_updated() -> DocumentConfig:
    """
    Modified version of the sample doc.

    """

    # Update the last node
    sample_doc = sample_document()
    update_id: str = str(uuid.uuid4())
    sample_doc.nodes[-1].text = f"[PYTEST] [update_id={update_id}] This NarrativeText element has been updated."
    sample_doc.nodes[-1].metadata = {'update_id': update_id} # Explicitly set metadata

    return sample_doc


def sample_question() -> QuestionConfig:
    """
    A sample question
    :return: The sample question
    """

    return QuestionConfig(
        questions=[
            "[PYTEST] This is a test question.",
        ],
        answer="[PYTEST] This is a test answer.",
        related_prompts=[
            RelatedPrompt(
                prompt="[PYTEST] This is a test related prompt.",
                label="test"
            )
        ]
    )


def sample_question_updated() -> Tuple[QuestionConfig, str]:
    """
    Modified version of the sample question.

    """

    # Update the last node
    sample_q = sample_question()
    update_id: str = str(uuid.uuid4())
    sample_q.questions[0] = f"[PYTEST] [update_id={update_id}] This is a test question."
    sample_q.answer = f"[PYTEST] [update_id={update_id}] This is a test answer."

    return sample_q, update_id
