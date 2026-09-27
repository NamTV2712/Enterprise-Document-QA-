import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import ts from "typescript";
import { describe, expect, test } from "vitest";

const catalog = JSON.parse(readFileSync(resolve(process.cwd(), "../tests/fixtures/cross_layer_contracts.json"), "utf8")) as {
  enums: Array<{ typescript: string; values: Array<string | number> }>;
};
const sourcePath = (name: string) => resolve(process.cwd(), "src", name);
const program = ts.createProgram(["types.ts", "lib/evaluationTypes.ts", "lib/operationalTypes.ts"].map(sourcePath), {
  target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ESNext, strictNullChecks: true,
  moduleResolution: ts.ModuleResolutionKind.Bundler, skipLibCheck: true, noEmit: true,
});
const checker = program.getTypeChecker();

describe("TEST-002 actual compiler-resolved TypeScript unions", () => {
  test.each(catalog.enums)("$typescript matches the shared Python contract without string widening", contract => {
    const [file, name] = contract.typescript.split(":");
    const [symbolName, field] = name.split(".");
    const source = program.getSourceFile(sourcePath(file));
    expect(source, file).toBeDefined();
    const declaration = source!.statements.find(statement =>
      (ts.isTypeAliasDeclaration(statement) || ts.isInterfaceDeclaration(statement)) && statement.name.text === symbolName);
    expect(declaration, name).toBeDefined();
    let type = checker.getTypeAtLocation(declaration!);
    if (field) {
      const property = type.getProperty(field);
      expect(property, name).toBeDefined();
      type = checker.getTypeOfSymbolAtLocation(property!, declaration!);
    }
    const members = type.isUnion() ? type.types : [type];
    const values = members.map(member => {
      expect(member.isLiteral(), checker.typeToString(member)).toBe(true);
      return (member as ts.LiteralType).value;
    });
    expect(new Set(values)).toEqual(new Set(contract.values));
    expect(values).toHaveLength(contract.values.length);
  });
});
