import React, { useMemo } from 'react';

export const StreamingText: React.FC<{ content: string }> = ({ content }) => {
  // 按换行分割，渲染流式文本
  const lines = useMemo(() => content.split('\n'), [content]);

  return (
    <>
      {lines.map((line, i) => (
        <React.Fragment key={i}>
          {i > 0 && <br />}
          <span className="animate-fade-in">{line}</span>
        </React.Fragment>
      ))}
    </>
  );
};
