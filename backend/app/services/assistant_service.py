from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from app.services.ollama_service import ollama_service
from app.services.chromadb_service import chromadb_service
from app.services.security_service import dual_security_scan
from app.schemas.assistant import AssistantResponse


SYSTEM_PROMPT = """You are a clinical assistant for a healthcare provider.
Answer medical questions accurately using the provided patient context.
Always cite which patient records you reference.
If you don't have enough information, say so clearly.
Never fabricate patient data or medical facts.
Protect patient privacy - do not include SSN or full addresses in responses."""


class AssistantService:
    async def query(
        self,
        question: str,
        patient_id: Optional[str],
        use_rag: bool,
        db: AsyncSession,
    ) -> AssistantResponse:
        # Step 1: Scan input
        input_scan = await dual_security_scan(
            content=question,
            scan_type="input",
            feature="clinical_assistant",
            db=db,
        )
        if input_scan.blocked:
            return AssistantResponse(
                answer="",
                security_scan=input_scan.model_dump(),
                blocked=True,
                blocked_by="Hidden Layer" if input_scan.hl_verdict == "block" else "AIM",
                blocked_reason=input_scan.hl_reason or input_scan.aim_reason,
            )

        # Step 2: Retrieve context via RAG
        context = ""
        sources = []
        if use_rag:
            try:
                query_embedding = await ollama_service.embed(question)
                results = chromadb_service.search(query_embedding, n_results=5)
                if results and results.get("documents") and results["documents"][0]:
                    for i, doc in enumerate(results["documents"][0]):
                        context += f"\n--- Patient Record {i+1} ---\n{doc}\n"
                        if results.get("metadatas") and results["metadatas"][0]:
                            meta = results["metadatas"][0][i]
                            sources.append({
                                "patient_id": meta.get("patient_id", "Unknown"),
                                "relevance": round(1 - (results["distances"][0][i] if results.get("distances") else 0), 3),
                            })
            except Exception:
                context = "(RAG unavailable - answering without patient context)"

        # Step 3: Build prompt and generate
        if patient_id:
            prompt = f"Focus on patient {patient_id}.\n\nContext:\n{context}\n\nQuestion: {question}"
        elif context:
            prompt = f"Patient Database Context:\n{context}\n\nQuestion: {question}"
        else:
            prompt = f"Question: {question}"

        answer = await ollama_service.generate(prompt, system=SYSTEM_PROMPT)

        # Step 4: Scan output
        output_scan = await dual_security_scan(
            content=answer,
            scan_type="output",
            feature="clinical_assistant",
            db=db,
        )
        if output_scan.blocked:
            return AssistantResponse(
                answer="",
                sources=sources,
                security_scan=output_scan.model_dump(),
                blocked=True,
                blocked_by="Hidden Layer" if output_scan.hl_verdict == "block" else "AIM",
                blocked_reason=output_scan.hl_reason or output_scan.aim_reason,
            )

        return AssistantResponse(
            answer=answer,
            sources=sources,
            security_scan=output_scan.model_dump(),
        )


assistant_service = AssistantService()
