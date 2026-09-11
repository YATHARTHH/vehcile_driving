import math
import random
from dataclasses import dataclass, field


@dataclass
class VehicleKinematics:
    """
    Kinematic model simulating realistic vehicle physics, engine mechanics, and GPS progression.
    """
    speed_kmph: float = 0.0
    rpm: float = 800.0  # Idle RPM
    throttle_pct: float = 0.0
    brake_pressure_bar: float = 0.0
    gear: int = 1
    engine_load_pct: float = 15.0
    tire_pressure_psi: float = 32.0
    odometer_km: float = 12500.0
    fuel_level_pct: float = 85.0
    engine_temp_c: float = 90.0
    lat: float = 18.5204  # Default: Pune / Mumbai coordinates
    lon: float = 73.8567
    heading_deg: float = 45.0
    vehicle_class: str = "passenger_car"
    powertrain: str = "ice_petrol"

    # Gear ratios for 5-speed transmission
    gear_ratios: list[float] = field(default_factory=lambda: [3.54, 2.05, 1.34, 0.97, 0.76])
    final_drive: float = 4.10

    def step(self, target_speed_kmph: float, dt: float = 1.0) -> dict[str, float]:
        """
        Advances the kinematic simulation by dt seconds toward target_speed_kmph.
        Returns a dictionary of raw sensor readings.
        """
        speed_diff = target_speed_kmph - self.speed_kmph

        if speed_diff > 1.0:
            # Accelerating
            accel_rate = min(speed_diff / 5.0, 3.5)  # m/s^2 capped
            self.speed_kmph = min(target_speed_kmph, self.speed_kmph + (accel_rate * 3.6 * dt))
            self.throttle_pct = min(100.0, max(15.0, (accel_rate / 3.5) * 85.0 + random.uniform(-2, 2)))
            self.brake_pressure_bar = 0.0
            self.engine_load_pct = min(95.0, 20.0 + self.throttle_pct * 0.7)
        elif speed_diff < -1.0:
            # Braking / Decelerating
            decel_rate = min(abs(speed_diff) / 3.0, 5.0)  # m/s^2 capped
            self.speed_kmph = max(0.0, self.speed_kmph - (decel_rate * 3.6 * dt))
            self.throttle_pct = 0.0
            self.brake_pressure_bar = min(120.0, (decel_rate / 5.0) * 80.0 + random.uniform(0, 5))
            self.engine_load_pct = max(10.0, 20.0 - decel_rate * 2.0)
        else:
            # Cruising at steady speed
            self.speed_kmph = target_speed_kmph + random.uniform(-0.5, 0.5)
            self.throttle_pct = max(10.0, min(35.0, self.speed_kmph * 0.35 + random.uniform(-2, 2)))
            self.brake_pressure_bar = 0.0
            self.engine_load_pct = 25.0 + random.uniform(-3, 3)

        # Select gear based on speed
        if self.speed_kmph < 15:
            self.gear = 1
        elif self.speed_kmph < 35:
            self.gear = 2
        elif self.speed_kmph < 55:
            self.gear = 3
        elif self.speed_kmph < 80:
            self.gear = 4
        else:
            self.gear = 5

        # Calculate RPM based on powertrain and gear
        if self.powertrain == "bev":
            # Electric vehicle reduction gear: single speed, RPM proportional to speed
            self.rpm = max(0.0, self.speed_kmph * 85.0)
        else:
            ratio = self.gear_ratios[self.gear - 1]
            wheel_rpm = (self.speed_kmph * 1000.0 / 60.0) / (2 * math.pi * 0.31)  # Tire radius ~0.31m
            calculated_rpm = wheel_rpm * ratio * self.final_drive
            self.rpm = max(800.0, min(6500.0, calculated_rpm + random.uniform(-20, 20)))

        # Update GPS coordinates along heading
        # 1 degree latitude ~ 111,000 meters
        distance_meters = (self.speed_kmph * 1000.0 / 3600.0) * dt
        delta_lat = (distance_meters * math.cos(math.radians(self.heading_deg))) / 111000.0
        delta_lon = (distance_meters * math.sin(math.radians(self.heading_deg))) / (111000.0 * math.cos(math.radians(self.lat)))

        self.lat += delta_lat
        self.lon += delta_lon
        self.heading_deg = (self.heading_deg + random.uniform(-1.0, 1.0)) % 360.0

        # Subtle tire pressure thermal expansion with speed
        self.tire_pressure_psi = 32.0 + (self.speed_kmph / 100.0) * 1.5 + random.uniform(-0.1, 0.1)

        # Odometer and consumption
        self.odometer_km += distance_meters / 1000.0
        self.fuel_level_pct = max(0.0, self.fuel_level_pct - (self.engine_load_pct * 0.0001 * dt))
        self.engine_temp_c = min(105.0, 90.0 + (self.engine_load_pct / 100.0) * 12.0)

        return {
            "speed_kmph": round(self.speed_kmph, 2),
            "rpm": round(self.rpm, 1),
            "throttle_pct": round(self.throttle_pct, 1),
            "brake_pressure_bar": round(self.brake_pressure_bar, 1),
            "engine_load_pct": round(self.engine_load_pct, 1),
            "tire_pressure_psi": round(self.tire_pressure_psi, 1),
            "odometer_km": round(self.odometer_km, 2),
            "fuel_level_pct": round(self.fuel_level_pct, 2),
            "engine_temp_c": round(self.engine_temp_c, 1),
            "gear_position": self.gear,
            "lat": round(self.lat, 6),
            "lon": round(self.lon, 6),
        }


# Alias for backwards compatibility / domain terminology
VehiclePhysicsModel = VehicleKinematics
