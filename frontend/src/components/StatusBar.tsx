import { Volume2, VolumeX, Cpu, Activity, Mic } from 'lucide-react';

interface StatusBarProps {
  isThinking: boolean;
  lastMemoryUpdate: string;
  isMuted: boolean;
  onToggleMute: () => void;
  voiceModeActive: boolean;
  onToggleVoiceMode: () => void;
  moodColor?: string;
  statusFlash?: 'none' | 'urgent' | 'proactive';
}

export default function StatusBar({ isThinking, lastMemoryUpdate, isMuted, onToggleMute, voiceModeActive, onToggleVoiceMode, moodColor = "bg-green-500", statusFlash = 'none' }: StatusBarProps) {
  const flashBorder = statusFlash === 'urgent' 
    ? 'border-b-red-500 shadow-[0_2px_12px_rgba(239,68,68,0.6)]'
    : statusFlash === 'proactive'
    ? 'border-b-emerald-500 shadow-[0_2px_12px_rgba(16,185,129,0.4)]'
    : '';
  return (
    <div className={`h-12 border-b border-[var(--color-glass-border)] glass-panel flex items-center justify-between px-6 shrink-0 z-10 w-full transition-all duration-300 ${flashBorder}`}>
      <div className="flex items-center gap-3">
        <div className="relative flex items-center justify-center w-6 h-6 rounded-md bg-[var(--color-core-accent)]/20 text-[var(--color-core-accent)] border border-[var(--color-core-accent)]/30">
          <Cpu size={14} className={isThinking ? 'animate-pulse' : ''} />
        </div>
        <span className="font-mono text-sm tracking-widest text-[var(--color-core-accent)] font-medium uppercase flex items-center gap-2">
          {isThinking ? 'TAM IS THINKING...' : 'TAM OS IS READY'}
          {!isThinking && <span className={`w-2 h-2 rounded-full ${moodColor} shadow-[0_0_8px_currentColor]`} title="Mood Indicator"></span>}
        </span>
        {isThinking && (
          <Activity size={14} className="text-[var(--color-core-accent)] animate-pulse ml-1" />
        )}
      </div>

      <div className="flex items-center gap-6">
        <div className="flex items-center gap-2 text-xs text-gray-400 font-mono">
          <span className="w-2 h-2 rounded-full bg-green-500"></span>
          MEMORY CORE: {lastMemoryUpdate}
        </div>
        
        <div className="flex items-center gap-3 border-l border-white/10 pl-4">
          <button 
            onClick={onToggleVoiceMode}
            className={`flex items-center gap-2 text-xs font-mono uppercase px-3 py-1.5 rounded-md transition-all ${
              voiceModeActive 
                ? 'bg-[var(--color-core-accent)]/20 text-[var(--color-core-accent)] border border-[var(--color-core-accent)]/50' 
                : 'text-gray-400 hover:text-white hover:bg-white/10 border border-transparent'
            }`}
            title="Toggle Hands-Free Voice Mode"
          >
            {voiceModeActive ? (
              <>
                <span className="w-2 h-2 rounded-full bg-[var(--color-core-accent)] animate-pulse"></span>
                Live
              </>
            ) : (
              <>
                <Mic size={14} />
                Voice Mode
              </>
            )}
          </button>
          
          <button 
            onClick={onToggleMute}
            className="text-gray-400 hover:text-white transition-colors p-1.5 rounded-md hover:bg-white/10"
            title={isMuted ? "Unmute Voice" : "Mute Voice"}
          >
            {isMuted ? <VolumeX size={18} /> : <Volume2 size={18} />}
          </button>
        </div>
      </div>
    </div>
  );
}
