import json
from backend.llm import call_llm

def extract_themes(verified_reviews, rejected_count):
    """
    Processes verified reviews to group them into recurring themes.
    Matches the Scorer interface contract for the Feedback Synthesiser pipeline.
    """
    if not verified_reviews:
        return []

    # Extract text from the cleaned review rows
    reviews_text = [review.get("text", "") for review in verified_reviews if "text" in review]

    prompt = f"""
    Analyze the following list of customer reviews and group them into distinct themes.
    You must return a valid JSON array of objects. Do not include markdown formatting.
    
    Each object must strictly follow this schema:
    - "name": A concise, descriptive string naming the theme.
    - "count": An integer representing the number of reviews that fall under this theme.
    - "samples": An array containing 1 to 3 direct string quotes from the reviews that illustrate this theme.
    
    Reviews to analyze:
    {json.dumps(reviews_text)}
    """

    # The call_llm function natively handles the 3 retries, backoff, and safe JSON fallback
    response = call_llm(prompt)

    try:
        # Parse the JSON if call_llm returns a raw string
        if isinstance(response, str):
            themes = json.loads(response)
        else:
            themes = response

        # Enforce the agreed data contract before passing to the Analyst
        validated_themes = []
        for theme in themes:
            if all(key in theme for key in ("name", "count", "samples")):
                validated_themes.append({
                    "name": str(theme["name"]),
                    "count": int(theme["count"]),
                    "samples": list(theme["samples"])
                })
        
        return validated_themes

    except (json.JSONDecodeError, TypeError, ValueError):
        # Fallback to an empty list to prevent pipeline crashes if the LLM output is malformed
        return []