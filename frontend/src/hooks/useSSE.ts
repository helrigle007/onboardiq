import { useState, useEffect, useRef } from 'react';
import type { SSEEvent } from '../types';

interface UseSSEOptions {
  guideId: string | null;
  onEvent?: (event: SSEEvent) => void;
}

interface UseSSEReturn {
  isConnected: boolean;
  events: SSEEvent[];
  error: string | null;
}

export function useSSE({ guideId, onEvent }: UseSSEOptions): UseSSEReturn {
  const [isConnected, setIsConnected] = useState(false);
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [error, setError] = useState<string | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  useEffect(() => {
    if (!guideId) return;

    const es = new EventSource(`/api/guides/${guideId}/stream`);
    eventSourceRef.current = es;

    es.onopen = () => setIsConnected(true);

    es.onmessage = (event) => {
      try {
        const parsed: SSEEvent = JSON.parse(event.data);
        if (parsed.type === 'keepalive') return;

        setEvents((prev) => [...prev, parsed]);
        onEvent?.(parsed);

        if (parsed.type === 'guide_complete' || parsed.type === 'error') {
          es.close();
          setIsConnected(false);
        }
      } catch {
        // Silently ignore malformed SSE data
      }
    };

    es.onerror = () => {
      setError('Connection lost');
      setIsConnected(false);
      es.close();
    };

    return () => {
      es.close();
      setIsConnected(false);
    };
  }, [guideId, onEvent]);

  return { isConnected, events, error };
}
