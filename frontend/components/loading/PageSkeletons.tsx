'use client'

/**
 * Page Loading Skeletons.
 *
 * Provides loading placeholder components for different pages.
 */

import React from 'react'
import { Skeleton } from '@/components/ui/skeleton'

export function PageSkeleton() {
  return (
    <div className="min-h-screen bg-[#08090c] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <Skeleton className="h-10 w-48 bg-[#1a1d24]" />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Skeleton className="h-32 bg-[#1a1d24]" />
          <Skeleton className="h-32 bg-[#1a1d24]" />
          <Skeleton className="h-32 bg-[#1a1d24]" />
        </div>
        <Skeleton className="h-96 bg-[#1a1d24]" />
      </div>
    </div>
  )
}

export function ChatSkeleton() {
  return (
    <div className="min-h-screen bg-[#08090c] flex flex-col">
      <div className="flex-1 p-4 space-y-4">
        {[1, 2, 3].map((i) => (
          <div key={i} className={`flex ${i % 2 === 0 ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[80%] ${i % 2 === 0 ? 'order-2' : ''}`}>
              <Skeleton className="h-16 w-64 bg-[#1a1d24]" />
            </div>
          </div>
        ))}
      </div>
      <div className="p-4 border-t border-[#1a1d24]">
        <Skeleton className="h-12 w-full bg-[#1a1d24]" />
      </div>
    </div>
  )
}

export function QuantSkeleton() {
  return (
    <div className="min-h-screen bg-[#08090c] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-32 bg-[#1a1d24]" />
          <Skeleton className="h-10 w-24 bg-[#1a1d24]" />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-4 gap-4">
          <div className="lg:col-span-1 space-y-4">
            <Skeleton className="h-64 bg-[#1a1d24]" />
            <Skeleton className="h-48 bg-[#1a1d24]" />
          </div>
          
          <div className="lg:col-span-3 space-y-4">
            <Skeleton className="h-80 bg-[#1a1d24]" />
            <div className="grid grid-cols-2 gap-4">
              <Skeleton className="h-48 bg-[#1a1d24]" />
              <Skeleton className="h-48 bg-[#1a1d24]" />
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export function KnowledgeGraphSkeleton() {
  return (
    <div className="min-h-screen bg-[#08090c] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <div className="flex justify-between items-center">
          <Skeleton className="h-8 w-40 bg-[#1a1d24]" />
          <Skeleton className="h-10 w-32 bg-[#1a1d24]" />
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <div className="lg:col-span-2">
            <Skeleton className="h-[600px] bg-[#1a1d24]" />
          </div>
          <div className="space-y-4">
            <Skeleton className="h-48 bg-[#1a1d24]" />
            <Skeleton className="h-48 bg-[#1a1d24]" />
            <Skeleton className="h-32 bg-[#1a1d24]" />
          </div>
        </div>
      </div>
    </div>
  )
}

export function DatacenterSkeleton() {
  return (
    <div className="min-h-screen bg-[#08090c] p-6">
      <div className="max-w-7xl mx-auto space-y-6">
        <Skeleton className="h-10 w-48 bg-[#1a1d24]" />
        
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <Skeleton key={i} className="h-24 bg-[#1a1d24]" />
          ))}
        </div>
        
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Skeleton className="h-80 bg-[#1a1d24]" />
          <Skeleton className="h-80 bg-[#1a1d24]" />
        </div>
        
        <Skeleton className="h-64 bg-[#1a1d24]" />
      </div>
    </div>
  )
}

export function TableSkeleton({ rows = 5, columns = 4 }: { rows?: number; columns?: number }) {
  return (
    <div className="w-full">
      <div className="grid gap-2 mb-2" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
        {Array.from({ length: columns }).map((_, i) => (
          <Skeleton key={i} className="h-8 bg-[#1a1d24]" />
        ))}
      </div>
      {Array.from({ length: rows }).map((_, rowIndex) => (
        <div key={rowIndex} className="grid gap-2 mb-2" style={{ gridTemplateColumns: `repeat(${columns}, 1fr)` }}>
          {Array.from({ length: columns }).map((_, colIndex) => (
            <Skeleton key={colIndex} className="h-12 bg-[#1a1d24]" />
          ))}
        </div>
      ))}
    </div>
  )
}

export function CardSkeleton() {
  return (
    <div className="bg-[#0d1117] border border-[#30363d] rounded-lg p-4 space-y-3">
      <Skeleton className="h-6 w-24 bg-[#1a1d24]" />
      <Skeleton className="h-4 w-full bg-[#1a1d24]" />
      <Skeleton className="h-4 w-3/4 bg-[#1a1d24]" />
      <div className="flex justify-between pt-2">
        <Skeleton className="h-8 w-20 bg-[#1a1d24]" />
        <Skeleton className="h-8 w-16 bg-[#1a1d24]" />
      </div>
    </div>
  )
}
