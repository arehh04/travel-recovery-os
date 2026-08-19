---
name: TR-OS Core
colors:
  surface: '#f7f9fb'
  surface-dim: '#d8dadc'
  surface-bright: '#f7f9fb'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f4f6'
  surface-container: '#eceef0'
  surface-container-high: '#e6e8ea'
  surface-container-highest: '#e0e3e5'
  on-surface: '#191c1e'
  on-surface-variant: '#45464d'
  inverse-surface: '#2d3133'
  inverse-on-surface: '#eff1f3'
  outline: '#76777d'
  outline-variant: '#c6c6cd'
  surface-tint: '#565e74'
  primary: '#000000'
  on-primary: '#ffffff'
  primary-container: '#131b2e'
  on-primary-container: '#7c839b'
  inverse-primary: '#bec6e0'
  secondary: '#00668a'
  on-secondary: '#ffffff'
  secondary-container: '#40c2fd'
  on-secondary-container: '#004d6a'
  tertiary: '#000000'
  on-tertiary: '#ffffff'
  tertiary-container: '#002113'
  on-tertiary-container: '#009668'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#dae2fd'
  primary-fixed-dim: '#bec6e0'
  on-primary-fixed: '#131b2e'
  on-primary-fixed-variant: '#3f465c'
  secondary-fixed: '#c4e7ff'
  secondary-fixed-dim: '#7bd0ff'
  on-secondary-fixed: '#001e2c'
  on-secondary-fixed-variant: '#004c69'
  tertiary-fixed: '#6ffbbe'
  tertiary-fixed-dim: '#4edea3'
  on-tertiary-fixed: '#002113'
  on-tertiary-fixed-variant: '#005236'
  background: '#f7f9fb'
  on-background: '#191c1e'
  surface-variant: '#e0e3e5'
typography:
  display-lg:
    fontFamily: Inter
    fontSize: 48px
    fontWeight: '700'
    lineHeight: 56px
    letterSpacing: -0.02em
  headline-lg:
    fontFamily: Inter
    fontSize: 32px
    fontWeight: '600'
    lineHeight: 40px
    letterSpacing: -0.01em
  headline-lg-mobile:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '600'
    lineHeight: 32px
  headline-md:
    fontFamily: Inter
    fontSize: 20px
    fontWeight: '600'
    lineHeight: 28px
  body-lg:
    fontFamily: Inter
    fontSize: 18px
    fontWeight: '400'
    lineHeight: 28px
  body-md:
    fontFamily: Inter
    fontSize: 16px
    fontWeight: '400'
    lineHeight: 24px
  label-md:
    fontFamily: Inter
    fontSize: 14px
    fontWeight: '600'
    lineHeight: 20px
    letterSpacing: 0.05em
  label-sm:
    fontFamily: Inter
    fontSize: 12px
    fontWeight: '500'
    lineHeight: 16px
  numeric-data:
    fontFamily: Inter
    fontSize: 24px
    fontWeight: '700'
    lineHeight: 32px
    letterSpacing: -0.01em
rounded:
  sm: 0.25rem
  DEFAULT: 0.5rem
  md: 0.75rem
  lg: 1rem
  xl: 1.5rem
  full: 9999px
spacing:
  unit: 4px
  container-margin: 24px
  gutter: 16px
  stack-sm: 8px
  stack-md: 16px
  stack-lg: 32px
---

## Brand & Style
The design system focuses on an **Intelligent, Calm, and Premium** experience for a modern AI-travel assistant. The brand personality is rooted in reliability and foresight, acting as a steady hand during travel disruptions.

The design style is **Corporate Modern with a Minimalist lean**. It emphasizes clarity through generous whitespace, high-quality typography, and a "Glass-adjacent" lightness that feels technical yet approachable. The UI avoids unnecessary decoration, using subtle borders and soft shadows to establish a clear hierarchy that guides users through complex recovery workflows with confidence.

## Colors
The palette is anchored by **Deep Navy**, conveying authority and intelligence, balanced by **Sky Blue** to provide a sense of optimism and digital-first innovation. 

- **Primary (Deep Navy):** Used for core branding, primary actions, and high-level navigation.
- **Secondary (Sky Blue):** Used for interactive elements, highlights, and AI-driven insights.
- **Semantic Colors:** Emerald Green, Amber, and Red are reserved strictly for status indicators (Success, Warning, Danger) to ensure immediate cognitive recognition.
- **Surface & Text:** The background uses a very light cool gray to reduce eye strain, while the text remains high-contrast Dark Navy for maximum legibility.

## Typography
This design system utilizes **Inter** exclusively to maintain a systematic and utilitarian feel. The hierarchy is designed for quick scanning:

- **Large Confident Headings:** Use `display-lg` and `headline-lg` to ground the page.
- **Strong Numerical Hierarchy:** The `numeric-data` style should be used for flight numbers, times, and confidence percentages to ensure they stand out in the recovery flow.
- **Compact Labels:** Use `label-md` for headers within cards and metadata to differentiate from body content.

## Layout & Spacing
The layout follows a **Fluid Grid** model for mobile-first utility, transitioning to a **Fixed 12-column grid** on desktop (max-width 1280px). 

- **Padding:** Use 24px horizontal margins on mobile to ensure content doesn't feel cramped.
- **Rhythm:** Spacing is based on a 4px baseline. Components should primarily use 16px (stack-md) for internal padding and 32px (stack-lg) for section vertical spacing.
- **Adaptive Rules:** On tablet and desktop, cards may span 4 or 6 columns. On mobile, all primary cards span the full width of the safe area.

## Elevation & Depth
Hierarchy is established through **Tonal Layers** and **Soft Shadows**. 

- **Surfaces:** Use the background color (#F8FAFC) for the base layer. Cards and interactive containers use white (#FFFFFF).
- **Shadows:** Apply a singular, extra-diffused shadow style for elevated cards: `box-shadow: 0 4px 20px -2px rgba(15, 23, 42, 0.08)`.
- **Borders:** All cards and inputs must feature a 1px solid border (#E2E8F0). This "ghost border" provides structure even when shadows are subtle.

## Shapes
The shape language is consistently **Rounded**, evoking a friendly and modern software feel.

- **Standard Cards:** 16px (rounded-lg).
- **Buttons & Inputs:** 8px (rounded-md).
- **Badges & Indicators:** Fully pill-shaped for immediate distinction from actionable buttons.

## Components
- **RecoveryTimeline:** A vertical list using thin 2px lines in #E2E8F0. Completed steps use Emerald Green icons; pending steps use Sky Blue rings.
- **RecommendationCard:** A white, elevated card with 16px corner radius. Includes a Primary Deep Navy button for "Accept" and a secondary Sky Blue text link for "View Details".
- **ConfidenceIndicator:** A circular progress ring or pill-shaped badge using a weight-based color scale (Secondary for high confidence, Warning for low).
- **EvidenceCard:** A flattened version of a card with a light Sky Blue tint background (#F0F9FF) to signal AI-generated data or supporting facts.
- **StatusBadges:** Small, pill-shaped containers with 12px font size. Use low-opacity backgrounds of the semantic colors with high-opacity text (e.g., Light Emerald background with Dark Emerald text).
- **BottomNavigation:** A fixed-position blur-effect bar (Glassmorphism) using white with 80% opacity. Use primary-colored outline icons for the active state and neutral gray for inactive states.
- **Input Fields:** 1px border (#E2E8F0), 12px vertical padding, transitions to a 2px Sky Blue border on focus.