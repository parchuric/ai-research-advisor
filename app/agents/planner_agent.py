from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field  # Changed from langchain_core.pydantic_v1
from typing import List, Dict, Any

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME
)

# Define the output structure for the plan
class ResearchPlan(BaseModel):
    plan_steps: List[str] = Field(description="A list of steps to execute the research based on deconstructed queries and retrieved info.")
    synthesis_questions: List[str] = Field(description="Questions to guide the final synthesis of information.")

class PlannerAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=0
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert research planner. Given a main query, deconstructed sub-queries, and retrieved information, create a plan to synthesize this information and answer the main query. Respond using the ResearchPlan tool."),
            ("human", "Main Query: {original_query}\n\nDeconstructed Queries: {deconstructed_queries}\n\nRetrieved Information: {retrieved_information}\n\nCreate a research plan.")
        ])
        self.structured_llm = self.llm.with_structured_output(ResearchPlan)

    async def create_plan(self, original_query: str, deconstructed_queries: List[str], retrieved_information: Dict[str, Any]) -> ResearchPlan:
        """
        Creates a research plan.
        """
        chain = self.prompt | self.structured_llm
        response = await chain.ainvoke({
            "original_query": original_query,
            "deconstructed_queries": deconstructed_queries,
            "retrieved_information": retrieved_information
        })
        return response
