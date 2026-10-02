import { useLocale } from "../../lib/i18n";
import { LocalConnection } from "../operations/OperationalShared";
import { ModalDialog } from "../ui/ModalDialog";
import { researchCopy } from "./researchCopy";

export function ResearchConnection({ onClose }: { onClose: () => void }) {
  const { locale } = useLocale();
  const copy = researchCopy[locale];
  return <ModalDialog open onClose={onClose} labelledBy="research-connect-title" className="agent-dialog console-card">
    <h2 id="research-connect-title">{copy.connect}</h2>
    <LocalConnection />
    <button type="button" className="secondary-action-button" onClick={onClose}>{copy.close}</button>
  </ModalDialog>;
}
