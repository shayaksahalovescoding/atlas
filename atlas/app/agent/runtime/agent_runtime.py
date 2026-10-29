import json
import logging
import asyncio
import time
from typing import Dict, List, Optional
from datetime import datetime

from atlas.app.model.ollama.ollama_provider import OllamaProvider
from atlas.app.model.prompts.system_prompts import (
    SYSTEM_PROMPT, DIAGNOSIS_PROMPT, INVESTIGATION_PROMPT,
    COUNTERFACTUAL_PROMPT, SUMMARY_PROMPT, EXPLANATION_PROMPT
)
from atlas.app.reasoning.context.context_builder import ContextBuilder
from atlas.app.reasoning.hypotheses.hypothesis_engine import HypothesisEngine
from atlas.app.reasoning.counterfactual.counterfactual_engine import CounterfactualEngine
from atlas.app.agent.tools.tool_registry import ToolRegistry
from atlas.app.core.events.event_bus import EventBus
from atlas.app.core.events.event_types import Event, EventType

logger = logging.getLogger("atlas.agent.runtime")


class QueryClassification:
    SIMPLE_LOOKUP = "simple_lookup"
    STRUCTURED_QUERY = "structured_query"
    AI_REASONING = "ai_reasoning"
    INVESTIGATION = "investigation"
    COUNTERFACTUAL = "counterfactual"


