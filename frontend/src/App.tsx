import { useState, useEffect, useRef, useCallback } from 'react';
import { v4 as uuidv4 } from 'uuid';
import ChatWindow from './components/ChatWindow';
import InputBar from './components/InputBar';
import StatusBar from './components/StatusBar';
import HUDPanel, { type HabitData, type TaskData, type ReminderData } from './components/HUDPanel';
import VoiceInterface from './components/VoiceInterface';
import { useVoiceMode } from './hooks/useVoiceMode';

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

let currentAudio: HTMLAudioElement | null = null;

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [sessionId, setSessionId] = useState<string>('');
  const [isThinking, setIsThinking] = useState(false);
  const [isMuted, setIsMuted] = useState(false);
  
  // HUD States
  const [tasks, setTasks] = useState<TaskData[]>([]);
  const [habits, setHabits] = useState<HabitData[]>([]);
  const [reminders, setReminders] = useState<ReminderData[]>([]);
  const [lastMemoryUpdates, setLastMemoryUpdates] = useState<string[]>([]);
  const [inbox, setInbox] = useState<any>(null);
  const [calendar, setCalendar] = useState<any[]>([]);
  const [fitness, setFitness] = useState<any[]>([]);
  const [study, setStudy] = useState<any[]>([]);
  const [mood, setMood] = useState<string>('bg-green-500');
  
  // Voice Mode Loop States
  const [voiceModeActive, setVoiceModeActive] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  
  const voiceModeRef = useRef(voiceModeActive);
  const lastSpokenMessageId = useRef<string | null>(null);

  useEffect(() => {
    voiceModeRef.current = voiceModeActive;
  }, [voiceModeActive]);

  useEffect(() => {
    let currentSession = localStorage.getItem('tam_session_id');
    if (!currentSession) {
      currentSession = uuidv4();
      localStorage.setItem('tam_session_id', currentSession);
    }
    setSessionId(currentSession);

    fetch('http://localhost:8000/hud_data')
      .then(res => res.json())
      .then(data => {
        setTasks(data.tasks || []);
        setHabits(data.habits || []);
        setReminders(data.reminders || []);
        setFitness(data.fitness || []);
        setStudy(data.study || []);
      })
      .catch(e => console.error("HUD fetch error", e));

    fetch('http://localhost:8000/dashboard_pulse')
      .then(res => res.json())
      .then(data => {
        setInbox(data.inbox);
        setCalendar(data.calendar);
      })
      .catch(e => console.error("Pulse fetch", e));
  }, []);

  const handleSendMessage = async (content: string) => {
    if (!content.trim() || !sessionId) return;

    const userMessage: Message = { id: uuidv4(), role: 'user', content };
    setMessages(prev => [...prev, userMessage]);
    setIsThinking(true);

    const assistantMessageId = uuidv4();
    setMessages(prev => [...prev, { id: assistantMessageId, role: 'assistant', content: '' }]);

    try {
      const response = await fetch('http://localhost:8000/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: content })
      });

      if (!response.ok) throw new Error('Network response error');

      const reader = response.body?.pipeThrough(new TextDecoderStream()).getReader();
      if (!reader) return;

      while (true) {
        const { value, done } = await reader.read();
        if (done) break;

        const lines = value.split('\n');
        let currentEvent = 'message';

        for (let i = 0; i < lines.length; i++) {
          const line = lines[i];
          if (line.startsWith('event: ')) {
            currentEvent = line.replace('event: ', '').trim();
          } else if (line.startsWith('data: ')) {
            const currentDataStr = line.replace('data: ', '').trim();
            if(!currentDataStr) continue;

            try {
              const data = JSON.parse(currentDataStr);

              if (currentEvent === 'message') {
                if (data.chunk === '[DONE]') {
                  setIsThinking(false);
                } else if (data.error) {
                  console.error("Tam error:", data.error);
                  setIsThinking(false);
                } else if (data.chunk) {
                  setMessages(prev => prev.map(msg => 
                    msg.id === assistantMessageId 
                      ? { ...msg, content: msg.content + data.chunk }
                      : msg
                  ));
                }
              } else if (currentEvent === 'hud_update') {
                if (data.type === 'habit') {
                  setHabits(prev => {
                    const exist = prev.find(h => h.habit === data.habit);
                    if(exist) {
                        return prev.map(h => h.habit === data.habit ? { ...h, status: 'done', date: new Date().toISOString() } : h);
                    }
                    return [...prev, { habit: data.habit, status: 'done', date: new Date().toISOString() }];
                  });
                } else if (data.type === 'task') {
                  setTasks(prev => [...prev, data.task]);
                } else if (data.type === 'task_completed') {
                  setTasks(prev => prev.filter(t => t.id !== data.task_id));
                } else if (data.type === 'reminder') {
                  setReminders(prev => [...prev, data.reminder]);
                } else if (data.type === 'memory') {
                  setLastMemoryUpdates(prev => [...prev, data.section]);
                  if (data.section.toLowerCase().includes('mood:') || data.section.toLowerCase().includes('overwhelm') || data.section.toLowerCase().includes('tired') || data.section.toLowerCase().includes('low')) {
                     setMood('bg-amber-500');
                  }
                } else if (data.type === 'fitness' || data.type === 'fitness_meal') {
                  setFitness(prev => [...prev, data.workout || data.meal].slice(-5));
                } else if (data.type === 'study') {
                  setStudy(prev => [...prev, data.study].slice(-5));
                }
              }
            } catch (e) {
              console.error("JSON parse error", e);
            }
          }
        }
      }
    } catch (error) {
      console.error("Send failed", error);
      setIsThinking(false);
    }
  };

  const applyVocabFix = (transcript: string) => {
    const corrections: Record<string, string> = {
      'tom': 'Tam',
      'Tom': 'Tam', 
      'time': 'Tam',
      'tan': 'Tam',
      'tam tam': 'Tam',
      'gym': 'gym',
      'divyanshi': 'Divyanshi',
      'hpml': 'HPML',
      'columbia': 'Columbia',
    };
    
    let fixed = transcript;
    Object.entries(corrections).forEach(([wrong, right]) => {
      const regex = new RegExp(`\\b${wrong}\\b`, 'gi');
      fixed = fixed.replace(regex, right);
    });
    return fixed;
  };

  const isSpeakingRef = useRef(false);
  const lastSpeakerEndRef = useRef(0);

  const handleBargeIn = useCallback(() => {
    if (currentAudio) {
        currentAudio.pause();
        currentAudio.currentTime = 0;
        currentAudio = null;
        isSpeakingRef.current = false;
        lastSpeakerEndRef.current = Date.now();
        setIsSpeaking(false);
    }
  }, []);

  const handleTranscript = useCallback((text: string) => {
    const corrected = applyVocabFix(text);
    const lower = corrected.toLowerCase();
    const hasWakeWord = lower.includes('tam') || lower.includes('tom') || lower.includes('time') || lower.includes('tan') || lower.includes('stop');

    // MUTE WINDOW: While Tam is speaking, or within 2.5 seconds of her finishing (to allow echo 'isFinal' to flush out)
    const isEchoWindow = isSpeakingRef.current || (Date.now() - lastSpeakerEndRef.current < 2500);

    if (corrected.trim()) {
        if (isEchoWindow) {
             // In the echo window, we MUST require the wake word to prevent the infinite feedback loop!
             if (hasWakeWord) {
                 handleSendMessage(corrected);
             }
        } else {
             // OUTSIDE echo window, the mic is naturally open for normal fluid conversational replies!
             handleSendMessage(corrected);
        }
    }
  }, [sessionId]);

  const submitToSpeak = async (text: string) => {
    if (!voiceModeActive) return;
    try {
      const resp = await fetch('http://localhost:8000/speak', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ text: text.replace(/\*\[TAM ACTION\].*\*/g, '').replace(/\[TAM ACTION\].*/g, '').trim() })
      });
      if (!resp.ok) throw new Error('TTS failed');
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      
      if (currentAudio) {
          currentAudio.pause();
          currentAudio.currentTime = 0;
          currentAudio = null;
      }
      
      const audio = new Audio(url);
      currentAudio = audio;
      isSpeakingRef.current = true;
      setIsSpeaking(true);
      
      audio.onended = () => {
        isSpeakingRef.current = false;
        lastSpeakerEndRef.current = Date.now();
        setIsSpeaking(false);
        currentAudio = null;
      };
      
      audio.play();
    } catch (e) {
      console.error(e);
      isSpeakingRef.current = false;
      setIsSpeaking(false);
    }
  };

  const { isListening, startListening, stopListening } = useVoiceMode(handleTranscript, handleBargeIn, voiceModeActive);

  useEffect(() => {
    const eventsSource = new EventSource('http://localhost:8000/events');
    eventsSource.onmessage = (event) => {
        try {
            const data = JSON.parse(event.data);
            if (data.autoSpeak && data.text) {
                submitToSpeak(data.text);
            }
        } catch (e) {}
    };
    return () => eventsSource.close();
  }, [voiceModeActive]);

  const toggleVoiceMode = () => {
    const nextState = !voiceModeActive;
    setVoiceModeActive(nextState);
    if (nextState) {
       startListening();
    } else {
       stopListening();
       if (currentAudio) {
           currentAudio.pause();
           currentAudio = null;
           setIsSpeaking(false);
       }
    }
  };


  useEffect(() => {
    if (isThinking || messages.length === 0) return;
    const lastMessage = messages[messages.length - 1];
    if (lastMessage.role === 'assistant' && lastMessage.content && lastSpokenMessageId.current !== lastMessage.id) {
      lastSpokenMessageId.current = lastMessage.id;
      
      const cleanContent = lastMessage.content.replace(/\*\[TAM ACTION\].*\*/g, '').trim();
      if (cleanContent && !cleanContent.includes("TAM hit tool limit")) {
         submitToSpeak(lastMessage.content);
      }
    }
  }, [messages, isThinking, isMuted]);

  return (
    <div className="flex h-screen overflow-hidden bg-[var(--color-core-bg)] text-gray-200 font-sans w-full flex-row">
      <div className="w-[60%] flex flex-col relative h-full flex-1 min-w-0">
        <StatusBar 
          isThinking={isThinking} 
          lastMemoryUpdate={lastMemoryUpdates.length ? "Recently updated" : "Stable"} 
          isMuted={isMuted}
          onToggleMute={() => setIsMuted(!isMuted)}
          voiceModeActive={voiceModeActive}
          onToggleVoiceMode={toggleVoiceMode}
          moodColor={mood}
        />
        
        <main className="flex-1 overflow-hidden relative">
          <ChatWindow messages={messages} />
        </main>

        <div className="p-4 border-t border-[var(--color-glass-border)] bg-[var(--color-core-bg)]/90 backdrop-blur-md z-10 shrink-0">
          <div className="max-w-4xl mx-auto">
            {voiceModeActive ? (
              <VoiceInterface 
                isListening={isListening} 
                isThinking={isThinking} 
                isSpeaking={isSpeaking} 
                onExit={toggleVoiceMode} 
              />
            ) : (
              <InputBar onSendMessage={handleSendMessage} isThinking={isThinking} />
            )}
          </div>
        </div>
      </div>

      <div className="w-[40%] h-full shrink-0">
        <HUDPanel 
          tasks={tasks} 
          habits={habits} 
          reminders={reminders} 
          lastMemoryUpdates={lastMemoryUpdates}
          inbox={inbox}
          calendar={calendar}
          fitness={fitness}
          study={study}
          onTamCommand={handleSendMessage} 
        />
      </div>
    </div>
  );
}
