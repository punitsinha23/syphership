# Syphership UI Design Specification

## 1. Design Direction

Syphership will use a **minimal, modern space theme** built around the
idea of shipping software into orbit.

The design should feel like:

> **Modern developer platform × quiet space aesthetic × orbital
> technology**

The website is **not** a spaceship simulator and should not look like a
sci-fi cockpit. Space is the visual language; the product remains a
serious developer/deployment platform.

### Core visual idea

**Code → Build → Deploy → Run**

The orbital system represents the software lifecycle. The spaceship is
reserved primarily for the interactive cursor and subtle motion effects.

------------------------------------------------------------------------

# 2. Design Reference

The primary visual reference is the **4th Syphership landing-page
concept**.

Important characteristics to preserve:

-   Dark space background
-   Large clean hero typography
-   Cyan accent color
-   Minimal star field
-   Orbital visualization on the right side of the hero
-   Technical but readable typography
-   Clean navigation
-   Product dashboard preview below the hero
-   Subtle technical labels
-   Strong negative space
-   Developer-focused product UI

The final implementation should be inspired by this composition rather
than being an exact copy.

------------------------------------------------------------------------

# 3. Visual Personality

Syphership should feel:

-   Minimal
-   Technical
-   Premium
-   Calm
-   Futuristic
-   Developer-focused
-   Confident
-   Memorable

Avoid making it feel:

-   Like a video game
-   Like a NASA control room
-   Like a spaceship simulator
-   Like a cyberpunk interface
-   Like a generic AI SaaS template
-   Like a cryptocurrency website

The space theme should support the product instead of overwhelming it.

------------------------------------------------------------------------

# 4. Color System

## Background

Primary background:

``` text
#070A0F
```

Use an almost-black background throughout the main landing page.

Supporting dark surfaces can use slightly lighter values:

``` text
#0B1017
#0D131B
#111820
```

## Primary Accent

Use a bright cyan / cyan-blue accent for important interactive elements.

Approximate direction:

``` text
#22D3EE
```

The accent should be used selectively for:

-   Primary buttons
-   Active states
-   Orbital points
-   Important indicators
-   Links
-   Deployment activity
-   Cursor/ship effects

## Text

Primary:

``` text
#F5F7FA
```

Secondary:

``` text
#A7B0BB
```

Muted:

``` text
#687482
```

## Semantic Status Colors

Running:

``` text
Green
```

Building:

``` text
Amber
```

Failed:

``` text
Red
```

These colors should remain muted and professional.

------------------------------------------------------------------------

# 5. Typography

Use a modern sans-serif as the primary typeface.

Preferred directions:

-   Inter
-   Geist
-   Space Grotesk

Typography should have strong hierarchy without becoming overly
decorative.

## Hero heading

Large, bold, clean:

``` text
Ship your code
into orbit.
```

The heading should be one of the strongest visual elements on the page.

## Technical text

Use a monospace font selectively for:

-   Deployment IDs
-   Commit hashes
-   Status labels
-   Build output
-   Logs
-   Technical metadata

Do not use monospace for the entire website.

------------------------------------------------------------------------

# 6. Navigation

The navigation should be simple and lightweight.

Example:

``` text
SYPHER//SHIP

Product
Features
Documentation
GitHub

Sign in
Get Started
```

### Logo

Use:

``` text
SYPHER//SHIP
```

The `//` can use the cyan accent.

The logo should be text-focused with a small geometric mark if desired.

### Navigation behavior

-   Transparent/dark background
-   Minimal borders
-   No large navigation container
-   Clear hover states
-   Primary CTA highlighted with cyan

------------------------------------------------------------------------

# 7. Hero Section

The hero is the primary visual statement of the landing page.

## Layout

Two-column composition:

``` text
┌───────────────────────────────┐
│                               │
│  TEXT             ORBIT       │
│                               │
│  Ship your code               │
│  into orbit.                  │
│                               │
│  Description                  │
│                               │
│  [Get Started] [View Docs]    │
│                               │
└───────────────────────────────┘
```

The left side contains the product message.

The right side contains the orbital visualization.

## Hero copy

Primary:

> Ship your code into orbit.

