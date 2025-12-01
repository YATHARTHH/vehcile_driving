

def get_health_recommendation(behavior_class):
    if behavior_class == "Safe":
        return "Vehicle health is optimal. Regular maintenance is enough."
    elif behavior_class == "Moderate":
        return "Monitor wear and tear. Consider a check-up."
    else:
        return "Driving behavior indicates stress on the vehicle. Inspection recommended."
