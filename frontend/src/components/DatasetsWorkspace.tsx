import { useEffect, useMemo, useRef, useState } from "react";
import {
  Archive,
  BarChart3,
  CheckCircle2,
  ChevronRight,
  CircleSlash2,
  Database,
  FileQuestion,
  RefreshCw,
  RotateCcw,
  ShieldCheck,
  TriangleAlert,
} from "lucide-react";

import { ApiError, getDataset, getDatasets } from "../lib/api";
import { useLocale } from "../lib/i18n";
import { describeRequestError } from "../lib/requestError";
import type {
  DatasetAvailability,
  DatasetCount,
  DatasetDetail,
  DatasetKind,
  DatasetRegistryId,
  DatasetSummary,
} from "../types";

type KindFilter = "all" | DatasetKind;

const DATASET_ORDER: DatasetRegistryId[] = ["serving-corpus", "evaluation-test-set"];

function kindLabel(kind: DatasetKind, vi: boolean): string {
  return kind === "corpus" ? (vi ? "Corpus phục vụ" : "Serving corpus") : (vi ? "Bộ đánh giá" : "Evaluation set");
}

function availabilityLabel(status: DatasetAvailability, vi: boolean): string {
  if (status === "available") return vi ? "Khả dụng" : "Available";
  if (status === "degraded") return vi ? "Suy giảm" : "Degraded";
  return vi ? "Không khả dụng" : "Unavailable";
}

function DatasetStatePill({ status, vi }: { status: DatasetAvailability; vi: boolean }) {
  const Icon = status === "available" ? CheckCircle2 : status === "degraded" ? TriangleAlert : CircleSlash2;
  return <span className={`registry-state registry-state--${status}`}><Icon aria-hidden="true" />{availabilityLabel(status, vi)}</span>;
}

function valueOrUnknown(value: string | number | null | undefined, vi: boolean): string {
  return value === null || value === undefined || value === "" ? (vi ? "Chưa xác định" : "Unknown") : String(value);
}

function CountList({ items, empty, label }: { items: DatasetCount[]; empty: string; label: string }) {
  if (items.length === 0) return <p className="registry-muted">{empty}</p>;
  return <ul className="registry-count-list" aria-label={label}>{items.map((item) => <li key={item.key}><span>{item.key}</span><strong>{item.count.toLocaleString()}</strong></li>)}</ul>;
}

function DatasetCoverageView({ detail, vi }: { detail: DatasetDetail; vi: boolean }) {
  const coverage = detail.coverage;
  if (!coverage) return <div className="registry-empty-inline"><FileQuestion aria-hidden="true" /><span>{vi ? "Coverage không khả dụng cho dataset này." : "Coverage is unavailable for this dataset."}</span></div>;

  if (coverage.kind === "corpus") {
    const yearValue = coverage.filing_years.availability === "recorded"
      ? coverage.filing_years.earliest === coverage.filing_years.latest
        ? valueOrUnknown(coverage.filing_years.earliest, vi)
        : `${valueOrUnknown(coverage.filing_years.earliest, vi)}–${valueOrUnknown(coverage.filing_years.latest, vi)}`
      : vi ? "Chưa xác định" : "Unknown";
    return (
      <div className="registry-coverage">
        <div className="registry-metric-grid">
          <div><strong>{coverage.documents.toLocaleString()}</strong><span>{vi ? "tài liệu" : "documents"}</span></div>
          <div><strong>{coverage.companies.toLocaleString()}</strong><span>{vi ? "công ty" : "companies"}</span></div>
          <div><strong>{coverage.chunks.toLocaleString()}</strong><span>chunks</span></div>
          <div><strong>{yearValue}</strong><span>{vi ? "năm filing" : "filing years"}</span></div>
        </div>
        <section><h3>{vi ? "Coverage section" : "Section coverage"}</h3><CountList items={coverage.sections} empty={vi ? "Không có section nào được ghi nhận." : "No sections were recorded."} label={vi ? "Số lượng section" : "Section counts"} /></section>
        <section><h3>{vi ? "Phạm vi công ty cấu hình" : "Configured company scope"}</h3><p className="registry-muted">{coverage.configured_companies_with_documents.length > 0 ? coverage.configured_companies_with_documents.join(", ") : (vi ? "Không có công ty cấu hình nào có tài liệu." : "No configured companies have documents.")}</p>{coverage.configured_companies_without_documents.length > 0 && <p className="registry-warning-copy">{vi ? "Không có tài liệu:" : "Without documents:"} {coverage.configured_companies_without_documents.join(", ")}</p>}</section>
        {coverage.filing_years.documents_without_value > 0 && <p className="registry-warning-copy">{coverage.filing_years.documents_without_value} {vi ? "tài liệu không có năm filing được ghi nhận." : "documents have no recorded filing year."}</p>}
      </div>
    );
  }

  return (
    <div className="registry-coverage">
      <div className="registry-metric-grid">
        <div><strong>{coverage.cases.toLocaleString()}</strong><span>{vi ? "case" : "cases"}</span></div>
        <div><strong>{coverage.categories.length.toLocaleString()}</strong><span>{vi ? "category" : "categories"}</span></div>
        <div><strong>{coverage.tickers.length.toLocaleString()}</strong><span>tickers</span></div>
        <div><strong>{coverage.sections.length.toLocaleString()}</strong><span>sections</span></div>
      </div>
      <div className="registry-coverage-columns">
        <section><h3>{vi ? "Category" : "Categories"}</h3><CountList items={coverage.categories} empty={vi ? "Không có category." : "No categories recorded."} label={vi ? "Số lượng category" : "Category counts"} /></section>
        <section><h3>{vi ? "Priority" : "Priorities"}</h3><CountList items={coverage.priorities} empty={vi ? "Không có priority." : "No priorities recorded."} label={vi ? "Số lượng priority" : "Priority counts"} /></section>
      </div>
      <section><h3>{vi ? "Ticker và section được ghi nhận" : "Recorded tickers and sections"}</h3><div className="registry-chip-list">{coverage.tickers.map((ticker) => <span key={ticker}>{ticker}</span>)}{coverage.sections.map((section) => <span key={section}>{section}</span>)}{coverage.tickers.length === 0 && coverage.sections.length === 0 && <span>{vi ? "Không có" : "None recorded"}</span>}</div></section>
      <p className="registry-muted">{vi ? "Registry chỉ công bố aggregate; câu hỏi và ground truth không được gửi đến trình duyệt." : "Only aggregate coverage is published; questions and ground truth are not sent to the browser."}</p>
    </div>
  );
}

