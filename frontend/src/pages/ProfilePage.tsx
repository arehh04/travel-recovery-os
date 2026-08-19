/** Profile page — editable settings with localStorage persistence. */

import { useState, useEffect } from 'react';
import type { ProfileData } from '../types/app';

const STORAGE_KEY = 'navires-profile';

const DEFAULT_DATA: ProfileData = {
  name: 'Traveler',
  flyerStatus: 'Standard',
  preferences: [],
  companionsCount: 0,
  currency: 'USD',
  appVersion: '0.10.0',
  notificationsEnabled: true,
};

const AVAILABLE_PREFERENCES = [
  'Window Seat', 'Aisle Seat', 'Extra Legroom', 'No Stops', 'Vegetarian Meal',
  'Early Departure', 'Late Departure', 'Business Class', 'Economy', 'Priority Boarding',
];

function loadProfile(): ProfileData {
  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      return { ...DEFAULT_DATA, ...JSON.parse(stored) };
    }
  } catch {
    // localStorage not available
  }
  return DEFAULT_DATA;
}

function saveProfile(data: ProfileData) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
  } catch {
    // ignore
  }
}

export function ProfilePage() {
  const [profile, setProfile] = useState<ProfileData>(loadProfile);
  const [editingName, setEditingName] = useState(false);
  const [nameInput, setNameInput] = useState(profile.name);
  const [editingPrefs, setEditingPrefs] = useState(false);
  const [selectedPrefs, setSelectedPrefs] = useState<string[]>(profile.preferences);
  const [editingCurrency, setEditingCurrency] = useState(false);
  const [savedMessage, setSavedMessage] = useState('');

  // Save to localStorage whenever profile changes
  useEffect(() => {
    saveProfile(profile);
  }, [profile]);

  const showSaved = (msg: string) => {
    setSavedMessage(msg);
    setTimeout(() => setSavedMessage(''), 2000);
  };

  const handleSaveName = () => {
    if (nameInput.trim()) {
      setProfile({ ...profile, name: nameInput.trim() });
      showSaved('Name updated');
    }
    setEditingName(false);
  };

  const handleTogglePref = (pref: string) => {
    setSelectedPrefs((prev) =>
      prev.includes(pref) ? prev.filter((p) => p !== pref) : [...prev, pref]
    );
  };

  const handleSavePrefs = () => {
    setProfile({ ...profile, preferences: selectedPrefs });
    setEditingPrefs(false);
    showSaved('Preferences updated');
  };

  const handleCurrencyChange = (currency: string) => {
    setProfile({ ...profile, currency });
    setEditingCurrency(false);
    showSaved('Currency updated');
  };

  return (
    <main className="max-w-3xl mx-auto px-container-margin pt-4 pb-12 flex flex-col gap-stack-lg">
      {/* Saved message toast */}
      {savedMessage && (
        <div className="fixed top-20 right-4 bg-tertiary text-on-tertiary px-4 py-2 rounded-lg shadow-lg z-50 flex items-center gap-2 animate-[fadeIn_0.3s_ease]">
          <span className="material-symbols-outlined text-[18px]">check_circle</span>
          {savedMessage}
        </div>
      )}

      {/* Profile Header Area */}
      <section className="flex flex-col items-center gap-4">
        <div className="relative group">
          <div className="w-24 h-24 rounded-full bg-surface-container-high border-4 border-background shadow-[0_4px_20px_-2px_rgba(15,23,42,0.08)] overflow-hidden flex items-center justify-center relative">
            {profile.avatarUrl ? (
              <img src={profile.avatarUrl} alt={profile.name} className="w-full h-full object-cover" />
            ) : (
              <span className="material-symbols-outlined text-[40px] text-on-surface-variant">person</span>
            )}
          </div>
          <button
            onClick={() => { setNameInput(profile.name); setEditingName(true); }}
            className="absolute bottom-0 right-0 w-8 h-8 rounded-full bg-secondary text-on-secondary flex items-center justify-center shadow-sm border-2 border-background hover:bg-secondary/90 transition-colors"
          >
            <span className="material-symbols-outlined text-[16px]">edit</span>
          </button>
        </div>
        <div className="text-center">
          {editingName ? (
            <div className="flex items-center gap-2 justify-center">
              <input
                className="tr-input font-headline-md text-headline-md text-center w-48"
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveName()}
                autoFocus
                placeholder="Your name"
              />
              <button onClick={handleSaveName} className="bg-primary-container text-on-primary p-2 rounded-lg hover:bg-primary-container/90">
                <span className="material-symbols-outlined text-[20px]">check</span>
              </button>
              <button onClick={() => setEditingName(false)} className="text-on-surface-variant p-2 rounded-lg hover:bg-surface-container-low">
                <span className="material-symbols-outlined text-[20px]">close</span>
              </button>
            </div>
          ) : (
            <h2 className="font-headline-md text-headline-md text-on-surface mb-1 cursor-pointer hover:text-secondary" onClick={() => { setNameInput(profile.name); setEditingName(true); }}>
              {profile.name}
            </h2>
          )}
          <p className="font-body-md text-body-md text-on-surface-variant">
            Frequent Flyer · {profile.flyerStatus}
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
          {editingPrefs ? (
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {AVAILABLE_PREFERENCES.map((pref) => (
                  <button
                    key={pref}
                    onClick={() => handleTogglePref(pref)}
                    className={`inline-flex items-center px-3 py-1.5 rounded-full font-label-sm text-label-sm border transition-all ${
                      selectedPrefs.includes(pref)
                        ? 'bg-secondary text-on-secondary border-secondary'
                        : 'bg-surface-container-low border-outline-variant/50 text-on-surface hover:border-secondary/30'
                    }`}
                  >
                    {pref}
                  </button>
                ))}
              </div>
              <div className="flex gap-2">
                <button onClick={handleSavePrefs} className="bg-primary-container text-on-primary font-label-sm text-label-sm px-4 py-2 rounded-lg flex items-center gap-1 hover:bg-primary-container/90">
                  <span className="material-symbols-outlined text-[16px]">check</span> Save
                </button>
                <button onClick={() => { setSelectedPrefs(profile.preferences); setEditingPrefs(false); }} className="text-on-surface-variant font-label-sm text-label-sm px-4 py-2 rounded-lg hover:bg-surface-container-low">
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="flex flex-wrap gap-2">
                {profile.preferences.length > 0 ? (
                  profile.preferences.map((pref, i) => (
                    <span key={i} className="inline-flex items-center px-3 py-1.5 rounded-full bg-surface-container-low border border-outline-variant/50 font-label-sm text-label-sm text-on-surface">
                      {pref}
                    </span>
                  ))
                ) : (
                  <span className="font-label-sm text-label-sm text-on-surface-variant">No preferences set</span>
                )}
              </div>
              <button
                onClick={() => { setSelectedPrefs(profile.preferences); setEditingPrefs(true); }}
                className="mt-auto self-start font-label-sm text-label-sm text-secondary hover:underline flex items-center gap-1"
              >
                Edit Preferences <span className="material-symbols-outlined text-[14px]">chevron_right</span>
              </button>
            </>
          )}
        </div>

        {/* Default Travelers & Currency */}
        <div className="flex flex-col gap-4">
          {/* Companions */}
          <div className="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant flex items-center justify-between hover:border-secondary/30 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
                <span className="material-symbols-outlined">group</span>
              </div>
              <div>
                <h3 className="font-label-md text-label-md text-on-surface">Companions</h3>
                <p className="font-label-sm text-label-sm text-on-surface-variant">{profile.companionsCount} Saved Profiles</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min="0"
                max="10"
                value={profile.companionsCount}
                onChange={(e) => setProfile({ ...profile, companionsCount: Math.max(0, Number(e.target.value)) })}
                className="tr-input w-16 text-center font-body-md text-body-md"
              />
            </div>
          </div>

          {/* Currency */}
          <div className="bg-surface-container-lowest rounded-xl p-5 border border-outline-variant flex items-center justify-between hover:border-secondary/30 transition-colors">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-full bg-surface-container-high flex items-center justify-center text-on-surface-variant">
                <span className="material-symbols-outlined">payments</span>
              </div>
              <div>
                <h3 className="font-label-md text-label-md text-on-surface">Currency</h3>
                {editingCurrency ? (
                  <select
                    className="tr-input font-label-sm text-label-sm mt-1"
                    value={profile.currency}
                    onChange={(e) => handleCurrencyChange(e.target.value)}
                    autoFocus
                  >
                    <option value="USD">USD ($)</option>
                    <option value="EUR">EUR (€)</option>
                    <option value="GBP">GBP (£)</option>
                    <option value="MYR">MYR (RM)</option>
                    <option value="JPY">JPY (¥)</option>
                  </select>
                ) : (
                  <p
                    className="font-label-sm text-label-sm text-on-surface-variant cursor-pointer hover:text-secondary"
                    onClick={() => setEditingCurrency(true)}
                  >
                    {profile.currency} ({profile.currency === 'USD' ? '$' : profile.currency === 'EUR' ? '€' : profile.currency === 'GBP' ? '£' : profile.currency === 'MYR' ? 'RM' : '¥'})
                  </p>
                )}
              </div>
            </div>
            {!editingCurrency && (
              <button onClick={() => setEditingCurrency(true)} className="text-on-surface-variant hover:text-secondary">
                <span className="material-symbols-outlined">chevron_right</span>
              </button>
            )}
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
                checked={profile.notificationsEnabled}
                onChange={(e) => {
                  setProfile({ ...profile, notificationsEnabled: e.target.checked });
                  showSaved(e.target.checked ? 'Notifications enabled' : 'Notifications disabled');
                }}
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
        <p className="font-label-sm text-label-sm text-on-surface-variant">Navires Recovery System v{profile.appVersion}</p>
      </div>
    </main>
  );
}
