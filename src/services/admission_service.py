import json
import os
import difflib
import logging
import unicodedata
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

def normalize_text(text: str) -> str:
    """Removes accents and converts to lowercase for robust matching."""
    if not text:
        return ""
    text = text.lower().strip()
    return ''.join(c for c in unicodedata.normalize('NFD', text) if unicodedata.category(c) != 'Mn')

def _calculate_wma_target(career_data: dict, season: str) -> float | None:
    """
    Calculates a Weighted Moving Average + 1.5% Safety Buffer 
    for a specific semester season ('-1' or '-2').
    """
    scores = []
    # Extract scores matching the requested season (e.g., all "-2" semesters)
    for sem, stats in career_data.items():
        if sem.endswith(season) and stats.get("cutoff_score") is not None:
            scores.append((sem, stats["cutoff_score"]))
            
    if not scores:
        return None
        
    # Sort chronologically descending to get the newest semesters first
    scores.sort(key=lambda x: x[0], reverse=True)
    
    # Take up to the 3 most recent scores
    recent_scores = [s[1] for s in scores[:3]]
    
    # Apply weights based on available data points
    if len(recent_scores) == 3:
        wma = (recent_scores[0] * 0.5) + (recent_scores[1] * 0.3) + (recent_scores[2] * 0.2)
    elif len(recent_scores) == 2:
        wma = (recent_scores[0] * 0.7) + (recent_scores[1] * 0.3)
    else:
        wma = recent_scores[0]
        
    # Add 1.5% safety buffer and round
    safe_target = wma * 1.015
    return round(safe_target, 2)

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
    Includes automated mathematical forecasting for specific careers.
    Returns a JSON string containing the results.
    """
    try:
        with open(JSON_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        target_career = None
        
        # 1. Resolve Specific Career (with bulletproof fuzzy matching)
        if career:
            career_norm = normalize_text(career)
            key_map = {normalize_text(k): k for k in data.keys()}
            
            if career_norm in key_map:
                target_career = key_map[career_norm]
            else:
                matches = difflib.get_close_matches(career_norm, list(key_map.keys()), n=1, cutoff=0.5)
                if matches:
                    target_career = key_map[matches[0]]
                    logger.info(f"Fuzzy matched '{career}' to '{target_career}'")
                else:
                    return json.dumps({"error": f"Could not find any career matching: '{career}'"})

        # 2. Mathematical Forecasting (Only if a specific career is targeted)
        insights = None
        if target_career and target_career in data:
            c_data = data[target_career]
            insights = {
                "trend_analysis": {
                    "recommended_safe_target_for_semesters_ending_in_1": _calculate_wma_target(c_data, "-1"),
                    "recommended_safe_target_for_semesters_ending_in_2": _calculate_wma_target(c_data, "-2"),
                    "counselor_note": "Advise the user to aim for the 'recommended_safe_target' corresponding to their target semester. This is calculated using a Weighted Moving Average of recent historical data plus a safety margin to account for fluctuations."
                }
            }

        # 3. Filter and Flatten Data
        results = []
        for c_name, c_data in data.items():
            if target_career and c_name != target_career:
                continue
                
            for sem, stats in c_data.items():
                if semester and sem != semester:
                    continue
                
                score = stats.get("cutoff_score")
                
                if min_score is not None:
                    if score is None or score < min_score:
                        continue
                        
                if max_score is not None:
                    if score is None or score > max_score:
                        continue
                
                results.append({
                    "career": c_name,
                    "semester": sem,
                    "cutoff_score": score,
                    "admitted_count": stats.get("admitted_count")
                })

        # 4. Sort Results
        if sort_by in ["cutoff_score", "admitted_count"]:
            reverse_sort = False if sort_order == "asc" else True
            results.sort(
                key=lambda x: x[sort_by] if x[sort_by] is not None else -999, 
                reverse=reverse_sort
            )

        # 5. Limit Results
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
            "results": results,
            "insights": insights  # The AI will read this object and formulate advice!
        })

    except Exception as e:
        logger.error(f"Error querying admission stats: {e}")
        return json.dumps({"error": "Internal database error while querying."})