from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field  # Changed from langchain_core.pydantic_v1
from typing import List

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME
)

# Define the output structure for deconstructed queries
class DeconstructedQueries(BaseModel):
    queries: List[str] = Field(description="A list of deconstructed, more specific queries.")

class QueryDeconstructorAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=0
        )
        # Create a prompt template that instructs the LLM on how to deconstruct queries
        # and to use the DeconstructedQueries tool for output.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert query deconstructor. Your task is to break down a complex user query into smaller, manageable, and specific sub-queries that can be independently researched. Respond using the DeconstructedQueries tool."),
            ("human", "{query}")
        ])
        # Bind the Pydantic model to the LLM, forcing it to use the tool
        self.structured_llm = self.llm.with_structured_output(DeconstructedQueries)

    async def deconstruct_query(self, query: str) -> DeconstructedQueries:
        """
        Deconstructs a complex query into simpler sub-queries.
        """
        chain = self.prompt | self.structured_llm
        response = await chain.ainvoke({"query": query})
        return response
