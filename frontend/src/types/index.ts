export interface User {
  id: number;
  username: string;
  vehicle_number: string;
  email?: string;
  created_at?: string;
}

export interface Trip {
  id: number;
  user_id: number;
  trip_date: string;
  distance_km: number;
  avg_speed_kmph: number;
  max_speed: number;
  max_rpm: number;
  fuel_consumed: number;
  brake_events: number;
  steering_angle: number;
  angular_velocity: number;
  acceleration: number;
  gear_position: number;
  tire_pressure: number;
  engine_load: number;
  throttle_position: number;
  brake_pressure: number;
  trip_duration: number;
  start_location?: string;
  end_location?: string;
}

export interface Alert {
  id: number;
  user_id: number;
  trip_id?: number;
  alert_type: string;
  severity: 'info' | 'warning' | 'critical';
  title: string;
  message: string;
  icon: string;
  timestamp: string;
  resolved: boolean;
}

export interface TripDetail {
  trip: Trip;
  logic_score: number;
  logic_behavior: string;
  ml_behavior: string;
  ml_confidence: number;
  ml_model_used: string;
  health_recommendation: string;
  maintenance_alerts: any[];
}

export interface RouteOption {
  type: 'direct' | 'eco' | 'fastest';
  name: string;
  description: string;
  distance_km: number;
  travel_time_minutes: number;
  fuel_consumption: number;
  fuel_cost: number;
  efficiency_score: number;
  traffic_info: {
    level: string;
    delay_factor: number;
    estimated_delay_minutes: number;
  };
  route_highlights: string[];
  coordinates: [number, number][];
}

export type AlertSeverity = 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL';

export interface VehicleLiveState {
  tenant_id: string;
  vehicle_id: string;
  state_version: number;
  event_timestamp: string;
  updated_at: string;
  speed_kmph: number;
  rpm: number;
  fuel_level_pct?: number | null;
  fuel_rate_lph?: number | null;
  fuel_consumed_total_l?: number | null;
  lat?: number | null;
  lon?: number | null;
  heading?: number | null;
  driving_score?: number | null;
  active_alerts: Array<{
    code: string;
    severity: AlertSeverity;
    message: string;
  }>;
  highest_alert_severity?: AlertSeverity | null;
}