export function DatasetsWorkspace() {
  const { locale } = useLocale();
  const vi = locale === "vi";
  const [kindFilter, setKindFilter] = useState<KindFilter>("all");
  const [items, setItems] = useState<DatasetSummary[]>([]);
  const [selectedId, setSelectedId] = useState<DatasetRegistryId | null>(null);
  const [detail, setDetail] = useState<DatasetDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [detailLoading, setDetailLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const listLifetime = useRef(0);
  const detailLifetime = useRef(0);

  useEffect(() => {
    const lifetime = ++listLifetime.current;
    const controller = new AbortController();
    setLoading(true);
    setError(null);
    void getDatasets(kindFilter === "all" ? null : kindFilter, controller.signal)
      .then((response) => {
        if (controller.signal.aborted || lifetime !== listLifetime.current) return;
        const ordered = [...response.items].sort((left, right) => DATASET_ORDER.indexOf(left.id) - DATASET_ORDER.indexOf(right.id));
        setItems(ordered);
        setSelectedId((current) => ordered.some((item) => item.id === current) ? current : ordered[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || lifetime !== listLifetime.current) return;
        setItems([]);
        setSelectedId(null);
        setError(describeRequestError(reason, vi ? "Không thể tải registry dataset." : "Could not load the dataset registry.", vi ? "vi" : "en").message);
      })
      .finally(() => {
        if (!controller.signal.aborted && lifetime === listLifetime.current) setLoading(false);
      });
    return () => controller.abort();
  }, [kindFilter, refreshVersion, vi]);

  useEffect(() => {
    detailLifetime.current += 1;
    setDetail(null);
    setDetailError(null);
    if (!selectedId) {
      setDetailLoading(false);
      return;
    }
    const datasetId = selectedId;
    const lifetime = detailLifetime.current;
    const controller = new AbortController();
    setDetailLoading(true);
    void getDataset(datasetId, controller.signal)
      .then((response) => {
        if (controller.signal.aborted || lifetime !== detailLifetime.current || response.id !== datasetId) return;
        setDetail(response);
      })
      .catch((reason: unknown) => {
        if (controller.signal.aborted || lifetime !== detailLifetime.current) return;
        const message = reason instanceof ApiError && reason.status === 404
          ? (vi ? "Dataset này không còn tồn tại trong registry. Hãy làm mới danh sách." : "This dataset is no longer present in the registry. Refresh the list.")
          : describeRequestError(reason, vi ? "Không thể tải chi tiết dataset." : "Could not load dataset details.", vi ? "vi" : "en").message;
        setDetailError(message);
      })
      .finally(() => {
        if (!controller.signal.aborted && lifetime === detailLifetime.current) setDetailLoading(false);
      });
    return () => controller.abort();
  }, [selectedId, vi, refreshVersion]);

  useEffect(() => () => {
    listLifetime.current += 1;
    detailLifetime.current += 1;
  }, []);

  const selectedSummary = useMemo(() => items.find((item) => item.id === selectedId) ?? null, [items, selectedId]);
  const availableCount = items.filter((item) => item.availability === "available").length;
  const degradedCount = items.filter((item) => item.availability === "degraded").length;
  const unknownRecords = items.filter((item) => item.record_count === null).length;

  return (
    <section className="workspace-page workspace-page--wide registry-workspace console-view-enter" aria-labelledby="datasets-title">
      <header className="console-page-header registry-page-header">
        <div className="console-page-header__identity">
          <div className="console-page-header__icon"><Archive aria-hidden="true" /></div>
          <div className="min-w-0">
            <h1 id="datasets-title" className="console-page-header__title">{vi ? "Dataset" : "Datasets"}</h1>
            <p className="console-page-header__subtitle">{vi ? "Coverage và provenance từ corpus phục vụ và bộ đánh giá — không sao chép dữ liệu gốc." : "Coverage and provenance for the serving corpus and evaluation set—without duplicating source data."}</p>
          </div>
        </div>
        <div className="console-page-header__actions">
          <span className="console-chip"><ShieldCheck aria-hidden="true" />{vi ? "Chỉ đọc" : "Read-only registry"}</span>
          <button type="button" className="console-btn" onClick={() => setRefreshVersion((value) => value + 1)} disabled={loading || detailLoading}><RefreshCw className={loading || detailLoading ? "animate-spin" : ""} aria-hidden="true" />{vi ? "Làm mới" : "Refresh"}</button>
        </div>
      </header>

      <div className="registry-summary" aria-label={vi ? "Tóm tắt registry dataset" : "Dataset registry summary"}>
        <div><strong>{items.length}</strong><span>{vi ? "dataset hiển thị" : "datasets shown"}</span></div>
        <div><strong>{availableCount}</strong><span>{vi ? "khả dụng" : "available"}</span></div>
        <div><strong>{degradedCount}</strong><span>{vi ? "suy giảm" : "degraded"}</span></div>
        <div><strong>{unknownRecords}</strong><span>{vi ? "count chưa rõ" : "unknown counts"}</span></div>
      </div>

      <div className="registry-filter-bar" role="tablist" aria-label={vi ? "Lọc theo loại dataset" : "Filter by dataset kind"}>
        {(["all", "corpus", "evaluation"] as KindFilter[]).map((kind) => <button key={kind} type="button" role="tab" aria-selected={kindFilter === kind} className={`registry-filter ${kindFilter === kind ? "is-active" : ""}`} onClick={() => setKindFilter(kind)}>{kind === "all" ? (vi ? "Tất cả dataset" : "All datasets") : kindLabel(kind, vi)}</button>)}
      </div>

      {error && <div className="workspace-alert workspace-alert--error registry-alert" role="alert"><span>{error}</span><button type="button" className="console-btn" onClick={() => setRefreshVersion((value) => value + 1)}><RotateCcw aria-hidden="true" />{vi ? "Thử lại" : "Retry"}</button></div>}

      <div className="registry-layout registry-layout--datasets">
        <section className="console-card registry-list" aria-labelledby="dataset-registry-heading" aria-busy={loading}>
          <div className="console-card__header"><div><h2 id="dataset-registry-heading" className="console-card__title">{vi ? "Registry dataset" : "Dataset registry"}</h2><p className="console-card__subtitle">{vi ? "Danh tính ổn định và count do backend sở hữu." : "Stable identities and backend-owned counts."}</p></div>{loading && <span className="console-loading" role="status"><span className="console-loading__spinner" />{vi ? "Đang tải…" : "Loading…"}</span>}</div>
          {!loading && !error && items.length === 0 ? <div className="console-empty" role="status"><CircleSlash2 aria-hidden="true" /><strong>{vi ? "Không có dataset" : "No datasets reported"}</strong><p>{vi ? "Registry đã tải thành công nhưng không có entry cho bộ lọc này." : "The registry loaded successfully but has no entries for this filter."}</p></div> : <div className="registry-dataset-list">{items.map((item) => <button key={item.id} type="button" className={`registry-dataset-row ${selectedId === item.id ? "is-selected" : ""}`} aria-pressed={selectedId === item.id} onClick={() => setSelectedId(item.id)}><span className="registry-dataset-row__icon">{item.kind === "corpus" ? <Database aria-hidden="true" /> : <BarChart3 aria-hidden="true" />}</span><span className="registry-dataset-row__body"><strong>{item.name}</strong><small>{item.description}</small><span className="registry-dataset-row__meta">{kindLabel(item.kind, vi)} · {item.record_count === null ? (vi ? "Số lượng chưa xác định" : "Count unknown") : `${item.record_count.toLocaleString()} ${item.record_unit}`}</span></span><DatasetStatePill status={item.availability} vi={vi} /><ChevronRight className="registry-dataset-row__arrow" aria-hidden="true" /></button>)}</div>}
        </section>

        <aside className="console-card registry-detail registry-dataset-detail" aria-label={selectedSummary ? `${selectedSummary.name} ${vi ? "chi tiết" : "details"}` : (vi ? "Chi tiết dataset" : "Dataset details")} aria-busy={detailLoading}>
          {detailLoading ? <div className="console-empty" role="status"><span className="console-loading__spinner" /><strong>{vi ? "Đang tải chi tiết…" : "Loading details…"}</strong></div> : detailError ? <div className="console-empty" role="alert"><TriangleAlert aria-hidden="true" /><strong>{vi ? "Không thể mở dataset" : "Dataset details unavailable"}</strong><p>{detailError}</p><button type="button" className="console-btn" onClick={() => setRefreshVersion((value) => value + 1)}><RotateCcw aria-hidden="true" />{vi ? "Thử lại" : "Retry"}</button></div> : !detail ? <div className="console-empty"><Archive aria-hidden="true" /><strong>{vi ? "Chọn một dataset" : "Select a dataset"}</strong><p>{vi ? "Coverage và provenance sẽ xuất hiện ở đây." : "Coverage and provenance will appear here."}</p></div> : <>
            <div className="console-card__header registry-detail__header"><div><p className="registry-eyebrow">{kindLabel(detail.kind, vi)}</p><h2 className="console-card__title">{detail.name}</h2></div><DatasetStatePill status={detail.availability} vi={vi} /></div>
            <div className="console-card__body registry-detail__body">
              {(detail.reason || detail.provenance.reason) && <div className={`registry-explanation registry-explanation--${detail.availability}`}><TriangleAlert aria-hidden="true" /><span><strong>{detail.reason_code ?? detail.provenance.reason_code ?? (vi ? "Trạng thái dataset" : "Dataset state")}</strong>{detail.reason ?? detail.provenance.reason}</span></div>}
              <DatasetCoverageView detail={detail} vi={vi} />
              <section className="registry-provenance" aria-labelledby="dataset-provenance-heading"><div className="registry-section-heading"><div><p className="registry-eyebrow">{vi ? "Nguồn gốc" : "Provenance"}</p><h3 id="dataset-provenance-heading">{vi ? "Binding được ghi nhận" : "Recorded binding"}</h3></div><span className={`registry-state registry-state--${detail.provenance.status}`}>{detail.provenance.status}</span></div><dl className="registry-facts"><div><dt>{vi ? "Authority" : "Authority"}</dt><dd>{detail.provenance.authority.replaceAll("_", " ")}</dd></div><div><dt>{vi ? "Revision nội dung" : "Content revision"}</dt><dd className="registry-identity">{valueOrUnknown(detail.revision, vi)}</dd></div><div><dt>{vi ? "Phiên bản build" : "Build version"}</dt><dd>{valueOrUnknown(detail.provenance.build_version, vi)}</dd></div><div><dt>{vi ? "Schema" : "Schema"}</dt><dd>{valueOrUnknown(detail.provenance.schema_version, vi)}</dd></div>{detail.provenance.collection_name && <div><dt>{vi ? "Collection index" : "Index collection"}</dt><dd>{detail.provenance.collection_name}</dd></div>}{detail.provenance.point_count !== null && <div><dt>{vi ? "Điểm index" : "Index points"}</dt><dd>{detail.provenance.point_count.toLocaleString()}</dd></div>}{detail.provenance.embedding_model_id && <div><dt>{vi ? "Embedding binding" : "Embedding binding"}</dt><dd className="registry-identity">{detail.provenance.embedding_model_id}</dd></div>}{detail.provenance.embedding_model_revision && <div><dt>{vi ? "Revision embedding" : "Embedding revision"}</dt><dd className="registry-identity">{detail.provenance.embedding_model_revision}</dd></div>}{detail.provenance.vector_dimension !== null && <div><dt>{vi ? "Chiều vector" : "Vector dimension"}</dt><dd>{detail.provenance.vector_dimension.toLocaleString()}</dd></div>}{detail.provenance.distance_metric && <div><dt>{vi ? "Distance metric" : "Distance metric"}</dt><dd>{detail.provenance.distance_metric}</dd></div>}</dl></section>
            </div>
          </>}
        </aside>
      </div>
    </section>
  );
}
