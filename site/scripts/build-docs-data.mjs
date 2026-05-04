import { promises as fs } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const scriptDir = path.dirname(fileURLToPath(import.meta.url));
const siteDir = path.resolve(scriptDir, "..");
const repoRoot = path.resolve(siteDir, "..");
const outputPath = path.join(siteDir, "assets", "data", "docs-data.js");

const ignoredDirectoryNames = new Set([
  ".git",
  ".worktrees",
  "node_modules",
  ".venv",
  "venv",
  "dist",
  "build",
  "coverage",
  "__pycache__"
]);

const ignoredRelativePrefixes = [
  "site/assets/data/",
  "apps/frontend/dist/",
  "apps/frontend/build/",
  "apps/web-frontend/dist/"
];

function normalizePath(value) {
  return value.split(path.sep).join("/");
}

function shouldSkip(relativePath) {
  const normalized = normalizePath(relativePath);
  return ignoredRelativePrefixes.some((prefix) => normalized.startsWith(prefix));
}

async function collectMarkdownFiles(directory) {
  const entries = await fs.readdir(directory, { withFileTypes: true });
  const files = [];

  for (const entry of entries) {
    const absolutePath = path.join(directory, entry.name);
    const relativePath = normalizePath(path.relative(repoRoot, absolutePath));

    if (entry.isDirectory()) {
      if (ignoredDirectoryNames.has(entry.name) || shouldSkip(`${relativePath}/`)) {
        continue;
      }

      files.push(...(await collectMarkdownFiles(absolutePath)));
      continue;
    }

    if (entry.isFile() && entry.name.toLowerCase().endsWith(".md") && !shouldSkip(relativePath)) {
      files.push(relativePath);
    }
  }

  return files;
}

function stripMarkdown(value) {
  const source = removeCodeFences(String(value));
  let output = "";
  let cursor = 0;
  while (cursor < source.length) {
    const target = readMarkdownTarget(source, cursor);
    if (target) {
      output += ` ${target.label} `;
      cursor = target.end;
      continue;
    }
    if (source[cursor] === "`") {
      const end = source.indexOf("`", cursor + 1);
      if (end > cursor + 1) {
        output += ` ${source.slice(cursor + 1, end)} `;
        cursor = end + 1;
        continue;
      }
    }
    output += "#>*_~|`-".includes(source[cursor]) ? " " : source[cursor];
    cursor += 1;
  }
  return collapseWhitespace(output);
}

function titleFromPath(relativePath) {
  const baseName = path.basename(relativePath, ".md");
  return collapseWhitespace(baseName.replaceAll("-", " ").replaceAll("_", " "))
    .split(" ")
    .map((word) => (word ? `${word[0].toUpperCase()}${word.slice(1)}` : word))
    .join(" ");
}

function slugifyHeading(text, used) {
  const base = slugBase(stripMarkdown(text)) || "section";
  const currentCount = used.get(base) || 0;
  used.set(base, currentCount + 1);
  return currentCount === 0 ? base : `${base}-${currentCount + 1}`;
}

function extractTitle(content, relativePath) {
  const heading = parseHeadings(content, 1).find((entry) => entry.level === 1);
  return heading ? stripMarkdown(heading.title) : titleFromPath(relativePath);
}

function extractDescription(content, title) {
  const lines = content.replaceAll("\r\n", "\n").replaceAll("\r", "\n").split("\n");
  let skippedTitle = false;

  for (const line of lines) {
    const trimmed = line.trim();
    if (!skippedTitle && parseHeading(trimmed)?.level === 1) {
      skippedTitle = true;
      continue;
    }
    if (!trimmed || trimmed.startsWith("#") || trimmed.startsWith("```") || trimmed.startsWith("|")) {
      continue;
    }

    const description = stripMarkdown(trimmed);
    if (description && description.toLowerCase() !== title.toLowerCase()) {
      return description.length > 220 ? `${description.slice(0, 217)}...` : description;
    }
  }

  return "Markdown document from the Auto Code repository.";
}

function extractHeadings(content) {
  const used = new Map();
  return parseHeadings(content, 4).map((heading) => {
    const title = stripMarkdown(heading.title);
    return {
      level: heading.level,
      title,
      id: slugifyHeading(title, used)
    };
  });
}

function parseHeadings(content, maxLevel) {
  return content
    .replaceAll("\r\n", "\n")
    .replaceAll("\r", "\n")
    .split("\n")
    .map((line) => parseHeading(line.trim()))
    .filter((heading) => heading && heading.level <= maxLevel);
}

function parseHeading(value) {
  let level = 0;
  while (level < value.length && value[level] === "#") {
    level += 1;
  }
  if (level < 1 || level > 6 || !isWhitespace(value[level])) {
    return null;
  }
  const title = value.slice(level).trim();
  return title ? { level, title } : null;
}

function readMarkdownTarget(source, cursor) {
  const prefix = source.startsWith("![", cursor) ? "![" : "[";
  if (!source.startsWith(prefix, cursor)) {
    return null;
  }
  const labelStart = cursor + prefix.length;
  const labelEnd = source.indexOf("](", labelStart);
  if (labelEnd < labelStart) {
    return null;
  }
  const hrefStart = labelEnd + 2;
  const hrefEnd = source.indexOf(")", hrefStart);
  if (hrefEnd < hrefStart) {
    return null;
  }
  return {
    label: source.slice(labelStart, labelEnd),
    end: hrefEnd + 1
  };
}

