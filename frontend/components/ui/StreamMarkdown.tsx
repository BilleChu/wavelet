'use client'

import { Streamdown } from 'streamdown'
import 'streamdown/styles.css'

interface StreamMarkdownProps {
  content: string
  className?: string
}

export function StreamMarkdown({ content, className = '' }: StreamMarkdownProps) {
  return (
    <div className={`streamdown-container ${className}`}>
      <Streamdown>{content}</Streamdown>
    </div>
  )
}

export default StreamMarkdown
