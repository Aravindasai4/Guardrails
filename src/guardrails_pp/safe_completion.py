from typing import Dict

SAFE_COMPLETIONS: Dict[str, str] = {
    "social_engineering": (
        "I can't help create impersonation, fraud, or scam content.\n\n"
        "What I *can* do safely:\n"
        "1) Explain how these scams work from a defender's perspective\n"
        "2) List common red flags attackers use (urgency, secrecy, authority)\n"
        "3) Give prevention controls (call-back verification, dual approval, DMARC/DKIM/SPF)\n"
        "4) Help design ethical training scenarios that do NOT include a usable scam template\n\n"
        "If you tell me the audience (finance team, general staff) and the goal (awareness vs tabletop), "
        "I'll tailor a safe training outline."
    ),
    "physical_harm": (
        "I can't help with instructions that could enable harm.\n\n"
        "What I *can* do safely:\n"
        "1) Provide high-level safety/engineering principles (risk, failure modes)\n"
        "2) Explain prevention and emergency response\n"
        "3) Share non-actionable educational context\n\n"
        "Tell me if this is for safety training, a class, or an incident prevention guide, and I'll adapt it."
    ),
    "data_exfiltration": (
        "I can't help with data theft, evasion, or bypassing security controls.\n\n"
        "What I *can* do safely:\n"
        "1) Defensive monitoring ideas (logging, alerting, anomaly detection)\n"
        "2) Hardening guidance (least privilege, DB auditing, DLP)\n"
        "3) A legal/ethical penetration test plan framework (scope, approvals, reporting)\n\n"
        "If you describe your environment at a high level (Postgres version, audit stack), I'll suggest defensive checks."
    ),
    "weapons_explosives": (
        "I can't provide information that could enable violence or harm.\n\n"
        "What I *can* do safely:\n"
        "1) Discuss security awareness and threat detection\n"
        "2) Explain safety protocols and emergency response\n"
        "3) Provide information on reporting suspicious activity\n\n"
        "If this is for a security training purpose, please clarify the context."
    ),
    "toxicity": (
        "I noticed some potentially harmful language in the request.\n\n"
        "What I *can* do safely:\n"
        "1) Help rephrase the request in a constructive way\n"
        "2) Address the underlying question without harmful framing\n"
        "3) Provide information on the topic in a respectful manner\n\n"
        "Could you rephrase your request?"
    ),
    "default": (
        "I can't help with that specific request, but I can help with safer alternatives.\n\n"
        "Please let me know if you'd like me to:\n"
        "1) Approach this topic from a different angle\n"
        "2) Provide educational context instead\n"
        "3) Help with a related but safer question"
    ),
}


def get_safe_completion(category: str) -> str:
    return SAFE_COMPLETIONS.get(category, SAFE_COMPLETIONS["default"])
