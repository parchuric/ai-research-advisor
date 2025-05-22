from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from typing import List, Dict, Any
from langchain_community.tools.tavily_search import TavilySearchResults # Added import

# For this example, we'll simulate retrieval with an LLM call.
# from langchain_community.retrievers import ... (e.g., TavilySearchResultsRetriever, ArxivRetriever)

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    TAVILY_API_KEY # Added import
)

class InformationRetrieverAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=0
        )
        # This is a simplified prompt. A real retrieval agent would use tools/vector stores.
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an information retrieval agent. Given a specific query, provide a concise summary of relevant information. For this basic version, you will act as a mock retriever."),
            ("human", "Retrieve information for the query: {sub_query}")
        ])

        # Initialize Tavily search tool
        if not TAVILY_API_KEY:
            print("Warning: TAVILY_API_KEY not set. Web search will not function.")
            self.search_tool = None
        else:
            self.search_tool = TavilySearchResults(max_results=3, api_key=TAVILY_API_KEY)

    async def retrieve_information(self, sub_query: str) -> str:
        """
        Retrieves information for a given sub-query.
        This implementation uses Tavily Search for web retrieval.
        """
        print(f"InformationRetrieverAgent: Attempting to retrieve information for: {sub_query}")
        if not self.search_tool:
            # Fallback if Tavily is not configured
            return f"Placeholder information for '{sub_query}'. (Tavily API key not configured)"
        
        try:
            print(f"Using Tavily to search for: {sub_query}")
            results = await self.search_tool.ainvoke(sub_query)
            # Process results: TavilySearchResults returns a list of dicts or a string
            # For simplicity, we'll join the content of the results.
            if isinstance(results, list):
                # Assuming results is a list of dictionaries with a 'content' key
                # Example structure: [{'url': '...', 'content': '...'}, ...]
                processed_results = "\n".join([item.get('content', '') for item in results if item.get('content')])
                return processed_results if processed_results else f"No content found by Tavily for '{sub_query}'."
            elif isinstance(results, str):
                return results # If it's already a string
            else:
                return f"Received unexpected result type from Tavily for '{sub_query}'."

        except Exception as e:
            print(f"Error during Tavily search for '{sub_query}': {e}")
            return f"Error retrieving information for '{sub_query}' using Tavily: {e}"

# Example usage (for testing purposes)
if __name__ == '__main__':
    import asyncio
    # You would need to have TAVILY_API_KEY set in your environment for this to work
    # For local testing, ensure your .env file is in a location discoverable by load_dotenv
    # or manually set the environment variable.
    # from dotenv import load_dotenv
    # load_dotenv(dotenv_path='../../.env') # Adjust path as necessary

    async def main():
        retriever = InformationRetrieverAgent()
        # Test with Tavily if API key is set
        if retriever.search_tool:
            query1 = "What are the latest advancements in AI for drug discovery?"
            info1 = await retriever.retrieve_information(query1)
            print(f"Query: {query1}\nRetrieved: {info1}\n")

            query2 = "Benefits of using LangGraph for agentic workflows"
            info2 = await retriever.retrieve_information(query2)
            print(f"Query: {query2}\nRetrieved: {info2}\n")
        else:
            print("Tavily search tool not initialized. Skipping live tests.")
            # Test placeholder functionality
            info_placeholder = await retriever.retrieve_information("test query")
            print(info_placeholder)

    asyncio.run(main())
