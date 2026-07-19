from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field

def to_strict_json_schema(model: type[BaseModel]) -> dict[str, Any]:
    schema = model.model_json_schema()
    
    def _make_strict(node: dict[str, Any]) -> None:
        if node.get("type") == "object":
            node["additionalProperties"] = False
            # Ensure all properties are marked required for strict mode
            if "properties" in node:
                node["required"] = list(node["properties"].keys())
        for key, value in node.items():
            if isinstance(value, dict):
                _make_strict(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        _make_strict(item)
                        
    _make_strict(schema)
    # Remove title/defs to keep it clean, though Groq usually handles defs.
    return schema


class FindingLocation(BaseModel):
    x: float
    y: float
    w: float
    h: float


class VisibleText(BaseModel):
    present: bool
    transcription: str
    text_context: str


class SceneProfile(BaseModel):
    medium: Literal[
        "photograph", "digital_painting", "3d_render", "illustration", 
        "anime_manga", "screenshot_ui", "screenshot_game", "scanned_print", 
        "vector_graphic", "mixed_media", "unclear"
    ]
    medium_confidence: Literal["high", "medium", "low"]
    medium_reasoning: str
    subject_description: str
    human_subjects_present: Optional[bool]
    human_subject_notes: Optional[str]
    lighting_and_physics_notes: str
    stylistic_elements_that_mimic_flaws: List[str]
    visible_text: VisibleText
    setting: Literal["real_world_photographable", "fictional_or_impossible", "ambiguous"]
    setting_notes: Optional[str]
    image_quality_notes: str
    flags_for_downstream_agents: str


class AgentFinding(BaseModel):
    type: str
    severity: Literal["low", "medium", "high", "critical"]
    location: Optional[FindingLocation] = None
    description: str


class AgentReport(BaseModel):
    thinking: str = Field(
        description="Your internal monologue and step-by-step reasoning before finalizing the report."
    )
    agent: Literal["metadata_analyst", "semantic_auditor"]
    provider: str
    findings: List[AgentFinding]
    manipulation_indicators: int
    authenticity_indicators: int
    confidence: float = Field(ge=0.0, le=1.0)
    preliminary_verdict: Literal[
        "authentic",
        "likely_authentic",
        "uncertain",
        "likely_manipulated",
        "manipulated",
    ]
    reasoning_summary: str


class FinalVerdict(BaseModel):
    thinking: str = Field(
        description="Your internal monologue and step-by-step reasoning before making the final verdict."
    )
    verdict: Literal[
        "authentic",
        "likely_authentic",
        "uncertain",
        "likely_manipulated",
        "manipulated",
    ]
    confidence: float = Field(ge=0.0, le=1.0)
    consensus: Literal["full_agreement", "partial_agreement", "conflict"]
    agent_a_report: AgentReport
    agent_b_report: AgentReport
    arbitrator_reasoning: str
    key_evidence: List[str]
    artifact_locations: List[AgentFinding]
    providers_used: List[str]
    degraded_mode: bool
