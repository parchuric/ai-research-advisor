import logging
import datetime
import json
from app.schemas.research_schemas import UserFeedback

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class FeedbackAgent:
    """
    A simple agent to log user feedback to a file.
    In a real application, this might write to a database or a more sophisticated logging system.
    """
    def __init__(self, feedback_file_path: str = "user_feedback.log"):
        self.feedback_file_path = feedback_file_path
        # Ensure the log file exists or can be created
        try:
            with open(self.feedback_file_path, "a") as f:
                pass # Just to ensure it can be opened/created
        except IOError as e:
            logging.error(f"Could not initialize feedback log file at {self.feedback_file_path}: {e}")
            # Potentially raise an error or handle this more gracefully

    def record_feedback(self, feedback_input: UserFeedback) -> UserFeedback | None:
        """
        Records user feedback by writing the UserFeedback object to a log file.
        """
        try:
            with open(self.feedback_file_path, "a") as f:
                f.write(feedback_input.model_dump_json() + "\\n")
            logging.info(f"Feedback recorded for query '{feedback_input.original_query}': {feedback_input.feedback_text}")
            return feedback_input
        except IOError as e:
            logging.error(f"Failed to write feedback to {self.feedback_file_path}: {e}")
            return None

# Example usage (optional, for testing)
if __name__ == "__main__":
    import datetime # Ensure datetime is imported for the example
    feedback_agent = FeedbackAgent(feedback_file_path="test_feedback.log")
    
    # Example of creating a UserFeedback object for testing
    test_feedback_1 = UserFeedback(
        original_query="What is quantum computing?",
        feedback_text="The explanation was clear and concise.",
        rating=5,
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    feedback_agent.record_feedback(test_feedback_1)
    
    test_feedback_2 = UserFeedback(
        original_query="Explain black holes.",
        feedback_text="A bit too technical for a beginner.",
        # Rating is optional
        timestamp=datetime.datetime.now(datetime.timezone.utc).isoformat()
    )
    feedback_agent.record_feedback(test_feedback_2)
    print(f"Test feedback written to test_feedback.log")
