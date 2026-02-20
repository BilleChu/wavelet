'use client';

import { useCallback, useEffect, useState, useRef } from 'react';
import {
  Bot,
  ChevronRight,
  Loader2,
  MessageCircle,
  Plus,
  RefreshCw,
  Search,
  Send,
  Sparkles,
  Star,
  User,
  X,
  Zap,
} from 'lucide-react';

import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { API_BASE_URL } from '@/services/apiConfig';

interface Skill {
  skill_id: string;
  name: string;
  description: string;
  triggers: string[];
}

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
  skill_id?: string;
  isStreaming?: boolean;
}

interface SkillsMarketplaceProps {
  onSkillSelect?: (skillId: string) => void;
}

export function SkillsMarketplace({ onSkillSelect }: SkillsMarketplaceProps) {
  const [skills, setSkills] = useState<Skill[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedSkill, setSelectedSkill] = useState<Skill | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [favorites, setFavorites] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadSkills();
    loadFavorites();
  }, []);

  const loadSkills = useCallback(async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/skills`);
      if (response.ok) {
        const data = await response.json();
        setSkills(data.skills || []);
      }
    } catch (error) {
      console.error('Failed to load skills:', error);
    } finally {
      setLoading(false);
    }
  }, []);

  const loadFavorites = useCallback(() => {
    const saved = localStorage.getItem('skill_favorites');
    if (saved) {
      setFavorites(new Set(JSON.parse(saved)));
    }
  }, []);

  const toggleFavorite = useCallback((skillId: string) => {
    setFavorites((prev) => {
      const next = new Set(prev);
      if (next.has(skillId)) {
        next.delete(skillId);
      } else {
        next.add(skillId);
      }
      localStorage.setItem('skill_favorites', JSON.stringify([...next]));
      return next;
    });
  }, []);

  const handleSkillSelect = (skill: Skill) => {
    setSelectedSkill(skill);
    onSkillSelect?.(skill.skill_id);
  };

  const filteredSkills = skills.filter((skill) => {
    if (!searchQuery) return true;
    return (
      skill.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
      skill.triggers.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
    );
  });

  return (
    <div className="space-y-6">
      <Card className="bg-zinc-900/50 border-zinc-800">
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-white" />
              </div>
              <div>
                <CardTitle>Skills 市场</CardTitle>
                <CardDescription>选择一个投资大师的技能开始对话</CardDescription>
              </div>
            </div>
            <Button variant="outline" size="sm" onClick={loadSkills} disabled={loading}>
              <RefreshCw className={`w-4 h-4 mr-2 ${loading ? 'animate-spin' : ''}`} />
              刷新
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          <div className="mb-4">
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-zinc-400" />
              <Input
                placeholder="搜索技能..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 bg-zinc-800 border-zinc-700"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {filteredSkills.map((skill) => (
              <div
                key={skill.skill_id}
                className={`p-4 rounded-lg border cursor-pointer transition-all ${
                  selectedSkill?.skill_id === skill.skill_id
                    ? 'border-purple-500 bg-purple-500/10'
                    : 'border-zinc-700 hover:border-zinc-600'
                }`}
                onClick={() => handleSkillSelect(skill)}
              >
                <div className="flex items-start justify-between mb-2">
                  <div className="flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/20 to-indigo-600/20 flex items-center justify-center">
                      <Bot className="w-4 h-4 text-purple-400" />
                    </div>
                    <h4 className="font-medium">{skill.name}</h4>
                  </div>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="h-6 w-6 p-0"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleFavorite(skill.skill_id);
                    }}
                  >
                    <Star
                      className={`w-4 h-4 ${
                        favorites.has(skill.skill_id)
                          ? 'fill-yellow-400 text-yellow-400'
                          : 'text-zinc-500'
                      }`}
                    />
                  </Button>
                </div>
                <p className="text-sm text-zinc-400 mb-3">{skill.description}</p>
                <div className="flex flex-wrap gap-1">
                  {skill.triggers.slice(0, 3).map((trigger) => (
                    <Badge key={trigger} variant="outline" size="sm">
                      {trigger}
                    </Badge>
                  ))}
                </div>
              </div>
            ))}
          </div>

          {filteredSkills.length === 0 && !loading && (
            <div className="text-center py-12 text-zinc-500">
              <Search className="w-12 h-12 mx-auto opacity-50 mb-4" />
              <p>没有找到匹配的技能</p>
            </div>
          )}
        </CardContent>
      </Card>

      {selectedSkill && (
        <SkillChatPanel
          skill={selectedSkill}
          onClose={() => setSelectedSkill(null)}
        />
      )}
    </div>
  );
}

function SkillChatPanel({ skill, onClose }: { skill: Skill; onClose: () => void }) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const scrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    fetchSuggestions();
    inputRef.current?.focus();
  }, [skill.skill_id]);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const fetchSuggestions = async () => {
    try {
      const response = await fetch(`${API_BASE_URL}/api/chat/suggestions`);
      if (response.ok) {
        const data = await response.json();
        setSuggestions(data.suggestions || []);
      }
    } catch (error) {
      console.error('Failed to fetch suggestions:', error);
    }
  };

  const sendMessage = useCallback(async (query: string) => {
    if (!query.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: query.trim(),
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    const assistantMessageId = (Date.now() + 1).toString();
    const assistantMessage: Message = {
      id: assistantMessageId,
      role: 'assistant',
      content: '',
      timestamp: new Date(),
      skill_id: skill.skill_id,
      isStreaming: true,
    };

    setMessages((prev) => [...prev, assistantMessage]);

    try {
      const history = messages.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch(`${API_BASE_URL}/api/chat/skill/${skill.skill_id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          query: query.trim(),
          history,
          stream: true,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to send message');
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No reader available');
      }

      const decoder = new TextDecoder();
      let accumulatedContent = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const chunk = decoder.decode(value, { stream: true });
        const lines = chunk.split('\n');

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'content' && data.delta) {
                accumulatedContent += data.delta;
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, content: accumulatedContent }
                      : m
                  )
                );
              } else if (data.type === 'done') {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, isStreaming: false }
                      : m
                  )
                );
              } else if (data.type === 'error') {
                setMessages((prev) =>
                  prev.map((m) =>
                    m.id === assistantMessageId
                      ? { ...m, content: `错误: ${data.error}`, isStreaming: false }
                      : m
                  )
                );
              }
            } catch {
              // Ignore parse errors
            }
          }
        }
      }
    } catch (error) {
      console.error('Chat error:', error);
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantMessageId
            ? { ...m, content: '抱歉，发生了错误，请稍后重试。', isStreaming: false }
            : m
        )
      );
    } finally {
      setIsLoading(false);
    }
  }, [messages, isLoading, skill.skill_id]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const handleSuggestionClick = (suggestion: string) => {
    sendMessage(suggestion);
  };

  return (
    <Card className="bg-zinc-900/50 border-zinc-800">
      <CardHeader className="pb-3 border-b border-zinc-800">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center">
              <Bot className="w-5 h-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-lg">{skill.name}</CardTitle>
              <p className="text-xs text-zinc-500">{skill.description}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="w-4 h-4" />
          </Button>
        </div>
      </CardHeader>

      <CardContent className="p-0">
        <ScrollArea className="h-80 p-4" ref={scrollRef}>
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center py-8">
              <MessageCircle className="w-12 h-12 text-zinc-600 mb-4" />
              <p className="text-zinc-400 mb-4">有什么可以帮助您的？</p>
              {suggestions.length > 0 && (
                <div className="flex flex-wrap gap-2 justify-center">
                  {suggestions.slice(0, 3).map((suggestion) => (
                    <Badge
                      key={suggestion}
                      variant="outline"
                      className="cursor-pointer hover:bg-zinc-700 max-w-full truncate"
                      onClick={() => handleSuggestionClick(suggestion)}
                    >
                      {suggestion}
                    </Badge>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message) => (
                <div
                  key={message.id}
                  className={`flex gap-3 ${
                    message.role === 'user' ? 'justify-end' : 'justify-start'
                  }`}
                >
                  {message.role === 'assistant' && (
                    <div className="w-7 h-7 rounded-full bg-gradient-to-br from-purple-500 to-indigo-600 flex items-center justify-center flex-shrink-0">
                      <Bot className="w-3.5 h-3.5 text-white" />
                    </div>
                  )}
                  <div
                    className={`max-w-[80%] rounded-lg px-3 py-2 text-sm ${
                      message.role === 'user'
                        ? 'bg-purple-500 text-white'
                        : 'bg-zinc-800 text-zinc-200'
                    }`}
                  >
                    <div className="whitespace-pre-wrap break-words">
                      {message.content}
                      {message.isStreaming && (
                        <span className="inline-block w-1.5 h-4 ml-0.5 bg-purple-400 animate-pulse" />
                      )}
                    </div>
                  </div>
                  {message.role === 'user' && (
                    <div className="w-7 h-7 rounded-full bg-zinc-700 flex items-center justify-center flex-shrink-0">
                      <User className="w-3.5 h-3.5 text-zinc-300" />
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </ScrollArea>

        <div className="p-4 border-t border-zinc-800">
          <div className="flex gap-2">
            <Input
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入您的问题..."
              className="bg-zinc-800 border-zinc-700"
              disabled={isLoading}
            />
            <Button
              size="icon"
              onClick={() => sendMessage(input)}
              disabled={!input.trim() || isLoading}
              className="bg-purple-500 hover:bg-purple-600"
            >
              {isLoading ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <Send className="w-4 h-4" />
              )}
            </Button>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default SkillsMarketplace;
