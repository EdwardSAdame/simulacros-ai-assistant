import json
import os
import difflib
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Construct the absolute path to your JSON file based on the repository structure
JSON_PATH = os.path.join(
    os.path.dirname(__file__), 
    "..", 
    "knowledge", 
    "unal", 
    "general", 
    "unal_admission_stats.json"
)

def query_admission_data(
    career: Optional[str] = None,
    min_score: Optional[float] = None,
    max_score: Optional[float] = None,
    semester: Optional[str] = None,
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = None,
    limit: Optional[int] = None
) -> str:
    """
    Dynamically queries admission stats based on multiple optional filters.
    Returns a JSON string containing the filtered, sorted, and limited results.
    """
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        target_career = None
        
        # 1. Resolve Specific Career (with fuzzy matching)
        if career:
            career_clean = career.lower().strip()
            if career_clean in data:
                target_career = career_clean
            else:
                matches = difflib.get_close_matches(career_clean, list(data.keys()), n=1, cutoff=0.6)
                if matches:
                    target_career = matches[0]
                    logger.info(f"Fuzzy matched '{career}' to '{target_career}'")
                else:
                    return json.dumps({"error": f"Could not find any career matching: '{career}'"})

        # 2. Filter and Flatten Data
        results = []
        for c_name, c_data in data.items():
            # Skip if we are looking for a specific career and this isn't it
            if target_career and c_name != target_career:
                continue
                
            for sem, stats in c_data.items():
                # Filter by semester
                if semester and sem != semester:
                    continue
                
                score = stats.get("cutoff_score")
                
                # Filter by min/max score
                # Note: We skip entries where the score is null (None) if a score filter is applied
                if min_score is not None:
                    if score is None or score < min_score:
                        continue
                        
                if max_score is not None:
                    if score is None or score > max_score:
                        continue
                
                # If it passes all filters, add to results
                results.append({
                    "career": c_name,
                    "semester": sem,
                    "cutoff_score": score,
                    "admitted_count": stats.get("admitted_count")
                })

        # 3. Sort Results
        if sort_by in ["cutoff_score", "admitted_count"]:
            # Default to descending (highest first) unless 'asc' is explicitly requested
            reverse_sort = False if sort_order == "asc" else True
            
            # Sort safely, putting None/null values at the bottom
            results.sort(
                key=lambda x: x[sort_by] if x[sort_by] is not None else -999, 
                reverse=reverse_sort
            )

        # 4. Limit Results
        if limit and limit > 0:
            results = results[:limit]

        return json.dumps({
            "query_applied": {
                "career_matched": target_career,
                "filters": {
                    "min_score": min_score,
                    "max_score": max_score,
                    "semester": semester
                },
                "sorting": {"by": sort_by, "order": sort_order},
                "limit": limit
            },
            "total_matches": len(results),
            "results": results
        })

    except Exception as e:
        logger.error(f"Error querying admission stats: {e}")
        return json.dumps({"error": "Internal database error while querying."})