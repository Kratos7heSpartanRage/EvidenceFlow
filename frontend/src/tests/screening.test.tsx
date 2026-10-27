import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';
import { ReasonModal } from '../components/ui/ReasonModal';
import { MachineSuggestionBadge, HumanDecisionBadge } from '../components/ui/Badge';
import { mockCriteriaVersion } from '../mocks/mockData';

describe('Screening Exclusion Validation (Client-Side Enforcement)', () => {
  it('disables the Confirm Exclusion button if no criterion is selected and reason is empty', () => {
    const handleConfirm = vi.fn();
    render(
      <ReasonModal
        isOpen={true}
        onClose={vi.fn()}
        criteria={mockCriteriaVersion.criteria}
        recordTitle="Test Study"
        onConfirm={handleConfirm}
      />
    );

    const confirmBtn = screen.getByRole('button', { name: /Confirm Exclusion/i });
    expect(confirmBtn).toBeDisabled();
    expect(screen.getByText(/You must select a criterion or enter a custom reason before submitting/i)).toBeInTheDocument();
  });

  it('enables the Confirm Exclusion button when a standard protocol criterion is selected', () => {
    const handleConfirm = vi.fn();
    render(
      <ReasonModal
        isOpen={true}
        onClose={vi.fn()}
        criteria={mockCriteriaVersion.criteria}
        recordTitle="Test Animal Study"
        onConfirm={handleConfirm}
      />
    );

    const nonHumanCriterion = screen.getByText('Non-Human Studies');
    fireEvent.click(nonHumanCriterion);

    const confirmBtn = screen.getByRole('button', { name: /Confirm Exclusion/i });
    expect(confirmBtn).not.toBeDisabled();

    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledWith(expect.objectContaining({
      criterion_id: 1,
      reason_text: expect.stringContaining('Non-Human Studies')
    }));
  });

  it('enables the Confirm Exclusion button when a custom free-text reason is provided', () => {
    const handleConfirm = vi.fn();
    render(
      <ReasonModal
        isOpen={true}
        onClose={vi.fn()}
        criteria={mockCriteriaVersion.criteria}
        recordTitle="Test Study"
        onConfirm={handleConfirm}
      />
    );

    const textarea = screen.getByPlaceholderText(/Pediatric cohort with mean age 14.2 years/i);
    fireEvent.change(textarea, { target: { value: 'Ineligible study population: pediatric adolescents' } });

    const confirmBtn = screen.getByRole('button', { name: /Confirm Exclusion/i });
    expect(confirmBtn).not.toBeDisabled();

    fireEvent.click(confirmBtn);
    expect(handleConfirm).toHaveBeenCalledWith(expect.objectContaining({
      reason_text: 'Ineligible study population: pediatric adolescents'
    }));
  });
});

describe('Badge Visual Distinction (Machine vs Human)', () => {
  it('renders MachineSuggestionBadge with outlined "Suggested" label and evidence strength', () => {
    const suggestion = {
      id: 501,
      record_id: 101,
      criteria_version_id: 1,
      content_hash: 'hash123',
      algo_version: 'v1.0',
      suggestion: 'exclude' as const,
      criterion_id: 1,
      evidence_json: {
        strength: 'strong' as const,
        explanation: 'MeSH contains Animals descriptor'
      },
      created_at: new Date().toISOString()
    };

    render(<MachineSuggestionBadge suggestion={suggestion} />);
    expect(screen.getByText('Suggested: Exclude')).toBeInTheDocument();
    expect(screen.getByText('strong')).toBeInTheDocument();
  });

  it('renders HumanDecisionBadge with solid reviewer indicator and origin', () => {
    const decision = {
      id: 601,
      review_id: 1,
      record_id: 101,
      decision: 'include' as const,
      reason_text: 'High quality double blind RCT',
      reviewer: 'Member D',
      origin: 'direct' as const,
      criteria_version_id: 1,
      created_at: new Date().toISOString()
    };

    render(<HumanDecisionBadge decision={decision} />);
    expect(screen.getByText('Included')).toBeInTheDocument();
    expect(screen.getByText('Decided by Member D')).toBeInTheDocument();
  });
});
