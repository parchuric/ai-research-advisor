from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from app.schemas.research_schemas import ResearchRequest, ResearchResponse, UserFeedback
from app.graph.research_graph import ResearchGraph, ResearchGraphState
from app.agents.feedback_agent import FeedbackAgent
from app.agents.feedback_analyzer_agent import FeedbackAnalyzerAgent # Added
from app.schemas.research_schemas import FeedbackAnalysisResult # Added
import os
import json
from pathlib import Path
import asyncio

app = FastAPI(
    title="AI Research Advisor API",
    description="API for the AI Research Advisor application using LangGraph.",
    version="0.1.0"
)

# Initialize the graph. Consider how to manage its lifecycle if it's resource-intensive.
# For simple cases, a global instance is fine. For production, consider dependency injection.
research_graph_instance = ResearchGraph()
feedback_agent_instance = FeedbackAgent() # Added
feedback_analyzer_agent = FeedbackAnalyzerAgent() # Added

SESSIONS_DIR = Path(__file__).resolve().parent.parent / "sessions"

@app.on_event("startup")
async def startup_event():
    # You can add any startup logic here, e.g., pre-loading models if not done in agents
    print("FastAPI application startup...")
    # Test Azure OpenAI connection (optional, config already checks for vars)
    try:
        # A lightweight test, e.g., trying to initialize one of the LLMs from an agent
        _ = research_graph_instance.query_deconstructor.llm 
        print("Azure OpenAI client seems configured.")
    except Exception as e:
        print(f"Error during startup related to Azure OpenAI config: {e}")
        # You might choose to raise an error here to prevent startup if critical
        
@app.post("/research/", response_model=ResearchResponse)
async def conduct_research(request: ResearchRequest):
    """
    Endpoint to conduct research based on a user query.
    It runs the query through the LangGraph research pipeline.
    """
    try:
        print(f"Received research request for query: {request.query}")
        # The graph's run method is async
        final_state: ResearchGraphState = await research_graph_instance.run(query=request.query)
        
        print(f"Graph execution finished. Final state: {final_state}")

        if final_state.get("error"):
             # You might want to map specific errors to HTTP status codes
            raise HTTPException(status_code=500, detail=f"Error during research: {final_state['error']}")

        # Construct the response based on the final state
        # This assumes your ResearchGraphState directly maps or contains the fields for ResearchResponse
        response_data = ResearchResponse(
            original_query=final_state.get("original_query", request.query), # Falls back to request.query
            deconstructed_queries=final_state.get("deconstructed_queries", []),
            retrieved_information=final_state.get("retrieved_information", {}),
            plan=final_state.get("plan"), # Pass plan to response
            summary=final_state.get("summary") # Pass summary to response
        )
        return response_data

    except HTTPException as http_exc:
        raise http_exc # Re-raise HTTPException
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

# New Feedback Endpoint
@app.post("/feedback/", status_code=201) # 201 for successful creation
async def submit_feedback(feedback_data: UserFeedback):
    """
    Endpoint to receive and record user feedback.
    """
    try:
        print(f"Received feedback: {feedback_data.model_dump_json(indent=2)}")
        # The FeedbackAgent's record_feedback method is synchronous in the current simple implementation
        # If it were async, you'd await it.
        # For this simple file logging, running it synchronously in a thread pool executor
        # might be an option for a production FastAPI app to avoid blocking the event loop,
        # but for now, direct call is fine given its simplicity.
        
        # We are directly passing the UserFeedback model which now includes the timestamp
        # The agent will just log it.
        # A more robust agent might generate the timestamp itself if not provided.
        
        # Let's adjust the agent to take the full UserFeedback object or create one if not given full
        # For now, let's assume the agent's record_feedback is simplified or we adapt.
        # The current FeedbackAgent.record_feedback expects original_query, feedback_text, rating.
        # Let's call it with those specific fields from the UserFeedback Pydantic model.
        
        recorded_feedback = feedback_agent_instance.record_feedback(feedback_data)
        
        if recorded_feedback:
            return {"message": "Feedback recorded successfully", "feedback_id": recorded_feedback.timestamp} # Or some other ID
        else:
            raise HTTPException(status_code=500, detail="Failed to record feedback.")
            
    except Exception as e:
        print(f"Error processing feedback: {e}")
        raise HTTPException(status_code=500, detail=f"An error occurred while processing feedback: {str(e)}")

@app.get("/feedback/analyze/", response_model=FeedbackAnalysisResult)
async def analyze_feedback_endpoint():
    """
    Analyzes all persisted user feedback and returns a summary.
    """
    try:
        analysis_result = await feedback_analyzer_agent.analyze_feedback()
        return analysis_result
    except Exception as e:
        # Log the exception for server-side review
        print(f"Error during feedback analysis endpoint: {e}") 
        # Return a structured error response using the Pydantic model
        return FeedbackAnalysisResult(
            total_feedback_entries=0,
            average_rating=None,
            feedback_summary=None,
            error_message=f"An unexpected error occurred during feedback analysis: {str(e)}"
        )

@app.get("/")
async def read_root():
    return {"message": "Welcome to the AI Research Advisor API. Use the /research/ endpoint to make requests."}

@app.get("/sessions/")
async def list_sessions():
    """
    Lists all persisted session files.
    """
    if not SESSIONS_DIR.exists() or not SESSIONS_DIR.is_dir():
        return []
    
    session_files = sorted(
        [f for f in os.listdir(SESSIONS_DIR) if f.startswith("session_") and f.endswith(".json")],
        reverse=True
    )
    return session_files

@app.get("/sessions/{session_filename}")
async def get_session(session_filename: str):
    """
    Retrieves the content of a specific session file.
    """
    session_file_path = SESSIONS_DIR / session_filename
    if not session_file_path.exists() or not session_file_path.is_file():
        raise HTTPException(status_code=404, detail="Session file not found")
    
    try:
        with open(session_file_path, "r") as f:
            session_data = json.load(f)
        # Ensure Pydantic models are reconstructed if they were stored as dicts
        # This might be more complex depending on how ResearchGraphState serializes them
        # For now, assume they are dicts that match the schema structure
        return ResearchResponse(
            original_query=session_data.get("original_query"),
            deconstructed_queries=session_data.get("deconstructed_queries"),
            retrieved_information=session_data.get("retrieved_information"),
            plan=session_data.get("plan"),
            summary=session_data.get("summary"),
            error=session_data.get("error")
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading session file: {str(e)}")

# Mount static files if you have any (e.g., for a web interface)
# app.mount("/static", StaticFiles(directory="static"), name="static")

# To run this application:
# 1. Ensure you have .env file configured with Azure OpenAI credentials.
# 2. In your terminal, navigate to the 'ai_research_advisor' directory.
# 3. Run the command: uvicorn app.main:app --reload --port 8000
