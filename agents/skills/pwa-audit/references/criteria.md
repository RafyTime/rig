# PWA audit criteria

Use this catalog to discover gaps and select outcomes for the agreed product target. Each ID is an outcome to score, not a point for using a particular API. Turn its checks into acceptance conditions for the relevant journeys. Add a project-specific criterion when a core promise is not covered here.

## Foundation and identity

Applies when the product targets an installed experience, or an existing PWA setup needs assessment.

- **F1. Delivery and configuration.** The served app links the intended manifest; manifest and worker URLs resolve correctly under the deployed base path, MIME types are appropriate, HTTPS is used outside local development, and worker scope is intentional. Inspect the built output as well as source configuration. Existing conflicting registrations are accounted for.
- **F2. Identity and launch.** Names, stable identity, start URL, navigation scope, display fallback, and language describe the app correctly. Launch works through login and deep links. Distinguish browser defaults from actual missing requirements; an absent optional field is not inherently a failure. Manifest scope and worker scope are independent.
- **F3. Visual assets.** Icons are reachable, have actual dimensions appropriate to target platforms, and remain legible under platform masks. Check maskable artwork padding, ordinary icons, and Apple touch icons where applicable. Screenshots and shortcuts support the intended installation journey when useful; declarations point to real routes/assets.
- **F4. Launch appearance.** Background, theme color, status/title bars, loading state, and light/dark appearance form a readable transition into the app. Test the rendered icon and launch appearance on target platforms. Require platform-specific startup imagery only when the agreed launch experience needs it.

