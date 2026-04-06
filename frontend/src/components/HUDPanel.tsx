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
  trigger_at: number;
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
    } catch(e) {}
  };

  const habitStreaks = habits.reduce((acc, curr) => {
    if (curr.status === 'done') {
      acc[curr.habit] = (acc[curr.habit] || 0) + 1;
    }
    return acc;
  }, {} as Record<string, number>);

  // Fitness Calcs (assume fitness prop holds today's nutritional data instead of just workouts, or sum from props if we had them. Wait, App.tsx passes `fitness`. We should fetch /hud_data explicitly or rely on props)
  // App.tsx sends `fitness` but it's an array of workouts. `calories_today` and `protein_today` are sent by /hud_data! 
  // Let's grab them globally or calculate them if they exist in props.
  // Wait, I didn't add calories/protein to HUDPanelProps. I will just render with dummy 0s, or I can pull from global state if needed.
  // Actually, I can compute it if `fitness` actually contains meals.
  // Let's just fetch it locally to be safe.
  
  const [hudStats, setHudStats] = useState<any>({});
  useEffect(() => {
    fetch('http://localhost:8000/hud_data')
    .then(r => r.json())
    .then(d => setHudStats(d))
    .catch(() => {});
  }, [fitness, study, habits]);

  const calories = hudStats.calories_today || 0;
  const protein = hudStats.protein_today || 0;
  const calPct = Math.min((calories / 2000) * 100, 100);
  const proPct = Math.min((protein / 150) * 100, 100);

  // Group study by subject
  const studyData = study.reduce((acc, s) => {
     if(s.subject) acc[s.subject] = (acc[s.subject] || 0) + (s.duration_minutes || 0);
     return acc;
  }, {} as Record<string, number>);
  
  // Check if HPML logged in last 2 days
  const hasRecentHPML = study.some(s => s.subject === 'HPML' && (Date.now() - new Date(s.date).getTime()) < 2 * 24 * 60 * 60 * 1000);

  return (
    <div className="h-full border-l border-[var(--color-glass-border)] bg-[#050810] flex flex-col p-4 gap-4 overflow-y-auto custom-scrollbar text-sm font-sans">
      
      {/* 1. System Status */}
      <div className="glass-panel text-center rounded-xl p-4 border border-[var(--color-core-accent)]/20 shadow-[0_4px_20px_rgba(0,0,0,0.5)] relative">
        <div className={`absolute top-4 right-4 w-3 h-3 rounded-full ${hudStats.mood === 'low' ? 'bg-blue-500' : hudStats.mood === 'high' ? 'bg-green-500' : 'bg-amber-500'} shadow-[0_0_8px_currentColor]`} />
        
        <h2 className="text-gray-500 font-mono text-xs uppercase tracking-widest mb-1">Local Time</h2>
        <div className="text-3xl font-mono text-white mb-1 tracking-tighter">{time.toLocaleTimeString()}</div>
        <div className="text-emerald-500/80 font-mono text-xs">{time.toDateString()}</div>
      </div>

      {/* 2. Today's Schedule */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-indigo-400 uppercase flex items-center gap-2">
          <LucideCalendar size={12} /> Today's Schedule
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-white/5">
          {calendar && calendar.length > 0 ? (
            <div className="flex flex-col gap-2">
              {calendar.slice(0, 4).map((ev, i) => (
                   <div key={i} className="flex justify-between items-start border-b border-white/5 pb-2 last:border-0 last:pb-0">
                     <span className="text-gray-200">{ev.title}</span>
                     <span className="text-xs text-indigo-300 font-mono bg-indigo-500/10 px-1 rounded">
                       {ev.start ? new Date(ev.start).toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'}) : 'All Day'}
                     </span>
                   </div>
              ))}
            </div>
          ) : (
            <div className="text-gray-600 text-xs italic">No events today.</div>
          )}
        </div>
      </div>

      {/* 3. Inbox Pulse */}
      <div className="flex flex-col gap-2">
        <h3 className="font-mono text-xs text-blue-400 uppercase flex items-center gap-2">
          <Mail size={12} /> Inbox Pulse
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-blue-500/20 bg-blue-500/5">
          {inbox ? (
            <>
              <div className="flex justify-between items-center mb-2 border-b border-blue-500/20 pb-2">
                <span className="text-gray-300">Unread</span>
                <span className="bg-blue-500 text-white text-xs font-bold px-2 py-0.5 rounded-full">{inbox.unread_count}</span>
              </div>
              {inbox.urgent && (
                 <div className="text-xs text-blue-200">
                   <span className="font-bold block text-blue-300">{inbox.sender}</span>
                   <span className="truncate block opacity-80">{inbox.urgent}</span>
                 </div>
              )}
            </>
          ) : (
            <div className="text-gray-600 text-xs italic">Gmail not connected.</div>
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
          <div className="flex flex-col gap-3">
            <div>
              <div className="flex justify-between text-xs text-gray-300 mb-1">
                <span>Calories</span>
                <span>{calories} / 2000</span>
              </div>
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className="h-full bg-orange-400 transition-all" style={{width: `${calPct}%`}} />
              </div>
            </div>
            <div>
              <div className="flex justify-between text-xs text-gray-300 mb-1">
                <span>Protein</span>
                <span>{protein}g / 150g</span>
              </div>
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden">
                <div className={`h-full transition-all ${proPct < 50 ? 'bg-amber-500' : 'bg-orange-400'}`} style={{width: `${proPct}%`}} />
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 6. Study This Week */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-purple-400 uppercase flex items-center gap-2">
          <BookOpen size={12} /> Study This Week
        </h3>
        <div className="glass-panel p-3 rounded-xl border border-purple-500/20">
           <div className="flex flex-wrap gap-x-4 gap-y-2 text-sm text-gray-300">
             {Object.keys(studyData).length > 0 ? Object.entries(studyData).map(([sub, mins]) => (
                <span key={sub}>
                   {sub}: {Math.round(mins/60*10)/10} hrs
                </span>
             )) : <span className="text-gray-600 text-xs italic">No study logs this week.</span>}
           </div>
           {!hasRecentHPML && Object.keys(studyData).length > 0 && (
              <div className="mt-2 text-xs text-red-400 flex items-center gap-1">
                 <div className="w-1.5 h-1.5 rounded-full bg-red-400 animate-pulse" />
                 HPML not logged in 2+ days
              </div>
           )}
        </div>
      </div>

      {/* 7. Priority Queue */}
      <div className="flex flex-col gap-2 mt-2">
        <h3 className="font-mono text-xs text-[var(--color-core-accent)] uppercase flex items-center justify-between">
          <div className="flex items-center gap-2"><CheckCircle2 size={12} /> Priority Queue</div>
        </h3>
        <div className="glass-panel rounded-xl border border-white/5 p-1">
          {tasks.slice(0,5).map(task => (
            <div key={task.id} className="p-2 border-b border-white/5 last:border-0 flex gap-3 items-start group hover:bg-white/5 transition-colors">
              <button 
                onClick={() => onTamCommand?.(`complete_task ${task.id}`)}
                className="mt-1 w-4 h-4 rounded-sm border border-gray-500 shrink-0 flex items-center justify-center hover:border-emerald-400 hover:bg-emerald-400/20 transition-all cursor-pointer"
              >
                <CheckCircle2 size={10} className="opacity-0 group-hover:opacity-50 text-emerald-400" />
              </button>
              <div className="flex-1">
                <div className="text-gray-200">{task.task}</div>
              </div>
            </div>
          ))}
          {tasks.length === 0 && <div className="p-3 text-gray-600 text-xs italic">All clear.</div>}
        </div>
      </div>

      {/* 8. Core Memory Pulse */}
      <div className="flex flex-col gap-2 mt-2 mb-8">
        <h3 className="font-mono text-xs text-[var(--color-core-accent)] uppercase flex items-center gap-2">
          <Database size={12} /> Core Memory Pulse
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
