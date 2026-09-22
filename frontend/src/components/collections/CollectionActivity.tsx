import { Activity, Loader2 } from "lucide-react";

import type { CollectionActivityRecord } from "../../types";
import { activityEventLabel, formatRelativeTime } from "../../lib/collectionModel";
import type { CollectionFailure } from "../../lib/collectionModel";

interface CollectionActivityProps {
  vi: boolean;
  events: CollectionActivityRecord[];
  total: number;
  loading: boolean;
  failure: CollectionFailure | null;
  now: number;
}

/**
 * The rail's Activity tab: the operations this workspace actually recorded,
 * newest first. Nothing here is synthesised — an empty list means the
 * workspace recorded no events for the collection.
 */
export function CollectionActivity({ vi, events, total, loading, failure, now }: CollectionActivityProps) {
  return (
    <div className="collection-activity">
      <div className="collection-contents__heading">
        <h4 className="collection-contents__title">{vi ? `Hoạt động (${total})` : `Activity (${total})`}</h4>
      </div>

      {loading && (
        <p className="collection-contents__status" role="status">
          <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
          {vi ? "Đang đọc hoạt động…" : "Reading activity…"}
        </p>
      )}

      {failure && !loading && (
        <div className="workspace-alert workspace-alert--error" role="alert">
          <strong>{failure.title}</strong>
          <p>{failure.message}</p>
        </div>
      )}

      {!loading && !failure && events.length === 0 && (
        <div className="console-empty">
          <Activity aria-hidden="true" />
          <strong>{vi ? "Chưa ghi nhận hoạt động" : "No recorded activity"}</strong>
          <p>{vi ? "Workspace ghi lại các thao tác thật trên bộ sưu tập này." : "The workspace records the real operations performed on this collection."}</p>
        </div>
      )}

      {events.length > 0 && (
        <ol className="collection-activity__list" aria-label={vi ? "Hoạt động đã ghi nhận" : "Recorded activity"}>
          {events.map((event) => (
            <li key={event.activity_id} className="collection-activity__item">
              <span className="collection-activity__dot" aria-hidden="true" />
              <span className="collection-activity__body">
                <span className="collection-activity__label">{activityEventLabel(event.event_type, vi)}</span>
                <span className="collection-activity__time">
                  {formatRelativeTime(event.occurred_at, vi, now) ?? (vi ? "không rõ thời điểm" : "time not reported")}
                </span>
              </span>
            </li>
          ))}
        </ol>
      )}

      {total > events.length && (
        <p className="collection-contents__note">
          {vi ? `Hiển thị ${events.length}/${total} sự kiện.` : `Showing ${events.length} of ${total} events.`}
        </p>
      )}
    </div>
  );
}
