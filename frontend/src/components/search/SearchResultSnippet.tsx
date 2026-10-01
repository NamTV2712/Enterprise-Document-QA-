import { memo } from "react";

import { snippetSegments } from "../../lib/searchModel";
import type { DiscoverySnippet } from "../../types";

/**
 * Renders one API-004 excerpt with its match ranges highlighted.
 *
 * The API returns plain text plus character offsets, so highlights are applied
 * by slicing the string into React nodes: no HTML from the response is ever
 * interpreted, and Unicode text survives unchanged.
 */
export const SearchResultSnippet = memo(function SearchResultSnippet({ snippet }: { snippet: DiscoverySnippet }) {
  const segments = snippetSegments(snippet);
  if (segments.length === 0) return null;
  return (
    <p className="console-result__excerpt search-result__snippet">
      {segments.map((segment, index) =>
        segment.match ? (
          <mark key={index} className="console-highlight">{segment.text}</mark>
        ) : (
          <span key={index}>{segment.text}</span>
        ),
      )}
    </p>
  );
});
