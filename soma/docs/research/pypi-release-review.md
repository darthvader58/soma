# Python release and documentation review

The integrating agent personally reviewed the library README and Mintlify documentation on November 25, 2026. This is an agent review of this bounded release, not a formal accessibility certification or a human usability study. No application UI source was changed for this release.

Reading this as: Python scientific-library documentation for researchers and developers, using the existing dark technical-reference style, ENERGY 1 / RHYTHM 2 / MOTION 1. The user requested dark-only presentation and complete library documentation. The established Mintlify navigation and green accent remain; the implementation adds actual library content rather than a new marketing skin.

## Direction and evidence

- Color: neutral dark surfaces preserve the requested theme; the existing green accent identifies navigation and links.
- Layout: a reading column, module navigation and page outline support lookup; tutorials progress through calculation, replay and export.
- Typography: the existing reading face serves prose, while monospace is confined to executable code and identifiers.
- Spacing: headings separate tasks and scientific qualifications from examples; code blocks scroll within their own containers.
- Components: tables compare installation extras and contract fields; no promotional cards or new illustrations were added.
- Badges: README badges link to the actual package, supported Python versions, workflow, license and documentation.
- Motion: only the documentation platform's navigation/focus transitions are used; there is no added animation.

The integrating agent built the documentation and checked links, anchors and redirects from `docs/`; all passed. `docs/scripts/generate_api_catalog.py --check` passed. The integrating agent executed all 21 selected data-free Python blocks across nine documentation pages in temporary working directories. Physical acquisition examples were not executed by that check.

Personal Aside inspection covered the quickstart and generated API catalog on desktop and at an actual 390 CSS-pixel viewport. The document width remained 390 pixels; long code scrolled within its block. Copy returned the visible `Copied` status. Enter opened mobile navigation and followed Installation; Escape dismissed search. Local search explicitly requires `mint login`, so local preview search is not represented as a production search verification. The measured normal-text pair `#a1a1a0` on `#0c0c0d` has 7.56:1 contrast using the skill's contrast checker. The page exposes `lang="en"`, a title, a main landmark and named native controls.

The final local engine suite passed 490 tests with 21 skips for conditionally available checks; installed-wheel checks were run separately and both passed. The complete PR validation matrix passed engine suites on Python 3.12/3.14 and clean distribution installs on Linux 3.12/3.13/3.14, macOS 3.14 and Windows 3.14: https://github.com/darthvader58/soma/actions/runs/45678072576 . A duplicate push workflow's macOS job acquired no runner and executed no steps; its annotation reported hosted-runner capacity constraints. Strict Twine and archive audits passed. Fresh installed-wheel checks calculated the 100 MiB synthetic relay case and independently replayed and verified its ZIP. These are software checks, not mission predictions.

## Hard gate

- R-02 PASS: new README and documentation prose was scanned for em dashes; none were introduced. Original scientific source titles remain unchanged.
- R-03 PASS: personal 390-pixel inspection measured a 390-pixel document; long code remains internally scrollable.
- R-17 PASS: fixture byte counts follow the declared inputs; the signature catalog is generated from source. No adoption or performance numbers were invented.
- R-18 PASS: no testimonials, avatars or fictional people were added.
- R-23 PASS: the user requested proper library documentation and README badges; no new logo, portrait or decorative visual asset was created.
- R-24 PASS: Mintlify's build and internal link/anchor/redirect checks passed for all configured pages.
- R-25 PASS: the inspected normal-text pair measures 7.56:1; existing dark theme and code highlighting are retained.
- R-26 PASS: copy feedback, mobile navigation and keyboard page links were exercised; local search states its authentication requirement.
- R-27 PASS: installation, missing solver, missing data, unsupported coverage, unresolved optimization and replay failures have specific instructions and examples; the library preserves unknown outcomes.
- R-28 PASS: no generic FAQ was added.
- R-32 PASS: native controls expose names and focus; Enter opened navigation and followed Installation, and Escape dismissed search.
- R-33 PASS: changes are maintained Markdown/MDX and Python source; the API catalog has an explicit source generator and CI drift check.
- R-34 PASS: dark-only is the user's instruction and strict Mintlify appearance is configured; no partial theme toggle was added.
- R-35 PASS: documentation was built and inspected; changed code examples executed, and copy/navigation controls were exercised.
- R-36 PASS: no compliance, security, customer or flight-readiness claim was added.
- R-37 PASS: the existing technical documentation direction and explicit dials are recorded above.
- R-38 PASS: example hardware, rates, contacts, service and relay states retain synthetic or assumed labels; public API entries come from maintained source.
- R-39 PASS: named native buttons, links, keyboard focus and English document metadata were inspected; no new input form, ARIA override, blocked zoom or ongoing animation was introduced.
- R-40 PASS: this change adds no media or render-blocking script and reports no unmeasured page-performance number; code and tables retain bounded regions.

