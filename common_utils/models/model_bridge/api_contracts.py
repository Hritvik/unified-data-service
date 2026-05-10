"""
Model bridge API contracts module.

This module is internal to common_utils.models and should not be imported directly.
Use 'from common_utils.models import ...' instead.
"""

# Prevent direct imports from this module
__all__ = []

from typing import Any, Dict, List, Optional, Type, Union

from pydantic import BaseModel, Field

from common_utils.enums import APIContract
from common_utils.exceptions.model_bridge import (
    UnsupportedAPIContractException,
    create_exception_with_context,
)


# Base Models
class Message(BaseModel):
    """Base message model for chat APIs."""

    role: str = Field(..., description="Message role (user, assistant, system)")
    content: str = Field(..., description="Message content")


class Tool(BaseModel):
    """Tool definition for function calling."""

    type: str = Field(..., description="Tool type")
    function: Dict[str, Any] = Field(..., description="Function definition")


# Error Response Models
class OpenAIError(BaseModel):
    """OpenAI API error response model."""

    message: str = Field(..., description="Error message")
    type: Optional[str] = Field(default=None, description="Error type")
    code: Optional[str] = Field(default=None, description="Error code")
    param: Optional[str] = Field(
        default=None, description="Parameter that caused the error"
    )


class ClaudeError(BaseModel):
    """Anthropic Claude API error response model."""

    type: str = Field(..., description="Error type")
    error: Dict[str, Any] = Field(..., description="Error details")


class GeminiError(BaseModel):
    """Google Gemini API error response model."""

    code: int = Field(..., description="HTTP status code")
    message: str = Field(..., description="Error message")
    status: str = Field(..., description="Error status")


# OpenAI API Contract Models
class OpenAIResponseFormat(BaseModel):
    """Response format specification for OpenAI."""

    type: str = Field(..., description="Response format type")


class OpenAIChatCompletionRequest(BaseModel):
    """OpenAI Chat Completion API request model."""

    messages: List[Dict[str, Any]] = Field(..., description="List of messages")
    temperature: Optional[float] = Field(
        default=0.7, description="Temperature for response generation"
    )
    max_tokens: Optional[int] = Field(
        default=1000, description="Maximum tokens in response"
    )
    top_p: Optional[float] = Field(default=None, description="Top-p sampling parameter")
    frequency_penalty: Optional[float] = Field(
        default=None, description="Frequency penalty"
    )
    presence_penalty: Optional[float] = Field(
        default=None, description="Presence penalty"
    )
    response_format: Optional[OpenAIResponseFormat] = Field(
        default=None, description="Response format specification"
    )
    tools: Optional[List[Tool]] = Field(default=None, description="Tools to use")
    tool_choice: Optional[Union[str, Dict[str, Any]]] = Field(
        default=None, description="Tool choice specification"
    )


class OpenAIUsage(BaseModel):
    """OpenAI usage information."""

    prompt_tokens: int = Field(..., description="Number of prompt tokens")
    completion_tokens: int = Field(..., description="Number of completion tokens")
    total_tokens: int = Field(..., description="Total number of tokens")


class OpenAIMessage(BaseModel):
    """OpenAI response message."""

    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")
    annotations: Optional[List[Any]] = Field(
        default=[], description="Message annotations"
    )
    refusal: Optional[Any] = Field(default=None, description="Refusal information")


class OpenAIChoice(BaseModel):
    """OpenAI response choice."""

    index: int = Field(..., description="Choice index")
    message: OpenAIMessage = Field(..., description="Response message")
    finish_reason: Optional[str] = Field(default=None, description="Finish reason")


class OpenAIChatCompletionResponse(BaseModel):
    """OpenAI Chat Completion API response model."""

    id: str = Field(..., description="Response ID")
    object: str = Field(..., description="Object type")
    created: int = Field(..., description="Creation timestamp")
    model: str = Field(..., description="Model used")
    choices: List[OpenAIChoice] = Field(..., description="Response choices")
    usage: OpenAIUsage = Field(..., description="Usage information")


# Claude API Contract Models
class ClaudeMessage(BaseModel):
    """Claude message model."""

    role: str = Field(..., description="Message role")
    content: str = Field(..., description="Message content")


class ClaudeChatRequest(BaseModel):
    """Anthropic Claude Chat API request model."""

    messages: List[ClaudeMessage] = Field(..., description="List of messages")
    max_tokens: Optional[int] = Field(
        default=1000, description="Maximum tokens in response"
    )
    temperature: Optional[float] = Field(
        default=0.7, description="Temperature for response generation"
    )
    top_p: Optional[float] = Field(default=None, description="Top-p sampling parameter")
    top_k: Optional[int] = Field(default=None, description="Top-k sampling parameter")
    anthropic_version: Optional[str] = Field(
        default=None, description="Anthropic API version"
    )
    system: Optional[str] = Field(default=None, description="System message for Claude")


class ClaudeContentBlock(BaseModel):
    """Claude content block."""

    type: str = Field(..., description="Content block type")
    text: str = Field(..., description="Text content")


