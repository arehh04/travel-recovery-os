/** Mobile bottom navigation — stitch UI inspired. */

interface NavItem {
  label: string;
  icon: string;
  key: string;
}

interface Props {
  items?: NavItem[];
  activeTab?: string;
  onTabChange?: (key: string) => void;
}

const DEFAULT_ITEMS: NavItem[] = [
  { label: 'Home', icon: 'home', key: 'home' },
  { label: 'Trips', icon: 'luggage', key: 'trips' },
  { label: 'Profile', icon: 'person', key: 'profile' },
];

export function BottomNav({
  items = DEFAULT_ITEMS,
  activeTab = 'home',
  onTabChange,
}: Props) {
  return (
    <nav className="bottom-nav" role="navigation" aria-label="Main navigation">
      {items.map((item) => (
        <button
          key={item.key}
          className={`bottom-nav-item ${activeTab === item.key ? 'active' : ''}`}
          onClick={() => onTabChange?.(item.key)}
          type="button"
        >
          <span className="material-symbols-outlined">{item.icon}</span>
          <span>{item.label}</span>
        </button>
      ))}
    </nav>
  );
}