Supporting copy:

> Build, deploy, and monitor your applications from one place.

Primary CTA:

> Get Started

Secondary CTA:

> View Documentation

------------------------------------------------------------------------

# 8. Orbital Visualization

The orbital visualization is one of Syphership's main visual identities.

It should be subtle rather than highly detailed.

Example concept:

``` text
             ·

       ╭─────────────╮
     ╱                 ╲
    │         ●         │
     ╲                 ╱
       ╰─────────────╯

             ·
```

### Characteristics

-   Thin orbital lines
-   Very subtle glow
-   Small cyan orbital point
-   Dark background
-   Minimal number of rings
-   No giant planet
-   No large spaceship illustration

The visualization should communicate movement, deployment, and orbit
without becoming the main product.

------------------------------------------------------------------------

# 9. Cursor Spaceship

The spaceship is Syphership's signature interactive element.

The cursor should be represented by a **small minimalist spacecraft**.

It should not look cartoonish.

## Normal state

A small spacecraft follows the mouse pointer.

## Movement

The ship can have a very subtle engine trail.

## Hover

When hovering an interactive element:

-   Ship can slightly rotate toward the element
-   Cursor/target can receive a subtle accent effect

## Fast movement

The engine trail can become slightly more visible.

## Click

A very short thrust/acceleration animation can occur.

## Deployment interaction

When a user starts a deployment, the ship can briefly move toward the
deployment/orbit visualization.

## Important rule

The cursor should enhance the website, not interfere with usability.

Provide a fallback/default cursor behavior if the custom cursor is
disabled or unsupported.

------------------------------------------------------------------------

# 10. Product Lifecycle Section

Introduce the product flow with a simple technical sequence.

Heading:

``` text
FROM COMMIT TO PRODUCTION
```

Three stages:

### 01 --- BUILD

Compile your application.

### 02 --- DEPLOY

Ship it with one click.

### 03 --- RUN

Monitor your production environment.

Visual connection:

``` text
01 BUILD
    ●────────●
             02 DEPLOY
                    ●────────●
                             03 RUN
```

Use thin cyan lines and small glowing points.

The section should remain compact and clean.

------------------------------------------------------------------------

# 11. Product Dashboard Preview

Below the hero/lifecycle section, show a large preview of the actual
Syphership application.

The dashboard should look like a real developer product, not a fictional
sci-fi control panel.

## Dashboard structure

``` text
┌───────────────────────────────────────────────┐
│ SYPHER//SHIP                     New Project +│
├──────────────┬────────────────────────────────┤
│ Projects     │ Projects                       │
│ Deployments  │                                │
│ Logs         │ Deploys today    14            │
│ Environments│ Avg build time  1m 18s         │
│ Settings     │ Uptime          99.98%         │
│              │ Active services 7              │
│              │                                │
│              │ All Projects                   │
│              │                                │
│              │ Anonyverse   RUNNING           │
│              │ Syphership   BUILDING          │
└──────────────┴────────────────────────────────┘
```

### Dashboard principles

-   Realistic developer terminology
-   Strong readability
-   Compact information hierarchy
-   Subtle borders
-   Dark surfaces
-   Cyan highlights
-   Green/amber deployment statuses
-   No excessive decorative elements

------------------------------------------------------------------------

# 12. Project Cards

Projects should be represented as clean technical rows/cards.

Example:

``` text
Anonyverse
anonyverse-web

● RUNNING

production
2m ago
99.99%
```

Another:

``` text
Syphership
syphership-platform

● BUILDING

main
45s ago
99.97%
```

The project data should feel realistic.

------------------------------------------------------------------------

# 13. Deployment Status

Syphership's backend deployment lifecycle:

``` text
QUEUED
   ↓
BUILDING
   ↓
DEPLOYING
   ↓
RUNNING
```

Failure path:

``` text
BUILDING
   ↓
FAILED
```

The UI should represent these states using both:

-   Text
-   Status indicator

Do not rely on color alone.

Example:

``` text
● RUNNING
● BUILDING
● FAILED
```

------------------------------------------------------------------------

# 14. Space Theme Rules

Space-related visuals should primarily appear in:

