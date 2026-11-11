// A line-by-line reading of a HalalScript document: its diwans with their fields
// and member duas, its duas, and its declared names. Hover and completion use it.
// It reads the text the way the grammar lays it out (one declaration per line,
// openers at the end of a line, closers alone on theirs), so it also works on a
// program the compiler would reject.

const NAME = "[A-Za-z_][A-Za-z0-9_]*";
const DIWAN = new RegExp(`^\\s*diwan\\s+(${NAME})\\b`);
const DUA = new RegExp(`^\\s*dua\\s+(${NAME})\\s+(${NAME})\\s*\\(([^)]*)\\)`);
const DECLARATION = new RegExp(`^\\s*(wallahi|bismillah|inshallah)\\s+(${NAME})\\s+(${NAME})\\s*:=`);
const FIELD = new RegExp(`^\\s*(bismillah|inshallah)\\s+(${NAME})\\s+(${NAME})\\s*$`);
const PARAMETER = new RegExp(`^\\s*(${NAME})\\s+(${NAME})\\s*$`);
const OPENS = /(\byalla|\{)\s*$/;
const CLOSES = /^\s*(khalas\b|\})/;

export const KIND_FLAG: Record<string, string> = {
  wallahi: "constant",
  bismillah: "immutable",
  inshallah: "mutable",
  parameter: "immutable",
};

export interface Variable {
  name: string;
  kind: string; // wallahi | bismillah | inshallah | parameter
  type: string;
  line: number;
  end: number; // the closer of the block that declares it: the last line it is visible on
  dua?: Dua; // the dua whose body or parameter list declares it
}

export interface Field {
  name: string;
  kind: string; // bismillah | inshallah
  type: string;
  line: number;
}

export interface Dua {
  name: string;
  result: string;
  params: { type: string; name: string }[];
  owner?: string; // the diwan of a member dua
  line: number;
  end: number; // the line of its closer
}

export interface Diwan {
  name: string;
  fields: Field[];
  duas: Dua[];
  line: number;
  end: number;
}

export interface Symbols {
  diwans: Map<string, Diwan>;
  duas: Dua[]; // global and member duas, in order
  variables: Variable[];
}

function code(line: string): string {
  const hash = line.indexOf("#");
  return hash === -1 ? line : line.slice(0, hash);
}

export function scan(lines: string[]): Symbols {
  const symbols: Symbols = { diwans: new Map(), duas: [], variables: [] };
  let depth = 0;
  let diwan: Diwan | undefined; // the diwan being read, at depth 1
  let dua: Dua | undefined; // the dua being read
  let duaDepth = 0;
  // One frame per open block, holding the variables it declares; the bottom
  // frame is the top level. Closing a block ends the visibility of its frame.
  const frames: Variable[][] = [[]];
  const last = lines.length - 1;
  lines.forEach((raw, line) => {
    const text = code(raw);
    let opened: Variable[] = []; // declared on this line, inside the block it opens
    if (CLOSES.test(text)) {
      for (const v of frames.length > 1 ? frames.pop()! : []) {
        v.end = line;
      }
      depth--;
      if (dua && depth === duaDepth) {
        dua.end = line;
        dua = undefined;
      }
      if (diwan && depth === 0) {
        diwan.end = line;
        diwan = undefined;
      }
      if (OPENS.test(text)) { // "} qadarallah {" is not the layout, but stay balanced
        frames.push([]);
        depth++;
      }
      return;
    }
    let match: RegExpExecArray | null;
    if ((match = DIWAN.exec(text)) && depth === 0) {
      diwan = { name: match[1], fields: [], duas: [], line, end: lines.length - 1 };
      symbols.diwans.set(diwan.name, diwan);
    } else if ((match = DUA.exec(text))) {
      const params = match[3].split(",").map((p) => PARAMETER.exec(p)).filter((p) => p !== null)
        .map((p) => ({ type: p![1], name: p![2] }));
      dua = { name: match[2], result: match[1], params, line, end: lines.length - 1 };
      if (diwan && depth === 1) {
        dua.owner = diwan.name;
        diwan.duas.push(dua);
      }
      symbols.duas.push(dua);
      duaDepth = depth;
      opened = params.map((p) => ({ name: p.name, kind: "parameter", type: p.type, line, end: last, dua }));
      symbols.variables.push(...opened);
    } else if ((match = DECLARATION.exec(text))) {
      const variable = { kind: match[1], type: match[2], name: match[3], line, end: last, dua };
      symbols.variables.push(variable);
      frames[frames.length - 1].push(variable);
    } else if (diwan && depth === 1 && (match = FIELD.exec(text))) {
      diwan.fields.push({ kind: match[1], type: match[2], name: match[3], line });
    }
    if (OPENS.test(text)) {
      frames.push(opened); // a dua's parameters belong to its body
      depth++;
    }
  });
  return symbols;
}

