ADMISSION_QUERY_TOOL = {
    "type": "function",
    "name": "query_admission_data",
    "description": "Queries historical university admission data. Use this to find specific career scores, filter by score ranges (e.g., less than 600), sort (e.g., highest scores), or limit results (e.g., top 5).",
    "parameters": {
        "type": "object",
        "properties": {
            "career": {
                "type": ["string", "null"],
                "description": "The specific name of the career to look up (e.g., medicina, ingenieria de sistemas). Set to null if the user is asking general questions like 'top 5 careers'."
            },
            "min_score": {
                "type": ["number", "null"],
                "description": "Minimum cutoff score. Use if the user asks for careers needing more than X points."
            },
            "max_score": {
                "type": ["number", "null"],
                "description": "Maximum cutoff score. Use if the user asks for careers needing less than X points."
            },
            "semester": {
                "type": ["string", "null"],
                "description": "Specific semester to filter by (e.g., '2022-1', '2023-2'). Set to null to search across all available semesters."
            },
            "sort_by": {
                "type": ["string", "null"],
                "description": "Field to sort by. Valid values are exactly: 'cutoff_score' or 'admitted_count'. Set to null if no sorting is requested."
            },
            "sort_order": {
                "type": ["string", "null"],
                "description": "Order to sort the results. Valid values are exactly: 'asc' (lowest first) or 'desc' (highest first). Set to null if no sorting is requested."
            },
            "limit": {
                "type": ["integer", "null"],
                "description": "Maximum number of careers to return. Use for 'top 5' or 'give me 3 options' queries. Set to null if no limit is specified."
            }
        },
        "required": [
            "career", 
            "min_score", 
            "max_score", 
            "semester", 
            "sort_by", 
            "sort_order", 
            "limit"
        ],
        "additionalProperties": False
    },
    "strict": True
}

def get_custom_tools() -> list:
    """Returns the list of custom function definitions for the AI."""
    return [ADMISSION_QUERY_TOOL]