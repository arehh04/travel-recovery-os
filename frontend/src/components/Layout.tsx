/** Shared layout — TopAppBar + BottomNav wrapping all pages. */

import { Outlet, useLocation, useNavigate, Link } from 'react-router-dom';
import { DevTools } from './DevTools';

const LOGO_SRC = '/Navires-logo.png';
const BRAND_NAME = 'Navires';

const NAV_ITEMS = [
  { label: 'Home', icon: 'home', path: '/' },
  { label: 'Trips', icon: 'luggage', path: '/history' },
  { label: 'Profile', icon: 'person', path: '/profile' },
];

/** Routes where the bottom nav should be suppressed. */
const NO_BOTTOM_NAV = ['/recovery/plan', '/recovery/engine'];

/** Routes where the top bar shows a back button instead of explore icon. */
const BACK_ROUTES = ['/recovery/plan', '/recovery/engine'];

export function Layout() {
  const location = useLocation();
  const navigate = useNavigate();

  const showBottomNav = !NO_BOTTOM_NAV.some((r) => location.pathname.startsWith(r));
  const showBack = BACK_ROUTES.some((r) => location.pathname.startsWith(r));
  const showClose = location.pathname === '/recovery/engine';

  const isActive = (path: string) => {
    if (path === '/') return location.pathname === '/';
    return location.pathname.startsWith(path);
  };

  return (
    <div className="bg-background min-h-screen flex flex-col selection:bg-secondary-fixed selection:text-on-secondary-fixed">
      {/* TopAppBar */}
      <header className="bg-background text-primary flex justify-between items-center w-full px-container-margin py-stack-md sticky top-0 z-50">
        {showBack ? (
          <button
            onClick={() => navigate(-1)}
            className="p-2 -ml-2 text-on-surface-variant hover:bg-surface-container transition-colors rounded-full flex items-center justify-center"
          >
            <span className="material-symbols-outlined">arrow_back</span>
          </button>
        ) : showClose ? (
          <Link
            to="/"
            className="text-primary hover:bg-surface-container transition-colors rounded-full p-2 -ml-2 flex items-center justify-center h-10 w-10"
          >
            <span className="material-symbols-outlined">close</span>
          </Link>
        ) : (
          <Link to="/" className="flex items-center gap-2 hover:bg-surface-container transition-colors rounded-lg p-2 -ml-2 cursor-pointer">
            <img src={LOGO_SRC} alt={BRAND_NAME} className="h-8 w-8 object-contain rounded-full shadow-sm" />
            <span className="font-headline-lg-mobile text-headline-lg-mobile font-bold text-primary tracking-tight">
              {BRAND_NAME}
            </span>
          </Link>
        )}

        {/* Center logo for back routes */}
        {showBack && (
          <div className="absolute left-1/2 -translate-x-1/2 flex items-center gap-2">
            <img src={LOGO_SRC} alt={BRAND_NAME} className="h-8 w-auto object-contain" />
            <span className="font-headline-lg-mobile text-headline-lg-mobile font-bold text-primary tracking-tight">
              {BRAND_NAME}
            </span>
          </div>
        )}

        {/* Desktop nav — hidden on back/close routes */}
        {!showBack && !showClose && (
          <nav className="hidden md:flex items-center gap-8">
            {NAV_ITEMS.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`font-label-md text-label-md transition-colors ${
                  isActive(item.path)
                    ? 'text-primary font-bold border-b-2 border-primary pb-1'
                    : 'text-on-surface-variant hover:text-primary'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </nav>
        )}

        <button className="w-10 h-10 flex items-center justify-center rounded-full hover:bg-surface-container transition-colors text-on-surface-variant hover:text-primary active:scale-95 duration-100">
          <span className="material-symbols-outlined text-[24px]">notifications</span>
        </button>
      </header>

      {/* Page content */}
      <Outlet />

      {/* BottomNav — mobile only, hidden on transactional routes */}
      {showBottomNav && (
        <nav className="md:hidden fixed bottom-0 left-0 w-full z-50 flex justify-around items-center px-gutter pb-6 pt-2 bg-surface/80 backdrop-blur-md border-t border-outline-variant shadow-[0_-4px_20px_-2px_rgba(15,23,42,0.08)] rounded-t-xl transition-transform duration-300">
          {NAV_ITEMS.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`flex flex-col items-center justify-center rounded-full px-6 py-1.5 transition-all hover:scale-90 duration-200 ease-out ${
                isActive(item.path)
                  ? 'bg-secondary-container text-on-secondary-container shadow-sm'
                  : 'text-on-surface-variant hover:text-secondary'
              }`}
            >
              <span
                className="material-symbols-outlined mb-0.5 text-[24px]"
                style={{ fontVariationSettings: isActive(item.path) ? "'FILL' 1" : "'FILL' 0" }}
              >
                {item.icon}
              </span>
              <span className="font-label-sm text-label-sm">{item.label}</span>
            </Link>
          ))}
        </nav>
      )}

      {/* Dev Tools Widget */}
      <DevTools />
    </div>
  );
}
