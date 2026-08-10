# Changelog

## [1.15.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.14.0...v1.15.0) (2026-08-10)


### Features

* **diagnostics:** attach anonymized request report on API failures ([4583557](https://github.com/cyrilcolinet/enki-integration-hass/commit/45835579ca7d201f60786b83d15ea4d9aebe585d))


### Bug Fixes

* **api:** surface response body in failed request errors ([333a1e2](https://github.com/cyrilcolinet/enki-integration-hass/commit/333a1e297f6b247e497e62d3d81172eee60cdf26))

## [1.14.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.13.2...v1.14.0) (2026-08-07)


### Features

* **diagnostics:** map uncovered capabilities to APK routes ([9351d5f](https://github.com/cyrilcolinet/enki-integration-hass/commit/9351d5f391b046b92e0caaaa92cca1934b86b0c3)), closes [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)

## [1.13.2](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.13.1...v1.13.2) (2026-08-07)


### Bug Fixes

* **discovery:** skip dashboard items missing deviceId ([85ec525](https://github.com/cyrilcolinet/enki-integration-hass/commit/85ec525548cb40169aa872c6a0b8d1867a9dcf50)), closes [#131](https://github.com/cyrilcolinet/enki-integration-hass/issues/131)

## [1.13.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.13.0...v1.13.1) (2026-08-04)


### Bug Fixes

* **telemetry:** mark check_multisensor_state as covered ([b893dfd](https://github.com/cyrilcolinet/enki-integration-hass/commit/b893dfdf6cdfa8580b2c156f2af8cb5e749c415c)), closes [#126](https://github.com/cyrilcolinet/enki-integration-hass/issues/126)

## [1.13.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.12.0...v1.13.0) (2026-08-01)


### Features

* **binary_sensor:** expose dry-contact electric-strike state ([e83a4f7](https://github.com/cyrilcolinet/enki-integration-hass/commit/e83a4f77ee893a321bebd734fad2d4d78478178c)), closes [#121](https://github.com/cyrilcolinet/enki-integration-hass/issues/121)


### Bug Fixes

* **api:** tolerate empty and non-JSON GET responses ([01e553a](https://github.com/cyrilcolinet/enki-integration-hass/commit/01e553a7eb260660a30930426b95fe92c151c0f7))
* **telemetry:** mark check_bulb_state as covered ([3338472](https://github.com/cyrilcolinet/enki-integration-hass/commit/3338472e5dbcc31263b0143fb871ca3bf9237b68)), closes [#122](https://github.com/cyrilcolinet/enki-integration-hass/issues/122)

## [1.12.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.11.0...v1.12.0) (2026-07-30)


### Features

* **fan:** restore Cadix pre-fan light state on stop ([423b57f](https://github.com/cyrilcolinet/enki-integration-hass/commit/423b57fe8bcf16bbbaa7282ef6a836f474d03942))

## [1.11.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.10.0...v1.11.0) (2026-07-30)


### Features

* **fan:** mirror Cadix fan/light coupling optimistically on start ([6cf2ecf](https://github.com/cyrilcolinet/enki-integration-hass/commit/6cf2ecf6639109ea9821d3f5816f990062c4334a))


### Bug Fixes

* **coordinator:** hold optimistic writes against stale cloud polls ([3dd5a36](https://github.com/cyrilcolinet/enki-integration-hass/commit/3dd5a36799b99205f73d55cc4757df11beda5187))

## [1.10.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.9.1...v1.10.0) (2026-07-29)


### Features

* **coordinator:** reconcile firmware side effects after commands ([4ec9c7b](https://github.com/cyrilcolinet/enki-integration-hass/commit/4ec9c7b4809b7d6e172a2043ef65c74ab6b6e5ff))

## [1.9.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.9.0...v1.9.1) (2026-07-29)


### Bug Fixes

* **light:** coalesce optimistic writes into one refresh ([8db8d4f](https://github.com/cyrilcolinet/enki-integration-hass/commit/8db8d4ffc6ece945f7632f1952823031edf6c947))
* **light:** keep dual fan light kits state in sync ([f8bd899](https://github.com/cyrilcolinet/enki-integration-hass/commit/f8bd8993b5164b34bbb90a200677782409135ee6))

## [1.9.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.8.0...v1.9.0) (2026-07-29)


### Features

* **light:** expose dual light kits on speed-driven ceiling fans ([926159f](https://github.com/cyrilcolinet/enki-integration-hass/commit/926159f0d0831ea80b8b84743388fef0e254ee0a))
* **switch:** expose water-heater on/off relay as a switch ([0facce5](https://github.com/cyrilcolinet/enki-integration-hass/commit/0facce5e9d69fb4ee8bae5d77a9d09c30b5682d0))

## [1.8.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.7.1...v1.8.0) (2026-07-27)


### Features

* **cover:** support RTS roller shutters without position ([4ad9bf8](https://github.com/cyrilcolinet/enki-integration-hass/commit/4ad9bf86ca14a476550cb0dab688c60d2d83f51a)), closes [#96](https://github.com/cyrilcolinet/enki-integration-hass/issues/96)


### Bug Fixes

* **api:** publish the discovery snapshot atomically ([fab9f15](https://github.com/cyrilcolinet/enki-integration-hass/commit/fab9f15e5ad63b49bb0b08dd8f9fdee5c06ecf93)), closes [#87](https://github.com/cyrilcolinet/enki-integration-hass/issues/87)

## [1.7.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.7.0...v1.7.1) (2026-07-26)


### Bug Fixes

* **diagnostics:** keep control hints on the discovery record ([85f6e56](https://github.com/cyrilcolinet/enki-integration-hass/commit/85f6e5696802918185ad8ff73c2a9344532fc088)), closes [#87](https://github.com/cyrilcolinet/enki-integration-hass/issues/87)

## [1.7.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.6.21...v1.7.0) (2026-07-26)


### Features

* **diagnostics:** expose control hint and telemetry exclusion ([d2a4849](https://github.com/cyrilcolinet/enki-integration-hass/commit/d2a4849dae9d36089497982867d4e29d82a7f309)), closes [#87](https://github.com/cyrilcolinet/enki-integration-hass/issues/87)

## [1.6.21](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.6.20...v1.6.21) (2026-07-25)


### Bug Fixes

* **ci:** open release PR ready, fix title pattern ([a37bce6](https://github.com/cyrilcolinet/enki-integration-hass/commit/a37bce66c32ce5a407956c79ef64fad2aacf90a1))
* close API session when entry setup fails ([b6bfa65](https://github.com/cyrilcolinet/enki-integration-hass/commit/b6bfa65d479ef055b62eaa4d1e5fe505bb469ed3))
* **diagnostics:** restore Download diagnostics button ([90a6b1b](https://github.com/cyrilcolinet/enki-integration-hass/commit/90a6b1bec237bc208c35a935344d565f85fa03b5))
* **sensor:** drop UnitOfRatio, unsupported before HA 2026.7 ([3eee87f](https://github.com/cyrilcolinet/enki-integration-hass/commit/3eee87fe3249b6f5dd78ed9599668a412ae122df))

## [1.6.20](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.6.19...v1.6.20) (2026-07-13)


### Bug Fixes

* **ci:** restore release gate, drop default with ([81ee3ed](https://github.com/cyrilcolinet/enki-integration-hass/commit/81ee3ed8c08ed409f278ec05920195c9d3a84b69))
* **light:** honor own endpoint_id in bare power fallback ([89f906f](https://github.com/cyrilcolinet/enki-integration-hass/commit/89f906f10320db7a033c4555edd19a3eb2b7204e))
* **light:** prefer fan_light_endpoints for bare on/off fallback ([1398807](https://github.com/cyrilcolinet/enki-integration-hass/commit/139880777efaba95d4daf56e816bbb1b01567bb3))
* **light:** route bare fan-light on via switch_electrical_power when unschemed ([d2bc56d](https://github.com/cyrilcolinet/enki-integration-hass/commit/d2bc56db5e4e3ba49b4ad1674dc05988422081e4)), closes [#74](https://github.com/cyrilcolinet/enki-integration-hass/issues/74)
* **telemetry:** silence SDK admin capability gaps ([88228a8](https://github.com/cyrilcolinet/enki-integration-hass/commit/88228a8339746394127955b0a719f53173a02038))

## Changelog

All notable changes to this project are documented in this file.

Release notes are generated by [release-please](https://github.com/googleapis/release-please)
from [Conventional Commits](https://www.conventionalcommits.org/) on `main`.
