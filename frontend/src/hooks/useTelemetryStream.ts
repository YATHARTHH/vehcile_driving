import { useEffect, useRef, useState, useCallback } from 'react';
import { useAuth } from '../store/authContext';
import { api } from '../services/api';
import { VehicleLiveState, AlertSeverity } from '../types';

export type StreamConnectionStatus =
  | 'CONNECTING'
  | 'AUTHENTICATING'
  | 'LIVE'
  | 'DISCONNECTED'
  | 'RECONNECTING';

export interface UseTelemetryStreamResult {
  liveState: VehicleLiveState | null;
  connectionStatus: StreamConnectionStatus;
  isLive: boolean;
  recentAlerts: Array<{ code: string; severity: AlertSeverity; message: string; timestamp?: string }>;
  refreshSnapshot: () => Promise<void>;
}

export const useTelemetryStream = (targetVehicleId?: string): UseTelemetryStreamResult => {
  const { token, user, isAuthenticated } = useAuth();
  const vehicleId = targetVehicleId || user?.vehicle_number || '';

  const [liveState, setLiveState] = useState<VehicleLiveState | null>(null);
  const [connectionStatus, setConnectionStatus] = useState<StreamConnectionStatus>('CONNECTING');
  const [recentAlerts, setRecentAlerts] = useState<
    Array<{ code: string; severity: AlertSeverity; message: string; timestamp?: string }>
  >([]);

  const currentVersionRef = useRef<number>(0);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef<number>(0);
  const reconnectTimerRef = useRef<number | null>(null);
  const pingTimerRef = useRef<number | null>(null);

  // ---------------------------------------------------------------------------
  // 1. REST Snapshot Synchronization
  // ---------------------------------------------------------------------------
  const refreshSnapshot = useCallback(async () => {
    if (!vehicleId || !token) return;
    try {
      const res = await api.get<VehicleLiveState>(`/telemetry/state/${vehicleId}`);
      if (res.data) {
        if (res.data.state_version >= currentVersionRef.current) {
          currentVersionRef.current = res.data.state_version;
          setLiveState(res.data);
          if (res.data.active_alerts?.length) {
            setRecentAlerts(prev => {
              const existingCodes = new Set(prev.map(a => a.code));
              const newAlerts = res.data.active_alerts.filter(a => !existingCodes.has(a.code));
              return [...newAlerts, ...prev].slice(0, 10);
            });
          }
        }
      }
    } catch {
      // Vehicle may not have a live cache entry yet if engine is off
    }
  }, [vehicleId, token]);

  // ---------------------------------------------------------------------------
  // 2. WebSocket Connection & Lifecycle Management
  // ---------------------------------------------------------------------------
  useEffect(() => {
    if (!isAuthenticated || !token || !vehicleId) {
      setConnectionStatus('DISCONNECTED');
      return;
    }

    let isUnmounted = false;

    const connectWebSocket = () => {
      if (isUnmounted) return;

      // Determine WS endpoint based on current host or standard dev port
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const host = window.location.hostname || 'localhost';
      const wsUrl = `${protocol}//${host}:8000/api/v1/telemetry/ws`;

      setConnectionStatus(reconnectAttemptsRef.current === 0 ? 'CONNECTING' : 'RECONNECTING');

      try {
        const ws = new WebSocket(wsUrl);
        wsRef.current = ws;

        ws.onopen = () => {
          if (isUnmounted) return;
          setConnectionStatus('AUTHENTICATING');

          // In-band JWT Authentication (prevents leaking token in query params)
          ws.send(JSON.stringify({
            type: 'authenticate',
            token: token,
          }));

          // Heartbeat ping every 20s
          if (pingTimerRef.current) window.clearInterval(pingTimerRef.current);
          pingTimerRef.current = window.setInterval(() => {
            if (ws.readyState === WebSocket.OPEN) {
              ws.send(JSON.stringify({ action: 'ping' }));
            }
          }, 20000);
        };

        ws.onmessage = (event) => {
          if (isUnmounted) return;
          try {
            const msg = JSON.parse(event.data);

            if (msg.type === 'authenticated') {
              setConnectionStatus('LIVE');
              reconnectAttemptsRef.current = 0;

              // Immediately fetch REST snapshot for guaranteed current baseline
              refreshSnapshot();

              // Subscribe to the target vehicle channel
              ws.send(JSON.stringify({
                action: 'subscribe',
                vehicle_id: vehicleId,
              }));
            } else if (msg.type === 'telemetry_snapshot' || msg.type === 'telemetry_update') {
              const frame: VehicleLiveState = msg.data;
              if (frame && frame.vehicle_id === vehicleId) {
                // Invariant: Monotonic state_version guard (drop out-of-order stale frames)
                if (frame.state_version > currentVersionRef.current) {
                  currentVersionRef.current = frame.state_version;
                  setLiveState(frame);

                  // Extract alerts
                  if (frame.active_alerts?.length) {
                    setRecentAlerts(prev => {
                      const existingCodes = new Set(prev.map(a => a.code));
                      const newAlerts = frame.active_alerts.filter(a => !existingCodes.has(a.code));
                      return [...newAlerts, ...prev].slice(0, 10);
                    });
                  }
                }
              }
            } else if (msg.type === 'error') {
              if (msg.code === 'AUTH_TIMEOUT' || msg.code === 'INVALID_TOKEN') {
                setConnectionStatus('DISCONNECTED');
              }
            }
          } catch {
            // Ignore non-json frames
          }
        };

        ws.onclose = () => {
          if (isUnmounted) return;
          if (pingTimerRef.current) window.clearInterval(pingTimerRef.current);
          setConnectionStatus('RECONNECTING');

          // Exponential backoff with jitter (1s to 10s)
          const attempt = reconnectAttemptsRef.current;
          const delay = Math.min(1000 * Math.pow(1.5, attempt) + Math.random() * 500, 10000);
          reconnectAttemptsRef.current += 1;

          reconnectTimerRef.current = window.setTimeout(() => {
            connectWebSocket();
          }, delay);
        };

        ws.onerror = () => {
          ws.close();
        };
      } catch {
        setConnectionStatus('DISCONNECTED');
      }
    };

    // Initial snapshot before socket finishes connecting
    refreshSnapshot();
    connectWebSocket();

    return () => {
      isUnmounted = true;
      if (pingTimerRef.current) window.clearInterval(pingTimerRef.current);
      if (reconnectTimerRef.current) window.clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
    };
  }, [isAuthenticated, token, vehicleId, refreshSnapshot]);

  return {
    liveState,
    connectionStatus,
    isLive: connectionStatus === 'LIVE',
    recentAlerts,
    refreshSnapshot,
  };
};
