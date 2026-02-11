import asyncio
import re
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.services.ollama_service import ollama_service
from app.services.chromadb_service import chromadb_service
from app.services.security_service import dual_security_scan, log_security_scan
from app.schemas.assistant import AssistantResponse
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
                    direct = chromadb_service.get_by_id(lookup_id)
                    if direct and direct.get("documents") and direct["documents"]:
                        doc = direct["documents"][0]
                        metadata = direct["metadatas"][0] if direct.get("metadatas") else {}
                        ctx += f"\n\n[Source 1 - Direct Match]: {doc}"
                        srcs.append({"content": doc[:200], "metadata": metadata})

                if not srcs:
                    query_embedding = await ollama_service.embed(question)
                    results = chromadb_service.search(query_embedding, n_results=5)
                    if results and results.get("documents") and results["documents"][0]:
                        for i, doc in enumerate(results["documents"][0]):
                            metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                            ctx += f"\n\n[Source {i + 1}]: {doc}"
                            srcs.append({"content": doc[:200], "metadata": metadata})
            except Exception as e:
                print(f"RAG error: {e}")
            return ctx, srcs

        input_scan_task = asyncio.create_task(dual_security_scan(
            content=question,
            scan_type="input",
            feature_name="clinical_assistant",
        ))
        rag_task = asyncio.create_task(_retrieve_context()) if use_rag else None

        input_scan = await input_scan_task
        await log_security_scan(db, input_scan, question)

        if input_scan["blocked"]:
            blocked_by = input_scan["blocked_by"][0] if input_scan["blocked_by"] else "Security"
            hl_reason = input_scan["hidden_layer_result"].get("reason")
            aim_reason = input_scan["aim_result"].get("reason")
            reason = hl_reason or aim_reason or "Security violation"
            return AssistantResponse(
                answer="",
                security_scan=input_scan,
                blocked=True,
                blocked_by=", ".join(input_scan["blocked_by"]),
                blocked_reason=reason,
            )

        # Step 2: Get RAG results (already running in parallel)
        context = ""
        sources = []
        if rag_task:
            context, sources = await rag_task
        
        # Step 3: Generate response with Ollama
        prompt = f"{SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {question}"
        
        try:
            answer = await ollama_service.generate(prompt)
        except AIMBlockedException as e:
            return AssistantResponse(
                answer="",
                sources=sources,
                security_scan=input_scan,
                blocked=True,
                blocked_by="AIM",
                blocked_reason=e.reason,
            )
        except Exception as e:
            return AssistantResponse(
                answer=f"Error generating response: {str(e)}",
                sources=sources,
                security_scan=input_scan,
                blocked=False,
            )
        
        # Step 4: Scan output with dual security
        output_scan = await dual_security_scan(
            content=answer,
            scan_type="output",
            feature_name="clinical_assistant",
            prompt=question,
        )
        
        # Log output scan to database
        await log_security_scan(db, output_scan, answer)
        
        if output_scan["blocked"]:
            blocked_by = output_scan["blocked_by"][0] if output_scan["blocked_by"] else "Security"
            hl_reason = output_scan["hidden_layer_result"].get("reason")
            aim_reason = output_scan["aim_result"].get("reason")
            reason = hl_reason or aim_reason or "Security violation"
            
            return AssistantResponse(
                answer="",
                sources=sources,
                security_scan=output_scan,
                blocked=True,
                blocked_by=", ".join(output_scan["blocked_by"]),
                blocked_reason=reason,
            )
        
        return AssistantResponse(
            answer=answer,
            sources=sources,
            security_scan=output_scan,
            blocked=False,
        )


assistant_service = AssistantService()