/** The dua whose lines hold this line; duas do not nest. */
export function duaAt(symbols: Symbols, line: number): Dua | undefined {
  return symbols.duas.find((d) => d.line <= line && line <= d.end);
}

/**
 * The variables a line can see, as the semantic pass would: those declared above
 * it in the same dua (parameters included), or outside every dua at the top
 * level, whose block has not closed yet. A dua never sees the top level.
 */
export function visibleAt(symbols: Symbols, line: number): Variable[] {
  const dua = duaAt(symbols, line);
  return symbols.variables.filter((v) => v.line <= line && line <= v.end && v.dua === dua);
}

/** The variable a name refers to on a line: the nearest visible declaration above. */
export function variableAt(symbols: Symbols, name: string, line: number): Variable | undefined {
  return visibleAt(symbols, line).filter((v) => v.name === name).pop();
}

/** The field a bare name refers to inside a member dua, when no variable hides it. */
export function ownFieldAt(symbols: Symbols, name: string, line: number): Field | undefined {
  const owner = duaAt(symbols, line)?.owner;
  return owner ? symbols.diwans.get(owner)?.fields.find((f) => f.name === name) : undefined;
}

/** The type of a name on a line: a variable, a parameter, or a field of the caller's diwan. */
export function typeOf(symbols: Symbols, name: string, line: number): string | undefined {
  return variableAt(symbols, name, line)?.type ?? ownFieldAt(symbols, name, line)?.type;
}

/** The diwan reached by a chain such as ["t", "purse"], or undefined. */
export function diwanOfChain(symbols: Symbols, chain: string[], line: number): Diwan | undefined {
  let type = typeOf(symbols, chain[0], line);
  for (const link of chain.slice(1)) {
    type = type && symbols.diwans.get(type)?.fields.find((f) => f.name === link)?.type;
  }
  return type ? symbols.diwans.get(type) : undefined;
}

/** The global dua of a name, or the member dua the caller's diwan declares under it. */
export function duaNamed(symbols: Symbols, name: string, line: number): Dua | undefined {
  const owner = duaAt(symbols, line)?.owner;
  const member = owner && symbols.diwans.get(owner)?.duas.find((d) => d.name === name);
  return member || symbols.duas.find((d) => !d.owner && d.name === name);
}

export function signature(dua: Dua): string {
  const params = dua.params.map((p) => `${p.type} ${p.name}`).join(", ");
  return `dua ${dua.result} ${dua.name}(${params})`;
}

/** The chain before a '.', read backwards from a column: "t.purse.co" gives ["t", "purse"]. */
export function chainBefore(lineText: string, column: number): { chain: string[]; partial: string } | undefined {
  const match = new RegExp(`(${NAME}(?:\\.${NAME})*)\\.(${NAME})?$`).exec(lineText.slice(0, column));
  return match ? { chain: match[1].split("."), partial: match[2] ?? "" } : undefined;
}
