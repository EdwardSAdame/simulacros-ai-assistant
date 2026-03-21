# src/config/tools_config.py

ADMISSION_QUERY_TOOL = {
    "type": "function",
    "name": "query_admission_data",
    "description": "Queries historical university admission data to forecast future trends. CRITICAL: This database ONLY contains PAST historical data. To predict a future semester, you must retrieve the past history by leaving the semester field null.",
    "parameters": {
        "type": "object",
        "properties": {
            "career": {
                "type": ["string", "null"],
                "description": "The specific name of the career to look up. Set to null if the user is asking general questions."
            },
            "min_score": {
                "type": ["number", "null"],
                "description": "Minimum cutoff score. CRITICAL: NEVER invent or guess this value based on your calculations. ONLY use this if the user EXPLICITLY types a numerical value requesting a specific lower bound."
            },
            "max_score": {
                "type": ["number", "null"],
                "description": "Maximum cutoff score. CRITICAL: NEVER invent or guess this value based on your calculations. ONLY use this if the user EXPLICITLY types a numerical value requesting a specific upper bound."
            },
            "semester": {
                "type": ["string", "null"],
                "description": "Specific historical semester to filter by. CRITICAL: NEVER pass a future or current semester because the database only holds past records. If the user asks about the future or a target semester that has not happened yet, you MUST set this to null to fetch the historical data."
            },
            "sort_by": {
                "type": ["string", "null"],
                "description": "Field to sort by. Valid values are exactly: 'cutoff_score' or 'admitted_count'. Set to null if no sorting is requested."
            },
            "sort_order": {
                "type": ["string", "null"],
                "description": "Order to sort the results. Valid values are exactly: 'asc' or 'desc'. Set to null if no sorting is requested."
            },
            "limit": {
                "type": ["integer", "null"],
                "description": "Maximum number of careers to return. Set to null if no limit is specified."
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