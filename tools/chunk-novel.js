#!/usr/bin/env node
import fs from 'node:fs';
import path from 'node:path';

function parseArgs(argv) {
  const args = { target: 50000, max: 60000, min: 35000, includePreamble: false };
  const positional = [];

  for (let i = 0; i < argv.length; i++) {
    const arg = argv[i];
    if (arg === '--out') args.out = argv[++i];
    else if (arg === '--target') args.target = Number(argv[++i]);
    else if (arg === '--max') args.max = Number(argv[++i]);
    else if (arg === '--min') args.min = Number(argv[++i]);
    else if (arg === '--include-preamble') args.includePreamble = true;
    else if (arg === '-h' || arg === '--help') args.help = true;
    else positional.push(arg);
  }

  args.input = positional[0];
  return args;
}

function printUsage() {
  console.log(`Usage: npm run chunk -- <input.txt> --out <dir> [options]\n\nOptions:\n  --target 50000       target characters per analysis chunk\n  --max 60000          preferred hard ceiling per chunk\n  --min 35000          preferred minimum before closing a chunk\n  --include-preamble   include text before the first chapter\n`);
}

const CHAPTER_RE = /^\s*第\s*([0-9零〇一二三四五六七八九十百千万两]+)\s*章(?:\s+|[：:、.．\-—]|$)(.*)$/;

function splitParagraphs(text) {
  return text.split(/\n{2,}/).map((part) => part.trim()).filter(Boolean);
}

function splitLongUnit(unit, target, max) {
  if (unit.text.length <= max) return [unit];

  const paragraphs = splitParagraphs(unit.text);
  const pieces = [];
  let buffer = [];
  let bufferLength = 0;
  let pieceNo = 1;

  const flush = () => {
    if (!buffer.length) return;
    const text = buffer.join('\n\n');
    pieces.push({ ...unit, text, chars: text.length, partial: true, pieceNo: pieceNo++ });
    buffer = [];
    bufferLength = 0;
  };

  for (const paragraph of paragraphs) {
    if (paragraph.length > max) {
      flush();

      // Last-resort split for an abnormally long paragraph: sentence boundaries only.
      const sentences = paragraph.match(/[^。！？!?；;]+[。！？!?；;]?/g) || [paragraph];
      let sentenceBuffer = '';
      for (const sentence of sentences) {
        if (sentenceBuffer && sentenceBuffer.length + sentence.length > target) {
          pieces.push({
            ...unit,
            text: sentenceBuffer,
            chars: sentenceBuffer.length,
            partial: true,
            pieceNo: pieceNo++
          });
          sentenceBuffer = '';
        }
        sentenceBuffer += sentence;
      }
      if (sentenceBuffer) {
        pieces.push({
          ...unit,
          text: sentenceBuffer,
          chars: sentenceBuffer.length,
          partial: true,
          pieceNo: pieceNo++
        });
      }
      continue;
    }

    const extraLength = (buffer.length ? 2 : 0) + paragraph.length;
    if (buffer.length && bufferLength + extraLength > target) flush();

    buffer.push(paragraph);
    bufferLength += (buffer.length > 1 ? 2 : 0) + paragraph.length;
  }

  flush();
  return pieces;
}

function parseNovel(text) {
  const normalized = text.replace(/\r\n?/g, '\n');
  const lines = normalized.split('\n');
  const chapters = [];
  const preamble = [];
  let current = null;

  for (const line of lines) {
    const match = line.match(CHAPTER_RE);
    if (match) {
      if (current) {
        current.text = current.lines.join('\n').trim();
        current.chars = current.text.length;
        delete current.lines;
        chapters.push(current);
      }

      current = {
        heading: line.trim(),
        chapterLabel: match[1],
        title: (match[2] || '').trim(),
        lines: [line.trim()]
      };
    } else if (current) {
      current.lines.push(line);
    } else {
      preamble.push(line);
    }
  }

  if (current) {
    current.text = current.lines.join('\n').trim();
    current.chars = current.text.length;
    delete current.lines;
    chapters.push(current);
  }

  return { preamble: preamble.join('\n').trim(), chapters };
}

