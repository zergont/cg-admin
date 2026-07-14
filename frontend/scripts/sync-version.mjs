// Синхронизирует package.json.version с единым источником — файлом VERSION
// в корне репозитория. Запускается автоматически перед dev/build.

import { readFileSync, writeFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const versionPath = join(__dirname, "..", "..", "VERSION");
const pkgPath = join(__dirname, "..", "package.json");

const version = readFileSync(versionPath, "utf-8").trim();
const pkgRaw = readFileSync(pkgPath, "utf-8");
const pkg = JSON.parse(pkgRaw);

if (pkg.version !== version) {
  pkg.version = version;
  writeFileSync(pkgPath, JSON.stringify(pkg, null, 2) + "\n");
  console.log(`[sync-version] package.json version → ${version}`);
}
