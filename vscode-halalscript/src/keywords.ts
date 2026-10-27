// Every HalalScript keyword with its meaning and its Official Ruling, as in the
// README. Hover and completion read this table.

export interface Keyword {
  word: string;
  role: string; // what it does in a program
  arabic: string;
  meaning: string; // the everyday meaning of the expression
  ruling: string;
  example: string;
}

export const KEYWORDS: Keyword[] = [
  {
    word: "assalamu",
    role: "program greeting (first word)",
    arabic: "السلام عليكم",
    meaning: "\"peace be upon you\" — the greeting on entering",
    ruling:
      "A program that enters without greeting is turned away at the door. The first line of every program is `assalamu alaikum`, in full.",
    example: "assalamu alaikum",
  },
  {
    word: "alaikum",
    role: "program greeting (second word)",
    arabic: "السلام عليكم",
    meaning: "\"…upon you\" — completes the greeting",
    ruling: "A lone `assalamu` is a greeting abandoned halfway, which is considered worse than none.",
    example: "assalamu alaikum",
  },
  {
    word: "wallahi",
    role: "compile-time constant",
    arabic: "والله",
    meaning: "\"by God, I swear\" — the oath that settles a matter beyond dispute",
    ruling:
      "A *wallahi* value is sworn before the program is born. An oath is not taken on what one will discover later, so its initialiser may name only literals and other *wallahi* values. To reassign it would be to break an oath, and the compiler, which keeps careful records, will not let the programmer become a perjurer.",
    example: "wallahi dirham NISAB := 85",
  },
  {
    word: "bismillah",
    role: "immutable variable",
    arabic: "بسم الله",
    meaning: "\"in the name of God\" — said at the beginning of an act",
    ruling:
      "Declaration is the act of naming, and there is no more solemn naming than one opened with *bismillah*. The value may be computed at runtime, but once begun in the Name it is not revisited.",
    example: "bismillah dirham x := 10",
  },
  {
    word: "inshallah",
    role: "mutable variable",
    arabic: "إن شاء الله",
    meaning: "\"if God wills\" — said of any future that is not certain",
    ruling:
      "A value declared *inshallah* is held only provisionally. It shall remain what it is — if God wills. He may will otherwise, and `:=` is how that will is expressed.",
    example: "inshallah dinar total := 0",
  },
  {
    word: "dirham",
    role: "type: 32-bit signed integer (i32)",
    arabic: "درهم",
    meaning: "the silver coin of the classical caliphates",
    ruling:
      "A dirham may always be placed in a purse of dinars; a dinar may never be pressed into a dirham's purse, for what spills over is *riba* — unlawful increase.",
    example: "bismillah dirham small := 7",
  },
  {
    word: "dinar",
    role: "type: 64-bit signed integer (i64)",
    arabic: "دينار",
    meaning: "the gold coin, worth many dirhams",
    ruling: "As gold exceeds silver, so does the dinar exceed the dirham.",
    example: "bismillah dinar big := 3000000000",
  },
  {
    word: "fatwa",
    role: "type: boolean",
    arabic: "فتوى",
    meaning: "a scholar's formal ruling on whether a thing is permitted",
    ruling:
      "Every *fatwa* resolves to exactly one of two verdicts: *halal* or *haram*. Those who want a third are referred to a looser type system.",
    example: "bismillah fatwa ruling := halal",
  },
  {
    word: "halal",
    role: "boolean literal: true",
    arabic: "حلال",
    meaning: "permitted",
    ruling: "The verdict of permission. There is no third verdict.",
    example: "bismillah fatwa ok := halal",
  },
  {
    word: "haram",
    role: "boolean literal: false",
    arabic: "حرام",
    meaning: "forbidden",
    ruling: "The verdict of prohibition. There is no third verdict.",
    example: "bismillah fatwa ok := haram",
  },
  {
    word: "istikhara",
    role: "if",
    arabic: "استخارة",
    meaning: "the prayer for guidance before making a decision",
    ruling:
      "Before a branch is taken, guidance is sought. The condition must be a *fatwa*, for guidance comes as a ruling and is not counted in coins.",
    example: "istikhara x == 1 yalla\n    x := 2\nkhalas",
  },
  {
    word: "qadarallah",
    role: "else",
    arabic: "قدر الله",
    meaning: "\"God has decreed it\" — said when things did not go as hoped",
    ruling:
      "When the *istikhara* returns *haram*, the programmer does not despair: they say *qadarallah* and walk the other path. A *qadarallah* with no *istikhara* is rejected — one cannot accept a decree that was never sought.",
    example: "qadarallah yalla\n    x := 3\nkhalas",
  },
  {
    word: "yalla",
    role: "block open (closed by khalas)",
    arabic: "يلا",
    meaning: "\"come on, let's go\"",
    ruling:
      "A block is entered with eagerness. It is a covenant, closed in the tongue in which it was opened: a *yalla* answered by `}` is a broken covenant.",
    example: "istikhara ok yalla",
  },
  {
    word: "khalas",
    role: "block close (opened by yalla)",
    arabic: "خلاص",
    meaning: "\"enough, it is finished\"",
    ruling: "A block is left with finality. A *khalas* without a *yalla* finishes what was never started.",
    example: "khalas",
  },
  {
    word: "ameen",
    role: "program exit with a value; inside a dua, its answer (return)",
    arabic: "آمين",
    meaning: "\"so be it\" — said at the end of a supplication",
    ruling:
      "Every program is a supplication and every supplication ends with *ameen*. At the top level it ends the program; inside a *dua* its value is the dua's answer. Nothing may be spoken after it — not in its block, not in the program.",
    example: "ameen total",
  },
  {
    word: "la",
    role: "logical not",
    arabic: "لا",
    meaning: "\"no\"",
    ruling: "The `!` is an exclamation, not an argument. Negation is spoken plainly: *la*.",
    example: "bismillah fatwa refused := la (x == 20)",
  },
  {
    word: "dua",
    role: "function (global, or a member of a diwan)",
    arabic: "دعاء",
    meaning: "\"supplication\" — a request that is answered",
    ruling:
      "Every program is a supplication, and a *dua* is a smaller one within it: it asks, and *ameen* gives its answer. A dua is offered with exactly what it asks, no more and no less, and it is answered in the coin it asked for. It carries only what is handed to it: the variables of the program stay outside.",
    example: "dua dirham add(dirham a, dirham b) yalla\n    ameen a + b\nkhalas",
  },
  {
    word: "diwan",
    role: "structure: fields, then member duas",
    arabic: "ديوان",
    meaning: "the register of the early caliphate, which recorded each person and their entries",
    ruling:
      "A register is drawn up before the business begins, and in each diwan the entries are written before the duties. An entry begun with *bismillah* is set when the object is created; an *inshallah* entry may be amended, but only by one whose every link to it is *inshallah* too.",
    example: "diwan Point yalla\n    inshallah dirham x\nkhalas",
  },
  {
    word: "sual",
    role: "read one dirham from the standard input",
    arabic: "سؤال",
    meaning: "\"question\"",
    ruling: "The program puts its question to the user and receives the answer as a dirham. It is asked as `sual()`, with nothing inside: the user supplies the answer.",
    example: "bismillah dirham a := sual()",
  },
  {
    word: "bayan",
    role: "print one value or string literal, and a newline",
    arabic: "بيان",
    meaning: "\"proclamation, official statement\"",
    ruling:
      "The program proclaims one thing at a time, for the herald has one voice. A string literal is a proclamation and nothing else: it cannot be stored, added or answered. A fatwa is proclaimed as *halal* or *haram*; an object as its diwan and its fields.",
    example: "bayan(\"the register:\")\nbayan(p)",
  },
  {
    word: "ma_dama",
    role: "reserved (while, in a later stage)",
    arabic: "ما دام",
    meaning: "\"as long as\"",
    ruling: "Reserved for a later stage — its time has not yet come.",
    example: "",
  },
];

export const KEYWORD_BY_WORD = new Map(KEYWORDS.map((k) => [k.word, k]));

export function keywordMarkdown(k: Keyword): string {
  const lines = [
    `**${k.word}** — ${k.role}`,
    "",
    `${k.arabic} · ${k.meaning}`,
    "",
    `> **Official Ruling.** ${k.ruling}`,
  ];
  if (k.example) {
    lines.push("", "```halalscript", k.example, "```");
  }
  return lines.join("\n");
}