## Purpose gate

- R-01 PASS: no new decorative gradient or glow was added.
- R-04 PASS: existing search, navigation and copy icons identify those functions; no decorative icon set was introduced.
- R-06 PASS: prose uses the existing reading face; monospace identifies executable code and API symbols.
- R-07 PASS: no background grid or pattern was introduced.
- R-08 PASS: previous/next navigation communicates real page relationships; no decorative arrows were added to calls to action.
- R-09 PASS: README badges report actual package, workflow, license and documentation records and link to those records.
- R-10 PASS: the existing documentation shell is retained; no stacked glass effect was added.
- R-12 PASS: spacing and code boundaries organize content; no repeated floating-card shadows were added.
- R-13 PASS: no distributed glow treatment was added.
- R-14 PASS: tutorials, reference signatures, tables and prose follow their distinct content needs; no repeated feature-card grid was introduced.
- R-19 PASS: no new animation was added; platform navigation transitions are consistent with MOTION 1.
- R-22 PASS: no generic illustration was introduced.

## Liveliness

- Dials PASS: ENERGY 1 / RHYTHM 2 / MOTION 1 are explicit above.
- Consistency PASS: restrained documentation, varied task/reference sections and limited transitions match the declared dials.
- Focal point PASS: each page has a task-specific heading and central reading/code column.
- Whitespace PASS: spacing separates scientific assumptions, commands and returned records.
- Accent PASS: the established green navigation/link accent is retained without new decorative color treatments.
- Identity PASS: explicit lunar frames, UTC, resource units, scientific status and replay recur across the examples.
- Design read PASS: this release continues the established dark technical-reference direction, recorded before final delivery.

## Craftsmanship and quality locks

- C-1 PASS: the direction record gives task-based reasons for palette, typography, spacing and structure.
- C-2 PASS: inspected copy and navigation controls work; local search's login requirement is explicit.
- C-3 PASS: content covers actual installation, calculation, reproduction, APIs and contribution tasks.
- C-4 PASS: desktop, narrow code layout, keyboard navigation and explicit failure guidance were checked.
- C-5 PASS: package metadata, fixture arithmetic and API signatures are traceable to maintained source and executed examples.
- R-05 PASS: this is a library manual with tutorials and reference sections, not a marketing-page template.
- R-11 PASS: native documentation controls and code regions retain the existing component treatment; no universal pill styling was added.
- R-15 PASS: action labels name their destination or operation, including Installation, Your first delivery plan and Copy.
- R-16 PASS: the new copy uses concrete workflow and model terms without promotional AI claims.
- R-20 PASS: lunar frame/terrain conventions, delayed byte availability and independent replay make the content specific to SOMA.
- R-21 PASS: dark-only follows the explicit user preference.
- R-29 PASS: neutral surfaces and the established green accent preserve the existing palette; syntax colors communicate code tokens.
- R-30 PASS: the existing documentation platform is used for SOMA's actual library content; no unrelated product design was copied.
- R-31 PASS: the direction section states a concrete purpose for each major visual decision.

All gate items pass for this bounded documentation change.

## Published artifacts and installation

PR #26 merged as `8418d027e30ce1b670a33d828e4fcecc1f18873f`. The normal-date `v0.1.0` tag triggered the successful [build and trusted-publishing workflow](https://github.com/darthvader58/soma/actions/runs/45685077384). The public PyPI page confirms version 0.1.0, Python >=3.12, GPL-3.0-only, workflow extras and provenance for both files.

The integrating agent performed an uncached install from `https://pypi.org/simple` in a new temporary environment outside the checkout. Both installed-distribution tests passed in 21.78 seconds: resources and console validation, insufficient direct contact, complete synthetic 100 MiB relay delivery, independent replay and ZIP verification. A separate fresh install of `soma-lunar[planning,service,verification]==0.1.0` passed `pip check`, imported all selected dependencies, exposed the installed local service's `/plans` OpenAPI path and found an executable CBC solver.

The distributions downloaded from the publishing workflow match PyPI's SHA-256 records exactly. Those same files are attached to the [GitHub release](https://github.com/darthvader58/soma/releases/tag/v0.1.0).

| Artifact | Bytes | SHA-256 |
| --- | ---: | --- |
| `soma_lunar-0.1.0-py3-none-any.whl` | 3,926,444 | `6d0e4907701fc54d4b547de348ec0e4b6a445a07f7194a24a472e3eab3fb04c5` |
| `soma_lunar-0.1.0.tar.gz` | 3,860,892 | `e34dac8196ade688f3db977482f968e5978f37aa68cc533a01f34aa9a69aa515` |

The installation guide records every direct dependency and extra from the published metadata, the CBC check, and the distinction between Python dependencies and separately acquired scientific files. A source-to-documentation comparison confirmed that every declared direct dependency version appears in that guide.
