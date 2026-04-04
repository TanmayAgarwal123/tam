import { useState, useRef, useCallback, useEffect } from 'react';

export const useVoiceMode = (
  onTranscript: (text: string) => void,
  onBargeIn: () => void,
  voiceModeActive: boolean
) => {
  const [isListening, setIsListening] = useState(false);
  const recognitionRef = useRef<any>(null);

  const startListening = useCallback(() => {
    const SpeechRecognition = window.SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      console.warn("Speech API not supported");
      return;
    }

    if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (e) { }
    }

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
      setIsListening(true);
    };

    recognition.onresult = (event: any) => {
      let finalTranscript = '';
      let interimTranscript = '';
      
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const segment = event.results[i][0].transcript;
        if (event.results[i].isFinal) {
          finalTranscript += segment + ' ';
        } else {
          interimTranscript += segment;
        }
      }
        
      const currentText = (finalTranscript + interimTranscript).toLowerCase();
      // Only barge-in (stop Tam from speaking) if the transcript specifically contains the Wakeword
      if (currentText.includes('tam') || currentText.includes('tom') || currentText.includes('time') || currentText.includes('tan') || currentText.includes('stop')) {
        onBargeIn();
      }
        
      if (finalTranscript.trim()) {
        onTranscript(finalTranscript.trim());
      }
    };

    recognition.onerror = (event: any) => {
      console.error("Speech recognition error", event.error);
    };

    recognition.onend = () => {
      setIsListening(false);
    };
    
    try {
        recognition.start();
        recognitionRef.current = recognition;
    } catch(e) {
        console.error("Failed to start listening", e);
    }
  }, [onTranscript, onBargeIn]);

  useEffect(() => {
    // If voice mode is on, but we are not listening, restart instantly!
    // This perfectly handles 'no-speech' timeouts natively looping
    if (voiceModeActive && !isListening) {
       // slight delay to prevent absolute thread blocking on endless loop
       const t = setTimeout(() => {
           startListening();
       }, 200);
       return () => clearTimeout(t);
    }
  }, [voiceModeActive, isListening, startListening]);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
        try { recognitionRef.current.abort(); } catch (e) { }
    }
    setIsListening(false);
  }, []);

  return { isListening, startListening, stopListening };
};