References: [manifest specification](https://www.w3.org/TR/appmanifest/), [manifest guidance](https://web.dev/learn/pwa/web-app-manifest), [app design](https://web.dev/learn/pwa/app-design).

## Installation and installed navigation

Applies to the chosen installation and platform targets. Retain ordinary browser usability.

- **I1. Installation path.** Users can follow a working installation path for each target browser/OS. Distinguish menu installation, promotional eligibility, and a custom prompt. Verify the installed result rather than assuming an install event proves success.
- **I2. Installation guidance.** If custom promotion is justified, it explains a benefit, appears at a useful moment, respects dismissal, and offers a supported action. Unsupported browsers get accurate instructions or no promotion. Hide promotion in the current installed context; avoid assuming universal knowledge of installations elsewhere.
- **I3. Navigation and identity boundaries.** Installed launch, deep links, refresh, back navigation, external links, and out-of-scope URLs behave predictably. Test authentication redirects and payment or third-party windows where used. Users can navigate without browser controls the selected display mode hides.

References: [installation criteria](https://web.dev/articles/install-criteria), [custom prompt](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/How_to/Trigger_install_prompt). Read the selected-platform notes before assigning install requirements.

## Service worker and updates

Applies where workers or persistent asset caches exist or are needed by the target. A worker is not automatically required for an online-only installed experience.

- **U1. Worker lifecycle.** Registration, install, activation, and update discovery succeed in the built app. The worker script can update, registration errors have useful recovery, and competing workers or obsolete registrations do not take control unexpectedly.
- **U2. Safe version transitions.** An existing session can transition to the next version without losing work or mixing incompatible page, worker, lazy-loaded asset, API, or stored-data versions. Check multiple tabs/windows and long-lived sessions. Use natural activation when adequate; a prompt is a product choice. If immediate activation is used, verify its coordination and safe reload behavior.
- **U3. Cache and rollback hygiene.** Revisioning, cleanup, resource retention, and error recovery support old and new clients during rollout or rollback. Cleanup is limited to caches the app owns. Existing installations can recover when PWA support is removed; deleting source registration alone does not retire a previously installed worker.

References: [worker lifecycle](https://developer.chrome.com/docs/workbox/service-worker-lifecycle), [immediate updates](https://developer.chrome.com/docs/workbox/handling-service-worker-updates).

## Connectivity and offline behavior

**N1 applies to core network-dependent journeys even in online-only products.** N2-N4 depend on the agreed offline promise and any existing caching or synchronization behavior.

- **N1. Honest failure and recovery.** Slow or failed requests leave understandable loading, error, retry, and recovery states. Preserve user input where relevant. Handle request failures rather than trusting `navigator.onLine`. Distinguish server rejection from network failure and avoid duplicate consequential actions on retries.
- **N2. Offline launch and navigation.** After the documented preparation, the promised routes, assets, and content work without connectivity. Test cold launch, reload, visited and unvisited routes, missing cache entries, and network restoration. Document first-visit limitations. A fallback page is sufficient only if it meets the agreed promise.
- **N3. Freshness and cache boundaries.** Choose strategies by resource and data sensitivity. Time-sensitive values, authenticated responses, errors, opaque responses, media range requests, and third-party resources receive intentional handling where relevant. Show when stale content matters. Bound cache growth and handle missing or outdated assets.
- **N4. Offline writes and synchronization.** When supported, show pending, failed, and completed work; preserve it across restart; use safe retry/idempotency and an explicit conflict policy. Test reconnect, expired authentication, account changes, duplicate delivery, and partial server success. Provide foreground recovery where background APIs are unavailable.

References: [caching](https://web.dev/learn/pwa/caching), [offline operation](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Offline_and_background_operation), [connectivity hints](https://developer.mozilla.org/en-US/docs/Web/API/Navigator/onLine).

## Storage, accounts, and permissions

Apply the relevant outcomes to the actual persisted data and capabilities, including caches an existing worker already creates.

- **D1. Storage resilience.** Handle quota failures, eviction, cleared storage, unavailable persistence, and schema upgrades without falsely reporting that work was saved. Offer re-download, export, or recovery where the product promise needs it. A persistence request does not guarantee permanent data retention.
- **D2. Account and privacy boundaries.** Cache/local-data policy matches sensitivity and shared-device use. Test logout, session expiry, user/tenant switching, offline access, and queued work belonging to a former account. Protected data must not leak across those boundaries. Inspect both worker caching and ordinary HTTP/CDN policy when they affect the finding.
- **D3. Contextual permissions.** Request permissions when the user takes a relevant action, explain the benefit, and support denial or revocation. Push subscriptions and other retained identifiers follow account ownership and logout decisions. Review relevant security headers for actual exposure; header presence alone is not proof of safety.

References: [offline data](https://web.dev/learn/pwa/offline-data), [storage quotas and eviction](https://developer.mozilla.org/en-US/docs/Web/API/Storage_API/Storage_quotas_and_eviction_criteria), [WebKit storage policy](https://webkit.org/blog/14403/updates-to-storage-policy/).

## Layout and interaction

Applies to core journeys on supported form factors, both in a tab and installed. Focus on concrete defects rather than enforcing a particular visual style.

- **X1. Viewport and input.** Responsive layout, safe areas, browser chrome, virtual keyboard, orientation, and desktop resizing leave controls readable and reachable. Inspect fixed bars, overlays, full-height layouts, zoom, and focused inputs on the relevant devices.
- **X2. Interaction and session continuity.** Touch, keyboard, mouse, scrolling, and gestures work where supported without accidental double actions or trapping navigation. On resume or OS termination, restore essential state or communicate its loss. Reconnect real-time subscriptions when the app uses them; assess the actual connection lifecycle rather than mandating particular event handlers.

References: [PWA app design](https://web.dev/learn/pwa/app-design), [PWA best practices](https://developer.mozilla.org/en-US/docs/Web/Progressive_web_apps/Guides/Best_practices).

## Accessibility

Use WCAG 2.2 AA as the default technical baseline unless a different target is agreed. Cover representative core journeys and PWA-specific install, update, connectivity, and permission UI. A focused PWA audit is not a complete site-wide conformance evaluation.

- **A1. Semantics and navigation.** Controls have appropriate semantics and accessible names; keyboard order, visible focus, dialogs, focus restoration, page changes, form labels, validation, and accessible authentication work in the selected journeys. Prefer native elements; additional ARIA is not a positive signal on its own.
- **A2. Perception and operation.** Verify contrast, text resizing, reflow, target size/spacing, alternatives to dragging or complex gestures, and reduced-motion behavior where relevant. WCAG 2.5.8 has a 24 CSS pixel target-size minimum with exceptions; larger targets can be appropriate without being a universal conformance rule.
- **A3. Dynamic PWA states.** Screen readers receive meaningful update, offline, retry, and synchronization status. Prompts are dismissible and keyboard-accessible, do not obscure focus, and do not repeatedly interrupt the task. Combine automated checks with manual keyboard and assistive-technology checks; record what was actually exercised.

References: [WCAG 2.2](https://www.w3.org/TR/WCAG22/), [criterion explanations](https://www.w3.org/WAI/WCAG22/Understanding/), [automation limits](https://www.w3.org/WAI/test-evaluate/tools/selecting/).

## Performance

Applies to representative journeys on the target device/network conditions. Use available measurement tools; do not require a specific provider or a perfect Lighthouse score.

- **P1. Loading and responsiveness.** Measure cold and warm loads, interaction responsiveness, visual stability, and installed startup where relevant. Use current Core Web Vitals: good field thresholds are LCP <= 2.5 s, INP <= 200 ms, CLS <= 0.1 at the 75th percentile, segmented by mobile/desktop. Report field performance unverified when field data is absent; a lab score or TBT is not measured field INP.
- **P2. Delivery and worker cost.** Diagnose measured bottlenecks in scripts, images, fonts, server delivery, precaching, and worker startup/routing. Compare cold and warm behavior so caching does not hide an expensive initial visit. Recommend preload, code splitting, compression, or cache changes only when evidence supports the benefit.

References: [Web Vitals](https://web.dev/articles/vitals), [lab and field differences](https://web.dev/articles/lab-and-field-data-differences), [Lighthouse PWA category removal](https://github.com/GoogleChrome/lighthouse/releases/tag/v12.0.0).

## Optional platform capabilities

Evaluate only capabilities tied to an agreed user need or already present in the app. Unsupported capabilities need graceful fallback; absence alone is not a defect.

- **C1. Capability delivers its promise.** For push, badges, share targets, file/protocol handlers, shortcuts, background work, or other integrations, verify permission flow, actual handling, launch routing, fallback, and target-platform support. A declaration without a working handler is incomplete. Notifications should open the intended account and destination without exposing sensitive content.

Reference: [PWA enhancements](https://web.dev/learn/pwa/enhancements). Verify individual APIs against current vendor documentation rather than treating this as a feature inventory.
