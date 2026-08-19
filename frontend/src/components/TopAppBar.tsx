/** Shared top app bar — stitch UI inspired. */

interface NavItem {
  label: string;
  icon: string;
  key: string;
}

interface Props {
  brandName?: string;
  logoSrc?: string;
  navItems?: NavItem[];
  activeTab?: string;
  onTabChange?: (key: string) => void;
}

const DEFAULT_NAV: NavItem[] = [
  { label: 'Home', icon: 'home', key: 'home' },
  { label: 'Trips', icon: 'luggage', key: 'trips' },
  { label: 'Profile', icon: 'person', key: 'profile' },
];

export function TopAppBar({
  brandName = 'Navires',
  logoSrc = '/Navires-logo.png',
  navItems = DEFAULT_NAV,
  activeTab = 'home',
  onTabChange,
}: Props) {
  return (
    <header className="top-app-bar">
      <div className="top-app-bar-inner">
        <div className="top-app-bar-brand" onClick={() => onTabChange?.('home')}>
          <img src={logoSrc} alt={brandName} className="top-app-bar-logo-img" />
          <span className="top-app-bar-name">{brandName}</span>
        </div>
        <nav className="top-app-bar-nav">
          {navItems.map((item) => (
            <a
              key={item.key}
              className={activeTab === item.key ? 'active' : ''}
              onClick={(e) => {
                e.preventDefault();
                onTabChange?.(item.key);
              }}
              href="#"
            >
              {item.label}
            </a>
          ))}
        </nav>
        <button className="top-app-bar-icon-btn" type="button" aria-label="Notifications">
          <span className="material-symbols-outlined">notifications</span>
        </button>
      </div>
    </header>
  );
}
