import { existsSync, mkdirSync, readFileSync, writeFileSync, copyFileSync, readdirSync, statSync, rmSync } from 'node:fs';
import { join, dirname, relative, resolve } from 'node:path';
import { createHash } from 'node:crypto';
import { logger } from './logger.js';

export function ensureDir(dirPath: string): void {
  if (!existsSync(dirPath)) {
    mkdirSync(dirPath, { recursive: true });
    logger.debug(`Created directory: ${dirPath}`);
  }
}

export function readFile(filePath: string): string {
  return readFileSync(filePath, 'utf-8');
}

export function readFileOrNull(filePath: string): string | null {
  try {
    return readFileSync(filePath, 'utf-8');
  } catch {
    return null;
  }
}

export function writeFile(filePath: string, content: string): void {
  ensureDir(dirname(filePath));
  writeFileSync(filePath, content, 'utf-8');
  logger.debug(`Wrote file: ${filePath}`);
}

export function copyFile(src: string, dest: string): void {
  ensureDir(dirname(dest));
  copyFileSync(src, dest);
  logger.debug(`Copied: ${src} → ${dest}`);
}

export function fileExists(filePath: string): boolean {
  return existsSync(filePath);
}

export function isDirectory(filePath: string): boolean {
  try {
    return statSync(filePath).isDirectory();
  } catch {
    return false;
  }
}

export function listFiles(dirPath: string, recursive = false): string[] {
  if (!existsSync(dirPath)) return [];

  const entries = readdirSync(dirPath, { withFileTypes: true });
  const files: string[] = [];

  for (const entry of entries) {
    const fullPath = join(dirPath, entry.name);
    if (entry.isFile()) {
      files.push(fullPath);
    } else if (recursive && entry.isDirectory()) {
      files.push(...listFiles(fullPath, true));
    }
  }

  return files;
}

export function listMarkdownFiles(dirPath: string): string[] {
  return listFiles(dirPath).filter((f) => f.endsWith('.md'));
}

export function sha256(content: string): string {
  return createHash('sha256').update(content).digest('hex');
}

export function fileChecksum(filePath: string): string {
  const content = readFile(filePath);
  return sha256(content);
}

export function relativePath(from: string, to: string): string {
  return relative(from, to);
}

export function resolvePath(...segments: string[]): string {
  return resolve(...segments);
}

export function removeDir(dirPath: string): void {
  if (existsSync(dirPath)) {
    rmSync(dirPath, { recursive: true, force: true });
    logger.debug(`Removed directory: ${dirPath}`);
  }
}

export function removeFile(filePath: string): void {
  if (existsSync(filePath)) {
    rmSync(filePath, { force: true });
    logger.debug(`Removed file: ${filePath}`);
  }
}
