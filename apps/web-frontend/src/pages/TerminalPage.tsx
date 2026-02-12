/**
 * Terminal Page
 * Dedicated page for terminal access
 */

import { useState } from 'react';
import TerminalComponent from '../components/Terminal';

export function TerminalPage() {
  const [sessionId] = useState(() => `terminal-${Date.now()}`);

  return (
    <div className="h-screen w-full bg-gray-900 p-4">
      <div className="h-full max-w-7xl mx-auto">
        <TerminalComponent
          id={sessionId}
          sessionId={sessionId}
          title="Terminal"
          isActive={true}
        />
      </div>
    </div>
  );
}

export default TerminalPage;
