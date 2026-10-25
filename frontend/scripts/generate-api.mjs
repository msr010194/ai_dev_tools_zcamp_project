// Generates src/api/schema.ts from the committed contract/openapi.json.
//   npm run generate:api   write the file
//   npm run check:api      exit 1 if the file is out of date (writes nothing)
import { readFile, writeFile } from "node:fs/promises";
import openapiTS, { astToString } from "openapi-typescript";

const SPEC = new URL("../../contract/openapi.json", import.meta.url);
const OUTPUT = new URL("../src/api/schema.ts", import.meta.url);
const HEADER =
  "// Generated from contract/openapi.json by `npm run generate:api`. Do not edit by hand.\n\n";

const render = async () => {
  const ast = await openapiTS(SPEC);
  return (HEADER + astToString(ast)).replace(/\r\n/g, "\n").replace(/\n*$/, "\n");
};

const expected = await render();

if (process.argv.includes("--check")) {
  const current = await readFile(OUTPUT, "utf8").catch(() => "");
  if (current.replace(/\r\n/g, "\n") !== expected) {
    console.error("src/api/schema.ts is out of date with contract/openapi.json. Run: npm run generate:api");
    process.exit(1);
  }
  console.log("src/api/schema.ts is up to date");
} else {
  await writeFile(OUTPUT, expected);
  console.log("Wrote src/api/schema.ts");
}
