import { useState, useEffect } from 'react';

interface StreamingTextProps {
  text: string;
  speed?: number;
  className?: string;
  onComplete?: () => void;
}

function StreamingTextInner({ text, speed = 20, className = '', onComplete }: StreamingTextProps) {
  const [displayed, setDisplayed] = useState('');
  const [isDone, setIsDone] = useState(false);

  useEffect(() => {
    let i = 0;

    const interval = setInterval(() => {
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

export function StreamingText(props: StreamingTextProps) {
  // Use key to force remount when text changes, resetting state cleanly
  return <StreamingTextInner key={props.text} {...props} />;
}
