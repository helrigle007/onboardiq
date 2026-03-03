import { useState, useEffect } from 'react';

interface StreamingTextProps {
  text: string;
  speed?: number;
  className?: string;
  onComplete?: () => void;
}

export function StreamingText({ text, speed = 20, className = '', onComplete }: StreamingTextProps) {
  const [displayed, setDisplayed] = useState('');
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    setDisplayed('');
    setIsDone(false);
    let i = 0;

    const interval = setInterval(() => {
      // Emit words rather than characters for more natural feel
      const nextSpace = text.indexOf(' ', i);
      const end = nextSpace === -1 ? text.length : nextSpace + 1;
      setDisplayed(text.slice(0, end));
      i = end;

      if (i >= text.length) {
        clearInterval(interval);
        setIsDone(true);
        onComplete?.();
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, onComplete]);

  return (
    <span className={className}>
      {displayed}
      {!isDone && <span className="inline-block w-0.5 h-4 bg-blue-500 animate-pulse ml-0.5 align-text-bottom" />}
    </span>
  );
}
