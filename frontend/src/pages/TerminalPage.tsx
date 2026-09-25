import { ExternalLink, RotateCw } from 'lucide-react';
import { useState } from 'react';

const terminalUrl = '/terminal/';

export function TerminalPage() {
  const [frameKey, setFrameKey] = useState(0);

  return (
    <div className="page terminalPage">
      <header className="pageHeader">
        <div>
          <h1>Terminal</h1>
          <p>SSH login to the server. Sign in with your Ubuntu username and password.</p>
        </div>
        <div className="rowActions">
          <button className="button secondary" type="button" onClick={() => setFrameKey((key) => key + 1)}>
            <RotateCw size={16} aria-hidden="true" />
            New session
          </button>
          <a className="button primary" href={terminalUrl} target="_blank" rel="noreferrer">
            <ExternalLink size={16} aria-hidden="true" />
            Open in tab
          </a>
        </div>
      </header>

      <div className="terminalFrameWrap">
        <iframe
          key={frameKey}
          className="terminalFrame"
          src={terminalUrl}
          title="Server terminal"
          allow="clipboard-read; clipboard-write"
        />
      </div>
    </div>
  );
}
