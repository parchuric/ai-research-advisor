import streamlit as st
import requests # To make HTTP requests to the FastAPI backend
import json # To pretty print dicts
import datetime # To timestamp feedback

# Configuration
BACKEND_URL = "http://localhost:8000/research/" # Ensure this matches your FastAPI URL
FEEDBACK_BACKEND_URL = "http://localhost:8000/feedback/" # Added for feedback
API_URL = "http://localhost:8000" # Base URL for API requests

st.set_page_config(page_title="AI Research Advisor", layout="wide")

st.title("AI Research Advisor 🤖")
st.caption("Your intelligent assistant for deconstructing and exploring complex topics.")

# --- Main Application ---
query = st.text_input("Enter your research query:", placeholder="e.g., Explain the impact of quantum computing on cryptography.")

if st.button("🔍 Conduct Research", type="primary"):
    if query:
        with st.spinner("Thinking... Deconstructing query and retrieving information..."):
            try:
                payload = {"query": query}
                response = requests.post(BACKEND_URL, json=payload, timeout=300) # Increased timeout
                response.raise_for_status()  # Raises an HTTPError for bad responses (4XX or 5XX)
                
                results = response.json()

                st.subheader("📝 Original Query")
                st.markdown(f"> {results.get('original_query', query)}")

                if results.get("deconstructed_queries"):
                    st.subheader("🧩 Deconstructed Sub-Queries")
                    for i, sub_query in enumerate(results["deconstructed_queries"]):
                        st.markdown(f"**{i+1}.** {sub_query}")
                
                if results.get("retrieved_information"):
                    st.subheader("📚 Retrieved Information Snippets")
                    retrieved_info = results["retrieved_information"]
                    if isinstance(retrieved_info, dict):
                        for sub_q, info in retrieved_info.items():
                            with st.expander(f"**Information for: '{sub_q}'**"):
                                st.markdown(info if isinstance(info, str) else json.dumps(info, indent=2))
                    else: # Fallback if the structure is not a dict (e.g. a simple string)
                        st.markdown(str(retrieved_info))
                
                # Display Research Plan
                if results.get("plan"):
                    st.subheader("🗺️ Research Plan")
                    plan_data = results["plan"]
                    if plan_data.get("plan_steps"):
                        st.markdown("**Plan Steps:**")
                        for i, step in enumerate(plan_data["plan_steps"]):
                            st.markdown(f"{i+1}. {step}")
                    
                    if plan_data.get("synthesis_questions"):
                        st.markdown("**Synthesis Questions:**")
                        for i, question in enumerate(plan_data["synthesis_questions"]):
                            st.markdown(f"{i+1}. {question}")
                elif not results.get("error"): # Only show if no major error occurred and plan is missing
                    st.info("No research plan was generated for this query.")

                # Display Summary
                if results.get("summary"):
                    st.subheader("📊 Summary")
                    summary_data = results["summary"]
                    if summary_data.get("summary_text"):
                        st.markdown("**Summary Text:**")
                        st.markdown(summary_data["summary_text"])
                    
                    if summary_data.get("key_points"):
                        st.markdown("**Key Points:**")
                        for i, point in enumerate(summary_data["key_points"]):
                            st.markdown(f"- {point}")
                elif not results.get("error"): # Only show if no major error occurred and summary is missing
                    st.info("No summary was generated for this query.")

                # --- Feedback Section ---
                st.markdown("---") # Visual separator
                st.subheader("🗣️ Provide Feedback")
                feedback_text = st.text_area("Let us know your thoughts on the results:", key=f"feedback_for_{results.get('original_query')}")
                feedback_rating = st.slider("Rate the quality of the results (1-5):", 1, 5, 3, key=f"rating_for_{results.get('original_query')}")
                
                if st.button("Submit Feedback", key=f"submit_feedback_{results.get('original_query')}"):
                    if feedback_text:
                        feedback_payload = {
                            "original_query": results.get('original_query', query),
                            "feedback_text": feedback_text,
                            "rating": feedback_rating,
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat() # Generate timestamp in UI
                        }
                        try:
                            feedback_response = requests.post(FEEDBACK_BACKEND_URL, json=feedback_payload, timeout=30)
                            feedback_response.raise_for_status()
                            st.success("Thank you for your feedback!")
                        except requests.exceptions.HTTPError as http_err_feedback:
                            st.error(f"Failed to submit feedback. HTTP error: {http_err_feedback}")
                            try:
                                error_detail_fb = feedback_response.json().get("detail", "No additional details.")
                                st.error(f"Backend feedback error detail: {error_detail_fb}")
                            except json.JSONDecodeError:
                                st.error("Could not parse error response from feedback backend.")
                        except Exception as e_fb:
                            st.error(f"An unexpected error occurred while submitting feedback: {e_fb}")
                    else:
                        st.warning("Please enter some feedback text before submitting.")

            except requests.exceptions.HTTPError as http_err:
                st.error(f"HTTP error occurred: {http_err}")
                try:
                    error_detail = response.json().get("detail", "No additional details provided.")
                    st.error(f"Backend error detail: {error_detail}")
                except json.JSONDecodeError:
                    st.error("Could not parse error response from backend.")
            except requests.exceptions.ConnectionError as conn_err:
                st.error(f"Error connecting to the backend at {BACKEND_URL}. Is the backend running?")
                st.error(f"Details: {conn_err}")
            except requests.exceptions.Timeout as timeout_err:
                st.error(f"The request to the backend timed out: {timeout_err}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
    else:
        st.warning("Please enter a research query.")

# --- Session Loading --- 
st.sidebar.title("Past Research Sessions")
session_files = []
try:
    response = requests.get(f"{API_URL}/sessions/")
    response.raise_for_status()
    session_files = response.json()
except requests.exceptions.RequestException as e:
    st.sidebar.error(f"Error loading sessions: {e}")

if session_files:
    selected_session_file = st.sidebar.selectbox(
        "Load a past session:", 
        options=["Select a session"] + session_files,
        index=0
    )
    if selected_session_file != "Select a session":
        if st.sidebar.button("Load Session"): 
            try:
                session_response = requests.get(f"{API_URL}/sessions/{selected_session_file}")
                session_response.raise_for_status()
                session_data = session_response.json()
                
                st.session_state.messages = [] # Clear current messages
                st.session_state.clear_input = True # Signal to clear input

                st.info(f"Loaded session: {selected_session_file}")
                
                # Display original query from loaded session
                if session_data.get("original_query"):
                    st.chat_message("user").write(session_data["original_query"])
                    st.session_state.messages.append({"role": "user", "content": session_data["original_query"]})
                
                # Display assistant response from loaded session
                with st.chat_message("assistant"):
                    if session_data.get("deconstructed_queries"):
                        st.subheader("Deconstructed Queries")
                        for dq in session_data["deconstructed_queries"]:
                            st.markdown(f"- {dq}")
                    
                    if session_data.get("retrieved_information"):
                        st.subheader("Retrieved Information")
                        for item in session_data["retrieved_information"]:
                            st.markdown(f"- **Source:** {item.get('source', 'N/A')}")
                            st.markdown(item.get('content', 'No content'))
                            st.divider()

                    if session_data.get("plan"):
                        st.subheader("Research Plan")
                        st.markdown(session_data["plan"].get("plan_steps", "No plan steps available."))

                    if session_data.get("summary"):
                        st.subheader("Summary")
                        st.markdown(session_data["summary"].get("summary_text", "No summary available."))

                    if session_data.get("error"):
                        st.error(f"Error in research: {session_data['error']}")
                
                st.session_state.messages.append({"role": "assistant", "content": session_data})
                st.session_state.current_research_response = session_data # Store for feedback
                st.rerun() # Rerun to reflect loaded state and clear input

            except requests.exceptions.RequestException as e:
                st.error(f"Error loading session {selected_session_file}: {e}")
            except Exception as e:
                st.error(f"An unexpected error occurred: {e}")
else:
    st.sidebar.info("No past sessions found.")

# --- Session Loading / Feedback Analysis Display ---
st.sidebar.title("Session Management & Feedback")

# --- Feedback Analysis Display ---
st.sidebar.subheader("Feedback Analysis")
if st.sidebar.button("Analyze All Feedback"):
    try:
        analysis_response = requests.get(f"{API_URL}/feedback/analyze/")
        analysis_response.raise_for_status()
        analysis_data = analysis_response.json()

        st.session_state.feedback_analysis_results = analysis_data
        
    except requests.exceptions.RequestException as e:
        st.sidebar.error(f"Error fetching feedback analysis: {e}")
        st.session_state.feedback_analysis_results = {"error_message": str(e)}
    except Exception as e:
        st.sidebar.error(f"An unexpected error occurred: {e}")
        st.session_state.feedback_analysis_results = {"error_message": str(e)}

if "feedback_analysis_results" in st.session_state and st.session_state.feedback_analysis_results:
    results = st.session_state.feedback_analysis_results
    st.sidebar.markdown(f"**Total Feedback Entries:** {results.get('total_feedback_entries', 'N/A')}")
    avg_rating = results.get('average_rating')
    if avg_rating is not None:
        st.sidebar.markdown(f"**Average Rating:** {avg_rating:.2f} / 5")
    else:
        st.sidebar.markdown("**Average Rating:** N/A")
    
    st.sidebar.markdown("**Feedback Summary:**")
    summary_text = results.get('feedback_summary', 'Not available.')
    if results.get("error_message") and not summary_text:
        summary_text = f"Error: {results.get('error_message')}"
    elif not summary_text:
        summary_text = "No summary generated or an error occurred."
    
    with st.sidebar.expander("View Full Summary", expanded=False):
        st.markdown(summary_text)
    
    if results.get("error_message") and "feedback_summary" in results: # If there was an error message in the result itself
        st.sidebar.error(f"Analysis Error: {results.get('error_message')}")

st.sidebar.header("About")
st.sidebar.info(
    "This application uses a LangGraph-based multi-agent system "
    "to help you break down complex research questions and gather initial information. "
    "The backend is built with FastAPI, and this UI is powered by Streamlit."
)
st.sidebar.markdown("---")
st.sidebar.markdown("### How to Run:")
st.sidebar.markdown("1. **Setup Backend:**")
st.sidebar.markdown("   - Ensure `.env` is configured with your Azure OpenAI keys.")
st.sidebar.markdown("   - Open a terminal in the project root (`ai_research_advisor`).")
st.sidebar.markdown("   - Create a virtual environment: `python -m venv .venv`")
st.sidebar.markdown(r"   - Activate it: `.\.venv\Scripts\activate` (Windows) or `source .venv/bin/activate` (Linux/macOS)")
st.sidebar.markdown("   - Install dependencies: `pip install -r requirements.txt`")
st.sidebar.markdown("   - Run FastAPI: `uvicorn app.main:app --reload --port 8000`")
st.sidebar.markdown("2. **Run Frontend (this app):**")
st.sidebar.markdown("   - Open another terminal in the project root.")
st.sidebar.markdown("   - Activate the virtual environment (if not already).")
st.sidebar.markdown("   - Run Streamlit: `streamlit run ui/streamlit_app.py`")

# To run this Streamlit app:
# 1. Make sure the FastAPI backend is running (see app/main.py instructions).
# 2. Open your terminal in the 'ai_research_advisor' directory.
# 3. Run the command: streamlit run ui/streamlit_app.py
