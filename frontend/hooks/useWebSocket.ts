"use client";

import { useEffect, useRef } from "react";
import { getWsUrl } from "@/lib/api";

type WsMessage = {
  type: string;
  payload?: unknown;
};

export function useWebSocket(onMessage: (msg: WsMessage) => void) {
  const handler = useRef(onMessage);
  handler.current = onMessage;

  useEffect(() => {
    let ws: WebSocket | null = null;
    let timer: ReturnType<typeof setTimeout>;

    const connect = () => {
      try {
        ws = new WebSocket(getWsUrl());
        ws.onmessage = (ev) => {
          try {
            const data = JSON.parse(ev.data);
            handler.current(data);
          } catch {
            /* ignore */
          }
        };
        ws.onclose = () => {
          timer = setTimeout(connect, 4000);
        };
      } catch {
        timer = setTimeout(connect, 4000);
      }
    };

    connect();
    return () => {
      clearTimeout(timer);
      ws?.close();
    };
  }, []);
}
