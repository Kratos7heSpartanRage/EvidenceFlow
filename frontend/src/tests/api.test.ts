import { afterEach, describe, expect, it, vi } from 'vitest';
import { api } from '../lib/api';
import type { Criterion } from '../types/api';

afterEach(() => vi.unstubAllGlobals());
const reply = (payload: unknown, status = 200) => Response.json(payload, { status });
const review = {
  id: 'review-uuid', title: 'Review', question: 'Question', pico: { population: 'adults' },
  created_at: '', updated_at: '', counts: {
    total_records: 0, unique_studies: 0, screened_included: 0,
    screened_excluded: 0, screened_maybe: 0, unscreened: 0, open_conflicts: 0
  }
};

describe('Live API boundary', () => {
  it('reports connection failures and retries without switching to fixtures', async () => {
    const fetcher = vi.fn().mockRejectedValueOnce(new Error('offline')).mockResolvedValueOnce(reply([]));
    vi.stubGlobal('fetch', fetcher);
    await expect(api.listReviews()).rejects.toThrow('Cannot reach the backend');
    expect(await api.listReviews()).toEqual([]); expect(fetcher).toHaveBeenCalledTimes(2);
  });
  it('surfaces field validation errors from FastAPI envelopes', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply({
      error: {
        code: 'VALIDATION_ERROR', message: 'Request validation failed',
        details: { errors: [{ loc: ['body', 'reason_text'], msg: 'Reason is required' }] }
      }
    }, 422)));
    await expect(api.submitScreeningDecision('record-uuid', { decision: 'exclude', reviewer: 'C' })).rejects.toThrow('reason_text: Reason is required');
  });
  it('maps nested PICO/counts and preserves empty criteria', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => reply(url.includes('duplicate-pairs') ? [] : review)));
    expect(await api.getReview('review-uuid')).toMatchObject({ id: 'review-uuid', population: 'adults', stats: { total_records: 0 } });
    expect((await api.getCriteria('review-uuid')).criteria).toEqual([]);
  });
  it('sends query specs with both search options', async () => {
    const fetcher = vi.fn().mockResolvedValue(reply({ id: 'query-uuid', version_number: 1, status: 'draft' })); vi.stubGlobal('fetch', fetcher);
    await api.createQuery('review-uuid', { expression: 'search', source: 'europe_pmc', options_json: { synonym: true, title_abstract_only: true } });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ label: 'search', parent_id: null, spec: { expression: 'search', source: 'europe_pmc', date_from: null, date_to: null, expand_synonyms: true, title_abstract_only: true } });
  });
  it('preserves zero preview hits and warnings', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(reply({ query_id: 'query-uuid', estimated_hits: 0, sample_records: [], warnings: ['limited'] })));
    expect(await api.previewQuery('query-uuid')).toMatchObject({ query_version_id: 'query-uuid', hit_count: 0, warnings: ['limited'] });
  });
  it('loads every record page and maps UUIDs, authors, decisions and suggestions separately', async () => {
    vi.stubGlobal('fetch', vi.fn(async (url: string) => {
      const page = Number(new URL(url, 'http://localhost').searchParams.get('page'));
      return reply({
        items: [{
          id: `record-${page}`, review_id: 'review-uuid', source: 'pubmed', source_record_id: `${page}`,
          title: 'Study', authors: [{ full_name: 'A. Author' }], is_representative: true, is_hidden: false,
          decision: { id: 'decision-uuid', decision: 'include', reviewer_name: 'C', origin: 'human', created_at: '' },
          suggestion: { id: 'suggestion-uuid', suggested_decision: 'maybe', confidence: 0, algorithm_version: 'v1', evidence_snippets: [{ code: 'rule', matched: ['adults'], explanation: 'Population matched.' }] }
        }], total: 2, page, page_size: 1
      });
    }));
    const result = await api.getRecords('review-uuid', { page_size: 1, show_hidden: true });
    expect(result.items).toHaveLength(2);
    expect(result.items[0]).toMatchObject({ id: 'record-1', authors_json: ['A. Author'], current_decision: { reviewer: 'C', record_id: 'record-1' }, suggestion: { suggestion: 'maybe', evidence_json: { explanation: 'Population matched.', rule_hits: ['adults'], strength: 'none' } } });
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining('representatives_only=false'), expect.anything());
  });
  it('preserves detector rules and sends only active criteria in new versions', async () => {
    const fetcher = vi.fn().mockResolvedValue(reply({ id: 'cv', review_id: 'review-uuid', version_number: 2, criteria: [] })); vi.stubGlobal('fetch', fetcher);
    const criterion: Criterion = { id: 'criterion-uuid', criteria_version_id: 'old', kind: 'exclude', code: 'custom', label: 'Animal', reason: 'Animal studies', detector: 'rule', detector_rule: 'rats|mice', is_active: true };
    await api.updateCriteria('review-uuid', [criterion, { ...criterion, is_active: false }]);
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({ criteria: [{ type: 'exclusion', label: 'Animal', description: 'Animal studies', detector_rule: 'rats|mice', field_target: null }] });
  });
  it('reads PICO from record detail and sends a batch PATCH with attribution', async () => {
    const fetcher = vi.fn().mockResolvedValueOnce(reply({ pico_spans: [{ id: 'span-uuid', element: 'P', text: 'adults', start_index: 0, end_index: 6, origin: 'machine', is_confirmed: false }] })).mockResolvedValueOnce(reply({ status: 'updated', updated_count: 1 })); vi.stubGlobal('fetch', fetcher);
    const annotations = await api.getPicoAnnotations('record-uuid');
    expect(annotations[0]).toMatchObject({ label: 'P', start_char: 0, status: 'suggested' });
    await api.updatePico('record-uuid', { op: 'confirm', annotation: annotations[0], reviewer: 'C' });
    expect(fetcher.mock.calls[0][0]).toBe('/api/records/record-uuid');
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ reviewer: 'C', ops: [{ op: 'confirm', span_id: 'span-uuid' }] });
  });
  it('maps reviewer names and consensus exclusion reasons', async () => {
    const fetcher = vi.fn().mockImplementation(() => Promise.resolve(reply({}))); vi.stubGlobal('fetch', fetcher);
    await api.submitPairDecision('review-uuid', { record_a_id: 'a', record_b_id: 'b', decision: 'reject', reviewer: 'C' });
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toMatchObject({ reviewer_name: 'C' });
    await api.submitScreeningDecision('a', { decision: 'include', reviewer: 'C' });
    expect(JSON.parse(fetcher.mock.calls[1][1].body)).toEqual({ decision: 'include', reviewer_name: 'C' });
    await api.resolveConflict('conflict-uuid', { resolution: 'unify', decision: 'exclude', reason: 'Animal study', reviewer: 'Panel' });
    expect(JSON.parse(fetcher.mock.calls[2][1].body)).toEqual({ decision: 'exclude', reason_text: 'Animal study', note: 'Animal study', reviewer: 'Panel' });
  });
});
