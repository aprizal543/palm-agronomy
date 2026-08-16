from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Query

from app.api.deps import SessionDep
from app.repositories.knowledge import KnowledgeRepository
from app.schemas.knowledge import RagAnswer
from app.services.rag import build_grounded_answer

router = APIRouter()


@router.get("/search", response_model=RagAnswer)
async def search_verified_knowledge(
    session: SessionDep,
    query: Annotated[str, Query(min_length=5, max_length=500)],
    top_k: Annotated[int, Query(ge=1, le=5)] = 3,
):
    retrieval = await KnowledgeRepository(session).search(
        question=query,
        top_k=top_k,
        trace_id=uuid4(),
        channel="api",
    )
    answer = build_grounded_answer(query, retrieval)
    await session.commit()
    return answer
