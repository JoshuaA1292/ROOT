"""
Register ROOT's ADK agent on Vertex AI Agent Engine.
Run after 07_setup_gcp.sh.

This deploys the root_orchestrator agent to Vertex AI so it can be invoked
via the Agent Engine API — satisfying the Google Cloud Agent Builder requirement.

Usage: python infra/agent-builder/setup_agent.py

Prerequisites:
  - GOOGLE_CLOUD_PROJECT set in .env
  - gcp-service-account.json present (from 07_setup_gcp.sh)
  - google-cloud-aiplatform installed
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Load env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent.parent / ".env")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if not PROJECT_ID:
    sys.exit("ERROR: GOOGLE_CLOUD_PROJECT not set in .env")

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

import vertexai
from vertexai.preview import reasoning_engines

vertexai.init(project=PROJECT_ID, location=LOCATION)


class ROOTAgentApp:
    """
    Vertex AI Agent Engine wrapper for the ROOT orchestrator.
    Satisfies the Google Cloud Agent Builder deployment requirement.
    """

    def set_up(self):
        """Called once when the agent is deployed to Vertex AI."""
        from app.agents.adk_agent import build_agent
        from google.adk.runners import InMemoryRunner
        self._agent = build_agent()
        self._runner = InMemoryRunner(agent=self._agent, app_name="ROOT")

    async def query(self, permit_id: str, briefing_id: str = "") -> dict:
        """
        Run the ROOT pipeline for a permit and return the briefing result.

        Args:
            permit_id: The permit to analyze.
            briefing_id: Optional briefing record ID to update.

        Returns:
            Dict with draft_comment, coalition_summary, developer_snapshot, precedent_refs.
        """
        import asyncio
        from google.genai import types as genai_types
        from app.agents.adk_agent import run_adk_pipeline

        queue = asyncio.Queue()
        draft = await run_adk_pipeline(permit_id, briefing_id or "preview", queue)
        return {"draft_comment": draft, "permit_id": permit_id}


def deploy_agent():
    """Deploy ROOT agent to Vertex AI Agent Engine."""
    print(f"Deploying ROOT agent to project={PROJECT_ID}, location={LOCATION}...")

    remote_app = reasoning_engines.ReasoningEngine.create(
        ROOTAgentApp(),
        requirements=[
            "google-adk>=2.1.0",
            "google-cloud-aiplatform>=1.57.0",
            "motor>=3.4.0",
            "pymongo>=4.7.0",
            "fastapi>=0.111.0",
            "pydantic>=2.7.0",
            "pydantic-settings>=2.3.0",
            "python-dotenv>=1.0.0",
        ],
        display_name="ROOT Urban Tree Intelligence Agent",
        description=(
            "Multi-agent system for urban tree permit analysis. "
            "Coordinates coalition discovery, precedent search, and Gemini-powered "
            "public comment drafting via Google ADK."
        ),
    )

    agent_resource_name = remote_app.resource_name
    print(f"\nDeployed successfully!")
    print(f"Resource name: {agent_resource_name}")
    print(f"\nAdd to .env:")
    print(f"  AGENT_BUILDER_AGENT_ID={agent_resource_name}")

    return agent_resource_name


if __name__ == "__main__":
    deploy_agent()
