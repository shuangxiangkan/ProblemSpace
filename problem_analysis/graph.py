from langgraph.graph import END, StateGraph

from problem_analysis.nodes import analyze_query
from problem_analysis.state import KeywordAnalysisState


def build_problem_analysis_graph():
    builder = StateGraph(KeywordAnalysisState)
    builder.add_node("analyze_query", analyze_query)
    builder.set_entry_point("analyze_query")
    builder.add_edge("analyze_query", END)
    return builder.compile()
