"""
Roadmap Tools
=============

Tools for managing roadmap features, including reordering within phases.
"""

import json
from pathlib import Path
from typing import Any

try:
    from claude_agent_sdk import tool

    SDK_TOOLS_AVAILABLE = True
except ImportError:
    SDK_TOOLS_AVAILABLE = False
    tool = None


def create_roadmap_tools(spec_dir: Path, project_dir: Path) -> list:
    """
    Create roadmap management tools.

    Args:
        spec_dir: Path to the spec directory
        project_dir: Path to the project root

    Returns:
        List of roadmap tool functions
    """
    if not SDK_TOOLS_AVAILABLE:
        return []

    tools = []

    # -------------------------------------------------------------------------
    # Tool: reorder_features
    # -------------------------------------------------------------------------
    @tool(
        "reorder_features",
        "Reorder roadmap features within a specific phase. Updates the features array to reflect the new order.",
        {
            "type": "object",
            "properties": {
                "phase_id": {
                    "type": "string",
                    "description": "The ID of the phase containing the features to reorder",
                },
                "feature_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Array of feature IDs in the desired new order",
                },
            },
            "required": ["phase_id", "feature_ids"],
        },
    )
    async def reorder_features(args: dict[str, Any]) -> dict[str, Any]:
        """Reorder features within a phase in the roadmap."""
        roadmap_file = project_dir / ".auto-claude" / "roadmap" / "roadmap.json"

        if not roadmap_file.exists():
            return {
                "content": [
                    {
                        "type": "text",
                        "text": "Error: Roadmap file not found. Generate a roadmap first.",
                    }
                ]
            }

        try:
            phase_id = args.get("phase_id")
            feature_ids = args.get("feature_ids", [])

            if not phase_id:
                return {
                    "content": [{"type": "text", "text": "Error: phase_id is required"}]
                }

            if not feature_ids:
                return {
                    "content": [
                        {"type": "text", "text": "Error: feature_ids array is required"}
                    ]
                }

            # Read roadmap
            with open(roadmap_file, encoding="utf-8") as f:
                roadmap = json.load(f)

            # Validate phase exists
            phases = roadmap.get("phases", [])
            phase_exists = any(p.get("id") == phase_id for p in phases)
            if not phase_exists:
                return {
                    "content": [
                        {
                            "type": "text",
                            "text": f"Error: Phase '{phase_id}' not found in roadmap",
                        }
                    ]
                }

            # Get all features
            all_features = roadmap.get("features", [])

            # Separate features by phase
            phase_features = [f for f in all_features if f.get("phase_id") == phase_id]
            other_features = [f for f in all_features if f.get("phase_id") != phase_id]

            # Validate all feature IDs exist in the phase
            existing_feature_ids = {f.get("id") for f in phase_features}
            for fid in feature_ids:
                if fid not in existing_feature_ids:
                    return {
                        "content": [
                            {
                                "type": "text",
                                "text": f"Error: Feature '{fid}' not found in phase '{phase_id}'",
                            }
                        ]
                    }

            # Create feature lookup
            feature_map = {f.get("id"): f for f in phase_features}

            # Reorder phase features according to feature_ids
            reordered_phase_features = []
            for fid in feature_ids:
                if fid in feature_map:
                    reordered_phase_features.append(feature_map[fid])

            # Combine: other phases first, then reordered phase features
            updated_features = other_features + reordered_phase_features

            # Update roadmap
            roadmap["features"] = updated_features

            # Update timestamp if metadata exists
            if "metadata" in roadmap:
                from datetime import datetime

                roadmap["metadata"]["updated_at"] = datetime.utcnow().isoformat() + "Z"

            # Write back to file
            with open(roadmap_file, "w", encoding="utf-8") as f:
                json.dump(roadmap, f, indent=2)

            # Build success message
            feature_titles = [
                f"{fid}: {feature_map[fid].get('title', 'Unknown')}"
                for fid in feature_ids
                if fid in feature_map
            ]

            result = f"""Successfully reordered {len(feature_ids)} features in phase '{phase_id}'

New order:
{chr(10).join(f"  {i + 1}. {title}" for i, title in enumerate(feature_titles))}

Roadmap file updated: {roadmap_file.relative_to(project_dir)}"""

            return {"content": [{"type": "text", "text": result}]}

        except json.JSONDecodeError as e:
            return {
                "content": [
                    {
                        "type": "text",
                        "text": f"Error: Failed to parse roadmap JSON: {e}",
                    }
                ]
            }
        except Exception as e:
            return {
                "content": [{"type": "text", "text": f"Error reordering features: {e}"}]
            }

    tools.append(reorder_features)

    return tools
