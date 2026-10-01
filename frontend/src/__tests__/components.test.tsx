// @vitest-environment jsdom
import '../test/setup';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import React from 'react';
import { ResponseResult } from '../components/ResponseResult';
import { FeedbackPanel } from '../components/FeedbackPanel';
import { CrossClientSanityBadge } from '../components/CrossClientSanityBadge';
import { ReplyWorkbench } from '../components/ReplyWorkbench';
import { AgentResponse, Client, CompareResponse, RecalledMemory } from '../types/api';
import { api } from '../api/client';

vi.mock('../api/client', () => ({
  api: {
    submitFeedback: vi.fn(),
    respond: vi.fn(),
  },
}));

const mockClientA: Client = {
  id: 'c1_apex',
  name: 'Apex Dynamics',
  contact_name: 'Sarah Chen',
  contact_email: 'sarah@apex.example',
  industry: 'Tech',
  primary_quirk: 'Async preferred',
};

const mockMemoryA: RecalledMemory = {
  id: 'mem-101',
  text: 'Sarah Chen prefers Slack updates over early morning calls.',
  type: 'experience',
  context: 'Communication preferences',
  metadata: { client_id: 'c1_apex', interaction_id: 'int_001' },
  tags: ['client:c1_apex'],
  entities: [],
  source_fact_ids: [],
  scores: { final: 0.92, reranker: 0.9, semantic: 0.85, keyword: 0.8 },
  source_interaction_id: 'int_001',
};

const mockAgentResponse: AgentResponse = {
  response_id: 'resp_test_123',
  client_id: 'c1_apex',
  incoming_text: 'Can we meet at 9am?',
  memory_enabled: true,
  draft_reply: 'Hello Sarah, I will post an async update in Slack instead.',
  client_brief: [
    {
      text: 'Client dislikes calls before 11am and prefers Slack.',
      source_interaction_ids: ['int_001'],
      source_memory_ids: ['mem-101'],
    },
  ],
  risk_flags: [
    {
      type: 'timing',
      text: 'Requesting 9am meeting violates 11am morning constraint.',
      sources: ['int_001'],
    },
  ],
  memory_used: [mockMemoryA],
  warnings: [],
  model_used: 'openai/gpt-oss-120b',
};

const mockAgentResponseOff: AgentResponse = {
  response_id: 'resp_test_124',
  client_id: 'c1_apex',
  incoming_text: 'Can we meet at 9am?',
  memory_enabled: false,
  draft_reply: 'Sure, 9am works great for me!',
  client_brief: [],
  risk_flags: [],
  memory_used: [],
  warnings: [],
  model_used: 'openai/gpt-oss-120b',
};

describe('Frontend Component Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders ResponseResult with draft, brief, risk flags, and model pill', () => {
    const handleOpenMemory = vi.fn();

    render(
      <ResponseResult
        response={mockAgentResponse}
        onOpenSourceMemory={handleOpenMemory}
      />
    );

    expect(screen.getByText(/Memory-Aware Reply/i)).toBeInTheDocument();
    expect(screen.getByText(/openai\/gpt-oss-120b/i)).toBeInTheDocument();
    expect(screen.getByText(/Hello Sarah, I will post an async update/i)).toBeInTheDocument();
    expect(screen.getByText(/Client dislikes calls before 11am/i)).toBeInTheDocument();
    expect(screen.getByText(/Requesting 9am meeting violates/i)).toBeInTheDocument();
  });

  it('disables feedback buttons and shows confirmation after submission', async () => {
    vi.mocked(api.submitFeedback).mockResolvedValue({ status: 'success', feedback: {} });

    render(<FeedbackPanel responseId="resp_test_123" />);

    const wentWellBtn = screen.getByRole('button', { name: /Went Well/i });
    expect(wentWellBtn).not.toBeDisabled();

    fireEvent.click(wentWellBtn);

    await waitFor(() => {
      expect(api.submitFeedback).toHaveBeenCalledWith({
        response_id: 'resp_test_123',
        outcome: 'went_well',
        notes: undefined,
      });
      expect(screen.getByText(/Feedback recorded as/i)).toBeInTheDocument();
    });
  });

  it('CrossClientSanityBadge verifies active client tag and detects leakage', () => {
    const { rerender } = render(
      <CrossClientSanityBadge
        activeClient={mockClientA}
        recalledMemories={[mockMemoryA]}
      />
    );

    expect(screen.getByText(/STRICT ISOLATION VERIFIED/i)).toBeInTheDocument();

    const leakedMemory: RecalledMemory = {
      ...mockMemoryA,
      id: 'mem-leaked-202',
      tags: ['client:c2_horizon'],
    };

    rerender(
      <CrossClientSanityBadge
        activeClient={mockClientA}
        recalledMemories={[leakedMemory]}
      />
    );

    expect(screen.getByText(/LEAKAGE DETECTED/i)).toBeInTheDocument();
  });

  it('renders warning banner for new client or degraded memory', () => {
    const degradedResponse: AgentResponse = {
      ...mockAgentResponse,
      warnings: ['No past memory found for this client (new client or initial interaction).'],
      memory_used: [],
    };

    render(
      <ResponseResult
        response={degradedResponse}
        onOpenSourceMemory={vi.fn()}
      />
    );

    expect(screen.getByText(/No past memory found for this client/i)).toBeInTheDocument();
  });

  it('ReplyWorkbench in compare mode renders memory-on and memory-off side-by-side', async () => {
    const compareMockResponse: CompareResponse = {
      memory_on: mockAgentResponse,
      memory_off: mockAgentResponseOff,
    };

    vi.mocked(api.respond).mockResolvedValue(compareMockResponse);

    render(
      <ReplyWorkbench
        activeClient={mockClientA}
        onOpenSourceMemory={vi.fn()}
        onResponseGenerated={vi.fn()}
      />
    );

    const compareBtn = screen.getByRole('button', { name: /Compare View/i });
    fireEvent.click(compareBtn);

    const textarea = screen.getByPlaceholderText(/Paste client email/i);
    fireEvent.change(textarea, { target: { value: 'Can we meet at 9am?' } });

    const submitBtn = screen.getByRole('button', { name: /Generate Draft Reply/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(api.respond).toHaveBeenCalledWith({
        client_id: 'c1_apex',
        incoming_text: 'Can we meet at 9am?',
        compare: true,
      });

      expect(screen.getByText(/Memory-Aware Reply \(Memory ON\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Generic Draft \(Memory OFF\)/i)).toBeInTheDocument();
      expect(screen.getByText(/Hello Sarah, I will post an async update in Slack instead/i)).toBeInTheDocument();
      expect(screen.getByText(/Sure, 9am works great for me!/i)).toBeInTheDocument();
    });
  });

  it('simulated API 500 error renders retryable error banner', async () => {
    vi.mocked(api.respond).mockRejectedValue(new Error('HTTP 500: Internal Server Error'));

    render(
      <ReplyWorkbench
        activeClient={mockClientA}
        onOpenSourceMemory={vi.fn()}
        onResponseGenerated={vi.fn()}
      />
    );

    const textarea = screen.getByPlaceholderText(/Paste client email/i);
    fireEvent.change(textarea, { target: { value: 'Hello server error test' } });

    const submitBtn = screen.getByRole('button', { name: /Generate Draft Reply/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/Generation Error/i)).toBeInTheDocument();
      expect(screen.getByText(/HTTP 500: Internal Server Error/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /Retry/i })).toBeInTheDocument();
    });
  });
});
