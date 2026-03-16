import { Link } from 'react-router-dom';

const features = [
  {
    title: 'Create Prompts',
    description:
      'Design and refine prompt templates with a powerful editor. Use Jinja2 syntax with dataset column placeholders for dynamic content.',
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M16.862 4.487l1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
      </svg>
    ),
  },
  {
    title: 'Review & Approve',
    description:
      'Structured review workflows with approval, revision requests, and comment threads. Track every change with full audit history.',
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9 12.75L11.25 15 15 9.75M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0z" />
      </svg>
    ),
  },
  {
    title: 'HuggingFace Integration',
    description:
      'Import datasets directly from HuggingFace Hub. Browse configs, splits, and samples without leaving the platform.',
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M20.25 6.375c0 2.278-3.694 4.125-8.25 4.125S3.75 8.653 3.75 6.375m16.5 0c0-2.278-3.694-4.125-8.25-4.125S3.75 4.097 3.75 6.375m16.5 0v11.25c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125V6.375m16.5 0v3.75m-16.5-3.75v3.75m16.5 0v3.75C20.25 16.153 16.556 18 12 18s-8.25-1.847-8.25-4.125v-3.75m16.5 0c0 2.278-3.694 4.125-8.25 4.125s-8.25-1.847-8.25-4.125" />
      </svg>
    ),
  },
  {
    title: 'AI Generation',
    description:
      'Generate multiple prompt variants with AI assistance. Test prompts against live LLM models via OpenRouter integration.',
    icon: (
      <svg className="h-8 w-8" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 0 0-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 0 0 2.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 0 0 2.456 2.456L21.75 6l-1.035.259a3.375 3.375 0 0 0-2.456 2.456zM16.894 20.567L16.5 21.75l-.394-1.183a2.25 2.25 0 0 0-1.423-1.423L13.5 18.75l1.183-.394a2.25 2.25 0 0 0 1.423-1.423l.394-1.183.394 1.183a2.25 2.25 0 0 0 1.423 1.423l1.183.394-1.183.394a2.25 2.25 0 0 0-1.423 1.423z" />
      </svg>
    ),
  },
];

export default function Home() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <section className="relative overflow-hidden px-6 py-24 sm:py-32 lg:px-8">
        <div className="absolute inset-0 -z-10 bg-[radial-gradient(45rem_50rem_at_top,theme(colors.indigo.100),transparent)] dark:bg-[radial-gradient(45rem_50rem_at_top,theme(colors.indigo.900/20),transparent)]" />
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-5xl font-extrabold tracking-tight sm:text-7xl">
            <span className="bg-gradient-to-r from-blue-600 via-purple-600 to-indigo-600 bg-clip-text text-transparent">
              PromptLab
            </span>
          </h1>
          <p className="mt-6 text-xl leading-8 text-gray-600 dark:text-gray-300">
            Collaborative Prompt Engineering Platform
          </p>
          <p className="mt-4 text-base leading-7 text-gray-500 dark:text-gray-400 max-w-2xl mx-auto">
            Design, review, and refine prompt templates for NLP tasks. Integrate with HuggingFace datasets,
            leverage AI-assisted generation, and manage collaborative workflows -- all in one place.
          </p>
          <div className="mt-10 flex items-center justify-center gap-x-4">
            <Link
              to="/app/login"
              className="rounded-lg bg-blue-600 px-6 py-3 text-sm font-semibold text-white shadow-sm hover:bg-blue-500 transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-600"
            >
              Get Started
            </Link>
            <a
              href="https://github.com/MagedSaeed/PromptLab"
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm font-semibold leading-6 text-gray-700 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              View on GitHub <span aria-hidden="true">&rarr;</span>
            </a>
          </div>
        </div>
      </section>

      {/* Features Section */}
      <section className="py-16 px-6 lg:px-8">
        <div className="mx-auto max-w-6xl">
          <div className="text-center mb-16">
            <h2 className="text-3xl font-bold tracking-tight text-gray-900 dark:text-white sm:text-4xl">
              Everything you need for prompt engineering
            </h2>
            <p className="mt-4 text-lg text-gray-500 dark:text-gray-400">
              A complete toolkit for teams working on NLP prompt design and dataset curation.
            </p>
          </div>
          <div className="grid grid-cols-1 gap-8 sm:grid-cols-2 lg:grid-cols-4">
            {features.map((feature) => (
              <div
                key={feature.title}
                className="relative rounded-2xl border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800/50 p-8 shadow-sm hover:shadow-md transition-shadow"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-blue-50 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400">
                  {feature.icon}
                </div>
                <h3 className="mt-6 text-lg font-semibold text-gray-900 dark:text-white">
                  {feature.title}
                </h3>
                <p className="mt-2 text-sm leading-6 text-gray-500 dark:text-gray-400">
                  {feature.description}
                </p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 px-6 lg:px-8">
        <div className="mx-auto max-w-3xl text-center">
          <div className="rounded-2xl bg-gradient-to-r from-blue-600 to-purple-600 p-10 shadow-lg">
            <h2 className="text-2xl font-bold text-white sm:text-3xl">
              Ready to start building better prompts?
            </h2>
            <p className="mt-4 text-blue-100">
              Sign in with your Google account to join your team and start collaborating.
            </p>
            <Link
              to="/app/login"
              className="mt-8 inline-block rounded-lg bg-white px-6 py-3 text-sm font-semibold text-blue-600 shadow-sm hover:bg-gray-50 transition-colors"
            >
              Sign in to PromptLab
            </Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-gray-200 dark:border-gray-700 py-8 px-6">
        <div className="mx-auto max-w-6xl text-center text-sm text-gray-500 dark:text-gray-400">
          PromptLab &mdash; Collaborative Prompt Engineering Platform
        </div>
      </footer>
    </div>
  );
}
