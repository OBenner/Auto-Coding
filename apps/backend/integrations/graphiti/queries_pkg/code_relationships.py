"""
Code relationship storage operations for Graphiti memory.

Handles storage and retrieval of code relationships including:
- Function call relationships (caller -> callee)
- Import dependencies (module -> imported modules)
- Class inheritance hierarchies (child -> parent)
"""

import json
import logging
from datetime import UTC, datetime

from core.sentry import capture_exception

from .schema import (
    EPISODE_TYPE_CLASS_INHERITANCE,
    EPISODE_TYPE_CODE_RELATIONSHIP,
    EPISODE_TYPE_FUNCTION_CALL,
    EPISODE_TYPE_IMPORT_DEPENDENCY,
)

logger = logging.getLogger(__name__)


class CodeRelationshipQueries:
    """
    Manages code relationship storage and retrieval operations.

    Provides high-level methods for storing semantic relationships
    between code entities in the knowledge graph.
    """

    def __init__(self, client, group_id: str, spec_context_id: str):
        """
        Initialize code relationship query manager.

        Args:
            client: GraphitiClient instance
            group_id: Group ID for memory namespace
            spec_context_id: Spec-specific context ID
        """
        self.client = client
        self.group_id = group_id
        self.spec_context_id = spec_context_id

    async def add_function_call(
        self,
        caller: str,
        callee: str,
        file_path: str,
        lineno: int,
        call_type: str = "function",
        module: str | None = None,
    ) -> bool:
        """
        Store a function call relationship.

        Args:
            caller: Name of the calling function/method
            callee: Name of the called function/method
            file_path: Path to the file containing the call
            lineno: Line number where call occurs
            call_type: Type of call (function, method, builtin)
            module: Module the callee belongs to (if imported)

        Returns:
            True if saved successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_FUNCTION_CALL,
                "spec_id": self.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "caller": caller,
                "callee": callee,
                "file_path": file_path,
                "lineno": lineno,
                "call_type": call_type,
                "module": module,
            }

            await self.client.graphiti.add_episode(
                name=f"call_{caller}_{callee}_{lineno}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Function call: {caller} -> {callee}",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            logger.debug(f"Stored function call: {caller} -> {callee} ({file_path}:{lineno})")
            return True

        except Exception as e:
            logger.warning(f"Failed to store function call relationship: {e}")
            capture_exception(
                e,
                operation="add_function_call",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                caller=caller,
                callee=callee,
            )
            return False

    async def add_import_dependency(
        self,
        importing_file: str,
        module: str,
        names: list[str] | None = None,
        alias: str | None = None,
        lineno: int = 0,
        is_from_import: bool = False,
    ) -> bool:
        """
        Store an import dependency relationship.

        Args:
            importing_file: File that contains the import
            module: Module being imported
            names: Specific names imported (empty if whole module)
            alias: Alias used for import (if any)
            lineno: Line number of import statement
            is_from_import: Whether this is 'from X import Y' style

        Returns:
            True if saved successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_IMPORT_DEPENDENCY,
                "spec_id": self.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "importing_file": importing_file,
                "module": module,
                "names": names or [],
                "alias": alias,
                "lineno": lineno,
                "is_from_import": is_from_import,
            }

            await self.client.graphiti.add_episode(
                name=f"import_{module}_{lineno}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Import dependency: {importing_file} imports {module}",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            logger.debug(f"Stored import: {importing_file} imports {module}")
            return True

        except Exception as e:
            logger.warning(f"Failed to store import dependency: {e}")
            capture_exception(
                e,
                operation="add_import_dependency",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                module=module,
            )
            return False

    async def add_inheritance_relationship(
        self,
        child: str,
        parent: str,
        file_path: str,
        lineno: int,
        parent_module: str | None = None,
    ) -> bool:
        """
        Store a class inheritance relationship.

        Args:
            child: Child class name
            parent: Parent class name
            file_path: Path to file containing the class
            lineno: Line number of class definition
            parent_module: Module the parent belongs to (if imported)

        Returns:
            True if saved successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_CLASS_INHERITANCE,
                "spec_id": self.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "child": child,
                "parent": parent,
                "file_path": file_path,
                "lineno": lineno,
                "parent_module": parent_module,
            }

            await self.client.graphiti.add_episode(
                name=f"inheritance_{child}_{parent}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Class inheritance: {child} extends {parent}",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            logger.debug(f"Stored inheritance: {child} -> {parent} ({file_path}:{lineno})")
            return True

        except Exception as e:
            logger.warning(f"Failed to store inheritance relationship: {e}")
            capture_exception(
                e,
                operation="add_inheritance_relationship",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                child=child,
                parent=parent,
            )
            return False

    async def add_file_relationships(
        self,
        file_path: str,
        relationships: dict,
    ) -> bool:
        """
        Store all relationships from a single file analysis.

        This is a bulk operation that stores function calls, imports,
        and inheritance relationships together.

        Args:
            file_path: Path to the analyzed file
            relationships: Dictionary containing relationship data with keys:
                - calls: List of function call dicts
                - imports: List of import dicts
                - inheritance: List of inheritance dicts

        Returns:
            True if all relationships saved successfully
        """
        try:
            from graphiti_core.nodes import EpisodeType

            episode_content = {
                "type": EPISODE_TYPE_CODE_RELATIONSHIP,
                "spec_id": self.spec_context_id,
                "timestamp": datetime.now(UTC).isoformat(),
                "file_path": file_path,
                "total_relationships": relationships.get("total_relationships", 0),
                "entities": relationships.get("entities", []),
                "calls_count": len(relationships.get("calls", [])),
                "imports_count": len(relationships.get("imports", [])),
                "inheritance_count": len(relationships.get("inheritance", [])),
            }

            await self.client.graphiti.add_episode(
                name=f"file_relationships_{file_path.replace('/', '_')}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}",
                episode_body=json.dumps(episode_content),
                source=EpisodeType.text,
                source_description=f"Code relationships for {file_path}",
                reference_time=datetime.now(UTC),
                group_id=self.group_id,
            )

            # Store individual relationships
            success_count = 0
            total_count = 0

            # Store function calls
            for call in relationships.get("calls", []):
                total_count += 1
                if await self.add_function_call(
                    caller=call["caller"],
                    callee=call["callee"],
                    file_path=file_path,
                    lineno=call["lineno"],
                    call_type=call.get("call_type", "function"),
                    module=call.get("module"),
                ):
                    success_count += 1

            # Store imports
            for imp in relationships.get("imports", []):
                total_count += 1
                if await self.add_import_dependency(
                    importing_file=file_path,
                    module=imp["module"],
                    names=imp.get("names", []),
                    alias=imp.get("alias"),
                    lineno=imp.get("lineno", 0),
                    is_from_import=imp.get("is_from_import", False),
                ):
                    success_count += 1

            # Store inheritance relationships
            for inh in relationships.get("inheritance", []):
                total_count += 1
                if await self.add_inheritance_relationship(
                    child=inh["child"],
                    parent=inh["parent"],
                    file_path=file_path,
                    lineno=inh["lineno"],
                    parent_module=inh.get("parent_module"),
                ):
                    success_count += 1

            logger.info(
                f"Stored {success_count}/{total_count} relationships from {file_path}"
            )
            return success_count == total_count

        except Exception as e:
            logger.warning(f"Failed to store file relationships: {e}")
            capture_exception(
                e,
                operation="add_file_relationships",
                group_id=self.group_id,
                spec_id=self.spec_context_id,
                file_path=file_path,
            )
            return False

    async def find_callers(
        self,
        function_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all functions that call the specified function.

        Args:
            function_name: Name of the function to find callers for
            limit: Maximum number of results to return

        Returns:
            List of caller information with caller name, file path, and line number
        """
        try:
            results = await self.client.graphiti.search(
                query=f"function call {function_name} caller callee",
                group_ids=[self.group_id],
                num_results=limit * 2,  # Get more to filter
            )

            callers = []
            seen = set()  # Deduplicate results

            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_FUNCTION_CALL in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_FUNCTION_CALL:
                            # Check if this is a call TO the function we're looking for
                            if data.get("callee") == function_name:
                                caller_info = (
                                    data.get("caller"),
                                    data.get("file_path"),
                                    data.get("lineno"),
                                )
                                if caller_info not in seen:
                                    seen.add(caller_info)
                                    callers.append(
                                        {
                                            "caller": data.get("caller"),
                                            "file_path": data.get("file_path"),
                                            "lineno": data.get("lineno"),
                                            "call_type": data.get("call_type", "function"),
                                            "module": data.get("module"),
                                        }
                                    )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            logger.info(f"Found {len(callers)} callers for function: {function_name}")
            return callers[:limit]

        except Exception as e:
            logger.warning(f"Failed to find callers: {e}")
            capture_exception(
                e,
                operation="find_callers",
                group_id=self.group_id,
                function_name=function_name,
            )
            return []

    async def find_callees(
        self,
        function_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all functions that the specified function calls.

        Args:
            function_name: Name of the function to find callees for
            limit: Maximum number of results to return

        Returns:
            List of callee information with callee name, file path, and line number
        """
        try:
            results = await self.client.graphiti.search(
                query=f"function call {function_name} caller callee",
                group_ids=[self.group_id],
                num_results=limit * 2,  # Get more to filter
            )

            callees = []
            seen = set()  # Deduplicate results

            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_FUNCTION_CALL in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_FUNCTION_CALL:
                            # Check if this is a call FROM the function we're looking for
                            if data.get("caller") == function_name:
                                callee_info = (
                                    data.get("callee"),
                                    data.get("file_path"),
                                    data.get("lineno"),
                                )
                                if callee_info not in seen:
                                    seen.add(callee_info)
                                    callees.append(
                                        {
                                            "callee": data.get("callee"),
                                            "file_path": data.get("file_path"),
                                            "lineno": data.get("lineno"),
                                            "call_type": data.get("call_type", "function"),
                                            "module": data.get("module"),
                                        }
                                    )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            logger.info(f"Found {len(callees)} callees for function: {function_name}")
            return callees[:limit]

        except Exception as e:
            logger.warning(f"Failed to find callees: {e}")
            capture_exception(
                e,
                operation="find_callees",
                group_id=self.group_id,
                function_name=function_name,
            )
            return []

    async def find_parent_classes(
        self,
        class_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all parent classes of the specified class.

        Args:
            class_name: Name of the class to find parents for
            limit: Maximum number of results to return

        Returns:
            List of parent class information with parent name, file path, and line number
        """
        try:
            results = await self.client.graphiti.search(
                query=f"class inheritance {class_name} parent child extends",
                group_ids=[self.group_id],
                num_results=limit * 2,  # Get more to filter
            )

            parents = []
            seen = set()  # Deduplicate results

            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_CLASS_INHERITANCE in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_CLASS_INHERITANCE:
                            # Check if this is inheritance FROM the class we're looking for
                            if data.get("child") == class_name:
                                parent_info = (
                                    data.get("parent"),
                                    data.get("file_path"),
                                    data.get("lineno"),
                                )
                                if parent_info not in seen:
                                    seen.add(parent_info)
                                    parents.append(
                                        {
                                            "parent": data.get("parent"),
                                            "file_path": data.get("file_path"),
                                            "lineno": data.get("lineno"),
                                            "parent_module": data.get("parent_module"),
                                        }
                                    )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            logger.info(f"Found {len(parents)} parent classes for: {class_name}")
            return parents[:limit]

        except Exception as e:
            logger.warning(f"Failed to find parent classes: {e}")
            capture_exception(
                e,
                operation="find_parent_classes",
                group_id=self.group_id,
                class_name=class_name,
            )
            return []

    async def find_child_classes(
        self,
        class_name: str,
        limit: int = 50,
    ) -> list[dict]:
        """
        Find all child classes that inherit from the specified class.

        Args:
            class_name: Name of the class to find children for
            limit: Maximum number of results to return

        Returns:
            List of child class information with child name, file path, and line number
        """
        try:
            results = await self.client.graphiti.search(
                query=f"class inheritance {class_name} parent child extends",
                group_ids=[self.group_id],
                num_results=limit * 2,  # Get more to filter
            )

            children = []
            seen = set()  # Deduplicate results

            for result in results:
                content = getattr(result, "content", None) or getattr(
                    result, "fact", None
                )
                if content and EPISODE_TYPE_CLASS_INHERITANCE in str(content):
                    try:
                        data = (
                            json.loads(content) if isinstance(content, str) else content
                        )
                        if not isinstance(data, dict):
                            continue
                        if data.get("type") == EPISODE_TYPE_CLASS_INHERITANCE:
                            # Check if this is inheritance TO the class we're looking for
                            if data.get("parent") == class_name:
                                child_info = (
                                    data.get("child"),
                                    data.get("file_path"),
                                    data.get("lineno"),
                                )
                                if child_info not in seen:
                                    seen.add(child_info)
                                    children.append(
                                        {
                                            "child": data.get("child"),
                                            "file_path": data.get("file_path"),
                                            "lineno": data.get("lineno"),
                                            "parent_module": data.get("parent_module"),
                                        }
                                    )
                    except (json.JSONDecodeError, TypeError, AttributeError):
                        continue

            logger.info(f"Found {len(children)} child classes for: {class_name}")
            return children[:limit]

        except Exception as e:
            logger.warning(f"Failed to find child classes: {e}")
            capture_exception(
                e,
                operation="find_child_classes",
                group_id=self.group_id,
                class_name=class_name,
            )
            return []

    async def get_inheritance_chain(
        self,
        class_name: str,
        max_depth: int = 10,
    ) -> list[str]:
        """
        Get the full inheritance chain from a class to its root ancestors.

        Args:
            class_name: Name of the class to get inheritance chain for
            max_depth: Maximum depth to traverse (prevents infinite loops)

        Returns:
            List of class names in inheritance order [ChildClass, Parent, GrandParent, ...]
        """
        try:
            chain = [class_name]
            current = class_name
            depth = 0

            while depth < max_depth:
                parents = await self.find_parent_classes(current, limit=1)
                if not parents:
                    # No more parents found
                    break

                parent_name = parents[0]["parent"]
                if parent_name in chain:
                    # Circular inheritance detected
                    logger.warning(
                        f"Circular inheritance detected for {class_name}: {parent_name} already in chain"
                    )
                    break

                chain.append(parent_name)
                current = parent_name
                depth += 1

            logger.info(
                f"Got inheritance chain for {class_name}: {' -> '.join(chain)}"
            )
            return chain

        except Exception as e:
            logger.warning(f"Failed to get inheritance chain: {e}")
            capture_exception(
                e,
                operation="get_inheritance_chain",
                group_id=self.group_id,
                class_name=class_name,
            )
            return [class_name]  # Return at least the original class