function packUnits(units, target, max, min) {
  const chunks = [];
  let currentUnits = [];
  let currentLength = 0;

  const flush = () => {
    if (!currentUnits.length) return;
    const text = currentUnits.map((unit) => unit.text).join('\n\n');
    chunks.push({ units: currentUnits, text, chars: text.length });
    currentUnits = [];
    currentLength = 0;
  };

  for (const unit of units) {
    if (!currentUnits.length) {
      currentUnits.push(unit);
      currentLength = unit.text.length;
      continue;
    }

    const joinedLength = currentLength + 2 + unit.text.length;
    if (joinedLength <= target) {
      currentUnits.push(unit);
      currentLength = joinedLength;
      continue;
    }

    if (
      joinedLength <= max &&
      (currentLength < min || Math.abs(target - joinedLength) < Math.abs(target - currentLength))
    ) {
      currentUnits.push(unit);
      currentLength = joinedLength;
      flush();
      continue;
    }

    flush();
    currentUnits.push(unit);
    currentLength = unit.text.length;
  }

  flush();
  return chunks;
}

function paddedIndex(value) {
  return String(value).padStart(3, '0');
}

function main() {
  const args = parseArgs(process.argv.slice(2));
  if (args.help || !args.input) {
    printUsage();
    process.exit(args.help ? 0 : 1);
  }

  if (
    ![args.target, args.max, args.min].every(Number.isFinite) ||
    args.min <= 0 ||
    args.target < args.min ||
    args.max < args.target
  ) {
    throw new Error('Require 0 < min <= target <= max');
  }

  const input = path.resolve(args.input);
  const outDir = path.resolve(args.out || `${input}.chunks`);
  const raw = fs.readFileSync(input, 'utf8');
  const { preamble, chapters } = parseNovel(raw);

  if (!chapters.length) {
    throw new Error('No chapter headings detected. Expected headings like “第1章 标题”.');
  }

  let units = [];
  for (const chapter of chapters) {
    units.push(...splitLongUnit(chapter, args.target, args.max));
  }

  if (args.includePreamble && preamble) {
    units.unshift({
      heading: 'PREAMBLE',
      chapterLabel: null,
      title: 'preamble',
      text: preamble,
      chars: preamble.length,
      preamble: true
    });
  }

  const chunks = packUnits(units, args.target, args.max, args.min);
  fs.mkdirSync(outDir, { recursive: true });

  const manifest = {
    version: 1,
    inputFile: path.basename(input),
    sourceChars: raw.length,
    detectedChapters: chapters.length,
    excludedPreambleChars: args.includePreamble ? 0 : preamble.length,
    settings: {
      targetChars: args.target,
      minChars: args.min,
      maxChars: args.max,
      includePreamble: args.includePreamble
    },
    chunks: []
  };

  chunks.forEach((chunk, index) => {
    const filename = `chunk_${paddedIndex(index + 1)}.txt`;
    fs.writeFileSync(path.join(outDir, filename), chunk.text, 'utf8');

    const chapterUnits = chunk.units.filter((unit) => !unit.preamble);
    manifest.chunks.push({
      index: index + 1,
      file: filename,
      chars: chunk.chars,
      unitCount: chunk.units.length,
      chapterStart: chapterUnits[0]?.heading || null,
      chapterEnd: chapterUnits[chapterUnits.length - 1]?.heading || null,
      containsPartialChapter: chunk.units.some((unit) => unit.partial),
      chapterHeadings: chapterUnits.map((unit) => unit.heading)
    });
  });

  fs.writeFileSync(
    path.join(outDir, 'manifest.json'),
    JSON.stringify(manifest, null, 2),
    'utf8'
  );

  const sizes = chunks.map((chunk) => chunk.chars);
  console.log(JSON.stringify({
    input: path.basename(input),
    sourceChars: raw.length,
    detectedChapters: chapters.length,
    excludedPreambleChars: manifest.excludedPreambleChars,
    chunks: chunks.length,
    minChunkChars: Math.min(...sizes),
    maxChunkChars: Math.max(...sizes),
    avgChunkChars: Math.round(sizes.reduce((sum, size) => sum + size, 0) / sizes.length),
    partialChapterChunks: manifest.chunks.filter((chunk) => chunk.containsPartialChapter).length,
    outDir
  }, null, 2));
}

main();
