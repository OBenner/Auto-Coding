"""
UI Component Template
=====================

Template for creating reusable UI components.
"""

from typing import Any, Dict

from ..registry import Template


class UiComponentTemplate(Template):
    """Template for UI component implementation."""

    def __init__(self):
        """Initialize the UI component template."""
        super().__init__(
            name="ui_component",
            description="Create reusable UI component with props and state management",
            category="ui",
            parameters={
                "component_name": {
                    "type": str,
                    "required": True,
                    "description": "Name of the component (e.g., 'Button', 'Modal', 'DataTable')",
                },
                "framework": {
                    "type": str,
                    "required": False,
                    "default": "react",
                    "description": "UI framework (react, vue, angular, svelte)",
                },
                "props": {
                    "type": list,
                    "required": True,
                    "description": "Component props (e.g., ['label', 'onClick', 'disabled'])",
                },
                "state_management": {
                    "type": bool,
                    "required": False,
                    "default": False,
                    "description": "Whether component manages internal state",
                },
                "accessibility": {
                    "type": bool,
                    "required": False,
                    "default": True,
                    "description": "Include WCAG accessibility features",
                },
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI component spec from parameters."""
        component_name = params["component_name"]
        framework = params.get("framework", "react")
        props = params["props"]
        state_management = params.get("state_management", False)
        accessibility = params.get("accessibility", True)

        props_str = ", ".join(props)

        return {
            "title": f"{component_name} Component",
            "description": f"Reusable {component_name} component built with {framework.capitalize()}.",
            "rationale": f"Create a consistent, reusable {component_name} component that can be used throughout the application, ensuring UI consistency and reducing code duplication.",
            "user_stories": [
                f"As a developer, I want to use a {component_name} component with consistent styling",
                f"As a user, I want the {component_name} to be responsive and accessible",
                "As a designer, I want the component to match the design system",
            ],
            "acceptance_criteria": [
                f"{component_name} component renders correctly",
                f"Component accepts all required props: {props_str}",
                "Component is responsive across mobile, tablet, and desktop",
                "Component follows design system guidelines",
            ] + (["Component manages internal state correctly"] if state_management else [])
            + (
                [
                    "Component meets WCAG 2.1 Level AA accessibility standards",
                    "Component supports keyboard navigation",
                    "Component has proper ARIA labels and roles",
                ]
                if accessibility
                else []
            ),
            "technical_details": f"""
### Component API

**Framework:** {framework.capitalize()}

**Props:**
{chr(10).join([f"- `{prop}`: [type and description]" for prop in props])}

### Example Usage

```{self._get_framework_extension(framework)}
<{component_name}
  {chr(10).join([f'  {prop}={{/* value */}}' for prop in props[:3]])}
/>
```

### Styling

- Follow design system tokens for colors, spacing, typography
- Support theme variants (light/dark mode)
- Responsive breakpoints: mobile (<768px), tablet (768-1024px), desktop (>1024px)

### State Management

{"- Component maintains internal state" if state_management else "- Stateless component (controlled by parent)"}
{"- State updates trigger re-renders" if state_management else ""}

### Accessibility Features

{"- Keyboard navigation support" if accessibility else ""}
{"- Screen reader compatible" if accessibility else ""}
{"- Focus management" if accessibility else ""}
{"- ARIA labels and roles" if accessibility else ""}
{"- Color contrast compliance" if accessibility else ""}

### Browser Support

- Chrome (latest 2 versions)
- Firefox (latest 2 versions)
- Safari (latest 2 versions)
- Edge (latest 2 versions)
""",
            "test_coverage": [
                f"Unit tests for {component_name} rendering",
                "Tests for all prop combinations",
                "Tests for responsive behavior",
                "Visual regression tests",
            ] + (["Tests for state changes"] if state_management else [])
            + (
                [
                    "Accessibility tests (axe-core)",
                    "Keyboard navigation tests",
                ]
                if accessibility
                else []
            ),
        }

    def _get_framework_extension(self, framework: str) -> str:
        """Get file extension for framework."""
        extensions = {
            "react": "jsx",
            "vue": "vue",
            "angular": "html",
            "svelte": "svelte",
        }
        return extensions.get(framework, "jsx")
