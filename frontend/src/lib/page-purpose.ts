export const PAGE_PURPOSE = {
  dashboard: 'What is happening across my engineering environment?',
  repositories: 'Which codebases are connected, and how are they performing?',
  repository: 'How healthy is this codebase?',
  pullRequests: 'Which changes need review first?',
  pullRequest: 'Is this change safe to merge?',
  security: 'What security problems exist?',
  codeQuality: 'Where is technical debt accumulating?',
  dependencies: 'What is the dependency health of this workspace?',
  analytics: 'Is engineering health improving or getting worse?',
  analysisRuns: 'Trace analysis execution, results, and historical snapshots.',
} as const
