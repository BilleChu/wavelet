'use client'

import Link from 'next/link'
import { Store, Sparkles } from 'lucide-react'
import { Button } from '@/components/ui'

interface SkillMarketButtonProps {
  installedCount?: number
  showLabel?: boolean
}

export default function SkillMarketButton({ installedCount = 0, showLabel = true }: SkillMarketButtonProps) {
  return (
    <Link href="/skills/marketplace">
      <Button
        variant="outline"
        className="gap-2 bg-gradient-to-r from-purple-500/10 to-indigo-500/10 border-purple-500/30 hover:from-purple-500/20 hover:to-indigo-500/20 transition-all group"
      >
        <div className="relative">
          <Store className="w-4 h-4 text-purple-400 group-hover:scale-110 transition-transform" />
          {installedCount > 0 && (
            <span className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-purple-500 rounded-full flex items-center justify-center">
              <span className="text-[10px] text-white font-bold">{installedCount}</span>
            </span>
          )}
        </div>
        {showLabel && (
          <span className="text-sm font-medium text-purple-300">技能市场</span>
        )}
      </Button>
    </Link>
  )
}

export function SkillRecommendation({ skills }: { skills: Array<{ id: string; name: string; description: string }> }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
      {skills.map((skill) => (
        <Link
          key={skill.id}
          href={`/skills/marketplace?skill=${skill.id}`}
          className="group"
        >
          <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.05] hover:border-purple-500/30 transition-all text-center">
            <div className="w-10 h-10 mx-auto rounded-lg bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center mb-2 group-hover:scale-110 transition-transform">
              <Sparkles className="w-5 h-5 text-white" />
            </div>
            <p className="text-xs text-white font-medium mb-1">{skill.name}</p>
            <p className="text-[10px] text-zinc-500 line-clamp-2">{skill.description}</p>
          </div>
        </Link>
      ))}
    </div>
  )
}