-   Hero
-   Background
-   Orbital visualizations
-   Section transitions
-   Cursor interaction
-   Deployment animations

Space visuals should **not** dominate:

-   Forms
-   Tables
-   Settings
-   Logs
-   Authentication pages
-   Error messages

These areas should prioritize usability.

------------------------------------------------------------------------

# 15. Background

The background should contain a very subtle star field.

Rules:

-   Small stars only
-   Low contrast
-   Sparse distribution
-   No giant nebula
-   No photographic galaxy background
-   No distracting animations

Optional elements:

-   Very faint grid
-   Thin orbital curves
-   Small points of light

The background should almost disappear when the user focuses on the
product content.

------------------------------------------------------------------------

# 16. Buttons

## Primary

Cyan background with dark text.

Example:

``` text
[ Get Started  → ]
```

Characteristics:

-   Medium radius
-   Strong contrast
-   Subtle hover glow
-   Short transition

## Secondary

Dark/transparent background with a thin border.

Example:

``` text
[ View Documentation → ]
```

Hover state can introduce a subtle cyan border.

Avoid:

-   Huge pill buttons
-   Excessive gradients
-   Heavy shadows
-   Animated rainbow effects

------------------------------------------------------------------------

# 17. Borders and Surfaces

Use subtle borders to separate interface areas.

Example direction:

``` text
border: rgba(255,255,255,0.10)
```

Cards should use dark surfaces only slightly lighter than the page
background.

Avoid excessive floating cards.

The interface should feel like a **single cohesive system**, not a
collection of disconnected boxes.

------------------------------------------------------------------------

# 18. Motion

Animations should be subtle and purposeful.

Good animations:

-   Cursor spacecraft movement
-   Orbital point movement
-   Button hover
-   Deployment state transitions
-   Small status pulses
-   Section reveal
-   Very subtle star movement

Avoid:

-   Constant floating animations
-   Large parallax effects
-   Excessive page transitions
-   Long loading animations
-   Distracting particle effects

Motion should communicate system activity.

------------------------------------------------------------------------

# 19. Responsive Design

The design must work on:

-   Desktop
-   Laptop
-   Tablet
-   Mobile

On mobile:

-   Hero becomes single-column
-   Orbital visualization moves below the heading
-   Navigation collapses
-   Dashboard preview becomes horizontally scrollable or simplified
-   Cursor spaceship behavior should be disabled where there is no mouse
-   Content remains readable without relying on the decorative space
    elements

------------------------------------------------------------------------

# 20. Design Principles

### Principle 1 --- Product first

The deployment platform is always more important than the theme.

### Principle 2 --- Space should be subtle

The user should notice the space aesthetic without feeling like they
entered a game.

### Principle 3 --- Real UI over fake sci-fi

Use real developer concepts:

``` text
Build
Deploy
Logs
Projects
Environment
Production
Commit
Branch
Uptime
```

Avoid meaningless futuristic terminology.

### Principle 4 --- Negative space

Do not fill every empty area with stars, lines, planets, or animations.

### Principle 5 --- Consistency

The same visual language should continue across:

``` text
Landing page
Authentication
Dashboard
Projects
Deployments
Logs
Settings
```

### Principle 6 --- Signature interaction

The spaceship cursor should become one of the recognizable Syphership
details.

------------------------------------------------------------------------

# 21. Landing Page Structure

Final landing page structure:

``` text
NAVIGATION
    ↓
HERO
    ├── Headline
    ├── Description
    ├── CTA buttons
    └── Orbital visualization
    ↓
FROM COMMIT TO PRODUCTION
    ├── Build
    ├── Deploy
    └── Run
    ↓
PRODUCT DASHBOARD PREVIEW
    ├── Metrics
    ├── Projects
    └── Deployment states
    ↓
FEATURES
    ↓
FINAL CTA
    ↓
FOOTER
```

------------------------------------------------------------------------

# 22. Overall Target

The final Syphership website should communicate:

> **A serious developer platform with a distinctive orbital identity.**

The goal is not to make the most visually complicated space website.

The goal is to make someone look at Syphership and immediately
recognize:

**"This is a deployment platform, and its identity is built around
shipping software into orbit."**
