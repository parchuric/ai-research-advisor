from pydantic import BaseModel
from typing import List, Dict, Any
from app.agents.planner_agent import ResearchPlan
from app.agents.summarizer_agent import SummarizedOutput # Added import

class ResearchRequest(BaseModel):
    query: str
    # Add any other relevant fields for a research request

class ResearchResponse(BaseModel):
    original_query: str
    deconstructed_queries: List[str] = None
    retrieved_information: Dict[str, Any] = None # Could be Dict[str, List[str]] or more complex
    plan: ResearchPlan | None = None # Added plan
    summary: SummarizedOutput | None = None # Added summary
    # Add other response fields as needed

class AgentOutput(BaseModel):
    output: Any
    agent_name: str

class UserFeedback(BaseModel):
    original_query: str
    feedback_text: str
    rating: int # e.g., 1-5 stars
    timestamp: str
    # session_id: str | None = None # Optional: to link feedback to a specific session state

class FeedbackAnalysisResult(BaseModel):
    total_feedback_entries: int
    average_rating: float | None
    feedback_summary: str | None
    error_message: str | None = None
