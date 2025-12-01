def calculate_driving_score(
    avg_speed, max_rpm, brake_events, steering_angle, angular_velocity,
    acceleration, gear_position, tire_pressure, engine_load,
    throttle_position, brake_pressure, trip_duration
):
    # Normalize and weight each feature
    score = (
        (avg_speed / 100) * 0.10 +                          # Higher speed within limit = better
        ((6000 - max_rpm) / 6000) * 0.10 +                  # Lower max RPM is better
        ((15 - brake_events) / 15) * 0.10 +                 # Fewer brake events = better
        ((30 - abs(steering_angle)) / 30) * 0.05 +          # Less sharp turns = better
        ((5 - abs(angular_velocity)) / 5) * 0.05 +          # Less erratic movement = better
        ((5 - abs(acceleration)) / 5) * 0.05 +              # Moderate acceleration = better
        ((6 - gear_position) / 6) * 0.05 +                  # Lower gear shifts = better
        ((35 - abs(tire_pressure - 32)) / 5) * 0.05 +       # Ideal tire pressure around 32 PSI
        ((100 - engine_load) / 100) * 0.10 +                # Lower engine load = better
        ((100 - throttle_position) / 100) * 0.10 +          # Lower throttle position = smoother drive
        ((100 - brake_pressure) / 100) * 0.05 +             # Less brake pressure = smoother drive
        ((60 - trip_duration) / 60) *0.1           # Shorter trips = possibly better for health
    ) * 100

    score = max(0, min(score, 100))  # Clamp score between 0 and 100

    behavior = classify_behavior(score)
    return behavior, round(score, 2)


def classify_behavior(score):
    if score >= 80:
        return "Safe"
    elif score >= 60:
        return "Moderate"
    else:
        return "Aggressive"
