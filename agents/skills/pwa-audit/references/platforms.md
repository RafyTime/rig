# Platform and verification notes

Reference baseline checked 2026-11-04. Consult current primary sources for selected browser/OS versions during each audit. Release announcements can supersede older tutorials. A standard's existence does not establish shipping browser support.

## Installation

- **Chromium:** Browser-menu installation, automatic promotion, and `beforeinstallprompt` have different conditions. The prompt API is not universal, and its absence does not prove installation is impossible. Evaluate the actual path users will take. [Current promotion criteria](https://web.dev/articles/install-criteria), [criteria changes](https://developer.chrome.com/blog/update-install-criteria), [prompt API](https://developer.mozilla.org/en-US/docs/Web/API/Window/beforeinstallprompt_event).
- **iOS/iPadOS:** Use platform-appropriate Add to Home Screen guidance. Since version 26, sites added to the Home Screen open as web apps by default, with an Open as Web App choice. Older statements that a manifest display value or proprietary meta tag is always required need version qualification. Test the installed app, not just a Safari tab. [WebKit Safari 26](https://webkit.org/blog/17333/webkit-features-in-safari-26-0/).
- **macOS Safari:** Add to Dock is available from macOS Sonoma and can install an ordinary website. This is a separate journey from iPhone installation. [Apple web apps guidance](https://support.apple.com/en-gb/104996).
- **Firefox:** Check the specific OS and release. Mozilla documents web apps on Windows; blanket claims that desktop Firefox cannot install web apps are outdated. Do not infer support on other operating systems from that feature. [Mozilla guidance](https://support.mozilla.org/en-US/kb/web-apps-firefox-windows).
- **Embedded browsers and restricted contexts:** Installation or permissions may be unavailable. If these are important acquisition paths, verify an understandable route into a supported browser rather than offering an inert button.

## Assets and launch

Chromium's promotional criteria include suitable 192px and 512px icons. Inspect actual image files and maskable padding. Rich install screenshots improve supported dialogs; they are not a universal install prerequisite. Android derives splash presentation from manifest assets/colors; Apple startup-image handling is platform-specific. A generated image for every historical device size is not a universal essential. Check the actual target launch experience and justify any extra assets. [Manifest and splash guidance](https://web.dev/learn/pwa/web-app-manifest), [rich install UI](https://developer.chrome.com/blog/richer-install-ui-desktop).

Keep manifest `id` stable across releases. Changes to installed names, icons, or metadata may propagate differently from application code; verify target-platform update behavior before promising an immediate change. [Manifest updates](https://web.dev/learn/pwa/update).

## Updates

An updated worker normally waits while the old worker still controls clients. A refresh is not a dependable way to activate a waiting worker. Immediate activation can let a new worker handle requests from an older page. Check multiple tabs, unsaved work, lazy-loaded chunks, and data migrations before choosing an update policy. A prompt is appropriate when users need control; natural activation can also satisfy the product. [Lifecycle](https://developer.chrome.com/docs/workbox/service-worker-lifecycle), [update coordination recipe](https://developer.chrome.com/docs/workbox/handling-service-worker-updates).

Build a version A/B test locally when feasible: open A, make a meaningful state change, serve B through the same isolated origin, and exercise the intended update path. Verify pending work and subsequent navigation. Use a dedicated browser profile and local ports so test workers and caches do not interfere with daily browsing or shared previews.

## Offline, storage, and push

An installed app is not automatically usable offline. Separate a fresh visit with no prepared data from a returning user's cached session. Test request failure even when the device reports itself online. [Offline operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation), [online-status limitations](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/onLine).

Storage is subject to quota, eviction, and user clearing; persistence is not a backup. Avoid repeating a blanket claim that all installed iOS app data disappears after seven days. Home Screen apps have specific policy treatment, and quota/eviction remain relevant. [WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/), [tracking prevention and Home Screen exemptions](https://webkit.org/tracking-prevention/).

Web Push is supported for Home Screen web apps from iOS/iPadOS 16.4, with permission tied to user interaction. This does not imply that every background API works there. Check push, background sync, periodic sync, and file integration independently; supply foreground recovery when needed. [WebKit Web Push](https://webkit.org/blog/13878/).

## Choosing evidence

- Inspect generated manifests, worker output, and relevant served headers. Respect the project's framework/plugin rather than prescribing a second worker implementation.
- Use available browser automation, DevTools, Lighthouse, or accessibility tooling for the questions they can answer. Lighthouse removed its PWA category in v12; there is no current PWA score to require. [Release notes](https://github.com/GoogleChrome/lighthouse/releases/tag/v12.0.0).
- Browser emulation can inspect layout and request failures but does not establish native installation, splash presentation, OS termination, or device-specific permission behavior. Leave those criteria unverified until exercised on suitable hardware or a representative platform environment.
- Keep credentials and private pages out of third-party audit services unless authorized. Use local tooling for authenticated journeys where possible.
- Every limitation should identify a next check. For example: "Not verified on iPhone: install on the target iOS version, cold-launch with connectivity disabled, and open a previously saved ticket."

## Workflow references

These informed the skill's design and are optional reading, not runtime dependencies:

- [Matt Pocock's grilling](https://github.com/mattpocock/skills/blob/main/grilling/SKILL.md): investigate facts; ask product decisions in dependent rounds. This skill bounds the interview to decisions that affect PWA scope.
- [Matt Pocock's writing for agents](https://github.com/mattpocock/skills/blob/main/writing-for-agents/SKILL.md): clear completion criteria and conditional references.
- [Addy Osmani's web quality audit](https://github.com/addyosmani/web-quality-skills/blob/main/skills/web-quality-audit/SKILL.md): distinguish runtime evidence from source hypotheses.
- [NexFabric's PWA audit](https://github.com/NexFabric/pwa-review-skill): a coverage cross-check. This skill uses product-specific outcomes instead of feature-presence totals.
- [Emil Kowalski's mobile-native](https://skills.sh/emilkowalski/skills/mobile-native): attention to mobile interaction and real-device verification.
