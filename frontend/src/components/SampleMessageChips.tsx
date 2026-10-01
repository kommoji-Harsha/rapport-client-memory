import React from 'react';
import { Sparkles } from 'lucide-react';

interface SampleMessageChipsProps {
  clientId?: string;
  onSelectSample: (text: string) => void;
}

const SAMPLE_MESSAGES: Record<string, { label: string; text: string }[]> = {
  c1_apex: [
    {
      label: 'Early Morning Call',
      text: 'Hi Jules! Can we get on a quick alignment call tomorrow at 9:00 AM EST to go over the sprint deliverables?',
    },
    {
      label: 'Async Update Check',
      text: 'Hey! Is there any blocker on the API auth module? Please post a quick update in Slack when you get a chance.',
    },
  ],
  c2_horizon: [
    {
      label: 'Invoice #04 Status',
      text: 'Hi! Just checking in on Invoice #INV-2024-04 sent last month. When can we expect payment clearance?',
    },
    {
      label: 'Payment Term Query',
      text: 'Hello Marcus, checking if the treasury batch run on the 15th will cover the outstanding $5,000 balance?',
    },
  ],
  c3_nexus: [
    {
      label: 'Tech Spec Submission',
      text: 'Hi Elena! We finished drafting the GraphQL API schema and retry mechanisms for Phase 2. Ready for signoff.',
    },
    {
      label: 'Dave Tech Approval',
      text: 'Hey Jules! Dave evaluated the webhook retry mechanism and gave green light. Can you send over the formal budget contract?',
    },
  ],
  c4_catalyst: [
    {
      label: 'Mid-sprint Add-on',
      text: 'Hey Jules! Great progress on the CMS. Could you also quickly throw in video thumbnail compression and analytics tagging before Friday?',
    },
    {
      label: 'Scope Baseline Check',
      text: 'Hi Jordan! We are locking down Sprint 4 baseline scope. Please review the deliverables before we start.',
    },
  ],
  c5_swiftpulse: [
    {
      label: 'Status Report Request',
      text: 'Dr. Thorne here. Please send a progress update on the HIPAA encryption audit and remaining billable hours for this month.',
    },
    {
      label: 'Budget Cap Query',
      text: 'Hello Aris! We are approaching the $5,000 monthly cloud infrastructure cap. Here is our proposed optimization plan.',
    },
  ],
  c6_vanguard: [
    {
      label: 'Weekly Update Channel',
      text: 'Hi Liam! Sending over the weekly status update for the fleet tracking integration. Should I post this in Slack or email?',
    },
    {
      label: 'Slack Channel Sync',
      text: 'Hey Jules! Reminder that our operations team operates exclusively in #vanguard-dev on Slack now.',
    },
  ],
};

const DEFAULT_SAMPLES = [
  {
    label: 'Early Sync Request',
    text: 'Can we schedule a 9:00 AM sync call tomorrow morning to review the project scope and budget?',
  },
  {
    label: 'Feature Scope Change',
    text: 'Loved the demo! Could we also add automated PDF export and custom video compression before Friday?',
  },
  {
    label: 'Invoice Followup',
    text: 'Checking in on the status of outstanding Invoice #INV-2024-02 due last week.',
  },
];

export const SampleMessageChips: React.FC<SampleMessageChipsProps> = ({
  clientId,
  onSelectSample,
}) => {
  const samples = (clientId && SAMPLE_MESSAGES[clientId]) || DEFAULT_SAMPLES;

  return (
    <div className="flex items-center space-x-2 overflow-x-auto py-1">
      <span className="text-xs font-medium text-slate-500 dark:text-slate-400 shrink-0 flex items-center gap-1">
        <Sparkles className="w-3 h-3 text-brand-500" />
        Sample messages:
      </span>
      {samples.map((sample, idx) => (
        <button
          key={idx}
          type="button"
          onClick={() => onSelectSample(sample.text)}
          className="px-2.5 py-1 rounded-full text-xs font-medium bg-slate-100 dark:bg-slate-800 text-slate-700 dark:text-slate-300 hover:bg-brand-50 hover:text-brand-700 dark:hover:bg-brand-950 dark:hover:text-brand-300 border border-slate-200 dark:border-slate-700 transition-colors shrink-0"
        >
          {sample.label}
        </button>
      ))}
    </div>
  );
};
