"""
app/services/agent_investigator.py
───────────────────────────────────
Agentic Workflow: Uses Gemini to investigate a flagged transaction
and write a human-readable Suspicious Activity Report (SAR).
"""
import json
import logging
from typing import Optional

try:
    import ollama
except ImportError:
    ollama = None
from pydantic import BaseModel, Field

from config.settings import settings
from app.models.transaction import Transaction
from app.models.behavior_profile import UserBehaviorProfile

logger = logging.getLogger(__name__)


class AgentInvestigator:

    def investigate(
        self,
        transaction: Transaction,
        profile: UserBehaviorProfile,
        model_name: str = "llama3.1"
    ) -> dict:
        """
        Synthesize the transaction and user history into a SAR report.
        """

        # Build context for the LLM
        txn_data = {
            "transaction_id": transaction.transaction_id,
            "amount": transaction.amount,
            "location": transaction.location,
            "merchant_type": transaction.merchant_type,
            "timestamp": transaction.timestamp.isoformat(),
            "decision": transaction.decision,
            "risk_score": transaction.risk_score,
            "reasons": json.loads(transaction.reasons or "[]"),
        }

        profile_data = {
            "avg_amount": profile.avg_amount,
            "transaction_count": profile.transaction_count,
            "frequent_locations": json.loads(profile.frequent_locations or "[]"),
            "active_hours": json.loads(profile.active_hours or "[]"),
        }

        prompt = f"""
        You are a senior fraud analyst AI copilot. Review the following flagged transaction and the user's historical profile.

        Transaction Details:
        {json.dumps(txn_data, indent=2)}

        User Profile (Historical reference):
        {json.dumps(profile_data, indent=2)}

        Please analyze why this transaction was flagged (if it was) and write a concise, bulleted Suspicious Activity Report (SAR) determining the likely nature of the event (e.g., account takeover, stolen card, or false positive). Ensure your insight relies ONLY on the data provided above.
        
        Respond ONLY with a valid JSON object matching exactly this schema:
        {{
          "summary": "A 2-3 sentence overview of the investigation findings.",
          "risk_level": "High, Medium, or Low.",
          "recommended_action": "Action for the human analyst (e.g., 'Contact user', 'Block card', 'Approve').",
          "bullet_points": ["point 1", "point 2", "point 3"]
        }}
        """

        if ollama is None:
            return {
                "summary": "AI Copilot investigation unavailable (ollama package not installed).",
                "risk_level": "Medium" if transaction.decision == "VERIFY" else ("High" if transaction.decision == "BLOCK" else "Low"),
                "recommended_action": "Review triggered reason codes and user transaction profile.",
                "bullet_points": json.loads(transaction.reasons or "[]")
            }

        try:
            response = ollama.chat(
                model=model_name,
                messages=[{'role': 'user', 'content': prompt}],
                format='json',
                options={'temperature': 0.2}
            )
            report = json.loads(response['message']['content'])
            return report
        except Exception as e:
            logger.error(f"Agent investigator failed: {e}")
            return {
                "summary": f"Failed to generate report: {str(e)}",
                "risk_level": "Unknown",
                "recommended_action": "Manual review required",
                "bullet_points": ["LLM generation failed"]
            }
