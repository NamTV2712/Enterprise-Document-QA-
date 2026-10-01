import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, expect, test, vi } from "vitest";
import { CollectionTargetDialog } from "./CollectionTargetDialog";
import { describeCollectionFailure } from "../../lib/collectionModel";

afterEach(() => { cleanup(); vi.unstubAllGlobals(); });

test("list 404 is an unavailable capability, while record 404 remains not found", async () => {
  const fetchImpl = vi.fn<typeof fetch>().mockResolvedValue(Response.json({ detail: "Local workspace capability is unavailable" }, { status: 404 }));
  vi.stubGlobal("fetch", fetchImpl);
  render(<CollectionTargetDialog open vi={false} source={null} onClose={vi.fn()} onSaved={vi.fn()} onFailure={vi.fn()} />);
  expect(await screen.findByText("Collections are unavailable in this mode")).toBeInTheDocument();
  expect(screen.queryByRole("button", { name: "Create and add" })).not.toBeInTheDocument();
  expect(screen.queryByText("Collection not found")).not.toBeInTheDocument();
  expect(describeCollectionFailure({ status: 404 }, false).kind).toBe("not_found");
  expect(fetchImpl).toHaveBeenCalledTimes(1);
});
