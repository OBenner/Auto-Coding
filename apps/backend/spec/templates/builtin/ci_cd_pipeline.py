"""CI/CD Pipeline Template"""

from typing import Any, Dict
from ..registry import Template


class CiCdPipelineTemplate(Template):
    """Template for CI/CD pipeline."""

    def __init__(self):
        super().__init__(
            name="ci_cd_pipeline",
            description="CI/CD pipeline with automated testing and deployment",
            category="infrastructure",
            parameters={
                "platform": {"type": str, "required": True, "description": "CI/CD platform (github-actions, gitlab-ci, jenkins)"},
                "stages": {"type": list, "required": True, "description": "Pipeline stages (build, test, deploy)"},
                "deploy_environments": {"type": list, "required": False, "default": ["staging", "production"], "description": "Deployment environments"},
            },
        )

    def generate(self, params: Dict[str, Any]) -> Dict[str, Any]:
        platform = params["platform"]
        stages = params["stages"]
        envs = params.get("deploy_environments", ["staging", "production"])

        return {
            "title": "CI/CD Pipeline",
            "description": f"Automated CI/CD pipeline using {platform}.",
            "rationale": "Automate testing and deployment to improve development velocity and reduce manual errors.",
            "user_stories": [
                "As a developer, I want automated tests on every commit",
                "As a team, I want automated deployments to staging/production",
            ],
            "acceptance_criteria": [
                f"Pipeline stages: {', '.join(stages)}",
                f"Deploy to: {', '.join(envs)}",
                "Automated tests block bad deployments",
                "Deployment rollback capability",
            ],
            "technical_details": f"Platform: {platform}\nStages: {', '.join(stages)}\nEnvironments: {', '.join(envs)}",
            "test_coverage": ["Pipeline configuration tests", "Deployment tests", "Rollback tests"],
        }
