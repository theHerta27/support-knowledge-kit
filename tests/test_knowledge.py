from pathlib import Path

import pytest

from support_knowledge.knowledge import KnowledgeBase


@pytest.fixture
def kb(tmp_path):
    (tmp_path / 'relocation.md').write_text(
        '---\ntitle: 宽带移机\nscope: 示例宽带\nupdated: 2026-11-09\n---\n'
        '# 宽带迁移\n\n## 同城\n同城移机需要核查覆盖和端口。\n\n'
        '## 跨城\n跨城市搬家不支持原线路直接迁移。广州搬到佛山属于跨城市。\n', encoding='utf-8')
    (tmp_path / 'billing.md').write_text(
        '# Billing 发票\n\nInvoice requests require the billing month.\n'
        '本知识库不包含个人账户收费记录。\n', encoding='utf-8')
    return KnowledgeBase(tmp_path)


def test_chinese_search_finds_source_and_readable_evidence(kb):
    hit = kb.search('广州搬到佛山宽带怎么迁移', limit=1)['matches'][0]
    assert hit['source_id'] == 'relocation.md'
    assert hit['scope'] == '示例宽带'
    assert hit['updated'] == '2026-11-09'
    source = kb.read(hit['source_id'], hit['start_line'], 80)
    assert '跨城市搬家不支持' in source['content']
    assert source['version'] == hit['version']


def test_english_search_is_case_insensitive(kb):
    assert kb.search('INVOICE')['matches'][0]['source_id'] == 'billing.md'


def test_no_match_is_empty(kb):
    assert kb.search('火星火箭燃料')['matches'] == []


def test_query_is_data_not_executable_syntax(kb):
    assert kb.search('" OR 1=1; DROP TABLE documents --')['matches'] == []


def test_ambiguous_search_keeps_candidates(kb):
    ids = {m['source_id'] for m in kb.search('宽带移机 invoice')['matches']}
    assert ids == {'relocation.md', 'billing.md'}


@pytest.mark.parametrize('query', ['', '  ', 'a' * 1001, None, 12])
def test_invalid_query_rejected(kb, query):
    with pytest.raises(ValueError):
        kb.search(query)


@pytest.mark.parametrize('limit', [0, 21, True, 1.5])
def test_invalid_limit_rejected(kb, limit):
    with pytest.raises(ValueError):
        kb.search('宽带', limit)


def test_read_paginates_exact_original_lines(kb):
    page = kb.read('relocation.md', start_line=6, max_lines=3)
    assert page['content'] == '6: # 宽带迁移\n7: \n8: ## 同城'
    assert page['next_start_line'] == 9
    last = kb.read('relocation.md', start_line=9, max_lines=80)
    assert last['next_start_line'] is None


def test_unicode_separators_do_not_change_physical_line_numbers(tmp_path):
    (tmp_path / 'policy.md').write_text(
        '# Policy\nFirst\u2028continued\nRefund available.\n', encoding='utf-8')
    kb = KnowledgeBase(tmp_path)
    page = kb.read('policy.md', start_line=2, max_lines=2)
    assert page['content'] == '2: First\u2028continued\n3: Refund available.'
    assert page['total_lines'] == 3


@pytest.mark.parametrize('source_id', ['../secret.md', '/etc/passwd', 'C:\\secret.md', 'missing.md'])
def test_only_indexed_source_ids_can_be_read(kb, source_id):
    with pytest.raises(ValueError):
        kb.read(source_id)


@pytest.mark.parametrize('start,max_lines', [(0, 10), (999, 10), (True, 10), (1, 0), (1, 201)])
def test_invalid_read_window_rejected(kb, start, max_lines):
    with pytest.raises(ValueError):
        kb.read('relocation.md', start, max_lines)


def test_startup_snapshot_keeps_search_and_read_consistent(tmp_path):
    path = tmp_path / 'a.md'
    path.write_text('# Refund\nOriginal refund policy.', encoding='utf-8')
    kb = KnowledgeBase(tmp_path)
    version = kb.read('a.md')['version']
    path.write_text('# Refund\nUpdated refund policy.', encoding='utf-8')
    assert 'Original' in kb.read('a.md')['content']
    refreshed = KnowledgeBase(tmp_path)
    assert 'Updated' in refreshed.read('a.md')['content']
    assert refreshed.read('a.md')['version'] != version


def test_hidden_material_and_non_markdown_are_not_loaded(tmp_path):
    (tmp_path / '.private').mkdir()
    (tmp_path / '.private' / 'secret.md').write_text('hidden secret', encoding='utf-8')
    (tmp_path / 'secret.txt').write_text('hidden secret', encoding='utf-8')
    (tmp_path / 'public.md').write_text('# Public\nPublished guidance', encoding='utf-8')
    kb = KnowledgeBase(tmp_path)
    assert kb.search('secret')['matches'] == []


def test_external_symlink_is_rejected(tmp_path):
    root = tmp_path / 'kb'
    root.mkdir()
    secret = tmp_path / 'secret.md'
    secret.write_text('secret', encoding='utf-8')
    try:
        (root / 'link.md').symlink_to(secret)
    except OSError:
        pytest.skip('Host does not allow symbolic links')
    with pytest.raises(ValueError, match='目录外'):
        KnowledgeBase(root)


def test_invalid_metadata_is_explained(tmp_path):
    (tmp_path / 'bad.md').write_text('---\n- a\n- b\n---\n# Text', encoding='utf-8')
    with pytest.raises(ValueError, match='frontmatter'):
        KnowledgeBase(tmp_path)


def test_long_line_is_rejected_instead_of_unbounded_tool_output(tmp_path):
    (tmp_path / 'big.md').write_text('x' * 5000, encoding='utf-8')
    with pytest.raises(ValueError, match='行'):
        KnowledgeBase(tmp_path)


def test_empty_or_missing_directory_is_explained(tmp_path):
    with pytest.raises(ValueError):
        KnowledgeBase(tmp_path)
    with pytest.raises(ValueError):
        KnowledgeBase(tmp_path / 'missing')
