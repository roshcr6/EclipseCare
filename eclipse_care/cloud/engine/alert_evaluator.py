"""Eclipse Care — LLM Hybrid Rule Engine for Alert Fatigue Reduction.

Uses deterministic rules for critical emergencies (falls) and an LLM to evaluate 
the semantic context of lower-tier warnings (e.g., HR anomalies, lack of movement).

Research Context:
Combining deterministic rules with LLM semantic reasoning is theorized to reduce false-positive
nursing home alarms, mitigating alert fatigue.

VALIDATION STATUS: Unknown.
  The specific false-positive reduction rate of this system has NOT been measured
  on realistic replayed data or real resident data. Do not cite percentage reductions.
"""

import os
import json
import structlog
from typing import Dict, Any, Tuple

logger = structlog.get_logger("engine.alert_evaluator")

# Attempt to load OpenAI for the LLM component
try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


class AlertEvaluator:
    """Evaluates incoming alerts to determine if they should page staff."""
    
    def __init__(self):
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.client = AsyncOpenAI(api_key=self.api_key) if OPENAI_AVAILABLE and self.api_key else None
        
        # System prompt instructing the LLM on how to evaluate clinical context
        self.system_prompt = """
        You are an expert clinical triage assistant in a nursing home.
        Your goal is to REDUCE ALERT FATIGUE by suppressing non-actionable alarms.
        
        You will receive an alert event and recent context (time of day, recent activity).
        Decide if this alert should be:
        - "ESCALATE": Needs immediate nurse attention.
        - "SUPPRESS": Normal behavior given context, do not disturb staff.
        
        Respond ONLY with a JSON object in this exact format:
        {"decision": "ESCALATE" or "SUPPRESS", "reason": "Short 1 sentence explanation"}
        """

    async def evaluate(self, alert_data: Dict[str, Any], context: Dict[str, Any] = None) -> Tuple[bool, str]:
        """
        Evaluate an alert.
        Returns (should_escalate: bool, reasoning: str)
        """
        alert_type = alert_data.get("type", "")
        severity = alert_data.get("severity", "warning")
        
        # TIER 1: Deterministic Rules (Bypass LLM for safety)
        if alert_type == "FALL_DETECTED" or alert_type == "CRITICAL_ELOPEMENT" or severity in ("emergency", "critical"):
            logger.info("Rule Engine: Escalating critical safety alert", type=alert_type)
            return True, "Deterministic Rule: Critical safety event (Fall or Elopement) requires immediate attention."

        # TIER 2: Semantic Evaluation via LLM
        if not self.client:
            logger.warning("LLM client not configured. Defaulting to ESCALATE to ensure safety.")
            return True, "LLM unavailable; safe default."

        try:
            logger.debug("Routing alert to LLM for context evaluation", type=alert_type)
            
            # Construct the prompt with context
            prompt = f"""
            Alert: {alert_type}
            Message: {alert_data.get('message', '')}
            Time of Day: {context.get('time_of_day', 'Unknown')}
            Recent Activity: {context.get('recent_activity', 'Unknown')}
            """
            
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini", # Fast, cheap, context-aware
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                response_format={"type": "json_object"},
                temperature=0.1
            )
            
            result_str = response.choices[0].message.content
            result = json.loads(result_str)
            
            decision = result.get("decision", "ESCALATE")
            reason = result.get("reason", "No reason provided by LLM")
            
            should_escalate = decision == "ESCALATE"
            
            logger.info("LLM Evaluation complete", escalate=should_escalate, reason=reason)
            return should_escalate, reason
            
        except Exception as e:
            logger.error("LLM evaluation failed", error=str(e))
            return True, "LLM evaluation failed; safe default."
