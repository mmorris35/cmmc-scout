"""CMMC Assessment Agent using LangChain and Comet ML."""

import os
import json
import re
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from langchain.chat_models import ChatOpenAI
from langchain.schema import HumanMessage, SystemMessage, AIMessage

from .prompts import (
    SYSTEM_PROMPT_TEMPLATE,
    CONTROL_ASSESSMENT_PROMPT,
    CLASSIFICATION_PROMPT,
    PROMPT_VERSION,
)

logger = logging.getLogger(__name__)


class AssessmentAgent:
    """
    CMMC Assessment Agent with Comet ML tracking.

    Uses LLM to:
    - Generate assessment questions for controls
    - Classify user responses
    - Provide remediation guidance
    """

    def __init__(
        self,
        control_data: Dict[str, Any],
        comet_experiment: Optional[Any] = None,
        model_name: str = "gpt-3.5-turbo",
        temperature: float = 0.3,
    ):
        """
        Initialize assessment agent.

        Args:
            control_data: Control information dictionary
            comet_experiment: Optional Comet ML experiment for tracking
            model_name: LLM model to use
            temperature: LLM temperature (lower = more deterministic)
        """
        self.control_data = control_data
        self.comet_experiment = comet_experiment
        self.model_name = model_name
        self.temperature = temperature

        # Initialize LLM
        api_key = os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("No LLM API key found. Set OPENAI_API_KEY or ANTHROPIC_API_KEY")

        self.llm = ChatOpenAI(
            model_name=model_name,
            temperature=temperature,
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Conversation history
        self.conversation_history = []

        # Log to Comet if available
        if self.comet_experiment:
            self.comet_experiment.log_parameters({
                "control_id": control_data.get("control_id"),
                "model_name": model_name,
                "temperature": temperature,
                "prompt_version": PROMPT_VERSION,
            })

        logger.info(f"AssessmentAgent initialized for control {control_data.get('control_id')}")

    def _sanitize_input(self, user_input: str) -> str:
        """
        Sanitize user input to prevent prompt injection.

        Args:
            user_input: Raw user input

        Returns:
            Sanitized input
        """
        # Remove potential prompt injection patterns
        sanitized = user_input.strip()

        # Remove excessive whitespace
        sanitized = re.sub(r'\s+', ' ', sanitized)

        # Limit length
        max_length = 2000
        if len(sanitized) > max_length:
            logger.warning(f"User input truncated from {len(sanitized)} to {max_length} chars")
            sanitized = sanitized[:max_length]

        # Check for suspicious patterns (but don't block legitimate responses)
        suspicious_patterns = [
            r'ignore\s+(all\s+)?previous\s+instructions',
            r'disregard\s+(all\s+)?previous',
            r'forget\s+(all\s+)?previous',
            r'new\s+instructions',
            r'system\s*:',
            r'assistant\s*:',
        ]

        for pattern in suspicious_patterns:
            if re.search(pattern, sanitized, re.IGNORECASE):
                logger.warning(f"Potential prompt injection detected: {pattern}")
                # Still allow the input, but log it

        return sanitized

    def generate_question(self) -> str:
        """
        Generate an assessment question for the control.

        Returns:
            Assessment question text
        """
        prompt = CONTROL_ASSESSMENT_PROMPT.format(
            control_id=self.control_data.get("control_id", ""),
            control_title=self.control_data.get("title", ""),
            requirement=self.control_data.get("requirement", ""),
            assessment_objective=self.control_data.get("assessment_objective", ""),
            discussion=self.control_data.get("discussion", ""),
        )

        messages = [
            SystemMessage(content="You are a CMMC assessment expert."),
            HumanMessage(content=prompt),
        ]

        start_time = datetime.utcnow()

        try:
            response = self.llm(messages)
            question = response.content

            # Log to Comet
            if self.comet_experiment:
                self.comet_experiment.log_text(question, metadata={
                    "type": "question",
                    "control_id": self.control_data.get("control_id"),
                })

            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.info(f"Generated question in {duration:.2f}s")

            return question

        except Exception as e:
            logger.error(f"Error generating question: {e}")
            # Fallback to template-based question
            return f"Do you have documented policies and procedures for {self.control_data.get('title')}? Please describe your implementation."

    def classify_response(self, user_response: str) -> Dict[str, Any]:
        """
        Classify a user's response to a control question.

        Args:
            user_response: User's response (will be sanitized)

        Returns:
            Classification result dictionary
        """
        # Sanitize input
        sanitized_response = self._sanitize_input(user_response)

        # Build system prompt
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            control_id=self.control_data.get("control_id", ""),
            control_title=self.control_data.get("title", ""),
            requirement=self.control_data.get("requirement", ""),
            assessment_objective=self.control_data.get("assessment_objective", ""),
        )

        # Build classification prompt
        classification_prompt = CLASSIFICATION_PROMPT.format(
            control_id=self.control_data.get("control_id", ""),
            control_title=self.control_data.get("title", ""),
            requirement=self.control_data.get("requirement", ""),
            user_response=sanitized_response,
        )

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=classification_prompt),
        ]

        start_time = datetime.utcnow()

        try:
            response = self.llm(messages)
            result_text = response.content

            # Try to parse JSON response
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback parsing if LLM didn't return valid JSON
                logger.warning("LLM response not valid JSON, using fallback parsing")
                result = self._parse_classification_fallback(result_text)

            # Normalize classification
            classification = result.get("classification", "").upper()
            if classification not in ["COMPLIANT", "PARTIAL", "NON_COMPLIANT"]:
                # Map variations
                if "PARTIAL" in classification or "PARTIALLY" in classification:
                    classification = "PARTIAL"
                elif "NON" in classification or "NOT" in classification:
                    classification = "NON_COMPLIANT"
                else:
                    classification = "PARTIAL"  # Default to partial if unclear

            result["classification"] = classification.lower()  # Store as lowercase

            # Log to Comet
            if self.comet_experiment:
                duration = (datetime.utcnow() - start_time).total_seconds()
                self.comet_experiment.log_metrics({
                    "classification_duration_sec": duration,
                    "confidence": result.get("confidence", 0.5),
                })
                self.comet_experiment.log_text(
                    f"User: {sanitized_response}\nClassification: {result['classification']}\nExplanation: {result.get('explanation')}",
                    metadata={
                        "type": "classification",
                        "control_id": self.control_data.get("control_id"),
                        "classification": result["classification"],
                    }
                )

            logger.info(f"Classified response as {result['classification']} in {(datetime.utcnow() - start_time).total_seconds():.2f}s")

            return result

        except Exception as e:
            logger.error(f"Error classifying response: {e}")
            # Fallback classification
            return {
                "classification": "partial",
                "explanation": "Unable to fully assess response. Manual review recommended.",
                "remediation": "Please provide more detailed information about your implementation.",
                "confidence": 0.3,
            }

    def _parse_classification_fallback(self, text: str) -> Dict[str, Any]:
        """
        Fallback parser when LLM doesn't return valid JSON.

        Args:
            text: Raw LLM response

        Returns:
            Parsed classification dictionary
        """
        # Try to extract classification
        classification = "partial"
        if "COMPLIANT" in text.upper() and "NON" not in text.upper():
            classification = "compliant"
        elif "NON" in text.upper() or "NOT COMPLIANT" in text.upper():
            classification = "non_compliant"

        # Extract explanation (first few sentences)
        sentences = text.split('.')
        explanation = '. '.join(sentences[:2]) + '.' if sentences else text

        return {
            "classification": classification,
            "explanation": explanation[:500],
            "remediation": "Please review this control manually for accurate assessment.",
            "confidence": 0.5,
        }

    def get_conversation_summary(self) -> str:
        """
        Get a summary of the conversation.

        Returns:
            Conversation summary
        """
        return f"Assessed control {self.control_data.get('control_id')} - {self.control_data.get('title')}"


def create_assessment_agent(
    control_data: Dict[str, Any],
    enable_comet: bool = True,
) -> AssessmentAgent:
    """
    Factory function to create an assessment agent with optional Comet tracking.

    Args:
        control_data: Control information
        enable_comet: Whether to enable Comet ML tracking

    Returns:
        AssessmentAgent instance
    """
    comet_experiment = None

    if enable_comet:
        try:
            from comet_ml import Experiment

            api_key = os.getenv("COMET_API_KEY")
            project_name = os.getenv("COMET_PROJECT_NAME", "cmmc-scout")

            if api_key:
                comet_experiment = Experiment(
                    api_key=api_key,
                    project_name=project_name,
                )
                comet_experiment.set_name(f"assessment_{control_data.get('control_id')}")
                comet_experiment.add_tag("assessment")
                comet_experiment.add_tag(control_data.get("domain", "unknown"))
                logger.info("Comet ML tracking enabled")
            else:
                logger.warning("COMET_API_KEY not set, tracking disabled")

        except ImportError:
            logger.warning("comet_ml not installed, tracking disabled")
        except Exception as e:
            logger.warning(f"Failed to initialize Comet: {e}")

    return AssessmentAgent(
        control_data=control_data,
        comet_experiment=comet_experiment,
    )
