def calculate_dynamic_risk(user):
    """
    Calculates User Vulnerability Score (0-100).
    Logic: 
    + Points for Clicks (Bad)
    + Points for Fast/Impulsive Clicks (Bad)
    - Points for Reporting the Email (Good)
    """
    base_score = 0
    logs = user.history
    
    if not logs:
        return 0.0

    total_campaigns = len(logs)
    clicks = sum(1 for log in logs if log.clicked)
    
    # 1. Click Ratio (Weight: 40%)
    if total_campaigns > 0:
        click_ratio = (clicks / total_campaigns) * 100
        base_score += (click_ratio * 0.4)

    # 2. Impulsiveness (Speed Factor)
    # If clicked within 60 seconds -> Very High Risk
    fast_clicks = 0
    for log in logs:
        if log.clicked and log.click_time:
            time_diff = (log.click_time - log.sent_at).total_seconds()
            if time_diff < 60: 
                fast_clicks += 1
    
    base_score += (fast_clicks * 15) # Heavy penalty for impulsiveness

    # 3. Reward for Reporting (The "Good Behavior" Bonus)
    reports = sum(1 for log in logs if log.reported)
    reward_points = reports * 10
    base_score -= reward_points

    # 4. Department Context
    dept_weights = {'Finance': 1.5, 'IT': 1.2, 'HR': 1.3}
    multiplier = dept_weights.get(user.department, 1.0)
    
    final_score = base_score * multiplier

    # Cap between 0 and 100
    return max(0.0, min(final_score, 100.0))