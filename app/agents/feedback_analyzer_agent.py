import json
from typing import List, Dict, Any
from pydantic import ValidationError
from app.schemas.research_schemas import UserFeedback, FeedbackAnalysisResult
from app.core.config import llm # Assuming LLM is configured for use

FEEDBACK_FILE = "user_feedback.log"

class FeedbackAnalyzerAgent:
    def __init__(self):
        self.feedback_file = FEEDBACK_FILE

    def _load_feedback(self) -> List[UserFeedback]:
        feedback_list = []
        try:
            with open(self.feedback_file, "r") as f:
                for line in f:
                    try:
                        data = json.loads(line.strip())
                        feedback_list.append(UserFeedback(**data))
                    except (json.JSONDecodeError, ValidationError) as e:
                        print(f"Skipping invalid feedback entry: {line.strip()} - Error: {e}")
        except FileNotFoundError:
            print(f"Feedback file {self.feedback_file} not found.")
        return feedback_list

    async def analyze_feedback(self) -> FeedbackAnalysisResult:
        feedback_entries = self._load_feedback()

        if not feedback_entries:
            return FeedbackAnalysisResult(
                total_feedback_entries=0,
                average_rating=None,
                feedback_summary="No feedback entries found to analyze.",
            )

        total_entries = len(feedback_entries)
        average_rating = sum(entry.rating for entry in feedback_entries) / total_entries if total_entries > 0 else None

        # For more sophisticated analysis, use an LLM to summarize feedback text
        # Concatenate feedback texts for summarization
        all_feedback_texts = "\n".join([f"- Rating: {entry.rating}/5, Feedback: {entry.feedback_text}" for entry in feedback_entries if entry.feedback_text])

        if not all_feedback_texts:
            return FeedbackAnalysisResult(
                total_feedback_entries=total_entries,
                average_rating=average_rating,
                feedback_summary="No textual feedback provided to summarize.",
            )

        try:
            prompt = f"""Analyze the following user feedback entries for an AI Research Advisor application.
Provide a concise summary of common themes, praises, criticisms, and suggestions.
Focus on actionable insights that could help improve the application.

Feedback Entries:
{all_feedback_texts}

Summary:"""
            
            response = await llm.ainvoke(prompt)
            summary_text = response.content if hasattr(response, 'content') else str(response) # Adapt based on LLM response structure

        except Exception as e:
            print(f"Error during LLM feedback summarization: {e}")
            summary_text = "Could not generate AI summary due to an error."
            return FeedbackAnalysisResult(
                total_feedback_entries=total_entries,
                average_rating=average_rating,
                feedback_summary=summary_text,
                error_message=f"LLM summarization error: {str(e)}"
            )

        return FeedbackAnalysisResult(
            total_feedback_entries=total_entries,
            average_rating=average_rating,
            feedback_summary=summary_text,
        )

# Example usage (for testing or a standalone script)
if __name__ == "__main__":
    import asyncio
    analyzer = FeedbackAnalyzerAgent()
    
    # Ensure there's some dummy data in user_feedback.log for testing
    # Example:
    # {"original_query": "Test query 1", "feedback_text": "Very helpful!", "rating": 5, "timestamp": "2025-05-23T10:00:00Z"}
    # {"original_query": "Test query 2", "feedback_text": "Confusing plan.", "rating": 2, "timestamp": "2025-05-23T10:05:00Z"}
    # {"original_query": "Test query 3", "feedback_text": "Good summary.", "rating": 4, "timestamp": "2025-05-23T10:10:00Z"}

    async def main():
        analysis_result = await analyzer.analyze_feedback()
        print("Feedback Analysis:")
        print(f"  Total Entries: {analysis_result.total_feedback_entries}")
        print(f"  Average Rating: {analysis_result.average_rating}")
        print(f"  Summary:\n{analysis_result.feedback_summary}")
        if analysis_result.error_message:
            print(f"  Error: {analysis_result.error_message}")
            
    asyncio.run(main())
