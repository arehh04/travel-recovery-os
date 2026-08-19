---
name: Navires
colors:
  surface: '#faf8fd'
  surface-dim: '#dbd9dd'
  surface-bright: '#faf8fd'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f5f3f7'
  surface-container: '#efedf1'
  surface-container-high: '#e9e7ec'
  surface-container-highest: '#e3e2e6'
  on-surface: '#1b1b1f'
  on-surface-variant: '#44474f'
  inverse-surface: '#303033'
  inverse-on-surface: '#f2f0f4'
  outline: '#75777f'
  outline-variant: '#c5c6d0'
  surface-tint: '#495e8a'
  primary: '#00020a'
  on-primary: '#ffffff'
  primary-container: '#001b44'
  on-primary-container: '#7084b3'
  inverse-primary: '#b1c6f9'
  secondary: '#006877'
  on-secondary: '#ffffff'
  secondary-container: '#53e3fd'
  on-secondary-container: '#006371'
  tertiary: '#080100'
  on-tertiary: '#ffffff'
  tertiary-container: '#381000'
  on-tertiary-container: '#b67558'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#d8e2ff'
  primary-fixed-dim: '#b1c6f9'
  on-primary-fixed: '#001a42'
  on-primary-fixed-variant: '#314671'
  secondary-fixed: '#a2eeff'
  secondary-fixed-dim: '#43d8f2'
  on-secondary-fixed: '#001f25'
  on-secondary-fixed-variant: '#004e5a'
  tertiary-fixed: '#ffdbcd'
  tertiary-fixed-dim: '#ffb596'
  on-tertiary-fixed: '#360f00'
  on-tertiary-fixed-variant: '#6d3920'
  background: '#faf8fd'
  on-background: '#1b1b1f'
  surface-variant: '#e3e2e6'
  sky-blue: '#2196F3'
  deep-teal: '#006874'
  surface-neutral: '#F4F7FA'
typography:
  display-lg:
    fontFamily: Hanken Grotesk
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Hanken Grotesk
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  body-md:
    fontFamily: Hanken Grotesk
    fontSize: 14px
    fontWeight: '400'
    lineHeight: 20px
  label-caps:
    fontFamily: JetBrains Mono
    fontSize: 12px
    fontWeight: '600'
    lineHeight: 16px
    letterSpacing: 0.08em
  numeric-flight:
    fontFamily: JetBrains Mono
    fontSize: 18px
    fontWeight: '700'
    lineHeight: 24px
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  unit: 4px
  gutter: 16px
  margin-mobile: 16px
  margin-desktop: 32px
  container-max: 1440px
---

## Brand & Style
The design system embodies the concept of "Intelligent Velocity"—a premium, operationally-focused aesthetic tailored for high-stakes travel technology. It moves away from the softness of a typical AI assistant toward a sophisticated, data-rich interface that evokes the precision of flight instrumentation and travel logistics.

The design style is **Corporate Modern with a "Glassmorphism" influence**. It utilizes clean lines, precise layouts, and subtle depth to convey authority and technological superiority. The visual narrative is one of calm efficiency during travel disruptions, using transparency and light to keep complex data feeling manageable and premium.

## Colors
The palette is derived directly from the brand's travel-centric identity, utilizing a hierarchy of blues to establish trust and technological prowess.

- **Primary (Midnight Navy):** The foundational color for typography and core structural elements, ensuring a grounded, institutional feel.
- **Secondary (Vibrant Teal):** Used for primary action buttons, key data highlights, and successful recovery indicators.
- **Tertiary (Sky Blue):** Applied to supporting graphical elements, interactive links, and secondary data visualizations.
- **Neutral (Cool Slate):** A sophisticated range of cool grays used for borders, subtle backgrounds, and metadata to maintain a clean, organized workspace.

## Typography
The system uses **Hanken Grotesk** for its clean, contemporary feel that balances approachability with professional rigor. For operational and technical data, **JetBrains Mono** is introduced to provide a "tool-like" precision that fits the aviation and technology theme.

Headlines should be tight and impactful, while body text prioritizes legibility. Use the monospaced label style for all flight numbers, gate information, and timestamps to distinguish operational data from narrative content.

## Layout & Spacing
The layout employs a **Fixed Grid** for desktop and a **Fluid Grid** for mobile. On desktop, a 12-column grid provides a structured framework for data-heavy dashboards, while a 4-column grid on mobile ensures a focused, single-task experience.

Spacing is strictly based on a 4px baseline to maintain mathematical harmony. Information density is kept medium-to-high to allow for efficient scanning of travel itineraries and recovery options without feeling cluttered.

## Elevation & Depth
Hierarchy is established through **Tonal Layers** and **Glassmorphism**. Rather than traditional heavy shadows, the design system uses high-precision depth cues:

- **Base Layer:** The "Surface Neutral" (#F4F7FA) acts as the canvas.
- **Glass Containers:** Primary cards use a semi-transparent white background with a backdrop-blur (20px) to create a high-end, modern tech feel.
- **Elevation Strokes:** Instead of shadows, use 1px inner borders in a lighter tint of the primary color or pure white to "lift" elements off the surface.
- **Active Elevation:** Only the most critical interactive elements (like an active flight card) receive a very soft, Sky Blue tinted shadow.

## Shapes
The shape language is **Soft (Level 1)**, leaning into a more technical and precise feel. Sharp enough to feel professional, but with just enough radius to feel modern and accessible.

- **Buttons & Inputs:** 4px radius (Soft) for a crisp, functional look.
- **Container Cards:** 8px radius (Large) for major UI sections.
- **Flight Path Indicators:** Use sharp 0px or pill-shaped ends for technical charts and timeline markers.

## Components
- **Operational Cards:** Utilize the Glassmorphism effect with a 1px Midnight Navy outline at 10% opacity. Headers should use `label-caps` for a technical feel.
- **Primary Action Buttons:** Solid Midnight Navy with white text; 4px corner radius. No shadows.
- **Status Chips:** High-contrast Teal or Sky Blue backgrounds with white text. Use `label-caps` for status indicators like "ON TIME" or "RECOVERED".
- **Flight Timeline:** A vertical or horizontal 2px solid Teal line connecting flight nodes. Nodes for "current position" should use the brand's blue-teal gradient.
- **Data Inputs:** Ghost-style inputs with a 1px cool slate border, transitioning to a 2px Teal border on focus.
- **Navigation Rail:** A slim, dark-themed sidebar using Midnight Navy, utilizing subtle Teal icons to represent different travel segments (Air, Rail, Hotel).