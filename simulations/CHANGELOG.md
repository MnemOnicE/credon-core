# Changelog

## [1.1.1](https://github.com/MnemOnicE/credon-core/compare/credon-simulations-v1.1.0...credon-simulations-v1.1.1) (2026-03-21)


### Bug Fixes

* **security:** replace insecure PRNG with cryptographically secure secrets module ([8e0e6e8](https://github.com/MnemOnicE/credon-core/commit/8e0e6e8986c7af86f779a221f5c48d23e7bb156e))


### Performance Improvements

* **simulations:** optimize social connectivity calculation by pre-calculating out_degrees ([830b3b3](https://github.com/MnemOnicE/credon-core/commit/830b3b35903f0ff7600aee8f69191557cd6346cb))
* **simulations:** optimize Transitive Trust normalization loop ([9897a7a](https://github.com/MnemOnicE/credon-core/commit/9897a7a94dcc5d8b27c4d78f150baf1e5ac95dd9))

## [1.1.0](https://github.com/MnemOnicE/credon-core/compare/credon-simulations-v1.0.0...credon-simulations-v1.1.0) (2026-03-10)


### Features

* add Governance Layer with $CRED, conviction, and dynamic quorums ([8dd3afb](https://github.com/MnemOnicE/credon-core/commit/8dd3afb7c54d3226772a14071715f0717a957e57))
* add Governance Layer with $CRED, conviction, and dynamic quorums ([a659378](https://github.com/MnemOnicE/credon-core/commit/a659378dd46fb2a627aef15a17d0428bb5df679a))
* Add minting throttle to Rewards Reservoir ($R_{res}$) ([4b75094](https://github.com/MnemOnicE/credon-core/commit/4b75094253ff5d333cefa1fd96a139de71ed3403))
* Add minting throttle to Rewards Reservoir ($R_{res}$) ([c7d3811](https://github.com/MnemOnicE/credon-core/commit/c7d381163ba071e429843cea329adeb6bf70815a))
* implement Credon v2.0 mathematical simulation framework ([65013c2](https://github.com/MnemOnicE/credon-core/commit/65013c2e51adc2d44192d225086bc349dbbab9a8))
* implement Credon v2.0 mathematical simulation framework ([95f20c2](https://github.com/MnemOnicE/credon-core/commit/95f20c25984edf685c2d2674df995247c68707f8))
* implement Governance 2.0 simulation with time-weighted conviction voting ([5edf50e](https://github.com/MnemOnicE/credon-core/commit/5edf50e92b87870215c2426e819a98d6e4413509))
* implement simulation baseline for bonded endorsement and sybil attack ([f4413d7](https://github.com/MnemOnicE/credon-core/commit/f4413d71565d582ba4ea6b78c7058078bf4b3aca))
* implement simulation baseline for bonded endorsement and sybil attack ([bf32d52](https://github.com/MnemOnicE/credon-core/commit/bf32d529439d099f6fd4d40385faf8462a511631))
* **simulations:** add parameter sweep analytics and CI workflow ([474de9d](https://github.com/MnemOnicE/credon-core/commit/474de9db3ebafce2b6de5c35ec983b55e0d9d921))
* **simulations:** add parameter sweep analytics and CI workflow ([454d091](https://github.com/MnemOnicE/credon-core/commit/454d0912e0f70f85522eb5c24144caad0de60bd2))
* **simulations:** apply math.sqrt throttle to EigenTrust edge weights ([ceae232](https://github.com/MnemOnicE/credon-core/commit/ceae2323c3083f8d33285a2e73310e7fd7a71b69))
* **simulations:** apply math.sqrt throttle to EigenTrust edge weights ([46e19bd](https://github.com/MnemOnicE/credon-core/commit/46e19bdf774e7e8a57a584024434e40a430c334b))


### Bug Fixes

* correct M_EPOCH and formatting issues to pass CI tests ([18e26f1](https://github.com/MnemOnicE/credon-core/commit/18e26f1c510dde4e050dae1ddc69e087b980a2a4))
* resolve CI failures for workflows and linting ([7c7b79e](https://github.com/MnemOnicE/credon-core/commit/7c7b79e7a2a11c57509abc6f74500e762581c0a2))


### Performance Improvements

* optimize agent filtering and imports in simulation engine ([71f0178](https://github.com/MnemOnicE/credon-core/commit/71f01785a032082c2ac214b9b594e9200b3bb89e))
* optimize total_interactions computation in EigenTrust ([c0cb470](https://github.com/MnemOnicE/credon-core/commit/c0cb4704362c10b4556c14263baf3d1a83332f2c))
* **simulations:** fix missing semantic taxonomy in benchmark script ([0651cd6](https://github.com/MnemOnicE/credon-core/commit/0651cd64ad3f775838df3c9cc4f184bbc24c95cb))
* **simulations:** optimize pagerank sink calculation ([82c5c28](https://github.com/MnemOnicE/credon-core/commit/82c5c282fbabb8943b03f605afd8b94724b4d39b))
