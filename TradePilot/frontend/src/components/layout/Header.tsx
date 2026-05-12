'use client';

import { Bell, Menu, MoonStar, Search, Sun } from 'lucide-react';
import { useEffect, useState } from 'react';

import { Avatar } from '@/components/ui/avatar';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/stores/auth-store';
import { useThemeStore } from '@/stores/theme-store';
import { cn } from '@/lib/utils/cn';

import { TradeModeToggle } from './TradeModeToggle';

export interface HeaderProps {
  title?: string;
  onMobileMenu?: () => void;
}

export function Header({ title = '대시보드', onMobileMenu }: HeaderProps) {
  const user = useAuthStore((s) => s.user);
  const toggleTheme = useThemeStore((s) => s.toggle);
  const theme = useThemeStore((s) => s.theme);
  const [now, setNow] = useState<string>('');

  useEffect(() => {
    const update = () => {
      const d = new Date();
      const pad = (n: number) => String(n).padStart(2, '0');
      setNow(
        `KST ${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(
          d.getMinutes(),
        )}:${pad(d.getSeconds())}`,
      );
    };
    update();
    const id = window.setInterval(update, 1000);
    return () => window.clearInterval(id);
  }, []);

  return (
    <header className="app-shell__header app-header" role="banner">
      <div className="app-header__left">
        <Button variant="ghost" size="icon" aria-label="메뉴" onClick={onMobileMenu}>
          <Menu className="h-4 w-4" />
        </Button>
        <h1 className="h5 truncate">{title}</h1>
        <span className="dot-sep" />
        <span className="text-subtle text-xs">{now}</span>
      </div>
      <div className="app-header__search">
        <Input
          leftIcon={<Search className="h-4 w-4" />}
          placeholder="종목명 또는 코드 검색 (Ctrl+K)"
        />
      </div>
      <div className="app-header__right">
        <TradeModeToggle />
        <Button variant="ghost" size="icon" aria-label="알림">
          <Bell className="h-4 w-4" />
        </Button>
        <div className="row items-center gap-2">
          <Avatar name={user?.nickname ?? '게'} />
          <span className={cn('text-sm text-muted hidden lg:inline')}>{user?.nickname ?? '게스트'}</span>
        </div>
        <Button variant="ghost" size="icon" aria-label="테마 전환" onClick={toggleTheme}>
          {theme === 'dark' ? <Sun className="h-4 w-4" /> : <MoonStar className="h-4 w-4" />}
        </Button>
      </div>
    </header>
  );
}
