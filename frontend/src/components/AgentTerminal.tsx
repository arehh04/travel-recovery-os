import { useEffect, useState, useRef } from 'react';

interface AgentEvent {
  type: string;
  timestamp: string;
  mission_id?: string;
  data: any;
}

interface AgentTerminalProps {
  missionId: string;
}

export function AgentTerminal({ missionId }: AgentTerminalProps) {
  const [logs, setLogs] = useState<AgentEvent[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!missionId) return;

    // Use SSE to stream events
    const eventSource = new EventSource(`/api/v1/missions/${missionId}/events`);

    eventSource.onmessage = (event) => {
      try {
        const parsed = JSON.parse(event.data);
        setLogs((prev) => [...prev, parsed]);
      } catch (err) {
        console.error('Failed to parse SSE data:', err);
      }
    };

    eventSource.onerror = () => {
      eventSource.close();
    };

    return () => {
      eventSource.close();
    };
  }, [missionId]);

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [logs]);

  if (!missionId || logs.length === 0) {
    return null;
  }

  return (
    <div className="bg-[#1e1e1e] border border-outline-variant shadow-lg rounded-xl overflow-hidden mt-6 text-left w-full">
      <div className="bg-[#2d2d2d] px-4 py-2 flex items-center gap-2 border-b border-[#3d3d3d]">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-[#ff5f56]"></div>
          <div className="w-3 h-3 rounded-full bg-[#ffbd2e]"></div>
          <div className="w-3 h-3 rounded-full bg-[#27c93f]"></div>
        </div>
        <span className="text-[#a0a0a0] text-xs font-mono ml-2 tracking-wider uppercase">Agent Reasoning Log</span>
      </div>
      <div 
        ref={scrollRef}
        className="p-4 h-64 overflow-y-auto font-mono text-xs sm:text-sm text-[#e0e0e0] flex flex-col gap-2"
      >
        {logs.map((log, i) => (
          <div key={i} className="flex gap-3">
            <span className="text-[#569cd6] shrink-0 hidden sm:inline">
              [{new Date(log.timestamp).toLocaleTimeString([], { hour12: false })}]
            </span>
            <span className="text-[#c586c0] shrink-0">
              {log.type.padEnd(12, ' ')}
            </span>
            <span className="text-white whitespace-pre-wrap break-words">
              {typeof log.data === 'string' ? log.data : JSON.stringify(log.data, null, 2)}
            </span>
          </div>
        ))}
        <div className="flex gap-3 animate-pulse mt-2">
          <span className="text-[#569cd6] hidden sm:inline">[{new Date().toLocaleTimeString([], { hour12: false })}]</span>
          <span className="text-white">_</span>
        </div>
      </div>
    </div>
  );
}
