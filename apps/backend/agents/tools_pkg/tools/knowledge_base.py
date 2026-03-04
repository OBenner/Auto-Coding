"""
Team Knowledge Base Tools
=========================

Tools for querying team documentation (Notion, Confluence, GitHub Wiki, GitBook).

Provides agents with access to team-specific documentation, coding standards,
conventions, and best practices that are stored in external knowledge bases.
"""

import logging
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None

logger = logging.getLogger(__name__)


def create_knowledge_base_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create team knowledge base tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of knowledge base tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: search_team_docs
    # -------------------------------------------------------------------------
    @tool(
        "search_team_docs",
        "Search team documentation for relevant information. Use this when you need to find team standards, conventions, or specific documentation.",
        {"query": str, "limit": int},
    )
    async def search_team_docs(args: dict[str, Any]) -> dict[str, Any]:
        """Search team documentation for relevant information."""
        query = args["query"]
        limit = args.get("limit", 10)

        manager = None
        try:
            # Import here to avoid circular imports
            from integrations.knowledge_base import KnowledgeBaseManager

            # Initialize manager
            manager = KnowledgeBaseManager(spec_dir, project_dir)

            # Check if knowledge base is available
            if not manager.is_enabled:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Team knowledge base is not configured. "
                            "To enable team documentation search, configure NOTION_TOKEN, "
                            "CONFLUENCE_API_TOKEN, GITHUB_TOKEN, or GITBOOK_API_KEY in .env",
                        }
                    ]
                }

            # Initialize if needed
            if not await manager.initialize():
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Failed to initialize team knowledge base. "
                            "Check your API credentials and configuration.",
                        }
                    ]
                }

            # Import indexer for search
            from integrations.knowledge_base.indexer import DocumentationIndexer

            indexer = DocumentationIndexer(spec_dir, project_dir, manager.state)

            # Search for relevant documents
            results = await indexer.search(query=query, limit=limit)

            if not results:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"No team documentation found for query: '{query}'\n\n"
                            "Try different search terms or check if documentation has been synced.",
                        }
                    ]
                }

            # Format results for agent
            result_parts = [
                f"Found {len(results)} team documentation results for '{query}':\n"
            ]

            for i, doc in enumerate(results, 1):
                title = doc.get("title", "Untitled")
                content = doc.get("content", "")
                url = doc.get("url", "")
                score = doc.get("score", 0.0)

                # Truncate content for readability
                max_content_length = 500
                if len(content) > max_content_length:
                    content = content[:max_content_length] + "..."

                result_parts.append(f"\n{i}. **{title}** (relevance: {score:.2f})")
                if url:
                    result_parts.append(f"   URL: {url}")
                result_parts.append(f"   {content}")

            return {"content": [{"type": "text", "text": "\n".join(result_parts)}]}

        except Exception as e:
            logger.warning(f"Failed to search team documentation: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error searching team documentation: {e}"}
                ]
            }
        finally:
            if manager is not None:
                await manager.close()

    tools.append(search_team_docs)

    # -------------------------------------------------------------------------
    # Tool: get_team_docs
    # -------------------------------------------------------------------------
    @tool(
        "get_team_docs",
        "Get all available team documentation. Use this to see what team documentation exists.",
        {"limit": int},
    )
    async def get_team_docs(args: dict[str, Any]) -> dict[str, Any]:
        """Get all available team documentation."""
        limit = args.get("limit", 50)

        manager = None
        try:
            # Import here to avoid circular imports
            from integrations.knowledge_base import KnowledgeBaseManager

            # Initialize manager
            manager = KnowledgeBaseManager(spec_dir, project_dir)

            # Check if knowledge base is available
            if not manager.is_enabled:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Team knowledge base is not configured. "
                            "To enable team documentation access, configure NOTION_TOKEN, "
                            "CONFLUENCE_API_TOKEN, GITHUB_TOKEN, or GITBOOK_API_KEY in .env",
                        }
                    ]
                }

            # Initialize if needed
            if not await manager.initialize():
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "Failed to initialize team knowledge base. "
                            "Check your API credentials and configuration.",
                        }
                    ]
                }

            # Import indexer for document access
            from integrations.knowledge_base.indexer import DocumentationIndexer

            indexer = DocumentationIndexer(spec_dir, project_dir, manager.state)

            # Get all documents
            documents = await indexer.get_all_documents(limit=limit)

            if not documents:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": "No team documentation available. "
                            "Documentation needs to be synced first. Run a sync operation to populate the knowledge base.",
                        }
                    ]
                }

            # Get index stats
            stats = indexer.get_index_stats()

            # Format results
            result_parts = [
                f"Team Documentation ({len(documents)} documents, "
                f"{stats.get('total_size_bytes', 0) / 1024:.1f} KB):\n"
            ]

            # Group by source
            by_source: dict[str, list[dict[str, Any]]] = {}
            for doc in documents:
                source = doc.get("metadata", {}).get("source", "unknown")
                if source not in by_source:
                    by_source[source] = []
                by_source[source].append(doc)

            for source, docs in sorted(by_source.items()):
                result_parts.append(f"\n## {source.upper()} ({len(docs)} docs)")
                for doc in docs[:20]:  # Limit per source
                    title = doc.get("title", "Untitled")
                    url = doc.get("url", "")
                    result_parts.append(f"- {title}")
                    if url:
                        result_parts.append(f"  {url}")

                if len(docs) > 20:
                    result_parts.append(f"  ... and {len(docs) - 20} more")

            return {"content": [{"type": "text", "text": "\n".join(result_parts)}]}

        except Exception as e:
            logger.warning(f"Failed to get team documentation: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error getting team documentation: {e}"}
                ]
            }
        finally:
            if manager is not None:
                await manager.close()

    tools.append(get_team_docs)

    return tools
