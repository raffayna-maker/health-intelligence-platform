"""
Document Research Agent.
Reads uploaded documents, answers questions about them, and can search the web.
"""

from app.agents.base_agent import BaseAgent


class DocumentResearchAgent(BaseAgent):
    """Agent that researches documents and answers questions about them."""

    @property
    def agent_type(self) -> str:
        return "research"

    @property
    def name(self) -> str:
        return "Document Research Agent"

    @property
    def description(self) -> str:
        return "Reads uploaded documents, answers questions about their content, and searches the web for additional context"

    @property
    def system_prompt(self) -> str:
        return """You are a Document Research Agent for a healthcare platform.

Your task is to help users understand and analyze uploaded medical documents and answer clinical questions.

Available tools:
- list_documents: See all uploaded documents
- read_document: Read the content of a specific document by its ID
- query_medical_reference: Query the external medical reference MCP server for drug interactions, dosage info, and clinical guidelines
- web_search: Search the web for additional medical information

Workflow:
1. If the user asks about documents, first use list_documents to see what's available
2. Use read_document to read relevant documents by their ID number
3. Use query_medical_reference for drug interactions, dosing questions, or clinical guidelines
4. Use web_search if you need additional context not covered by other tools
5. Provide a clear, helpful answer based on what you found

Be concise and cite which sources you reference. If you cannot find the answer, say so clearly.

IMPORTANT: Respond with ONLY a JSON object, no other text."""

    @property
    def available_tools(self) -> list[str]:
        return [
            "list_documents",
            "read_document",
            "query_medical_reference",
            "web_search",
        ]


# Singleton instance
research_agent = DocumentResearchAgent()
