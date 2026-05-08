"""Knowledge-to-Action Translation for HENLA-6 KS-17.

Translates theoretical knowledge into safe operational plans, warnings, and strategies.
"""

from __future__ import annotations

from typing import Any


class ActionableInsight:
    def __init__(self, knowledge_id: str, insight_type: str, action_guidance: str):
        self.knowledge_id = knowledge_id
        self.insight_type = insight_type # plan, warning, experiment
        self.action_guidance = action_guidance


class KnowledgeToActionEngine:
    def __init__(self):
        self.insights: list[ActionableInsight] = []

    def derive_insight(self, knowledge_id: str, insight_type: str, guidance: str) -> ActionableInsight:
        insight = ActionableInsight(knowledge_id, insight_type, guidance)
        self.insights.append(insight)
        return insight

    def get_summary(self) -> dict[str, Any]:
        return {
            "insights_generated": len(self.insights),
            "by_type": {
                "warning": len([i for i in self.insights if i.insight_type == "warning"]),
                "plan": len([i for i in self.insights if i.insight_type == "plan"])
            }
        }
