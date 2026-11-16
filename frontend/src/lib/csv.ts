/** Minimal RFC-4180 style CSV parser / writer used for batch preview and export. */

export function parseCsv(text: string): string[][] {
  const rows: string[][] = [];
  let row: string[] = [];
  let field = "";
  let inQuotes = false;
  let closedQuote = false;
  const src = text.replace(/^\uFEFF/, "");
  if (src.includes("\0")) throw new Error("CSV contains a null character.");

  for (let i = 0; i < src.length; i++) {
    const ch = src[i];
    if (inQuotes) {
      if (ch === '"') {
        if (src[i + 1] === '"') {
          field += '"';
          i++;
        } else {
          inQuotes = false;
          closedQuote = true;
        }
      } else {
        field += ch;
      }
    } else if (ch === '"') {
      if (field || closedQuote)
        throw new Error("Unexpected quote in CSV field.");
      inQuotes = true;
    } else if (ch === ",") {
      row.push(field);
      field = "";
      closedQuote = false;
    } else if (ch === "\n" || ch === "\r") {
      if (ch === "\r" && src[i + 1] === "\n") i++;
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      closedQuote = false;
    } else {
      if (closedQuote)
        throw new Error("Unexpected text after a quoted CSV field.");
      field += ch;
    }
  }
  if (inQuotes) throw new Error("CSV contains an unclosed quoted field.");
  if (field.length > 0 || row.length > 0 || closedQuote) {
    row.push(field);
    rows.push(row);
  }
  return rows.filter((r) => r.some((c) => c.trim() !== ""));
}

export function toCsv(rows: (string | number | null | undefined)[][]): string {
  return rows
    .map((r) =>
      r
        .map((v) => {
          const s = v === null || v === undefined ? "" : String(v);
          return /[",\n\r]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
        })
        .join(","),
    )
    .join("\n");
}

export function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
