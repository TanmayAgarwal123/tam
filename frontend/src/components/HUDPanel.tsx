import { useState, useEffect } from 'react';
import { CheckCircle2, Activity, Clock, Database, Mail, Calendar as LucideCalendar, Dumbbell, BookOpen } from 'lucide-react';

export interface HabitData {
  habit: string;
  status: string;
  date: string;
}

export interface TaskData {
  id: string;
  task: string;
  priority: string;
  deadline?: string;
  completed?: boolean;
}

export interface ReminderData {
  id: string;
  message: string;
  trigger_at: number; // unix timestamp seconds
}

interface HUDPanelProps {
  tasks: TaskData[];
  habits: HabitData[];
  reminders: ReminderData[];
  lastMemoryUpdates: string[];
  inbox: any;
  calendar: any[];
  fitness: any[];
  study: any[];
  onTamCommand?: (cmd: string) => void;
}

export default function HUDPanel({ tasks, habits, reminders, lastMemoryUpdates, inbox, calendar, fitness, study, onTamCommand }: HUDPanelProps) {
  const [time, setTime] = useState(new Date());
  const [activeReminders, setActiveReminders] = useState<ReminderData[]>([]);

  useEffect(() => {
    setActiveReminders(reminders);
  }, [reminders]);

  useEffect(() => {
    const int = setInterval(() => {
      setTime(new Date());
      const now = Math.floor(Date.now() / 1000);
      setActiveReminders(prev => {
        const next = [...prev];
        next.forEach(rem => {
          if (rem.trigger_at <= now && rem.trigger_at > 0) {
            handleTriggerAudio(rem.message);
            rem.trigger_at = -1;
          }
        });
        return next;
      });
    }, 1000);
    return () => clearInterval(int);
  }, []);

  const handleTriggerAudio = async (text: string) => {
    try {
      const res = await fetch("http://localhost:8000/speak", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: "Reminder: " + text })
      });
      if(res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const audio = new Audio(url);
        audio.play();
      }
    } catch(e) {
      console.error(e);
    }
  };

  const habitStreaks = habits.reduce((acc, curr) => {
    if (curr.status === 'done') {
      acc[curr.habit] = (acc[curr.habit] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  return (
    <div className="h-full border-l border-[var(--color-glass-border)] bg-[#050810] flex flex-col p-4 gap-4 overflow-y-auto custom-scrollbar text-sm font-sans">
      
      {/* 1. System Status */}
      <div className="glass-panel text-center rounded-xl p-4 border border-[var(--color-core-accent)]/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)]">
        <h2 className="text-gray-500 font-mono text-xs uppercase tracking-widest mb-1">Local Time</h2>
        <div className="text-3xl font-mono text-white mb-1 tracking-tighter">{time.toLocaleTimeString()}</div>
        <div className="text-emerald-500/80 font-mono text-xs">{time.toDateString()}</div>
      </div>

      {reminders.length > 0 && (
        <div className="flex flex-col gap-2">
          {activeReminders.map(rem => {
            const now = Math.floor(Date.now() / 1000);
            const diff = rem.trigger_at > 0 ? rem.trigger_at - now : 0;
            const isFlashing = rem.trigger_at === -1;
            return (
              <div key={rem.id} className={`rounded-xl p-3 border backdrop-blur-sm transition-colors ${
                isFlashing ? 'bg-amber-500/20 border-amber-500 text-amber-50 animate-pulse' : 'glass-panel border-white/5 text-gray-200'
              }`}>
                <div className="flex justify-between items-center mb-1">
                  <span className="font-semibold"><Clock size={12} className="inline mr-2" />{rem.message}</span>
                  {rem.trigger_at > 0 && <span className="font-mono text-xs text-amber-400">T-{diff}s</span>}
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 2. Today's Schedule */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-indigo-400 uppercase flex items-center gap-2">
          <LucideCalendar size={12} /> Today's Schedule
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-white/5">
          {calendar && calendar.length > 0 ? (
            <div className="flex flex-col gap-2">
              {calendar.slice(0, 4).map((ev, i) => {
                 const timeStr = ev.start ? new Date(ev.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'All Day';
                 return (
                   <div key={i} className="flex justify-between items-start border-b border-white/5 pb-2 last:border-0 last:pb-0">
                     <span className="text-gray-200">{ev.title}</span>
                     <span className="text-xs text-indigo-300 font-mono bg-indigo-500/10 px-1 rounded">{timeStr}</span>
                   </div>
                 );
              })}
            </div>
          ) : (
            <div className="text-gray-600 text-xs italic">No events retrieved.</div>
          )}
        </div>
      </div>

      {/* 3. Inbox Pulse */}
      <div className="flex flex-col gap-2">
        <h3 className="font-mono text-xs text-blue-400 uppercase flex items-center gap-2">
          <Mail size={12} /> Inbox Pulse
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-blue-500/20 bg-blue-500/5">
          <div className="flex justify-between items-center mb-2 border-b border-blue-500/20 pb-2">
            <span className="text-gray-300">Unread</span>
            <span className="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">{inbox ? inbox.unread_count : 0}</span>
          </div>
          {inbox && inbox.urgent && (
             <div className="text-xs text-blue-200">
               <span className="font-bold block text-blue-300">{inbox.sender}</span>
               <span className="truncate block opacity-80">{inbox.urgent}</span>
             </div>
          )}
        </div>
      </div>

      {/* 4. Consistency HUD */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-emerald-400 uppercase flex items-center justify-between">
          <div className="flex items-center gap-2"><Activity size={12} /> Consistency HUD</div>
        </h3>
        {Object.entries(habitStreaks).map(([habitName, streak]) => (
          <div key={habitName} className="glass-panel p-3 rounded-xl border border-white/5 flex flex-col gap-2 hover:border-emerald-500/30 transition-colors group">
            <div className="flex justify-between items-center text-gray-300">
              <span className="capitalize">{habitName}</span>
              <div className="flex items-center gap-3">
                <span className="text-emerald-400 font-mono text-xs">Streak: {streak}</span>
                <button 
                  onClick={() => onTamCommand?.(`Log my ${habitName} habit as done for today.`)}
                  className="w-5 h-5 rounded bg-emerald-500/20 text-emerald-400 flex items-center justify-center hover:bg-emerald-500 hover:text-white transition-colors opacity-0 group-hover:opacity-100"
                >+</button>
              </div>
            </div>
            <div className="w-full h-1 bg-white/10 rounded-full overflow-hidden flex">
              {[...Array(Math.min(streak, 7))].map((_, i) => (
                <div key={i} className="h-full flex-1 bg-emerald-500 border-r border-black/50 last:border-0" />
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* 5. Fitness Today */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-orange-400 uppercase flex items-center gap-2">
          <Dumbbell size={12} /> Fitness Today
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-orange-500/20">
            {fitness && fitness.length > 0 ? (
               <div className="flex flex-col gap-1 text-sm text-gray-300">
                  {fitness.map((f, i) => (
                      <div key={i} className="flex justify-between border-b border-white/5 pb-1 last:border-0 last:pb-0">
                          <span className="capitalize text-orange-200">{f.type || 'Workout'}</span>
                          <span>{f.duration_minutes ? `${f.duration_minutes}m` : ''}</span>
                      </div>
                  ))}
               </div>
            ) : (
                <div className="text-gray-600 text-xs italic">Awaiting logs...</div>
            )}
        </div>
      </div>

      {/* 6. Study This Week */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-purple-400 uppercase flex items-center gap-2">
          <BookOpen size={12} /> Study / Focus
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-purple-500/20">
            {study && study.length > 0 ? (
               <div className="flex flex-col gap-1 text-sm text-gray-300">
                  {study.slice(-3).map((s, i) => (
                      <div key={i} className="flex justify-between border-b border-white/5 pb-1 last:border-0 last:pb-0">
                          <span className="truncate max-w-[70%]">{s.subject || 'Session'} <span className="opacity-50 text-xs ml-1">{s.difficulty || ''}</span></span>
                          <span className="text-purple-300">{s.duration_minutes ? `${s.duration_minutes}m` : ''}</span>
                      </div>
                  ))}
               </div>
            ) : (
                <div className="text-gray-600 text-xs italic">No focus blocks recorded yet.</div>
            )}
        </div>
      </div>

      {/* 7. Priority Queue */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-[var(--color-core-accent)] uppercase flex items-center justify-between">
          <div className="flex items-center gap-2"><CheckCircle2 size={12} /> Priority Queue</div>
        </h3>
        <div className="glass-panel rounded-xl border border-white/5 p-1">
          {tasks.map(task => (
            <div key={task.id} className="p-2 border-b border-white/5 last:border-0 flex gap-3 items-start group hover:bg-white/5 transition-colors">
              <button 
                onClick={() => onTamCommand?.(`Mark the task "${task.task}" as completed.`)}
                className="mt-1 w-4 h-4 rounded-sm border border-gray-500 shrink-0 flex items-center justify-center hover:border-emerald-400 hover:bg-emerald-400/20 transition-all cursor-pointer"
              >
                <CheckCircle2 size={10} className="opacity-0 group-hover:opacity-50 text-emerald-400" />
              </button>
              <div className="flex-1">
                <div className="text-gray-200">{task.task}</div>
                <div className="flex gap-2 items-center mt-1">
                  <span className={`text-[10px] px-1.5 py-0.5 rounded font-mono uppercase ${
                    task.priority === 'high' ? 'bg-amber-500/20 text-amber-500' :
                    task.priority === 'medium' ? 'bg-blue-500/20 text-blue-400' :
                    'bg-gray-500/20 text-gray-400'
                  }`}>{task.priority}</span>
                  {task.deadline && <span className="text-[10px] text-gray-500">{task.deadline}</span>}
                </div>
              </div>
            </div>
          ))}
          {tasks.length === 0 && <div className="p-3 text-gray-600 text-xs italic">All clear.</div>}
        </div>
      </div>

      {/* 8. Core Memory Pulse */}
      <div className="flex flex-col gap-2 mt-2 mb-8">
        <h3 className="font-mono text-xs text-[var(--color-core-accent)] uppercase flex items-center gap-2">
          <Database size={12} /> Core Memory
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-white/5">
          {lastMemoryUpdates.length === 0 ? (
            <div className="text-gray-600 text-xs italic">Memory stable.</div>
          ) : (
            <div className="flex flex-col gap-1">
              {lastMemoryUpdates.slice(-3).map((u, i) => (
                 <div key={i} className="text-xs text-indigo-400 font-mono opacity-80 border-l-2 border-indigo-500 pl-2">
                   [{new Date().toLocaleTimeString([], {hour:'2-digit', minute:'2-digit'})}] {u}
                 </div>
              ))}
            </div>
          )}
        </div>
      </div>

    </div>
  );
}
