import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCsv, toCsv } from "../src/lib/csv.ts";
import { formatMoney, formatNumber } from "../src/lib/format.ts";

test("CSV round trip preserves quoted commas, CRLF, newlines and escaped quotes", () => {
  const rows = [
    ["id", "description"],
    ["PR-1", 'Hose, 1/2"\r\nSS'],
    ["PR-2", ""],
  ];
  assert.deepEqual(parseCsv(toCsv(rows)), rows);
});
test("BOM and blank trailing rows do not alter the header", () => {
  assert.deepEqual(parseCsv("\uFEFFid,value\r\nPR-1,10\r\n\r\n"), [
    ["id", "value"],
    ["PR-1", "10"],
  ]);
});
for (const input of [
  'id,value\n1,"unfinished',
  'id,value\n1,"closed"oops',
  'id,value\n1,un"quoted',
  "id\n\0",
]) {
  test(`malformed CSV is rejected: ${JSON.stringify(input)}`, () =>
    assert.throws(() => parseCsv(input)));
}
test("decimal formatting preserves values beyond JavaScript integer precision", () => {
  assert.equal(
    formatMoney("9007199254740993.01"),
    "₹9,00,71,99,25,47,40,993.01",
  );
  assert.equal(formatNumber("-123456.0050"), "-1,23,456.0050");
  assert.equal(formatMoney(null), "—");
});
