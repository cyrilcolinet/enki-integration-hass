# Changelog

## [1.19.2](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.19.1...v1.19.2) (2026-08-31)


### Bug Fixes

* **telemetry:** mark hue/saturation as covered for RGB lights ([c82d1b7](https://github.com/cyrilcolinet/enki-integration-hass/commit/c82d1b73bc7a2c212c1b6ebb09e73e1be5b340ff)), closes [#187](https://github.com/cyrilcolinet/enki-integration-hass/issues/187)

## [1.19.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.19.0...v1.19.1) (2026-08-21)


### Bug Fixes

* **manifest:** drop aiohttp requirement ([9bbd360](https://github.com/cyrilcolinet/enki-integration-hass/commit/9bbd360f3bd7449dc030f1c8e90d72d0aad6e992))

## [1.19.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.18.0...v1.19.0) (2026-08-21)


### Features

* **api:** debug-log accepted outbound commands ([6eeceea](https://github.com/cyrilcolinet/enki-integration-hass/commit/6eeceea8a7b9eb702723efa19d0c1caaebd66154))
* **automation:** expose device triggers for binary sensors ([3781a0a](https://github.com/cyrilcolinet/enki-integration-hass/commit/3781a0a66d44cddc8cfaf71f2c2c60ab03e13b4c))

## [1.18.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.17.0...v1.18.0) (2026-08-21)


### Features

* **auth:** reauth flow + translated repair issues ([43edaf6](https://github.com/cyrilcolinet/enki-integration-hass/commit/43edaf64eed557d7f08bf9c13206185131215e46))
* **blueprints:** add frost, humidity, consumption, tamper, pilot-wire ([808a8fa](https://github.com/cyrilcolinet/enki-integration-hass/commit/808a8fad6aaae6dc3b6f7c3638c526e9d86686c6))
* **blueprints:** add leak, low-battery, window-heating automations ([38751de](https://github.com/cyrilcolinet/enki-integration-hass/commit/38751dee1075c546877054d71c573f15b4d5582e))
* **blueprints:** add motion light, auto fan, covers, contact, siren ([45280f8](https://github.com/cyrilcolinet/enki-integration-hass/commit/45280f85ec16395f5eaaa377772948c5a11e8a41))
* **blueprints:** add vibration, update, offline, solar, away, sunset ([a70ab1a](https://github.com/cyrilcolinet/enki-integration-hass/commit/a70ab1aa25f8c7ba4943573905bec367767d197c))
* **entities:** categorize config and diagnostic entities ([41c33f1](https://github.com/cyrilcolinet/enki-integration-hass/commit/41c33f1e8045206527882a898a5cf19b85e2f5a6))
* **thermostat:** add offset, child-lock, preheating controls ([0b14777](https://github.com/cyrilcolinet/enki-integration-hass/commit/0b1477756b6711b3d7627686733a6d512f95d7de)), closes [#167](https://github.com/cyrilcolinet/enki-integration-hass/issues/167)
* **update:** expose device firmware in Settings → Updates ([d7f3ba0](https://github.com/cyrilcolinet/enki-integration-hass/commit/d7f3ba02268bd8471860bd3379f8907a264475a3))


### Bug Fixes

* **referentiel:** bump version 2.23.0 → 2.26.0 ([daaa915](https://github.com/cyrilcolinet/enki-integration-hass/commit/daaa915e5067e5d4f80d70d6406a2b9dbf9021a0))

## [1.17.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.16.1...v1.17.0) (2026-08-20)


### Features

* **camera:** add motion-notification blueprint + README ([7ece00f](https://github.com/cyrilcolinet/enki-integration-hass/commit/7ece00f040da5bee847577665e7b7696fd5fcba0)), closes [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)
* **camera:** expose Lexman camera events as HA entities ([fa8bfc4](https://github.com/cyrilcolinet/enki-integration-hass/commit/fa8bfc41cee3e0d398f0a91e14b9d45cc2635d60)), closes [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)


### Bug Fixes

* **camera:** distinct FR name for the snapshot entity ([96421ab](https://github.com/cyrilcolinet/enki-integration-hass/commit/96421ab74fcd8e3617725c6348e1ac332057fa78)), closes [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)
* **camera:** mark cameras as supported so discovery creates the device ([006c61b](https://github.com/cyrilcolinet/enki-integration-hass/commit/006c61b9cab2d20629bf30f1e1ed11c47dec5cfb)), closes [#135](https://github.com/cyrilcolinet/enki-integration-hass/issues/135)

## [1.16.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.16.0...v1.16.1) (2026-08-19)


### Bug Fixes

* **apk:** auto-detect DI classes and correct camera-meari key ([9d93863](https://github.com/cyrilcolinet/enki-integration-hass/commit/9d938634df2c3a92864c534c70a09871238697e0))
* **fan:** read power-only fan on/off from electrical power ([582521e](https://github.com/cyrilcolinet/enki-integration-hass/commit/582521e78623f18650c6c5255318b343bb06142c)), closes [#157](https://github.com/cyrilcolinet/enki-integration-hass/issues/157)

## [1.16.0](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.15.1...v1.16.0) (2026-08-17)


### Features

* **sensor:** add brightness and presence to Evology multisensor ([e3fdd95](https://github.com/cyrilcolinet/enki-integration-hass/commit/e3fdd95a91994f888690a1049d8036c0a390759b)), closes [#153](https://github.com/cyrilcolinet/enki-integration-hass/issues/153)
* **switch:** support Evology 2-channel in-wall module ([1852af1](https://github.com/cyrilcolinet/enki-integration-hass/commit/1852af1a5a50e153460f3ba9f698948f346eef07)), closes [#152](https://github.com/cyrilcolinet/enki-integration-hass/issues/152)

## [1.15.1](https://github.com/cyrilcolinet/enki-integration-hass/compare/v1.15.0...v1.15.1) (2026-08-13)


### Bug Fixes

* **light:** don't let a failed state read block light commands ([b900d97](https://github.com/cyrilcolinet/enki-integration-hass/commit/b900d97d6174339b277a04f651aaa8b971aa1961)), closes [#143](https://github.com/cyrilcolinet/enki-integration-hass/issues/143)

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
