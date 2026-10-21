import { describe, expect, it } from "vitest";
import { ApiError, describeError } from "./api";
import { checkFile, formatBytes, groundingSentence, pageRef, timeAgo } from "./format";

describe("formatBytes", () => {
  it("scales units", () => {
    expect(formatBytes(512)).toBe("512 B");
    expect(formatBytes(2048)).toBe("2 KB");
    expect(formatBytes(3.5 * 1024 * 1024)).toBe("3.5 MB");
  });
});

describe("timeAgo", () => {
  const now = 1_800_000_000_000;
  it("reads naturally", () => {
    expect(timeAgo(now / 1000 - 10, now)).toBe("just now");
    expect(timeAgo(now / 1000 - 600, now)).toBe("10 min ago");
    expect(timeAgo(now / 1000 - 86400, now)).toBe("yesterday");
    expect(timeAgo(now / 1000 - 3 * 86400, now)).toBe("3 days ago");
  });
});

describe("groundingSentence", () => {
  it("says when everything is backed", () => {
    expect(groundingSentence({ claims: 4, verified: 3, approximate: 1, grounded_rate: 1 })).toBe("All 4 claims are backed by quotes found in the document.");
  });
  it("tells the reader what to double-check", () => {
    expect(groundingSentence({ claims: 5, verified: 4, unverified: 1, grounded_rate: 0.8 })).toContain("1 isn't, so check it");
  });
  it("is silent with no claims", () => {
    expect(groundingSentence({ claims: 0, grounded_rate: null })).toBeNull();
  });
});

describe("checkFile", () => {
  it("accepts supported files", () => expect(checkFile({ name: "Report.PDF", size: 1000 })).toBeNull());
  it("rejects other types, empty and oversized files", () => {
    expect(checkFile({ name: "photo.png", size: 1000 })).toMatch(/supported type/);
    expect(checkFile({ name: "a.pdf", size: 0 })).toMatch(/empty/);
    expect(checkFile({ name: "a.pdf", size: 30 * 1024 * 1024 })).toMatch(/limit is 20 MB/);
  });
});

describe("pageRef", () => {
  it("labels pages and parts", () => {
    expect(pageRef("Page", 3)).toBe("p. 3");
    expect(pageRef("Part", 2)).toBe("part 2");
    expect(pageRef("Page", null)).toBe("");
  });
});

describe("describeError", () => {
  it("passes API messages through and explains network failures", () => {
    expect(describeError(new ApiError("NOT_READY", "Still indexing.", 409))).toBe("Still indexing.");
    expect(describeError(new TypeError("Failed to fetch"))).toMatch(/Can't reach/);
  });
});
