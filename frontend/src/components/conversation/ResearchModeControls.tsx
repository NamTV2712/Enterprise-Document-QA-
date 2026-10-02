import { useLocale } from "../../lib/i18n";
import { researchCopy } from "./researchCopy";
import type { useConversationAgent } from "./useConversationAgent";
import "./research.css";

export function ResearchModeControls({ agent, busy, onConnect }: {
  agent: ReturnType<typeof useConversationAgent>; busy: boolean; onConnect: () => void;
}) {
  const { locale } = useLocale();
  const copy = researchCopy[locale];
  const connected = agent.model.session.status === "connected";
  return <div className="research-mode-controls">
    <div role="group" aria-label={copy.mode} className="research-mode-picker">
      {(["quick", "deep"] as const).map((mode) => <button key={mode} type="button" aria-pressed={agent.mode === mode}
        disabled={busy} onClick={() => agent.setMode(mode)}>{copy[mode]}</button>)}
    </div>
    <p className={agent.mode === "quick" ? "sr-only" : "research-mode-hint"}>{agent.mode === "quick" ? copy.quickHint : copy.deepHint}</p>
    {agent.mode === "deep" && <>
      {!connected ? <button type="button" className="secondary-action-button" onClick={onConnect}>{copy.connect}</button> : <>
        {!agent.model.session.canExecute || agent.readOnly ? <p>{copy.readOnly}</p>
          : agent.model.session.decisionProviderAvailable ? <label className="research-consent"><input type="checkbox"
            checked={agent.consent} disabled={busy} onChange={(event) => agent.setConsent(event.target.checked)} />{copy.consent}</label>
            : <p className="research-mode-hint">{copy.providerUnavailable}</p>}
        <button type="button" className="research-text-action" onClick={() => agent.model.session.disconnect()} disabled={busy}>
          {locale === "vi" ? "Ngắt kết nối" : "Disconnect"}</button>
      </>}
      {(agent.model.createError !== null || agent.linkError) && <p role="alert">{copy.error}</p>}
    </>}
  </div>;
}
