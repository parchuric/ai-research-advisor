from langchain_openai import AzureChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from pydantic import BaseModel, Field
from typing import Dict, Any

from app.core.config import (
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_API_VERSION,
    AZURE_OPENAI_DEPLOYMENT_NAME
)

# Define the output structure for the summary
class SummarizedOutput(BaseModel):
    summary: str = Field(description="A concise summary of the provided information.")

class SummarizerAgent:
    def __init__(self):
        self.llm = AzureChatOpenAI(
            azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
            api_version=AZURE_OPENAI_API_VERSION,
            azure_endpoint=AZURE_OPENAI_ENDPOINT,
            api_key=AZURE_OPENAI_API_KEY,
            temperature=0
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert summarizer. Your task is to create a concise and coherent summary of the provided text. Focus on the key information and present it clearly. Respond using the SummarizedOutput tool."),
            ("human", "Please summarize the following information:\n\n{combined_information}\n\nProvide a concise summary.")
        ])
        self.structured_llm = self.llm.with_structured_output(SummarizedOutput)

    async def summarize_information(self, retrieved_information: Dict[str, Any]) -> SummarizedOutput:
        """
        Summarizes the retrieved information.
        """
        # Combine all retrieved information into a single string
        # Assuming retrieved_information is Dict[sub_query, text_info]
        combined_text = []
        for sub_query, info in retrieved_information.items():
            if isinstance(info, str) and not info.startswith("Placeholder information for") and not info.startswith("Error retrieving information for") and not info.startswith("No content found by Tavily for"):
                combined_text.append(f"Information regarding '{sub_query}':\n{info}\n---")
        
        if not combined_text:
            return SummarizedOutput(summary="No valid information was available to summarize.")

        full_text_to_summarize = "\n\n".join(combined_text)
        
        # Check token limit (very basic check, a more robust solution would use a tokenizer)
        # GPT-4 context can be large, but let's be mindful.
        # This is a rough estimate, actual token count will vary.
        # A common token limit for prompts might be around 4000-8000 tokens for older models,
        # newer models support much larger contexts.
        # For now, let's assume the combined text won't exceed limits for typical use cases.
        # If it does, truncation or iterative summarization would be needed.

        chain = self.prompt | self.structured_llm
        response = await chain.ainvoke({
            "combined_information": full_text_to_summarize
        })
        return response

if __name__ == '__main__':
    import asyncio
    from dotenv import load_dotenv
    # Load .env file from the project root
    load_dotenv(dotenv_path='../../.env')


    async def test_summarizer():
        summarizer = SummarizerAgent()
        sample_info = {
            "AI impact on healthcare": "AI is revolutionizing healthcare by improving diagnostics, personalizing treatments, and accelerating drug discovery. Machine learning algorithms can analyze medical images with high accuracy.",
            "Quantum computing basics": "Quantum computing leverages quantum mechanics to perform complex calculations. Qubits, unlike classical bits, can exist in superpositions, enabling parallel processing.",
            "Invalid data": "Placeholder information for 'test query'", # Should be ignored
            "Empty data": "" # Should be ignored
        }
        
        # Test with valid information
        print("\n--- Test with valid information ---")
        output = await summarizer.summarize_information(sample_info)
        print(f"Summary: {output.summary}")

        # Test with only invalid/empty information
        print("\n--- Test with only invalid/empty information ---")
        sample_info_invalid = {
            "Invalid data 1": "Placeholder information for 'test query'",
            "Invalid data 2": "Error retrieving information for 'another query'",
            "No content": "No content found by Tavily for 'empty search'"
        }
        output_invalid = await summarizer.summarize_information(sample_info_invalid)
        print(f"Summary for invalid info: {output_invalid.summary}")

        # Test with no information
        print("\n--- Test with no information ---")
        output_no_info = await summarizer.summarize_information({})
        print(f"Summary for no info: {output_no_info.summary}")

    asyncio.run(test_summarizer())