class ClaudeUsage(BaseModel):
    """Claude usage information."""

    input_tokens: int = Field(..., description="Number of input tokens")
    output_tokens: int = Field(..., description="Number of output tokens")


class ClaudeChatResponse(BaseModel):
    """Anthropic Claude Chat API response model."""

    id: str = Field(..., description="Response ID")
    type: str = Field(..., description="Response type")
    role: str = Field(..., description="Response role")
    content: List[ClaudeContentBlock] = Field(..., description="Response content")
    model: str = Field(..., description="Model used")
    stop_reason: Optional[str] = Field(default=None, description="Stop reason")
    stop_sequence: Optional[str] = Field(default=None, description="Stop sequence")
    usage: ClaudeUsage = Field(..., description="Usage information")


# Gemini API Contract Models
class GeminiPart(BaseModel):
    """Gemini content part."""

    text: str = Field(..., description="Text content")


class GeminiContent(BaseModel):
    """Gemini content."""

    role: str = Field(..., description="Content role")
    parts: List[GeminiPart] = Field(..., description="Content parts")


class GeminiGenerationConfig(BaseModel):
    """Gemini generation configuration."""

    temperature: Optional[float] = Field(
        default=0.7, description="Temperature for response generation"
    )
    maxOutputTokens: Optional[int] = Field(
        default=1000, description="Maximum output tokens"
    )
    topP: Optional[float] = Field(default=None, description="Top-p sampling parameter")
    topK: Optional[int] = Field(default=None, description="Top-k sampling parameter")
    candidateCount: Optional[int] = Field(
        default=None, description="Number of candidates to generate"
    )
    stopSequences: Optional[List[str]] = Field(
        default=None, description="Stop sequences for generation"
    )


class GeminiSafetySetting(BaseModel):
    """Gemini safety setting."""

    category: str = Field(..., description="Safety category")
    threshold: str = Field(..., description="Safety threshold")


class GeminiChatRequest(BaseModel):
    """Google Gemini Chat API request model."""

    contents: List[GeminiContent] = Field(..., description="List of contents")
    generationConfig: Optional[GeminiGenerationConfig] = Field(
        default=None, description="Generation configuration"
    )
    safetySettings: Optional[List[GeminiSafetySetting]] = Field(
        default=None, description="Safety settings"
    )


class GeminiUsageMetadata(BaseModel):
    """Gemini usage metadata."""

    promptTokenCount: int = Field(..., description="Number of prompt tokens")
    candidatesTokenCount: int = Field(..., description="Number of candidate tokens")
    totalTokenCount: int = Field(..., description="Total number of tokens")


class GeminiCandidate(BaseModel):
    """Gemini response candidate."""

    content: GeminiContent = Field(..., description="Candidate content")
    finishReason: Optional[str] = Field(default=None, description="Finish reason")
    index: int = Field(..., description="Candidate index")
    safetyRatings: Optional[List[Dict[str, Any]]] = Field(
        default=None, description="Safety ratings"
    )


class GeminiChatResponse(BaseModel):
    """Google Gemini Chat API response model."""

    candidates: List[GeminiCandidate] = Field(..., description="Response candidates")
    promptFeedback: Optional[Dict[str, Any]] = Field(
        default=None, description="Prompt feedback"
    )
    usageMetadata: Optional[GeminiUsageMetadata] = Field(
        default=None, description="Usage metadata"
    )


# Factory for creating API contract models
class APIContractModelFactory:
    """Factory for creating API contract models based on contract type."""

    @staticmethod
    def get_request_model(
        api_contract: APIContract,
    ) -> Type[Union[OpenAIChatCompletionRequest, ClaudeChatRequest, GeminiChatRequest]]:
        """Get the appropriate request model for the given API contract."""
        contract_mapping = {
            APIContract.OPENAI_CHAT_COMPLETION: OpenAIChatCompletionRequest,
            APIContract.CLAUDE_CHAT: ClaudeChatRequest,
            APIContract.GEMINI_CHAT: GeminiChatRequest,
        }

        if api_contract not in contract_mapping:
            raise create_exception_with_context(
                UnsupportedAPIContractException,
                f"Unsupported API contract: {api_contract}",
                api_contract=str(api_contract),
                details={"supported_contracts": list(contract_mapping.keys())},
            )

        return contract_mapping[api_contract]

    @staticmethod
    def get_response_model(
        api_contract: APIContract,
    ) -> Type[
        Union[OpenAIChatCompletionResponse, ClaudeChatResponse, GeminiChatResponse]
    ]:
        """Get the appropriate response model for the given API contract."""
        contract_mapping = {
            APIContract.OPENAI_CHAT_COMPLETION: OpenAIChatCompletionResponse,
            APIContract.CLAUDE_CHAT: ClaudeChatResponse,
            APIContract.GEMINI_CHAT: GeminiChatResponse,
        }

        if api_contract not in contract_mapping:
            raise create_exception_with_context(
                UnsupportedAPIContractException,
                f"Unsupported API contract: {api_contract}",
                api_contract=str(api_contract),
                details={"supported_contracts": list(contract_mapping.keys())},
            )

        return contract_mapping[api_contract]