class AgentRuntime:
    def __init__(self, ai_provider: OllamaProvider,
                 context_builder: ContextBuilder,
                 hypothesis_engine: HypothesisEngine,
                 counterfactual_engine: CounterfactualEngine,
                 tool_registry: ToolRegistry,
                 event_bus: EventBus):
        self._ai = ai_provider
        self._context_builder = context_builder
        self._hypothesis_engine = hypothesis_engine
        self._counterfactual = counterfactual_engine
        self._tools = tool_registry
        self._event_bus = event_bus
        self._max_actions = 10
        self._max_runtime_seconds = 60
        self._query_count = 0
        self._active_query = False

    async def process_query(self, question: str) -> Dict:
        if self._active_query:
            return {"error": "A query is already being processed"}

        self._active_query = True
        self._query_count += 1
        start = time.perf_counter()

        try:
            self._event_bus.publish_sync(Event(
                event_type=EventType.AI_QUERY_STARTED,
                timestamp=datetime.now().isoformat(),
                source="agent_runtime",
                metadata={"question": question[:200]},
            ))

            classification = self._classify_query(question)

            if classification == QueryClassification.SIMPLE_LOOKUP:
                result = await self._handle_simple_lookup(question)
            elif classification == QueryClassification.COUNTERFACTUAL:
                result = await self._handle_counterfactual(question)
            elif classification == QueryClassification.STRUCTURED_QUERY:
                result = await self._handle_structured_query(question)
            else:
                result = await self._handle_ai_reasoning(question)

            elapsed = (time.perf_counter() - start) * 1000
            result["processing_time_ms"] = round(elapsed, 1)
            result["classification"] = classification

            self._event_bus.publish_sync(Event(
                event_type=EventType.AI_QUERY_COMPLETED,
                timestamp=datetime.now().isoformat(),
                source="agent_runtime",
                metadata={"question": question[:200], "time_ms": elapsed},
            ))

            return result

        except Exception as e:
            logger.error(f"Query processing error: {e}", exc_info=True)
            self._event_bus.publish_sync(Event(
                event_type=EventType.AI_QUERY_FAILED,
                timestamp=datetime.now().isoformat(),
                source="agent_runtime",
                metadata={"error": str(e)},
            ))
            return {"error": str(e), "answer": f"I encountered an error while processing your question: {e}"}
        finally:
            self._active_query = False

    def _classify_query(self, question: str) -> str:
        q = question.lower()

        counterfactual_phrases = [
            "what would happen", "what if", "what happens if",
            "what will break", "what will happen", "impact of",
            "if i disable", "if i stop", "if i terminate",
            "if i close", "if i remove", "how much memory",
        ]
        for phrase in counterfactual_phrases:
            if phrase in q:
                return QueryClassification.COUNTERFACTUAL

        simple_phrases = [
            "how much ram", "what is my cpu", "uptime",
            "how many processes", "disk space", "network speed",
            "what processes", "list services", "list applications",
            "show me", "what is running",
        ]
        for phrase in simple_phrases:
            if phrase in q:
                return QueryClassification.STRUCTURED_QUERY

        reasoning_phrases = [
            "why", "what caused", "explain", "diagnose",
            "reason", "investigate", "analyze", "slow",
            "crash", "problem", "issue", "unusual",
            "changed", "different", "abnormal", "wrong",
        ]
        for phrase in reasoning_phrases:
            if phrase in q:
                return QueryClassification.AI_REASONING

        return QueryClassification.AI_REASONING

    async def _handle_simple_lookup(self, question: str) -> Dict:
        context = self._context_builder.build_system_context()
        health = context.get("system_health", {})

        return {
            "answer": self._format_system_summary(health),
            "data": health,
            "source": "deterministic",
        }

    async def _handle_structured_query(self, question: str) -> Dict:
        context = self._context_builder.build_system_context(question)

        relevant = context.get("relevant_entities", [])
        if relevant:
            entity_details = []
            for ent in relevant[:5]:
                detail = self._context_builder.build_entity_context(ent["id"])
                entity_details.append(detail)
            context["entity_details"] = entity_details

        if not self._ai.connected:
            return {
                "answer": self._format_structured_answer(context),
                "data": context,
                "source": "deterministic",
            }

        prompt = DIAGNOSIS_PROMPT.format(
            context=json.dumps(context, indent=2, default=str)[:4000],
            question=question,
        )

        response = await self._ai.generate(prompt, SYSTEM_PROMPT, temperature=0.3)
        return {
            "answer": response,
            "data": context,
            "evidence": context.get("candidate_hypotheses", []),
            "source": "ai",
        }

    async def _handle_counterfactual(self, question: str) -> Dict:
        q = question.lower()

        if "process" in q or "terminate" in q or "kill" in q:
            words = question.split()
            for word in words:
                results = self._counterfactual._graph.search(word, "process")
                if results:
                    impact = self._counterfactual.simulate_process_termination(results[0].id)
                    if not self._ai.connected:
                        return {"answer": self._format_impact(impact), "data": impact, "source": "deterministic"}

                    prompt = COUNTERFACTUAL_PROMPT.format(
                        action=f"Terminate process: {results[0].name}",
                        context=json.dumps(self._context_builder.build_system_context(), default=str)[:2000],
                        impact=json.dumps(impact, indent=2, default=str)[:2000],
                    )
                    response = await self._ai.generate(prompt, SYSTEM_PROMPT, temperature=0.3)
                    return {"answer": response, "data": impact, "source": "ai"}

        elif "service" in q or "disable" in q:
            words = question.split()
            for word in words:
                results = self._counterfactual._graph.search(word, "service")
                if results:
                    impact = self._counterfactual.simulate_service_disable(results[0].id)
                    if not self._ai.connected:
                        return {"answer": self._format_impact(impact), "data": impact, "source": "deterministic"}

                    prompt = COUNTERFACTUAL_PROMPT.format(
                        action=f"Disable service: {results[0].name}",
                        context=json.dumps(self._context_builder.build_system_context(), default=str)[:2000],
                        impact=json.dumps(impact, indent=2, default=str)[:2000],
                    )
                    response = await self._ai.generate(prompt, SYSTEM_PROMPT, temperature=0.3)
                    return {"answer": response, "data": impact, "source": "ai"}

        context = self._context_builder.build_system_context(question)
        if self._ai.connected:
            prompt = DIAGNOSIS_PROMPT.format(
                context=json.dumps(context, indent=2, default=str)[:4000],
                question=question,
            )
            response = await self._ai.generate(prompt, SYSTEM_PROMPT)
            return {"answer": response, "data": context, "source": "ai"}

        return {"answer": "Could not determine the specific entity for simulation.", "source": "error"}

    async def _handle_ai_reasoning(self, question: str) -> Dict:
        context = self._context_builder.build_system_context(question)
        hypotheses = self._hypothesis_engine.generate_hypotheses(question)

        context["hypotheses"] = [h.to_dict() for h in hypotheses]

        if not self._ai.connected:
            top = hypotheses[0] if hypotheses else None
            if top:
                return {
                    "answer": f"Most likely: {top.name} (confidence: {top.score:.0%})\n\nEvidence:\n" +
                              "\n".join(f"- {e['evidence']}" for e in top.supporting_evidence),
                    "data": context,
                    "hypotheses": [h.to_dict() for h in hypotheses],
                    "source": "deterministic",
                }
            return {"answer": "Unable to determine the cause without more data.", "source": "deterministic"}

        prompt = DIAGNOSIS_PROMPT.format(
            context=json.dumps(context, indent=2, default=str)[:6000],
            question=question,
        )

        response = await self._ai.generate(prompt, SYSTEM_PROMPT, temperature=0.4)
        return {
            "answer": response,
            "data": context.get("system_health"),
            "hypotheses": [h.to_dict() for h in hypotheses],
            "evidence": context.get("active_anomalies", []),
            "source": "ai",
        }

    def _format_system_summary(self, health: Dict) -> str:
        lines = [
            f"CPU: {health.get('cpu_percent', 0):.0f}%",
            f"Memory: {health.get('memory_percent', 0):.0f}%",
            f"Swap: {health.get('swap_percent', 0):.0f}%",
            f"Processes: {health.get('process_count', 0)}",
            f"Uptime: {health.get('uptime', 0) // 3600}h {(health.get('uptime', 0) % 3600) // 60}m",
        ]
        return "\n".join(lines)

    def _format_structured_answer(self, context: Dict) -> str:
        parts = []
        health = context.get("system_health", {})
        parts.append(f"System Health: CPU {health.get('cpu_percent', 0):.0f}%, RAM {health.get('memory_percent', 0):.0f}%")

        consumers = context.get("top_resource_consumers", [])
        if consumers:
            parts.append("\nTop Memory Consumers:")
            for c in consumers[:5]:
                parts.append(f"  {c['name']}: {c.get('memory_bytes', 0) / (1024*1024):.0f} MB")

        anomalies = context.get("active_anomalies", [])
        if anomalies:
            parts.append("\nActive Anomalies:")
            for a in anomalies:
                parts.append(f"  ⚠ {a['description']}")

        return "\n".join(parts)

    def _format_impact(self, impact: Dict) -> str:
        if "error" in impact:
            return impact["error"]
        lines = []
        if "process" in impact:
            lines.append(f"Process: {impact['process'].get('name', 'Unknown')}")
        if "service" in impact:
            lines.append(f"Service: {impact['service'].get('name', 'Unknown')}")
        if impact.get("memory_freed_bytes"):
            lines.append(f"Memory freed: {impact['memory_freed_bytes'] / (1024*1024):.0f} MB")
        if impact.get("total_affected"):
            lines.append(f"Total affected entities: {impact['total_affected']}")
        if impact.get("warnings"):
            for w in impact["warnings"]:
                lines.append(f"⚠ {w}")
        return "\n".join(lines)
