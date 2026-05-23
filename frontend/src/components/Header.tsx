import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useState, useEffect, useRef } from 'react';
import { tokenStorage, authApi } from '../api/client';
import type { ChatPageHandle } from '../pages/ChatPage';

interface UserInfo {
  id: string;
  username: string;
  email?: string;
  tenant_id?: string;
  is_active: boolean;
}

export interface HeaderProps {
  chatPageRef?: React.RefObject<ChatPageHandle | null>;
}

const navItems = [
  { label: '知识库', path: '/knowledge-bases' },
  { label: '文档管理', path: '/knowledge-bases/:kbId/documents' },
  { label: '智能问答', path: '/knowledge-bases/:kbId/chat' },
  { label: 'Agent', path: '/agent' },
];

function getAvatarColor(username: string): string {
  const colors = [
    'bg-blue-500',
    'bg-purple-500',
    'bg-pink-500',
    'bg-teal-500',
    'bg-orange-500',
    'bg-indigo-500',
    'bg-rose-500',
    'bg-cyan-500',
  ];
  let hash = 0;
  for (let i = 0; i < username.length; i++) {
    hash = username.charCodeAt(i) + ((hash << 5) - hash);
  }
  return colors[Math.abs(hash) % colors.length];
}

function getInitial(username: string): string {
  return username.trim().charAt(0).toUpperCase();
}

export default function Header({ chatPageRef }: HeaderProps) {
  const location = useLocation();
  const navigate = useNavigate();
  const [user, setUser] = useState<UserInfo | null>(null);
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const token = tokenStorage.get();
    if (!token) {
      setUser(null);
      return;
    }
    authApi.me()
      .then((u: UserInfo) => setUser(u))
      .catch(() => {
        tokenStorage.clear();
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('username');
        setUser(null);
      });
  }, []);

  // Close dropdown on outside click
  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setDropdownOpen(false);
      }
    }
    document.addEventListener('mousedown', handleClick);
    return () => document.removeEventListener('mousedown', handleClick);
  }, []);

  // Close dropdown on navigation
  useEffect(() => {
    setDropdownOpen(false);
  }, [location.pathname]);

  const handleLogout = () => {
    tokenStorage.clear();
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('username');
    setUser(null);
    setDropdownOpen(false);
    navigate('/login');
  };

  const storedUsername = localStorage.getItem('username');
  const displayName = user?.username ?? storedUsername ?? '';
  const avatarColor = displayName ? getAvatarColor(displayName) : 'bg-gray-400';
  const avatarInitial = displayName ? getInitial(displayName) : '?';

  return (
    <header className="bg-white shadow-sm border-b border-gray-200 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo + Nav */}
          <div className="flex items-center gap-8">
            <Link
              to="/knowledge-bases"
              className="flex items-center gap-2 text-primary-600 font-bold text-xl hover:text-primary-700 transition-colors"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-primary-600 rounded-lg flex items-center justify-center shadow-sm">
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5 text-white"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
                  />
                </svg>
              </div>
              SmartRAG
            </Link>
            <nav className="hidden sm:flex items-center gap-1">
              {navItems.map((item) => {
                const base = item.path.split('/:')[0];
                const active = location.pathname.startsWith(base);
                return (
                  <Link
                    key={item.path}
                    to={item.path}
                    className={`px-3 py-2 rounded-lg text-sm font-medium transition-colors ${
                      active
                        ? 'bg-primary-50 text-primary-700'
                        : 'text-gray-600 hover:text-primary-600 hover:bg-gray-50'
                    }`}
                  >
                    {item.label}
                  </Link>
                );
              })}
            </nav>
          </div>

          {/* Right side: clear button + user menu */}
          <div className="flex items-center gap-2">
            {location.pathname.includes('/chat') && chatPageRef?.current && (
              <button
                onClick={() => chatPageRef.current?.clearConversation()}
                className="p-2 text-gray-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition"
                title="清空对话"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
              </button>
            )}
            {user || storedUsername ? (
              <div className="relative" ref={dropdownRef}>
                <button
                  onClick={() => setDropdownOpen((o) => !o)}
                  className="flex items-center gap-2.5 pl-1 pr-2 py-1 rounded-full hover:bg-gray-50 transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500"
                >
                  {/* Avatar */}
                  <div
                    className={`w-8 h-8 ${avatarColor} rounded-full flex items-center justify-center text-white text-sm font-bold shadow-sm`}
                  >
                    {avatarInitial}
                  </div>
                  {/* Name + chevron */}
                  <span className="hidden sm:block text-sm font-medium text-gray-700">
                    {displayName}
                  </span>
                  <svg
                    xmlns="http://www.w3.org/2000/svg"
                    className={`hidden sm:block h-4 w-4 text-gray-400 transition-transform duration-200 ${dropdownOpen ? 'rotate-180' : ''}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </button>

                {/* Dropdown */}
                {dropdownOpen && (
                  <div className="absolute right-0 mt-2 w-52 bg-white rounded-xl shadow-lg shadow-gray-900/10 border border-gray-100 py-1 z-50 overflow-hidden">
                    {/* User info */}
                    <div className="px-4 py-3 border-b border-gray-100">
                      <p className="text-sm font-semibold text-gray-900 truncate">{displayName}</p>
                      {user?.email && (
                        <p className="text-xs text-gray-400 truncate mt-0.5">{user.email}</p>
                      )}
                    </div>

                    {/* Account badge */}
                    <div className="px-4 py-2 flex items-center gap-2">
                      <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-green-50 text-green-600">
                        <span className="w-1.5 h-1.5 bg-green-500 rounded-full mr-1.5" />
                        已登录
                      </span>
                    </div>

                    <div className="border-t border-gray-100 mt-1 pt-1" />

                    {/* Menu items */}
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2.5 px-4 py-2.5 text-sm text-gray-700 hover:bg-red-50 hover:text-red-600 transition-colors"
                    >
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
                      </svg>
                      退出登录
                    </button>
                  </div>
                )}
              </div>
            ) : (
              <Link
                to="/login"
                className="flex items-center gap-1.5 px-4 py-2 text-sm font-medium text-white bg-primary-600 hover:bg-primary-700 rounded-lg transition-colors shadow-sm"
              >
                <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
                登录
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}
