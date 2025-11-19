"""Versioned prompts for CMMC assessment agent.

All prompts are version-controlled and tracked in Comet ML for performance analysis.
"""

# Version tracking
PROMPT_VERSION = "1.0.0"

# System prompt for the CMMC assessment agent
SYSTEM_PROMPT_TEMPLATE = """You are a CMMC (Cybersecurity Maturity Model Certification) Level 2 assessment agent specializing in NIST SP 800-171 compliance evaluation.

Your role is to:
1. Ask specific, targeted questions about CMMC controls
2. Evaluate user responses against NIST SP 800-171 requirements
3. Classify responses as COMPLIANT, PARTIAL, or NON-COMPLIANT
4. Provide clear, actionable remediation guidance
5. Never make assumptions - ask for clarification when uncertain

Current Control Being Assessed:
Control ID: {control_id}
Title: {control_title}
Requirement: {requirement}
Assessment Objective: {assessment_objective}

Guidelines for Classification:
- COMPLIANT: Policy exists, properly documented, evidence available, meets all requirements
- PARTIAL: Policy exists but has implementation gaps (missing audit trails, incomplete automation, etc.)
- NON-COMPLIANT: No policy, no process, critical gaps, or fundamental requirements not met

Be professional, thorough, and provide specific examples when suggesting improvements.
"""

# Prompt for assessing a specific control
CONTROL_ASSESSMENT_PROMPT = """You are evaluating the following CMMC control:

Control: {control_id} - {control_title}
Requirement: {requirement}

Assessment Objective: {assessment_objective}

Discussion: {discussion}

Ask the user a clear, specific question to determine if this control is implemented.
Focus on:
1. Whether documented policies exist
2. How the process is implemented
3. What evidence can be provided

Keep your question concise and professional.
"""

# Prompt for classifying user responses (with few-shot examples)
CLASSIFICATION_PROMPT = """Based on the user's response, classify their compliance with this CMMC control.

Control: {control_id} - {control_title}
Requirement: {requirement}

User Response: {user_response}

Examples of Classifications:

Example 1 - COMPLIANT:
User: "We have a documented access control policy approved by management. Access requests go through our ServiceNow ticketing system which logs all approvals with timestamps. We conduct quarterly access reviews and maintain audit logs for 3 years."
Classification: COMPLIANT
Reasoning: Documented policy, proper process with audit trail, evidence available

Example 2 - PARTIAL:
User: "We have an access control policy. Manager approves access requests via email, then IT creates the account in Active Directory."
Classification: PARTIAL
Reasoning: Policy exists but email approvals lack proper audit trail; needs ticketing system

Example 3 - NON-COMPLIANT:
User: "We don't have a formal policy. IT creates accounts when people ask for them."
Classification: NON-COMPLIANT
Reasoning: No documented policy, no formal approval process, no audit trail

Now classify this response:
User Response: {user_response}

Provide:
1. Classification: COMPLIANT, PARTIAL, or NON-COMPLIANT
2. Brief explanation (2-3 sentences)
3. If PARTIAL or NON-COMPLIANT, specific remediation steps

Format your response as JSON:
{{
  "classification": "COMPLIANT|PARTIAL|NON_COMPLIANT",
  "explanation": "Brief explanation here",
  "remediation": "Specific steps if needed (or null if compliant)",
  "confidence": 0.0-1.0
}}
"""

# Prompt for gap analysis and remediation suggestions
REMEDIATION_PROMPT = """Analyze the following compliance gaps and provide prioritized remediation guidance.

Domain: {domain}
Non-Compliant Controls: {non_compliant_controls}
Partially Compliant Controls: {partial_controls}

For each gap, provide:
1. Priority (1-10, where 10 is critical)
2. Estimated effort (Low/Medium/High)
3. Estimated timeline (weeks)
4. Specific implementation steps
5. Estimated cost range (if applicable)

Format as a prioritized action plan suitable for presentation to management.
"""

# Prompt safety guidelines
PROMPT_SAFETY_NOTES = """
IMPORTANT SECURITY MEASURES:
1. User input is sanitized before being inserted into prompts
2. System prompts are isolated from user content
3. Tokens are NEVER included in prompt context
4. All prompt-response pairs are logged to Comet ML
5. Prompt injection attempts are detected and blocked
"""
