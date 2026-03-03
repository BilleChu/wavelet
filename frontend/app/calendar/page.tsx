'use client';

import { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { CalendarDays, Clock, RefreshCw, Download, AlertCircle, TrendingUp, Globe, Zap } from 'lucide-react';
import { calendarService, CalendarEvent, CountryInfo, ImportanceLevel, CalendarStats } from '@/services/calendarService';

const IMPORTANCE_CONFIG = {
  high: { label: '高', color: 'bg-red-500', textColor: 'text-red-400', emoji: '🔴' },
  medium: { label: '中', color: 'bg-yellow-500', textColor: 'text-yellow-400', emoji: '🟡' },
  low: { label: '低', color: 'bg-green-500', textColor: 'text-green-400', emoji: '🟢' },
};

function formatEventTime(time: string | null): string {
  if (!time) return '--:--';
  return time;
}

function EventCard({ event, isPast }: { event: CalendarEvent; isPast: boolean }) {
  const config = IMPORTANCE_CONFIG[event.importance] || IMPORTANCE_CONFIG.low;
  
  return (
    <div className={`p-3 rounded-lg border ${isPast ? 'bg-zinc-900/30 border-zinc-800' : 'bg-zinc-900/50 border-zinc-700'} hover:border-zinc-600 transition-colors`}>
      <div className="flex items-start justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">{config.emoji}</span>
          <span className="text-sm font-medium text-zinc-200">{event.event}</span>
        </div>
        <Badge variant="outline" className={`${config.textColor} border-current text-xs`}>
          {config.label}
        </Badge>
      </div>
      
      <div className="flex items-center gap-4 text-xs text-zinc-400">
        <div className="flex items-center gap-1">
          <Clock className="w-3 h-3" />
          <span>{formatEventTime(event.time)}</span>
        </div>
        {event.currency && (
          <div className="flex items-center gap-1">
            <Globe className="w-3 h-3" />
            <span>{event.currency}</span>
          </div>
        )}
        {event.country && (
          <span className="text-zinc-500">{event.country}</span>
        )}
      </div>
      
      <div className="grid grid-cols-3 gap-2 mt-3 text-xs">
        <div>
          <span className="text-zinc-500">实际: </span>
          <span className={event.actual ? 'text-zinc-300' : 'text-zinc-600'}>{event.actual || '--'}</span>
        </div>
        <div>
          <span className="text-zinc-500">预测: </span>
          <span className={event.forecast ? 'text-zinc-300' : 'text-zinc-600'}>{event.forecast || '--'}</span>
        </div>
        <div>
          <span className="text-zinc-500">前值: </span>
          <span className={event.previous ? 'text-zinc-300' : 'text-zinc-600'}>{event.previous || '--'}</span>
        </div>
      </div>
    </div>
  );
}

function DateGroup({ date, events, isPast }: { date: string; events: CalendarEvent[]; isPast: boolean }) {
  const dateObj = new Date(date);
  const dayName = dateObj.toLocaleDateString('zh-CN', { weekday: 'short' });
  const formattedDate = dateObj.toLocaleDateString('zh-CN', { month: 'long', day: 'numeric' });
  const isToday = date === new Date().toISOString().split('T')[0];
  
  return (
    <div className="mb-6">
      <div className={`flex items-center gap-2 mb-3 ${isToday ? 'text-amber-400' : 'text-zinc-400'}`}>
        <CalendarDays className="w-4 h-4" />
        <span className="font-medium">{formattedDate}</span>
        <span className="text-xs">({dayName})</span>
        {isToday && <Badge className="bg-amber-500 text-black text-xs">今天</Badge>}
        <Badge variant="outline" className="text-xs">{events.length} 事件</Badge>
      </div>
      <div className="space-y-2">
        {events.map((event) => (
          <EventCard key={event.event_id} event={event} isPast={isPast} />
        ))}
      </div>
    </div>
  );
}

export default function CalendarPage() {
  const [loading, setLoading] = useState(true);
  const [fetching, setFetching] = useState(false);
  const [events, setEvents] = useState<CalendarEventsResponse | null>(null);
  const [stats, setStats] = useState<CalendarStats | null>(null);
  const [countries, setCountries] = useState<CountryInfo[]>([]);
  const [importanceLevels, setImportanceLevels] = useState<ImportanceLevel[]>([]);
  
  const [selectedCountry, setSelectedCountry] = useState<string>('all');
  const [selectedImportance, setSelectedImportance] = useState<string>('all');
  const [activeTab, setActiveTab] = useState<string>('upcoming');

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [countriesRes, levelsRes, statsRes] = await Promise.all([
        calendarService.getCountries(),
        calendarService.getImportanceLevels(),
        calendarService.getStats(),
      ]);
      
      setCountries(countriesRes.countries);
      setImportanceLevels(levelsRes.levels);
      setStats(statsRes);
      
      const eventsRes = await calendarService.getEvents({
        countries: selectedCountry !== 'all' ? selectedCountry : undefined,
        importances: selectedImportance !== 'all' ? selectedImportance : undefined,
        past_days: 7,
        future_days: 30,
        source: 'db',
      });
      
      setEvents(eventsRes);
    } catch (error) {
      console.error('Failed to load calendar data:', error);
    } finally {
      setLoading(false);
    }
  }, [selectedCountry, selectedImportance]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const handleFetchNewData = async () => {
    setFetching(true);
    try {
      await calendarService.fetchAndSave({
        past_days: 7,
        future_days: 30,
      });
      
      setTimeout(() => {
        loadData();
      }, 2000);
    } catch (error) {
      console.error('Failed to fetch data:', error);
    } finally {
      setFetching(false);
    }
  };

  const groupEventsByDate = (events: CalendarEvent[], isPast: boolean) => {
    const grouped: Record<string, CalendarEvent[]> = {};
    
    events.forEach((event) => {
      if (!grouped[event.date]) {
        grouped[event.date] = [];
      }
      grouped[event.date].push(event);
    });
    
    Object.keys(grouped).forEach((date) => {
      grouped[date].sort((a, b) => {
        if (!a.time) return 1;
        if (!b.time) return -1;
        return a.time.localeCompare(b.time);
      });
    });
    
    const sortedDates = Object.keys(grouped).sort((a, b) => {
      if (isPast) {
        return b.localeCompare(a);
      }
      return a.localeCompare(b);
    });
    
    return sortedDates.map((date) => ({
      date,
      events: grouped[date],
    }));
  };

  const upcomingGroups = events ? groupEventsByDate(events.future_events, false) : [];
  const pastGroups = events ? groupEventsByDate(events.past_events, true) : [];

  return (
    <div className="container mx-auto py-6 px-4 max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-zinc-100 flex items-center gap-2">
            <CalendarDays className="w-6 h-6 text-amber-400" />
            经济日历
          </h1>
          <p className="text-zinc-400 text-sm mt-1">
            全球重要经济事件和数据发布日历
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleFetchNewData}
            disabled={fetching}
          >
            {fetching ? (
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
            ) : (
              <Download className="w-4 h-4 mr-2" />
            )}
            {fetching ? '抓取中...' : '抓取最新数据'}
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500">总事件数</p>
                <p className="text-2xl font-bold text-zinc-100">{stats?.total_events || 0}</p>
              </div>
              <CalendarDays className="w-8 h-8 text-amber-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500">高重要性</p>
                <p className="text-2xl font-bold text-red-400">{stats?.by_importance?.high || 0}</p>
              </div>
              <AlertCircle className="w-8 h-8 text-red-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500">中等重要性</p>
                <p className="text-2xl font-bold text-yellow-400">{stats?.by_importance?.medium || 0}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-yellow-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
        
        <Card className="bg-zinc-900/50 border-zinc-800">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-xs text-zinc-500">低重要性</p>
                <p className="text-2xl font-bold text-green-400">{stats?.by_importance?.low || 0}</p>
              </div>
              <Zap className="w-8 h-8 text-green-400 opacity-50" />
            </div>
          </CardContent>
        </Card>
      </div>

      <div className="flex items-center gap-4 mb-6">
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400">国家/地区:</span>
          <Select value={selectedCountry} onValueChange={setSelectedCountry}>
            <SelectTrigger className="w-40 bg-zinc-800 border-zinc-700">
              <SelectValue placeholder="全部" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部</SelectItem>
              {countries.map((c) => (
                <SelectItem key={c.code} value={c.code}>
                  {c.name} ({c.currency})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        
        <div className="flex items-center gap-2">
          <span className="text-sm text-zinc-400">重要性:</span>
          <Select value={selectedImportance} onValueChange={setSelectedImportance}>
            <SelectTrigger className="w-32 bg-zinc-800 border-zinc-700">
              <SelectValue placeholder="全部" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">全部</SelectItem>
              {importanceLevels.map((l) => (
                <SelectItem key={l.code} value={l.code}>
                  {l.emoji} {l.name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-zinc-900 border border-zinc-800">
          <TabsTrigger value="upcoming" className="data-[state=active]:bg-amber-500 data-[state=active]:text-black">
            即将到来 ({events?.future_events?.length || 0})
          </TabsTrigger>
          <TabsTrigger value="past" className="data-[state=active]:bg-zinc-700">
            已发生 ({events?.past_events?.length || 0})
          </TabsTrigger>
        </TabsList>

        <TabsContent value="upcoming" className="mt-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
              <span className="ml-2 text-zinc-400">加载中...</span>
            </div>
          ) : upcomingGroups.length > 0 ? (
            upcomingGroups.map((group) => (
              <DateGroup key={group.date} date={group.date} events={group.events} isPast={false} />
            ))
          ) : (
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="py-12 text-center">
                <CalendarDays className="w-12 h-12 mx-auto text-zinc-600 mb-4" />
                <p className="text-zinc-400">暂无即将到来的事件</p>
                <p className="text-zinc-500 text-sm mt-2">点击"抓取最新数据"获取最新日历信息</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        <TabsContent value="past" className="mt-4">
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <RefreshCw className="w-6 h-6 animate-spin text-amber-400" />
              <span className="ml-2 text-zinc-400">加载中...</span>
            </div>
          ) : pastGroups.length > 0 ? (
            pastGroups.map((group) => (
              <DateGroup key={group.date} date={group.date} events={group.events} isPast={true} />
            ))
          ) : (
            <Card className="bg-zinc-900/50 border-zinc-800">
              <CardContent className="py-12 text-center">
                <CalendarDays className="w-12 h-12 mx-auto text-zinc-600 mb-4" />
                <p className="text-zinc-400">暂无历史事件记录</p>
              </CardContent>
            </Card>
          )}
        </TabsContent>
      </Tabs>
    </div>
  );
}