function removeCodeFences(value) {
  let output = "";
  let cursor = 0;
  while (cursor < value.length) {
    const start = value.indexOf("```", cursor);
    if (start === -1) {
      output += value.slice(cursor);
      break;
    }
    output += value.slice(cursor, start);
    const end = value.indexOf("```", start + 3);
    cursor = end === -1 ? value.length : end + 3;
  }
  return output;
}

function slugBase(value) {
  let slug = "";
  let pendingDash = false;
  for (const char of stripCombiningMarks(value).toLowerCase()) {
    if (isSlugCharacter(char)) {
      if (pendingDash && slug) {
        slug += "-";
      }
      slug += char;
      pendingDash = false;
    } else {
      pendingDash = true;
    }
  }
  return slug;
}

function stripCombiningMarks(value) {
  let output = "";
  for (const char of String(value).normalize("NFKD")) {
    const code = char.codePointAt(0);
    if (code >= 0x0300 && code <= 0x036f) {
      continue;
    }
    output += char;
  }
  return output;
}

function collapseWhitespace(value) {
  let output = "";
  let pendingSpace = false;
  for (const char of String(value)) {
    if (isWhitespace(char)) {
      pendingSpace = output.length > 0;
    } else {
      if (pendingSpace) {
        output += " ";
        pendingSpace = false;
      }
      output += char;
    }
  }
  return output.trim();
}

function countWords(value) {
  return collapseWhitespace(value).split(" ").filter(Boolean).length;
}

function isSlugCharacter(char) {
  const code = char.codePointAt(0);
  return (
    (code >= 48 && code <= 57) ||
    (code >= 97 && code <= 122) ||
    (code >= 1072 && code <= 1103) ||
    char === "ё"
  );
}

function isWhitespace(char) {
  return char === " " || char === "\t" || char === "\n" || char === "\r";
}

function categorize(relativePath) {
  if (relativePath === "README.md") return "Start";
  if (relativePath.startsWith("guides/")) return "Guides";
  if (relativePath.startsWith("docs/api/")) return "API";
  if (relativePath.startsWith("docs/architecture/")) return "Architecture";
  if (relativePath.startsWith("docs/roadmap/")) return "Roadmap";
  if (
    relativePath.startsWith("docs/frontend/") ||
    relativePath.startsWith("docs/components/") ||
    relativePath.startsWith("docs/stores/")
  ) {
    return "Frontend";
  }
  if (relativePath.startsWith("docs/enterprise/") || relativePath.startsWith("docs/compliance/")) return "Enterprise";
  if (relativePath.startsWith("docs/")) return "Docs";
  if (relativePath.startsWith("apps/backend/")) return "Backend";
  if (relativePath.startsWith("apps/frontend/")) return "Desktop App";
  if (relativePath.startsWith("apps/")) return "Applications";
  if (relativePath.startsWith("tests/")) return "Testing";
  if (relativePath.startsWith(".github/")) return "GitHub";
  if (relativePath.startsWith(".")) return "Project Internals";
  return "Root";
}

function sortDocs(left, right) {
  const categoryOrder = [
    "Start",
    "Guides",
    "Architecture",
    "API",
    "Frontend",
    "Desktop App",
    "Backend",
    "Enterprise",
    "Roadmap",
    "Docs",
    "Testing",
    "Applications",
    "GitHub",
    "Root",
    "Project Internals"
  ];
  const leftCategory = categoryOrder.indexOf(left.category);
  const rightCategory = categoryOrder.indexOf(right.category);
  const categoryScore = (leftCategory === -1 ? 999 : leftCategory) - (rightCategory === -1 ? 999 : rightCategory);
  return categoryScore || left.path.localeCompare(right.path);
}

async function buildDocsData() {
  const markdownFiles = (await collectMarkdownFiles(repoRoot)).sort();
  const docs = [];

  for (const relativePath of markdownFiles) {
    const content = await fs.readFile(path.join(repoRoot, relativePath), "utf8");
    const title = extractTitle(content, relativePath);
    const description = extractDescription(content, title);
    const headings = extractHeadings(content);
    const wordCount = countWords(stripMarkdown(content));

    docs.push({
      path: relativePath,
      title,
      category: categorize(relativePath),
      description,
      headings,
      wordCount,
      content
    });
  }

  docs.sort(sortDocs);

  const categories = Array.from(new Set(docs.map((doc) => doc.category)));
  const payload = {
    generatedBy: "site/scripts/build-docs-data.mjs",
    totalDocuments: docs.length,
    totalWords: docs.reduce((sum, doc) => sum + doc.wordCount, 0),
    categories,
    docs
  };

  await fs.mkdir(path.dirname(outputPath), { recursive: true });
  await fs.writeFile(
    outputPath,
    `window.AUTO_CODE_MARKDOWN_DOCS = ${JSON.stringify(payload, null, 2)};\n`,
    "utf8"
  );

  console.log(`Generated ${normalizePath(path.relative(repoRoot, outputPath))} with ${docs.length} Markdown documents.`);
}

buildDocsData().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
