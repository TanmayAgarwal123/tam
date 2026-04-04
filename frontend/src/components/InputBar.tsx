import { useState, useRef, useEffect } from 'react';
import { Send, Mic, MicOff } from 'lucide-react';

interface InputBarProps {
  onSendMessage: (text: string) => void;
  isThinking: boolean;
}

export default function InputBar({ onSendMessage, isThinking }: InputBarProps) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  
  // Need to use any for SpeechRecognition since it's not well typed in TS standard DOM lib
  const recognitionRef = useRef<any>(null);

  useEffect(() => {
    const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (SpeechRecognition) {
      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        // Auto-fill but do NOT send automatically, append if input exists
        setInput(prev => prev ? `${prev} ${transcript}` : transcript);
        setIsRecording(false);
      };

      recognition.onerror = (event: any) => {
        console.error("Speech recognition error", event.error);
        setIsRecording(false);
      };

      recognition.onend = () => {
        setIsRecording(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isThinking) return;
    onSendMessage(input);
    setInput('');
  };

  const toggleRecording = () => {
    if (!recognitionRef.current) {
      alert("Speech recognition is not supported in this browser.");
      return;
    }

    if (isRecording) {
      recognitionRef.current.stop();
    } else {
      try {
        recognitionRef.current.start();
        setIsRecording(true);
      } catch (e) {
        console.error("Failed to start recording:", e);
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  return (
    <form 
      onSubmit={handleSubmit} 
      className="relative flex items-end gap-2 p-2 glass-panel rounded-xl border border-[var(--color-core-accent)]/30 focus-within:border-[var(--color-core-accent)]/80 transition-colors bg-[#0a0f1e]/80 shadow-[0_4px_30px_rgba(0,0,0,0.5)]"
    >
      <div className="flex-1 relative">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Direct command line..."
          className="w-full max-h-48 min-h-[52px] bg-transparent text-gray-100 placeholder-gray-500 p-3 outline-none resize-none overflow-y-auto font-sans"
          disabled={isThinking}
          rows={input.split('\n').length > 1 ? Math.min(input.split('\n').length, 5) : 1}
        />
      </div>

      <div className="flex flex-col gap-2 shrink-0 pb-1 pr-1">
        <button
          type="button"
          onClick={toggleRecording}
          disabled={isThinking}
          className={`p-3 rounded-lg flex items-center justify-center transition-colors ${
            isRecording 
              ? 'bg-red-500/20 text-red-400 border border-red-500/50 animate-pulse' 
              : 'text-gray-400 hover:text-white hover:bg-white/5'
          }`}
          title="Voice Input"
        >
          {isRecording ? <Mic size={20} /> : <MicOff size={20} />}
        </button>

        <button
          type="submit"
          disabled={!input.trim() || isThinking}
          className={`p-3 rounded-lg flex items-center justify-center transition-all ${
            input.trim() && !isThinking
              ? 'bg-[var(--color-core-accent)] text-white shadow-[0_0_15px_rgba(99,102,241,0.5)] hover:bg-[var(--color-core-accent-hover)]'
              : 'bg-white/5 text-gray-500 cursor-not-allowed'
          }`}
          title="Send Command"
        >
          <Send size={20} />
        </button>
      </div>
    </form>
  );
}
