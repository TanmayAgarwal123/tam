import { useState, useRef, useCallback, useEffect } from 'react';

export const useVoiceMode = (
  onTranscript: (text: string) => void,
  onBargeIn: () => void,
  voiceModeActive: boolean
) => {
  const [isListening, setIsListening] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const audioCtxRef = useRef<AudioContext | null>(null);
  const silenceStartRef = useRef<number | null>(null);
  const animFrameRef = useRef<number | null>(null);

  const cleanup = useCallback(() => {
    if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach(t => t.stop());
    }
    if (audioCtxRef.current) {
      audioCtxRef.current.close().catch(() => {});
    }
    mediaRecorderRef.current = null;
    streamRef.current = null;
    audioCtxRef.current = null;
    setIsListening(false);
  }, []);

  const stopListening = useCallback(() => {
    cleanup();
  }, [cleanup]);

  const startListening = useCallback(async () => {
    if (!voiceModeActive) return;
    cleanup();
    
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;
      
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      
      const audioChunks: Blob[] = [];
      mediaRecorder.ondataavailable = (e) => {
        if (e.data.size > 0) audioChunks.push(e.data);
      };
      
      mediaRecorder.onstop = async () => {
        setIsListening(false);
        const audioBlob = new Blob(audioChunks, { type: 'audio/webm' });
        
        if (audioBlob.size > 1000) {  // Only run transcribe if an actual sample exists
            const formData = new FormData();
            formData.append('audio', audioBlob, 'recording.webm');
            
            try {
                const res = await fetch('http://localhost:8000/transcribe', {
                   method: 'POST',
                   body: formData
                });
                if (res.ok) {
                   const data = await res.json();
                   if (data.transcript && data.transcript.trim()) {
                       const fixes: Record<string, string> = {
                         '\\btom\\b': 'Tam', '\\bTom\\b': 'Tam',
                         '\\btan\\b': 'Tam', '\\btime\\b': 'Tam',
                         '\\bhpml\\b': 'HPML', '\\bcuda\\b': 'CUDA',
                         '\\bcolumbia\\b': 'Columbia', '\\banthropics\\b': 'Anthropic',
                         '\\bdivyanshi\\b': 'Divyanshi',
                       };
                       let fixed = data.transcript.trim();
                       Object.entries(fixes).forEach(([pattern, replacement]) => {
                         fixed = fixed.replace(new RegExp(pattern, 'gi'), replacement);
                       });
                       onTranscript(fixed);
                   }
                }
            } catch (err) {
                console.error("Transcribe failed", err);
            }
        }
        
        // Loop back if voice mode is still active
        if (voiceModeActive) {
            setTimeout(() => {
               if(voiceModeActive) startListening();
            }, 500);
        }
      };

      mediaRecorder.onstart = () => {
        onBargeIn(); // Kill any playing audio the moment we start
        setIsListening(true);
        
        const audioCtx = new AudioContext();
        audioCtxRef.current = audioCtx;
        const source = audioCtx.createMediaStreamSource(stream);
        const analyser = audioCtx.createAnalyser();
        analyser.fftSize = 512;
        source.connect(analyser);
        
        const buffer = new Uint8Array(analyser.fftSize);
        silenceStartRef.current = null;
        const SILENCE_THRESHOLD = 5; // Adjust based on env noise
        const SILENCE_DURATION = 1500; // 1.5 seconds silence stops record
        
        const checkSilence = () => {
          if (!mediaRecorderRef.current || mediaRecorderRef.current.state === 'inactive') return;
          
          analyser.getByteTimeDomainData(buffer);
          let rawVolume = 0;
          for(let i=0; i<buffer.length; i++) {
              let v = Math.abs(buffer[i] - 128);
              if (v > rawVolume) rawVolume = v;
          }
          const volume = rawVolume;

          if(volume < SILENCE_THRESHOLD) {
            if(!silenceStartRef.current) {
                silenceStartRef.current = Date.now();
            } else if(Date.now() - silenceStartRef.current > SILENCE_DURATION) {
                mediaRecorderRef.current.stop();
                return;
            }
          } else {
            silenceStartRef.current = null;
          }
          
          animFrameRef.current = requestAnimationFrame(checkSilence);
        };
        
        checkSilence();
      };
      
      mediaRecorder.start();
      
    } catch (e) {
      console.error("Mic access denied or error", e);
      setIsListening(false);
    }
  }, [voiceModeActive, cleanup, onTranscript, onBargeIn]);

  useEffect(() => {
    if (voiceModeActive && !isListening && !mediaRecorderRef.current) {
        startListening();
    } else if (!voiceModeActive) {
        stopListening();
    }
    
    return () => {
        if (!voiceModeActive) stopListening();
    };
  }, [voiceModeActive]);

  return { isListening, startListening, stopListening };
};
