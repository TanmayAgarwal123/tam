import { useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '../App';
import { Terminal } from 'lucide-react';

export default function ChatWindow({ messages }: { messages: Message[] }) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  if (messages.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-center p-8 opacity-70">
        <div className="w-16 h-16 rounded-2xl glass-panel flex items-center justify-center text-[var(--color-core-accent)] mb-6 shadow-[0_0_30px_rgba(99,102,241,0.2)]">
          <Terminal size={32} />
        </div>
        <h1 className="text-2xl font-mono tracking-wider mb-2 text-white">TAM OS</h1>
        <p className="text-gray-400 max-w-md mx-auto">
          Intelligent life OS active. Ready for input.
        </p>
      </div>
    );
  }

  return (
    <div className="h-full overflow-y-auto w-full pb-32 pt-8 absolute inset-0 custom-scrollbar">
      <div className="max-w-4xl mx-auto px-6 flex flex-col gap-8">
        {messages.map((msg) => (
          <div 
            key={msg.id} 
            className={`flex gap-4 w-full ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            {msg.role === 'assistant' && (
              <div className="shrink-0 w-8 h-8 rounded bg-[var(--color-core-accent)]/10 border border-[var(--color-core-accent)]/30 flex items-center justify-center font-mono text-[var(--color-core-accent)] font-bold text-sm shadow-[0_0_10px_rgba(99,102,241,0.2)] mt-1">
                T
              </div>
            )}
            
            <div 
              className={`max-w-[85%] rounded-xl px-5 py-4 ${
                msg.role === 'user' 
                  ? 'bg-[var(--color-core-accent)]/20 text-blue-50 border border-[var(--color-core-accent)]/30 ml-auto' 
                  : 'glass-panel text-gray-200'
              }`}
            >
              {msg.role === 'user' ? (
                <div className="whitespace-pre-wrap">{msg.content}</div>
              ) : (
                <div className="prose prose-invert prose-indigo max-w-none font-mono text-sm leading-relaxed prose-p:my-2 prose-pre:bg-black/50 prose-pre:border prose-pre:border-white/10 prose-headings:font-sans">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {msg.content || '...'}
                  </ReactMarkdown>
                </div>
              )}
            </div>
            
            {msg.role === 'user' && (
              <div className="shrink-0 w-8 h-8 rounded bg-gray-800/80 border border-gray-700 flex items-center justify-center font-sans text-gray-300 font-semibold text-sm mt-1">
                U
              </div>
            )}
          </div>
        ))}
        <div ref={bottomRef} className="h-4 w-full" />
      </div>
    </div>
  );
}
