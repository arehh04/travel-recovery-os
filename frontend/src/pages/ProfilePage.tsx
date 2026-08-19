/** Profile page — stitch profile settings with dynamic data. */

import { useState } from 'react';
import type { ProfileData } from '../types/app';

interface Props {
  data?: Partial<ProfileData>;
}

const DEFAULT_DATA: ProfileData = {
  name: 'Traveler',
  flyerStatus: 'Standard',
  preferences: [],
  companionsCount: 0,
  currency: 'USD',
  appVersion: '0.10.0',
  notificationsEnabled: true,
};

export function ProfilePage({ data: propData }: Props = {}) {
  const [notifications, setNotifications] = useState(propData?.notificationsEnabled ?? true);
  const data = { ...DEFAULT_DATA, ...propData };

  return (
    <main className="max-w-3xl mx-auto px-container-margin pt-4 pb-12 flex flex-col gap-stack-lg">
      {/* Profile Header Area */}
      <section className="flex flex-col items-center gap-4">
        <div className="relative group">
          <div className="w-24 h-24 rounded-full bg-surface-container-high border-4 border-background shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] overflow-hidden flex items-center justify-center relative">
            {data.avatarUrl ? (
              <img src={data.avatarUrl} alt={data.name} className="w-full h-full object-cover" />
            ) : (
              <span className="material-symbols-outlined text-[40px] text-on-surface-variant">person</span>
            )}
          </div>
          <button className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center shadow-sm border-2 border-background hover:bg-secondary/90 transition-colors">
            <span className="material-symbols-outlined text-[16px]">edit</span>
          </button>
        </div>
        <div className="text-center">
          <h2 className="font-headline-md text-headline-md text-on-surface mb-1">{data.name}</h2>
          <p className="font-body-md text-body-md text-on-surface-variant">
            Frequent Flyer · {data.flyerStatus}
          </p>
        </div>
      </section>

      {/* Bento Grid for Profile Settings */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {/* Travel Preferences Card */}
        <div className="glass-card rounded-xl p-5 border border-outline-variant shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] flex flex-col gap-4 relative overflow-hidden group hover:border-secondary/30 transition-colors">
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2 text-secondary">
              <span className="material-symbols-outlined">tune</span>
              <h3 className="font-label-md text-label-md">Travel Preferences</h3>
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            {data.preferences.length > 0 ? (
              data.preferences.map((pref, i) => (
                <span key={i} className="inline-flex items-center px-3 py-1.5 rounded-full bg-surface-container-low border border-outline-variant/50 font-label-sm text-label-sm text-on-surface">
                  {pref}
                </span>
              ))
            ) : (
              <span className="font-label-sm text-label-sm text-on-surface-variant">No preferences set</span>
            )}
          </div>
          <button className="mt-auto self-start font-label-sm text-label-sm text-secondary hover:underline flex items-center gap-1">
            Edit Preferences <span className="material-symbols-outlined text-[14px]">chevron_right</span>
          </button>
        </div>

        {/* Default Travelers & Currency */}
        <div className="flex flex-col gap-4">
          {/* Companions */}
          <div className="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant flex items-center justify-between hover:border-secondary/30 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
                <span className="material-symbols-outlined">group</span>
              </div>
              <div>
                <h3 className="font-label-md text-label-md text-on-surface">Companions</h3>
                <p className="font-label-sm text-label-sm text-on-surface-variant">{data.companionsCount} Saved Profiles</p>
              </div>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant">chevron_right</span>
          </div>

          {/* Currency */}
          <div className="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant flex items-center justify-between hover:border-secondary/30 transition-colors cursor-pointer">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
                <span className="material-symbols-outlined">payments</span>
              </div>
              <div>
                <h3 className="font-label-md text-label-md text-on-surface">Currency</h3>
                <p className="font-label-sm text-label-sm text-on-surface-variant">{data.currency} ($)</p>
              </div>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant">chevron_right</span>
          </div>
        </div>
      </div>

      {/* System & App Settings List */}
      <section className="mt-4">
        <h3 className="font-label-sm text-label-sm text-on-surface-variant uppercase tracking-wider mb-3 px-2">App Settings</h3>
        <div className="bg-surface-container-lowest rounded-xl border border-outline-variant overflow-hidden flex flex-col">
          {/* Notifications Toggle */}
          <div className="p-4 flex items-center justify-between border-b border-outline-variant/50 hover:bg-surface-container-low transition-colors">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-on-surface-variant">notifications_active</span>
              <span className="font-body-md text-body-md text-on-surface">Push Notifications</span>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                checked={notifications}
                onChange={(e) => setNotifications(e.target.checked)}
                className="sr-only peer"
                type="checkbox"
              />
              <div className="w-11 h-6 bg-surface-container-high peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-secondary"></div>
            </label>
          </div>
          {/* About */}
          <a className="p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors" href="#">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-on-surface-variant">info</span>
              <span className="font-body-md text-body-md text-on-surface">About Navires</span>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant text-[20px]">chevron_right</span>
          </a>
          {/* Support */}
          <a className="p-4 flex items-center justify-between hover:bg-surface-container-low transition-colors" href="#">
            <div className="flex items-center gap-3">
              <span className="material-symbols-outlined text-on-surface-variant">help</span>
              <span className="font-body-md text-body-md text-on-surface">Help &amp; Support</span>
            </div>
            <span className="material-symbols-outlined text-on-surface-variant text-[20px]">chevron_right</span>
          </a>
        </div>
      </section>

      {/* Branding Footer */}
      <div className="flex flex-col items-center justify-center py-8 opacity-60">
        <img src="/Navires-logo.png" alt="Navires Logo" className="h-12 w-auto mb-2 grayscale object-contain" />
        <p className="font-label-sm text-label-sm text-on-surface-variant">Navires Recovery System v{data.appVersion}</p>
      </div>
    </main>
  );
}
