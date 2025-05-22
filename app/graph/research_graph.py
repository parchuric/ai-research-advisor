import json # Added for session persistence
import os # Added for session persistence
import datetime # Added for session persistence
from typing import TypedDict, List, Dict, Any
from langgraph.graph import StateGraph, END

from app.agents.deconstructor_agent import QueryDeconstructorAgent, DeconstructedQueries
from app.agents.retriever_agent import InformationRetrieverAgent
from app.agents.planner_agent import PlannerAgent, ResearchPlan
from app.agents.summarizer_agent import SummarizerAgent, SummarizedOutput # Added import

# Define the state for our graph
class ResearchGraphState(TypedDict):
    original_query: str
    deconstructed_queries: List[str] | None
    retrieved_information: Dict[str, str] | None # Maps sub_query to retrieved_info
    plan: ResearchPlan | None
    summary: SummarizedOutput | None # Added summary state
    error: str | None

class ResearchGraph:
    def __init__(self):
        self.query_deconstructor = QueryDeconstructorAgent()
        self.info_retriever = InformationRetrieverAgent()
        self.planner = PlannerAgent()
        self.summarizer = SummarizerAgent() # Initialize summarizer
        self.graph = self._build_graph()
        self.sessions_dir = os.path.join(os.path.dirname(__file__), "..", "..", "sessions") # Define sessions directory
        if not os.path.exists(self.sessions_dir):
            os.makedirs(self.sessions_dir)

    async def _deconstruct_node(self, state: ResearchGraphState) -> ResearchGraphState:
        print(f"---NODE: DECONSTRUCTING QUERY--- Input state: {state}")
        try:
            deconstructed_output: DeconstructedQueries = await self.query_deconstructor.deconstruct_query(state["original_query"])
            updated_state = {**state, "deconstructed_queries": deconstructed_output.queries, "error": None}
            print(f"---NODE: DECONSTRUCT FINISHED--- Output state partial: {{'deconstructed_queries': {deconstructed_output.queries}, 'error': None}}")
            return updated_state
        except Exception as e:
            print(f"Error in deconstruction: {e}")
            updated_state = {**state, "error": f"Failed to deconstruct query: {e}"}
            print(f"---NODE: DECONSTRUCT ERRORED--- Output state partial: {{'error': '{updated_state['error']}'}}")
            return updated_state

    async def _retrieval_node(self, state: ResearchGraphState) -> ResearchGraphState:
        print(f"---NODE: RETRIEVING INFORMATION--- Input state: {state}")
        if state.get("error"): # If deconstruction failed, skip
            print("---NODE: RETRIEVAL SKIPPED DUE TO PREVIOUS ERROR---")
            return state
        
        all_retrieved_info = {}
        sub_query_errors = []
        if state.get("deconstructed_queries"):
            for sub_query in state["deconstructed_queries"]:
                try:
                    print(f"Retrieving for: {sub_query}")
                    info = await self.info_retriever.retrieve_information(sub_query)
                    all_retrieved_info[sub_query] = info
                except Exception as e:
                    print(f"Error retrieving for {sub_query}: {e}")
                    all_retrieved_info[sub_query] = f"Failed to retrieve information: {e}"
                    sub_query_errors.append(f"For '{sub_query}': {e}")
            
            current_error = state.get("error")
            if sub_query_errors:
                new_error_message = f"Errors during retrieval: {'; '.join(sub_query_errors)}"
                updated_error = f"{current_error}; {new_error_message}" if current_error else new_error_message
            else:
                updated_error = current_error

            updated_state = {**state, "retrieved_information": all_retrieved_info, "error": updated_error}
            print(f"---NODE: RETRIEVAL FINISHED--- Output state partial: {{'retrieved_information': {all_retrieved_info}, 'error': {updated_error}}}")
            return updated_state
        else:
            print("---NODE: RETRIEVAL - NO DECONSTRUCTED QUERIES---")
            updated_state = {**state, "error": "No deconstructed queries to retrieve."}
            print(f"---NODE: RETRIEVAL ERRORED--- Output state partial: {{'error': '{updated_state['error']}'}}")
            return updated_state

    async def _planner_node(self, state: ResearchGraphState) -> ResearchGraphState:
        print(f"---NODE: PLANNING--- Input state: {state}")
        if state.get("error") or not state.get("original_query") or not state.get("deconstructed_queries") or not state.get("retrieved_information"):
            print("---NODE: PLANNING SKIPPED DUE TO PREVIOUS ERROR OR MISSING DATA---")
            # Ensure plan is None if skipped, and summary is also None as it depends on retrieved_information
            return {**state, "plan": None, "summary": None} if "plan" not in state or "summary" not in state else state

        try:
            plan_output: ResearchPlan = await self.planner.create_plan(
                original_query=state["original_query"],
                deconstructed_queries=state["deconstructed_queries"],
                retrieved_information=state["retrieved_information"]
            )
            updated_state = {**state, "plan": plan_output, "error": state.get("error")}
            print(f"---NODE: PLANNING FINISHED--- Output state partial: {{'plan': {plan_output}}}")
            return updated_state
        except Exception as e:
            print(f"Error in planning: {e}")
            current_error = state.get("error")
            new_error_message = f"Failed to create plan: {e}"
            updated_error = f"{current_error}; {new_error_message}" if current_error else new_error_message
            # Ensure summary is also None if planning fails
            updated_state = {**state, "plan": None, "summary": None, "error": updated_error}
            print(f"---NODE: PLANNING ERRORED--- Output state partial: {{'plan': None, 'summary': None, 'error': '{updated_error}'}}")
            return updated_state

    async def _summarizer_node(self, state: ResearchGraphState) -> ResearchGraphState:
        print(f"---NODE: SUMMARIZING--- Input state: {state}")
        # Summarizer should run even if planning failed, as long as retrieval was successful.
        # However, if retrieval itself failed or produced no usable info, summarizer might not be useful.
        if not state.get("retrieved_information") or not any(isinstance(info, str) and not info.startswith("Placeholder") and not info.startswith("Error retrieving") and not info.startswith("No content found") for info in state["retrieved_information"].values()):
            print("---NODE: SUMMARIZING SKIPPED DUE TO MISSING OR INVALID RETRIEVED DATA---")
            return {**state, "summary": SummarizedOutput(summary="No valid information was available to summarize.")}

        # If a critical error occurred before summarization (e.g. in deconstruction), we might also skip.
        # For now, we rely on the check above for retrieved_information.
        # An earlier error in the deconstruction or retrieval node that prevents useful information
        # from being passed should lead to the "No valid information" summary.

        try:
            summary_output: SummarizedOutput = await self.summarizer.summarize_information(
                retrieved_information=state["retrieved_information"]
            )
            # Preserve existing error, but add summary
            updated_state = {**state, "summary": summary_output, "error": state.get("error")}
            print(f"---NODE: SUMMARIZING FINISHED--- Output state partial: {{'summary': {summary_output}}}")
            return updated_state
        except Exception as e:
            print(f"Error in summarization: {e}")
            current_error = state.get("error")
            new_error_message = f"Failed to summarize information: {e}"
            updated_error = f"{current_error}; {new_error_message}" if current_error else new_error_message
            updated_state = {**state, "summary": SummarizedOutput(summary=f"Failed to generate summary: {e}"), "error": updated_error}
            print(f"---NODE: SUMMARIZING ERRORED--- Output state partial: {{'summary': {{'summary': '{updated_state['summary'].summary}'}}, 'error': '{updated_error}'}}")
            return updated_state

    async def _error_handler_node(self, state: ResearchGraphState) -> ResearchGraphState:
        print(f"---NODE: ERROR HANDLER--- Input state: {state}")
        # This node currently just passes the state through.
        # Session saving will occur in the main run method based on the final state.
        return state

    def _should_continue(self, state: ResearchGraphState) -> str:
        print(f"---LOGIC: SHOULD_CONTINUE--- Checking state: {state}")

        if state.get("error"):
            # If an error is set by deconstruct, retrieve, or plan, and we haven't run summarizer yet,
            # we might still want to run summarizer if there's some data.
            # However, if the error is critical (e.g., from deconstruction), summarizer might not make sense.
            # The current logic: if any error, go to error_handler. Error handler goes to END.
            # Let's refine this: if error occurs in planner, we still go to summarizer.
            # If error in deconstruct/retrieve, then error_handler.

            # Check if the error is from planner specifically
            is_planner_error = state["error"] and "Failed to create plan" in state["error"]
            
            if not is_planner_error: # Critical error before or during planning (not planner itself)
                 print(f"Critical error in state: {state['error']}. Routing to error_handler.")
                 return "error_handler"
            # If it's a planner error, we might still proceed to summarizer if data exists.
            # The summarizer node itself will check if retrieved_information is usable.

        # Deconstruction -> Retrieval
        if state.get("deconstructed_queries") is not None and state.get("retrieved_information") is None:
            print("Routing from deconstruction to retrieve_information.")
            return "retrieve_information"

        # Retrieval -> Planner
        if state.get("retrieved_information") is not None and state.get("plan") is None:
            print("Routing from retrieve_information to planner.")
            return "planner"
        
        # Planner -> Summarizer
        # This condition means planner has run (or attempted to run and set plan to None)
        # and summarizer hasn't run yet.
        if state.get("plan") is not None or (state.get("retrieved_information") is not None and state.get("plan") is None):
            if state.get("summary") is None:
                 print("Routing from planner (or after planner attempt) to summarizer.")
                 return "summarizer"

        # Summarizer -> END
        if state.get("summary") is not None:
            print("All steps done (deconstruction, retrieval, planning, summarization). Routing to END.")
            return END
        
        # Fallback / Initial state before deconstruction (should be handled by entry point)
        # Or if deconstruction failed silently (no queries, no error)
        if state.get("deconstructed_queries") is None and not state.get("error"):
            print("State suggests deconstruction hasn't run or failed silently. Routing to error_handler.")
            # state["error"] = "Internal Error: Deconstruction did not produce queries or an error." # Avoid direct mutation
            return "error_handler" 

        print(f"Warning: _should_continue reached an unexpected state configuration: {state}. Routing to END.")
        return END

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(ResearchGraphState)

        workflow.add_node("deconstruct_query", self._deconstruct_node)
        workflow.add_node("retrieve_information", self._retrieval_node)
        workflow.add_node("planner", self._planner_node)
        workflow.add_node("summarizer", self._summarizer_node) # Added summarizer node
        workflow.add_node("error_handler", self._error_handler_node)

        workflow.set_entry_point("deconstruct_query")

        workflow.add_conditional_edges(
            "deconstruct_query",
            self._should_continue,
            {
                "retrieve_information": "retrieve_information",
                "error_handler": "error_handler",
                # END: END # Should not happen if error is set or next step is retrieval
            }
        )
        workflow.add_conditional_edges(
            "retrieve_information",
            self._should_continue,
             {
                "planner": "planner",
                "error_handler": "error_handler",
                # END: END # Should not happen
            }
        )
        workflow.add_conditional_edges(
            "planner",
            self._should_continue,
            {
                "summarizer": "summarizer", # Route to summarizer
                "error_handler": "error_handler" # If planner sets an error that _should_continue deems critical
            }
        )
        workflow.add_conditional_edges(
            "summarizer",
            self._should_continue,
            {
                END: END, # Normal flow after summarizer
                "error_handler": "error_handler" # If summarizer sets an error
            }
        )
        workflow.add_edge("error_handler", END)
        
        return workflow.compile()

    def _serialize_state(self, state: ResearchGraphState) -> Dict[str, Any]:
        """Converts ResearchGraphState to a JSON-serializable dictionary."""
        serialized_state = {}
        for key, value in state.items():
            if hasattr(value, 'model_dump'): # For Pydantic models like ResearchPlan, SummarizedOutput
                serialized_state[key] = value.model_dump()
            elif isinstance(value, (list, dict, str, int, float, bool, type(None))):
                serialized_state[key] = value
            else:
                # For other types, convert to string or handle as needed
                serialized_state[key] = str(value)
        return serialized_state

    async def _save_session(self, state: ResearchGraphState):
        """Saves the research session state to a JSON file."""
        if state.get("error") and "Critical error during graph execution" in state["error"]:
            print("---SESSION SAVING SKIPPED due to critical graph execution error---")
            return

        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            session_filename = f"session_{timestamp}.json"
            session_filepath = os.path.join(self.sessions_dir, session_filename)

            # Prepare state for JSON serialization
            # Pydantic models (plan, summary) need to be dumped to dicts
            serializable_state = self._serialize_state(state)

            with open(session_filepath, 'w') as f:
                json.dump(serializable_state, f, indent=4)
            print(f"---SESSION SAVED to {session_filepath}---")
        except Exception as e:
            print(f"Error saving session: {e}")


    async def run(self, query: str) -> ResearchGraphState:
        """
        Executes the research graph with the given query and saves the session.
        """
        initial_inputs = {
            "original_query": query,
            "deconstructed_queries": None,
            "retrieved_information": None,
            "plan": None,
            "summary": None, # Added summary to initial inputs
            "error": None
        }
        print(f"---GRAPH INVOKING--- Initial inputs: {initial_inputs}")
        final_state_from_graph: ResearchGraphState
        try:
            # Ensure a recursion limit, default is 25, can be adjusted.
            final_state_from_graph = await self.graph.ainvoke(initial_inputs, config={"recursion_limit": 15})
            print(f"---GRAPH INVOKE FINISHED--- Final state from graph.ainvoke: {final_state_from_graph}")
        except Exception as e:
            print(f"Exception during graph.ainvoke: {e}")
            # Fallback state in case of unexpected error from ainvoke itself
            final_state_from_graph = {
                "original_query": query,
                "deconstructed_queries": None,
                "retrieved_information": None,
                "plan": None,
                "summary": None, 
                "error": f"Critical error during graph execution: {str(e)}"
            }
        
        await self._save_session(final_state_from_graph) # Save session after graph execution
        return final_state_from_graph
