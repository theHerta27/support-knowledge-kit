"""Small, inspectable Markdown search; no model, network or persistent index."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from hashlib import sha256
from math import log
import os
from pathlib import Path
import re
import unicodedata

import yaml


def tokenize(text: str) -> list[str]:
    """English words and overlapping Chinese bigrams (not semantic embeddings)."""
    text = unicodedata.normalize('NFKC', text).lower()
    terms = re.findall(r'[a-z0-9]+', text)
    for run in re.findall(r'[\u3400-\u9fff]+', text):
        terms.extend(run[i:i + 2] for i in range(len(run) - 1))
        if len(run) == 1:
            terms.append(run)
    return terms


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    scope: str
    updated: str
    source_url: str
    version: str
    lines: tuple[str, ...]
    body_start: int

    def metadata(self) -> dict:
        return {k: getattr(self, k) for k in (
            'source_id', 'title', 'scope', 'updated', 'source_url', 'version')}


@dataclass(frozen=True)
class Passage:
    source_id: str
    section: str
    start: int
    end: int
    terms: Counter


class KnowledgeBase:
    """An immutable startup snapshot so search citations and source reads agree."""

    def __init__(self, root: Path | str):
        self.root = Path(root).expanduser().resolve()
        if not self.root.is_dir():
            raise ValueError('资料目录不存在或不是文件夹')
        self.sources: dict[str, Source] = {}
        self.passages: list[Passage] = []
        total_bytes = 0
        for path in self._markdown_files():
            if len(self.sources) >= 500:
                raise ValueError('资料超过 500 个文件，请缩小目录范围')
            if path.stat().st_size > 512_000:
                raise ValueError(f'{path.name}: 单文件不能超过 512 KB')
            # Bound the read too, in case a file grows between stat and open.
            with path.open('rb') as handle:
                raw = handle.read(512_001)
            total_bytes += len(raw)
            if len(raw) > 512_000 or total_bytes > 10_000_000:
                raise ValueError('资料超过单文件或目录容量限制')
            source = self._load_source(path, raw)
            self.sources[source.source_id] = source
            self.passages.extend(self._split(source))
        if not self.passages:
            raise ValueError('目录中没有可检索的 UTF-8 Markdown 正文')
        self.df: Counter = Counter()
        for passage in self.passages:
            self.df.update(passage.terms.keys())
        self.average_length = sum(sum(p.terms.values()) for p in self.passages) / len(self.passages)

    def _markdown_files(self):
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not (Path(directory) / d).is_symlink())
            for filename in sorted(files):
                if filename.startswith('.') or Path(filename).suffix.lower() != '.md':
                    continue
                path = Path(directory) / filename
                if not path.resolve().is_relative_to(self.root):
                    raise ValueError('不读取资料目录外的链接文件')
                yield path

    def _load_source(self, path: Path, raw: bytes) -> Source:
        try:
            text = raw.decode('utf-8-sig').replace('\r\n', '\n').replace('\r', '\n')
            # splitlines() also splits U+2028/NEL copied from documents, which
            # shifts citations away from the file's actual CR/LF line numbers.
            parts = text.split('\n')
            if parts[-1] == '':
                parts.pop()
            lines = tuple(parts)
        except UnicodeDecodeError as exc:
            raise ValueError(f'{path.name}: 请使用 UTF-8 编码') from exc
        if any(len(line) > 4000 for line in lines):
            raise ValueError(f'{path.name}: 单行超过 4000 字符，请分行')
        metadata, body_start = {}, 0
        if lines and lines[0].strip() == '---':
            closing = next((i for i in range(1, len(lines)) if lines[i].strip() == '---'), None)
            if closing is None:
                raise ValueError(f'{path.name}: frontmatter 缺少结束分隔线')
            try:
                metadata = yaml.safe_load('\n'.join(lines[1:closing])) or {}
            except yaml.YAMLError as exc:
                raise ValueError(f'{path.name}: frontmatter YAML 格式错误') from exc
            if not isinstance(metadata, dict):
                raise ValueError(f'{path.name}: frontmatter 必须是键值对象')
            body_start = closing + 1
        title = next((line.lstrip('#').strip() for line in lines[body_start:] if line.startswith('# ')), path.stem)
        values = {}
        for key, default in [('title', title), ('scope', ''), ('updated', ''), ('source_url', '')]:
            value = metadata.get(key, default)
            if key == 'updated' and hasattr(value, 'isoformat'):
                value = value.isoformat()
            if not isinstance(value, str):
                raise ValueError(f'{path.name}: frontmatter {key} 必须是文字')
            values[key] = value
        if values['source_url'] and not re.match(r'^https?://', values['source_url'], re.I):
            raise ValueError(f'{path.name}: source_url 只接受 HTTP/HTTPS 地址')
        return Source(path.relative_to(self.root).as_posix(), **values,
                      version=sha256(raw).hexdigest(), lines=lines, body_start=body_start)

    @staticmethod
    def _split(source: Source):
        start, section = source.body_start, source.title
        for i in range(start, len(source.lines) + 1):
            heading = i < len(source.lines) and re.match(r'^#{1,6}\s+', source.lines[i])
            if i == len(source.lines) or (heading and i > start) or i - start >= 35:
                text = '\n'.join(source.lines[start:i])
                terms = Counter(tokenize(text + '\n' + source.title))
                if text.strip() and terms:
                    yield Passage(source.source_id, section, start + 1, i, terms)
                start = i
            if heading:
                section = source.lines[i].lstrip('#').strip()

    @staticmethod
    def _integer(value, low, high, name):
        if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
            raise ValueError(f'{name} 必须是 {low}～{high} 的整数')

    def search(self, query: str, limit: int = 5) -> dict:
        if not isinstance(query, str) or not query.strip() or len(query) > 1000:
            raise ValueError('query 必须是 1～1000 字符的非空文字')
        self._integer(limit, 1, 20, 'limit')
        query_terms = set(tokenize(query))
        ranked = []
        for passage in self.passages:
            length = sum(passage.terms.values())
            score = 0.0
            for term in query_terms.intersection(passage.terms):
                frequency = passage.terms[term]
                idf = log(1 + (len(self.passages) - self.df[term] + 0.5) / (self.df[term] + 0.5))
                score += idf * frequency * 2.5 / (frequency + 1.5 * (0.25 + 0.75 * length / self.average_length))
            if score > 0:
                ranked.append((score, passage))
        ranked.sort(key=lambda pair: (-pair[0], pair[1].source_id, pair[1].start))
        matches = []
        for score, passage in ranked[:limit]:
            source = self.sources[passage.source_id]
            text = '\n'.join(source.lines[passage.start - 1:passage.end])
            matches.append(dict(source.metadata(), section=passage.section,
                                start_line=passage.start, end_line=passage.end,
                                excerpt=text[:400], excerpt_truncated=len(text) > 400,
                                score=round(score, 6)))
        return {'query': query, 'matches': matches,
                'note': '本地 BM25 词项检索；score 是排序分数，不是答案正确率。请读取原文并核对适用条件。'}

    def read(self, source_id: str, start_line: int = 1, max_lines: int = 80) -> dict:
        if not isinstance(source_id, str) or source_id not in self.sources:
            raise ValueError('source_id 未登记；请使用 search_knowledge 返回的 source_id')
        source = self.sources[source_id]
        self._integer(start_line, 1, len(source.lines), 'start_line')
        self._integer(max_lines, 1, 200, 'max_lines')
        numbered, count, end = [], 0, start_line - 1
        for i in range(start_line - 1, min(len(source.lines), start_line - 1 + max_lines)):
            line = f'{i + 1}: {source.lines[i]}'
            if numbered and count + len(line) + 1 > 16000:
                break
            numbered.append(line)
            count += len(line) + 1
            end = i + 1
        return dict(source.metadata(), start_line=start_line, end_line=end,
                    total_lines=len(source.lines), content='\n'.join(numbered),
                    next_start_line=end + 1 if end < len(source.lines) else None)
