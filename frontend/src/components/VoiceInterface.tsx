import { Mic, Activity } from 'lucide-react';

interface VoiceInterfaceProps {
  isListening: boolean;
  isThinking: boolean;
  isSpeaking: boolean;
  onExit: () => void;
}

export default function VoiceInterface({ isListening, isThinking, isSpeaking, onExit }: VoiceInterfaceProps) {
  let statusText = "Ready";
  let icon = <Mic size={24} className="text-gray-400" />;
  
  if (isSpeaking) {
    statusText = "Speaking...";
    icon = (
      <div className="flex gap-1 items-center h-6">
        <div className="w-1 bg-[var(--color-core-accent)] animate-bounce h-4" style={{ animationDelay: '0ms' }} />
        <div className="w-1 bg-[var(--color-core-accent)] animate-bounce h-6" style={{ animationDelay: '150ms' }} />
        <div className="w-1 bg-[var(--color-core-accent)] animate-bounce h-3" style={{ animationDelay: '300ms' }} />
        <div className="w-1 bg-[var(--color-core-accent)] animate-bounce h-5" style={{ animationDelay: '100ms' }} />
      </div>
    );
  } else if (isThinking) {
    statusText = "Processing...";
    icon = <Activity size={24} className="text-amber-500 animate-pulse" />;
  } else if (isListening) {
    statusText = "Listening...";
    icon = (
      <div className="relative flex items-center justify-center">
        <div className="absolute inset-0 rounded-full border-2 border-[var(--color-core-accent)] animate-ping opacity-50" style={{ transform: 'scale(1.5)' }} />
        <Mic size={24} className="text-[var(--color-core-accent)]" />
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-6 glass-panel rounded-xl border border-[var(--color-core-accent)]/30 backdrop-blur-md bg-[#0a0f1e]/80 shadow-[0_4px_30px_rgba(0,0,0,0.5)]">
      <div className="flex items-center justify-center w-16 h-16 rounded-full bg-white/5 mb-4">
        {icon}
      </div>
      <div className="font-mono text-[var(--color-core-accent)] tracking-widest text-sm mb-4 uppercase">
        {statusText}
      </div>
      <button 
        onClick={onExit}
        className="text-xs text-gray-500 hover:text-gray-300 font-sans border-b border-transparent hover:border-gray-500 transition-all flex items-center gap-1"
      >
        ✕ Exit Voice Mode
      </button>
    </div>
  );
}
