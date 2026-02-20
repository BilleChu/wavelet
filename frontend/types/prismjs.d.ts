declare module 'prismjs/components/prism-core' {
  export const highlight: (code: string, grammar: unknown, language: string) => string;
  export const languages: Record<string, unknown>;
}

declare module 'prismjs/components/prism-python' {
  // This module adds Python language support to Prism
}

declare module 'prismjs/themes/prism-tomorrow.css' {
  // CSS module
}
