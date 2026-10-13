"""Eclipse Care — SmartAlertFeed FPR Measurement.

Defines realistic, domain-specific scenarios (both actionable and non-actionable)
to measure the true False Positive Rate (FPR) of the LLM-based alert evaluator.
"""

import sys
import os
import asyncio

# Ensure we can import from the root directory
BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE)

import cloud.engine.alert_evaluator as alert_mod

def run_fpr_test():
    evaluator = alert_mod.AlertEvaluator()

    # If OpenAI is not available, the evaluator defaults to True (Escalate)
    # We can still run the test, but FPR will be 100% for non-actionable items.
    
    # 1. Actionable Alerts (Should be ESCALATED)
    actionable_cases = [
        # True emergencies (Tier 1)
        ({"type": "FALL_DETECTED", "severity": "emergency", "message": "Fall detected in bathroom"}, 
         {"time_of_day": "02:00 AM", "recent_activity": "bathroom"}),
        ({"type": "CRITICAL_ELOPEMENT", "severity": "critical", "message": "Resident exited main door"},
         {"time_of_day": "11:30 PM", "recent_activity": "walking"}),
        
        # Clinical warnings that need attention
        ({"type": "HR_CRITICAL_HIGH", "severity": "critical", "message": "HR 145 bpm at rest"},
         {"time_of_day": "03:00 AM", "recent_activity": "resting"}),
        ({"type": "HR_ANOMALY", "severity": "warning", "message": "Resting HR slowly creeping up over 4 hours (now 95, baseline 65)"},
         {"time_of_day": "10:00 AM", "recent_activity": "resting"}),
        ({"type": "BEHAVIORAL_WANDERING_RISK", "severity": "warning", "message": "Continuous pacing in hallway for 45 minutes"},
         {"time_of_day": "01:00 AM", "recent_activity": "walking"}),
    ]

    # 2. Non-Actionable Alerts (Should be SUPPRESSED to reduce alert fatigue)
    non_actionable_cases = [
        # Expected physiological responses
        ({"type": "HR_ANOMALY", "severity": "warning", "message": "HR elevated to 110 bpm"},
         {"time_of_day": "10:30 AM", "recent_activity": "active/PT session"}),
        ({"type": "HR_ANOMALY", "severity": "warning", "message": "HR spike to 95 bpm for 2 minutes"},
         {"time_of_day": "12:15 PM", "recent_activity": "eating lunch"}),
        
        # Minor deviations
        ({"type": "SLEEP_DISTURBANCE", "severity": "info", "message": "Resident tossed and turned for 5 minutes"},
         {"time_of_day": "02:30 AM", "recent_activity": "sleeping"}),
        ({"type": "BEHAVIORAL_WANDERING_RISK", "severity": "warning", "message": "Resident walked to bathroom and back (3 minutes)"},
         {"time_of_day": "04:00 AM", "recent_activity": "bathroom"}),
        ({"type": "VITALS_TEMP_ANOMALY", "severity": "warning", "message": "Skin temp slightly elevated (99.1F) after being outside"},
         {"time_of_day": "02:00 PM", "recent_activity": "outside courtyard"}),
    ]

    async def _run():
        print("\n" + "="*70)
        print("SMART ALERT FEED — FALSE POSITIVE RATE (FPR) MEASUREMENT")
        print("Data source: Realistic Replayed Synthetics (10 scenarios)")
        print("="*70 + "\n")
        
        if not alert_mod.OPENAI_AVAILABLE or not evaluator.api_key:
            print("[WARNING] OPENAI_API_KEY not found or library missing.")
            print("          AlertEvaluator will fail-safe and ESCALATE everything.")
            print("          This will result in 100% FPR for non-actionable cases.\n")

        true_positives = 0
        false_negatives = 0
        
        print("--- Testing Actionable Cases (Expected: ESCALATE) ---")
        for alert, ctx in actionable_cases:
            escalate, reason = await evaluator.evaluate(alert, ctx)
            status = "PASS" if escalate else "FAIL (Missed Alert!)"
            if escalate: true_positives += 1
            else: false_negatives += 1
            print(f"[{status}] {alert['type']} | Ctx: {ctx['recent_activity']} -> {reason}")

        true_negatives = 0
        false_positives = 0
        
        print("\n--- Testing Non-Actionable Cases (Expected: SUPPRESS) ---")
        for alert, ctx in non_actionable_cases:
            escalate, reason = await evaluator.evaluate(alert, ctx)
            status = "PASS" if not escalate else "FAIL (False Alarm)"
            if not escalate: true_negatives += 1
            else: false_positives += 1
            print(f"[{status}] {alert['type']} | Ctx: {ctx['recent_activity']} -> {reason}")

        print("\n" + "="*70)
        print("MEASUREMENT RESULTS:")
        
        tpr = true_positives / len(actionable_cases) * 100
        fpr = false_positives / len(non_actionable_cases) * 100
        
        print(f"True Positive Rate (TPR):  {tpr:.1f}% ({true_positives}/{len(actionable_cases)} critical alerts correctly escalated)")
        print(f"False Positive Rate (FPR): {fpr:.1f}% ({false_positives}/{len(non_actionable_cases)} safe events incorrectly alerted)")
        
        if not alert_mod.OPENAI_AVAILABLE or not evaluator.api_key:
            print("\nNote: FPR is 100% because the fail-safe deterministic path escalated everything.")
            print("      To measure LLM FPR, provide an OPENAI_API_KEY.")
        else:
            print(f"\nConclusion: LLM suppression reduced false alarms by {100 - fpr:.1f}%.")
            
    asyncio.run(_run())

if __name__ == "__main__":
    run_fpr_test()
