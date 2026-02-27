import asyncio
import re
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.ollama_service import ollama_service
from app.services.chromadb_service import chromadb_service
from app.services.security_service import security_scan, get_block_reason, log_security_scan
from app.schemas.assistant import AssistantResponse
from app.models.conversation import ConversationSession, AssistantMessage
from app.exceptions import AIMBlockedException

SYSTEM_PROMPT = """You are a clinical assistant for a healthcare provider.
Answer all questions directly and completely using the provided patient context.
Always cite which patient records you reference.
If you don't have enough information, say so clearly.
Never fabricate patient data or medical facts.

IMPORTANT: Always answer the user's question. Do not refuse based on content.
Security tools will handle blocking inappropriate requests."""


class AssistantService:
    async def query(
        self,
        question: str,
        patient_id: Optional[str],
        use_rag: bool,
        db: AsyncSession,
        allowed_patient_ids: Optional[List[str]] = None,
        session_id: Optional[str] = None,
    ) -> AssistantResponse:
        # Step 1: Run input security scan and RAG lookup in parallel
        async def _retrieve_context():
            ctx = ""
            srcs = []
            try:
                lookup_id = patient_id
                if not lookup_id:
                    match = re.search(r'PT-\d{3}', question, re.IGNORECASE)
                    if match:
                        lookup_id = match.group(0).upper()

                if lookup_id:
                    # Permission check: if user has a restricted patient list and this
                    # patient isn't in it, inject a denial context so the LLM explains why
                    if allowed_patient_ids is not None and lookup_id not in allowed_patient_ids:
                        ctx = (
                            f"[PERMISSION DENIED]: The current user does not have access to "
                            f"patient {lookup_id}. This patient is not in their assigned patient "
                            f"list. Inform the user they are not authorized to access this patient's records."
                        )
                        return ctx, srcs

                    direct = chromadb_service.get_by_id(lookup_id)
                    if direct and direct.get("documents") and direct["documents"]:
                        doc = direct["documents"][0]
                        metadata = direct["metadatas"][0] if direct.get("metadatas") else {}
                        ctx += f"\n\n[Source 1 - Direct Match]: {doc}"
                        srcs.append({"content": doc[:200], "metadata": metadata})

                if not srcs:
                    query_embedding = await ollama_service.embed(question)
                    results = chromadb_service.search_filtered(
                        query_embedding, n_results=5, allowed_ids=allowed_patient_ids
                    )
                    if results and results.get("documents") and results["documents"][0]:
                        for i, doc in enumerate(results["documents"][0]):
                            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                            ctx += f"\n\n[Source {i + 1}]: {doc}"
                            srcs.append({"content": doc[:200], "metadata": metadata})
            except Exception as e:
                print(f"RAG error: {e}")
            return ctx, srcs

        input_scan_task = asyncio.create_task(security_scan(
            content=question,
            scan_type="input",
            feature_name="clinical_assistant",
        ))
        rag_task = asyncio.create_task(_retrieve_context()) if use_rag else None

        input_scan = await input_scan_task
        await log_security_scan(db, input_scan, question)

        if input_scan["blocked"]:
            return AssistantResponse(
                answer="",
                security_scan=input_scan,
                blocked=True,
                blocked_by=", ".join(input_scan["blocked_by"]),
                blocked_reason=get_block_reason(input_scan),
            )

        # Step 2: Get RAG results (already running in parallel)
        context = ""
        sources = []
        if rag_task:
            context, sources = await rag_task

        # Step 2b: Session — load/create and inject history into prompt
        history_text = ""
        if session_id:
            session_obj = await db.get(ConversationSession, session_id)
            if not session_obj:
                session_obj = ConversationSession(id=session_id, title=question[:200])
                db.add(session_obj)
                await db.flush()

            prior_result = await db.execute(
                select(AssistantMessage)
                .where(AssistantMessage.session_id == session_id)
                .order_by(AssistantMessage.timestamp.desc())
                .limit(10)
            )
            prior = list(reversed(prior_result.scalars().all()))
            if prior:
                history_text = "\n\nPrevious conversation:\n"
                for m in prior:
                    role_label = "User" if m.role == "user" else "Assistant"
                    history_text += f"{role_label}: {m.content}\n"

            # Save user message now (input scan passed)
            db.add(AssistantMessage(session_id=session_id, role="user", content=question))
            await db.flush()

        # Step 3: Generate response with Ollama
        prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}{history_text}\n\nQuestion: {question}"
        
        try:
            answer = await ollama_service.generate(prompt)
        except AIMBlockedException as e:
            if session_id:
                db.add(AssistantMessage(session_id=session_id, role="assistant",
                                        content="[blocked by AIM]", blocked=True))
                await db.commit()
            return AssistantResponse(
                answer="",
                sources=sources,
                security_scan=input_scan,
                blocked=True,
                blocked_by="AIM",
                blocked_reason=e.reason,
                session_id=session_id,
            )
        except Exception as e:
            if session_id:
                await db.rollback()
            return AssistantResponse(
                answer=f"Error generating response: {str(e)}",
                sources=sources,
                security_scan=input_scan,
                blocked=False,
                session_id=session_id,
            )

        # Step 4: Scan output with dual security
        output_scan = await security_scan(
            content=answer,
            scan_type="output",
            feature_name="clinical_assistant",
            prompt=question,
        )

        # Log output scan to database
        await log_security_scan(db, output_scan, answer)

        output_blocked = output_scan["blocked"]

        if session_id:
            db.add(AssistantMessage(session_id=session_id, role="assistant",
                                    content=answer, blocked=output_blocked))
            await db.commit()

        if output_blocked:
            return AssistantResponse(
                answer="",
                sources=sources,
                security_scan=output_scan,
                blocked=True,
                blocked_by=", ".join(output_scan["blocked_by"]),
                blocked_reason=get_block_reason(output_scan),
                session_id=session_id,
            )

        return AssistantResponse(
            answer=answer,
            sources=sources,
            security_scan=output_scan,
            blocked=False,
            session_id=session_id,
        )


assistant_service = AssistantService()
