import {StrictMode} from 'react';
import {createRoot} from 'react-dom/client';
import App from './App.tsx';
import {ErrorBoundary} from './components/ErrorBoundary.tsx';
import {LocaleProvider} from './lib/i18n.tsx';
import {LocalWorkspaceSessionProvider} from './lib/localWorkspaceSession.tsx';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ErrorBoundary>
      <LocaleProvider>
        <LocalWorkspaceSessionProvider>
          <App />
        </LocalWorkspaceSessionProvider>
      </LocaleProvider>
    </ErrorBoundary>
  </StrictMode>,
);
