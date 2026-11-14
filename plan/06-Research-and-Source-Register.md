# Research and Source Register

## How to interpret the references

The P references below are research publications or explicitly identified scholarly conference contributions. They are the methodological evidence for the plan. The D references are standards, official datasets, implementation documentation, or inspected source code. They support specifications and current software details rather than substituting for research. A citation means that the source supports the particular nearby statement; it does not mean the source validates SOMA as a complete system. Where SOMA combines methods or makes a product decision, the chapters identify that step as a proposed adaptation.

The audit deliberately avoids borrowing numerical mission-performance results. Published illumination percentages apply to particular locations, dates, heights, and terrain products. Published networking goodput applies to particular experiment configurations. Published constellation coverage applies to a particular design and set of assumptions. Those numbers are not SOMA results. The worked transfer example in Part 3 is a hand-checkable synthetic test, not a lunar simulation.

## P01

**Tapia, J. I., Kumar, S., and Grogan, P. T. (2025). “Scalable Model-Centric Engineering Analysis Workflows Using Distributed Task Queues with the Tradespace Analysis Tool for Constellations.” Journal of Aerospace Information Systems, 22(11), 973–982.** DOI: [10.2514/1.I011573](https://doi.org/10.2514/1.I011573).

This journal paper supports treating TAT-C as a reusable preconceptual Earth-observing constellation-analysis workflow, with coverage, revisit, and data-latency analyses. It examines distributed analysis execution and scaling; it is not evidence of native lunar propagation, lunar terrain geometry, a lunar communications scheduler, or a lunar RF model. SOMA adopts the modular analysis pattern while its current-code claims are independently grounded in D02. No reported scaling number is used as a performance promise for SOMA.

For historical context only, Le Moigne and colleagues' **“TAT-C: A Trade-Space Analysis Tool for Constellations”**, presented at NASA's Earth Science Technology Forum in 2016, is available through [NASA NTRS](https://ntrs.nasa.gov/api/citations/20180007288/downloads/20180007288.pdf). That earlier architecture belongs to TAT-C's concept lineage and should not be read as documentation of every current Python implementation detail.

## P02

**Acton, C. H. (1996). “Ancillary Data Services of NASA's Navigation and Ancillary Information Facility.” Planetary and Space Science, 44(1), 65–70.** DOI: [10.1016/0032-0633(95)00107-7](https://doi.org/10.1016/0032-0633(95)00107-7). **Acton, C., Bachman, N., Semenov, B., and Wright, E. (2018). “A Look Towards the Future in the Handling of Space Science Mission Geometry.” Planetary and Space Science, 150, 9–12.** DOI: [10.1016/j.pss.2017.02.013](https://doi.org/10.1016/j.pss.2017.02.013).

These papers establish the SPICE geometry-information approach: identified ancillary data support calculations involving positions, velocities, orientations, body geometry, and observation planning. They justify a kernel-based, reproducible geometry layer. The older paper is foundational, not a current lunar-kernel recipe. Neither paper means that any arbitrary kernel set is appropriate, that planetary kernels contain every relay orbit, or that SPICE itself closes RF links or optimizes the network. Current lunar frame choices are additionally checked against D03.

## P03

**Mazarico, E., Neumann, G. A., Smith, D. E., Zuber, M. T., and Torrence, M. H. (2011). “Illumination Conditions of the Lunar Polar Regions Using LOLA Topography.” Icarus, 211(2), 1066–1081.** DOI: [10.1016/j.icarus.2010.10.030](https://doi.org/10.1016/j.icarus.2010.10.030). [Publisher record](https://www.sciencedirect.com/science/article/pii/S0019103510004203).

This is the principal research basis for precomputing directional terrain horizons and combining them with lunar ephemerides to evaluate illumination. Its abstract describes horizon profiles from LOLA topography and validation against LRO Wide-Angle Camera images. The publisher's full-text fetch was blocked during this audit, so the method was cross-checked against the authors' openly available [2011 LEAG contribution](https://www.lpi.usra.edu/meetings/leag2011/pdf/2030.pdf), the official LOLA product documentation in D04, and the explicit method description in Barker et al., P05. The LEAG contribution is a conference abstract, not an additional journal validation. No paper-specific illuminated fraction is transferred to SOMA's proposed sites.

## P04

**Gläser, P., Scholten, F., De Rosa, D., Marco Figuera, R., Oberst, J., Mazarico, E., Neumann, G. A., and Robinson, M. S. (2014). “Illumination Conditions at the Lunar South Pole Using High Resolution Digital Terrain Models from LOLA.” Icarus, 243, 78–90.** DOI: [10.1016/j.icarus.2014.08.013](https://doi.org/10.1016/j.icarus.2014.08.013). [Publisher record](https://www.sciencedirect.com/science/article/abs/pii/S0019103514004278).

The paper supports evaluating local illumination with higher-resolution terrain and treating observer height as an important input. The publisher record describes a 20-meter-pixel terrain model and a long-duration investigation at surface level and at elevated heights. The corresponding author-group conference abstract, **“Connecting Ridge: A Landing Site at the Lunar South Pole with Extended Illumination,”** explains the horizon method and is openly available through [DLR](https://elib.dlr.de/94242/1/EPSC2014-136-1.pdf). The journal full-text fetch was blocked; the plan uses the verified scope and method, supported independently by P05, rather than claiming to reproduce the journal's site-specific numerical results. A favorable elevated-site result is not evidence that every lander has uninterrupted solar power.

## P05

**Barker, M. K., et al. (2021). “Improved LOLA Elevation Maps for South Pole Landing Sites: Error Estimates and Their Impact on Illumination Conditions.” Planetary and Space Science, 203, 105119.** DOI: [10.1016/j.pss.2020.105119](https://doi.org/10.1016/j.pss.2020.105119). [NASA record](https://ntrs.nasa.gov/citations/20205009660). [Public full text](https://ntrs.nasa.gov/api/citations/20205009660/downloads/Mike%20Barker_%20Paper_%20Improved%20Lola.pdf).

This paper provides the strongest detailed support for the terrain-quality treatment. Section 4 addresses elevation-model uncertainties; Section 5 uses the horizon method, considers the visible fraction of the solar disk, separates near-field and far-field terrain, and studies how perturbed terrain changes illumination. It distinguishes track geolocation uncertainty from surface-height uncertainty and examines continuous shadow and illumination periods as well as averages. The public full text was inspected. Its reported uncertainty values apply to its products and regions, not every lunar DEM or rendered mesh. SOMA's proposed conservative margins and eventual ensemble runs are adaptations of the uncertainty reasoning, not an already calibrated probability-of-success model.

## P06

**Saliwanchik, B. R. B., Herrmann, S., Kotov, I., O'Connor, P., Potekhin, M., Slosar, A., and Bale, S. (2024). “LuSEE-Night Power Requirements and Power Generation Strategy.” Proceedings of SPIE, 13102, 131021G.** DOI: [10.1117/12.3020538](https://doi.org/10.1117/12.3020538). [Open manuscript](https://arxiv.org/abs/2407.07173). [Readable full text](https://arxiv.org/html/2407.07173v1).

This conference-proceedings paper is the concrete lunar power-budget precedent. Section 3 models projected solar-panel area, partial solar-disk visibility, efficiency, degradation factors, and structural shadowing. The work simulates generation, draw, and reserves to inform the instrument's operating concept. It supports converting a time-varying illumination environment into an energy history rather than equating sunlight percentage with electrical power. Its particular battery, solar array, nonpolar location, environmental model, and predicted schedule are mission-specific. The plan does not copy them as validated defaults for a south-pole communications lander, and does not treat a design study as proof of completed flight operation.

## P07

**Zhang, L., Xiong, L., Sun, J., et al. (2024). “System Design and Validation of Queqiao-2 Lunar Relay Communication Satellite.” Chinese Space Science and Technology, 44(5), 23–39.** DOI: [10.16708/j.cnki.1000-758X.2024.0071](https://doi.org/10.16708/j.cnki.1000-758X.2024.0071). [Journal record](https://journal26.magtechjournal.com/kjkxjs/EN/10.16708/j.cnki.1000-758X.2024.0071).

The inspected paper reports actual spacecraft development, launch, orbit insertion, communications tests, and support for Chang'e-6. Its communications-design discussion identifies different user-facing and Earth-facing links, equipment, and rates, and its validation discussion reports in-orbit link testing. It provides operational evidence for a lunar-relay-to-ground architecture and context for Queqiao's earlier L2-region operation. It does not establish public access, live availability, an open precise ephemeris, or compatibility with arbitrary user hardware. The plan deliberately describes what the paper reported in 2024 rather than asserting an unverified current service state. An independent dated government announcement corroborates [April 2024 communications testing](https://english.www.gov.cn/news/202404/12/content_WS6618a4a4c6d0868f4e8e5f98.html).

## P08

**Brack, D., Roorda, T., Mathur, R., et al. (2025). “Preliminary Design of the Lunar Data Network Constellation Under Operational Considerations.” Conference paper AAS 25-758.** [NASA record](https://ntrs.nasa.gov/citations/20250006883). [Public full text](https://ntrs.nasa.gov/api/citations/20250006883/downloads/AAS_25_758_LDN_design_v7.pdf).

This preliminary design paper presents a five-satellite elliptical frozen lunar constellation and analyzes orbit choices against coverage and service considerations. It supports treating relay-orbit design as a substantive engineering problem and using researched architectures as inspiration for bounded presets. It does not establish that the whole proposed constellation was deployed, that its coverage applies to SOMA's scenario, or that a simple two-body ellipse reproduces a frozen operational orbit. The plan does not convert its planned launch dates into current operational facts.

## P09

**Israel, D. J., Mitchell, J. W., Johnson, M. A., et al. (2020). “LunaNet: A Flexible and Extensible Lunar Exploration Communications and Navigation Infrastructure.”** [NASA-hosted research paper](https://ntrs.nasa.gov/api/citations/20200001555/downloads/20200001555.pdf).

This architecture paper describes network, positioning/navigation/timing, and science-related services and multiple possible arrangements of surface and orbiting provider nodes. It supports a flexible network model instead of a compulsory fixed chain. The text explains that connectivity and sufficient network capacity are necessary for useful service. It is an architectural proposal, not evidence that all described services exist at every lunar location or that SOMA is interoperable with an operational network. The current specification is separately listed as D06.

## P10

**Wang, D., Wang, E., and Wang, R. (2025). “Delay/Disruption Tolerant Networking Performance Characterization in Cislunar Relay Communication Architecture.” Sensors, 25(1), 195.** DOI: [10.3390/s25010195](https://doi.org/10.3390/s25010195). [Publisher article](https://www.mdpi.com/1424-8220/25/1/195). [Public full text in PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11723082/).

The inspected full text describes a three-computer testbed, protocol configurations, 115,200-bit-per-second link settings, selected delays and bit-error rates, a one-megabyte file, and repeated runs. Section 5 explicitly states that link disruption was not introduced. The primary path uses a lunar-orbiter relay; the secondary path uses an Earth-orbit relay. The paper supports comparing protocol goodput under those experimental assumptions. It does not validate orbital visibility, RF link budgets, battery feasibility, outage-aware scheduling, or the superiority of a compulsory lunar-relay-plus-Earth-relay chain. Its cited Mars rover energy and data-return examples are not lunar results and are not reused as SOMA claims.

## P11

**Moy, M., Kassouf-Short, R., Kortas, N., Cleveland, J., Tomko, B., Conricode, D., Kirkpatrick, Y., Cardona, R., Heller, B., and Curry, J. (2023). “Contact Multigraph Routing: Overview and Implementation.” 2023 IEEE Aerospace Conference.** DOI: [10.1109/AERO55745.2023.10115729](https://doi.org/10.1109/AERO55745.2023.10115729). [NASA record](https://ntrs.nasa.gov/citations/20230002637). [Public full text](https://ntrs.nasa.gov/api/citations/20230002637/downloads/AeroConf_2023___Contact_Multigraph_Routing-20230221.pdf).

Section 2 defines scheduled contacts with timing, rates, and one-way light time and discusses temporal compatibility and earliest-arrival routing. It also addresses bundle size, available route volume, and projected arrival in route selection. This supports SOMA's contact-plan representation and finite-volume routing logic. It does not generate lunar contacts from physics, schedule a lander's battery, validate a particular relay network, or establish that SOMA conforms to CCSDS SABR. SOMA does not need to reproduce the paper's multigraph optimization to adopt the underlying contact-plan ideas.

## P12

**Li, J., Wang, P., Li, H., and Shi, K. (2022). “Enhanced Time-Expanded Graph for Space Information Network Modeling.” Science China Information Sciences, 65(9), 192301.** DOI: [10.1007/s11432-020-3202-2](https://doi.org/10.1007/s11432-020-3202-2). [Primary full text](http://scis.scichina.com/en/2022/192301.pdf).

Section 3.2 models contact-interval capacity as rate multiplied by interval duration, uses bounded carry edges for cached data, and includes transceiver restrictions. Equations 7–8 address storage and Equation 12 addresses an energy budget. This is direct research support for finite capacity and store-and-forward in a time-expanded network. The paper's implemented resource-allocation method is maximum-flow based. Its physical energy assumptions, including a particular relationship between transmission behavior and power, should not be copied as a validated lunar hardware model. SOMA's battery treatment instead uses an explicit generation/load budget and profile-specific radio costs.

## P13

**Liu, R., Ding, X., Wu, W., and Guo, W. (2023). “Distributed Coordination of Space–Ground Multiresources for Remote Sensing Missions.” Remote Sensing, 15(13), 3362.** DOI: [10.3390/rs15133362](https://doi.org/10.3390/rs15133362). [Article](https://www.mdpi.com/2072-4292/15/13/3362). [Public full text](https://mdpi-res.com/d_attachment/remotesensing/remotesensing-15-03362/article_deploy/remotesensing-15-03362-v2.pdf).

Sections 2.2–2.3 formulate a modified time-expanded graph with temporal flow and resource constraints. Equation 5 imposes start/end timing, Equation 8 associates successful scheduling with the required finite data volume, Equations 10–15 address equipment conflicts, and Equations 16–19 address storage and capacity. The resulting formulation is a mixed-integer linear program. This provides strong backing for SOMA's proposed small centralized finite-volume, deadline-constrained scheduler. The paper concerns Earth remote-sensing systems and a different objective and decomposition method. It does not validate SOMA's lunar geometry, hardware profiles, policy ordering, or a joint lunar energy-and-routing implementation.

## P14

**Day, B., and Law, E. (2017). “Moon Trek: An Interactive Web Portal for Current and Future Lunar Missions.” Scholarly conference contribution.** [NASA record](https://ntrs.nasa.gov/citations/20170008884). [Public abstract](https://ntrs.nasa.gov/api/citations/20170008884/downloads/20170008884.pdf).

This contribution describes a web portal joining lunar data products with interactive visualization and analysis for mission planning and related audiences. It supports the precedent for a map-based lunar analysis interface. It is not a controlled usability study of SOMA, a performance benchmark for Cesium, or evidence that another general lunar atlas is needed. The choice to use Cesium and the decision to emphasize a delivery schedule are engineering/product proposals, with current API details verified separately in D05 and D11.

## P15

**Friis, H. T. (1946). “A Note on a Simple Transmission Formula.” Proceedings of the IRE, 34(5), 254–256.** DOI: [10.1109/JRPROC.1946.234568](https://doi.org/10.1109/JRPROC.1946.234568). [Publisher record](https://ieeexplore.ieee.org/document/1697062). [University-hosted reprint](https://capmimo.ece.wisc.edu/capmimo_papers/friis_original_1946.pdf).

This foundational paper derives the free-space radio transmission relation and discusses its limitations. It supports the path-loss starting point in Part 3, not a complete lunar propagation, noise, modulation, coding, or mission-reliability model. Additional loss and receiver-performance terms are required for a usable link budget. The original free-space formulation must not be stretched into a claim that a terrain-obstructed or grazing surface link works. D09 supplies the practical telecommunications-design context.

## D01

**NASA Space Apps 2026: Lunar Landing Site Navigator.** [Challenge details](https://www.spaceappschallenge.org/2026/challenges/lunar-landing-site-navigator/?tab=details).

The live challenge text was read in the browser because the text-fetch path returned an unrelated third-party-link notice. The actual brief asks for accessible site/date evaluation, Sun and Earth positions relative to the horizon, and power and direct-to-Earth communication information. Relay scheduling is SOMA's extension, not an explicit requirement of the challenge. The brief is the product-scope source, not a research paper validating a method.

## D02

**TATC source audit, commit b459b9a02b53cb8d7a171a81fa995df0856dff53, checked 13 November 2026.** [Pinned repository](https://github.com/code-lab-org/tatc/tree/b459b9a02b53cb8d7a171a81fa995df0856dff53). [README](https://github.com/code-lab-org/tatc/blob/b459b9a02b53cb8d7a171a81fa995df0856dff53/README.md). [BSD 3-Clause license](https://github.com/code-lab-org/tatc/blob/b459b9a02b53cb8d7a171a81fa995df0856dff53/LICENSE).

The pinned code, not a paper about an earlier version, supports the implementation findings. Relevant locations include **src/tatc/schemas/orbit/gp.py**, approximately lines 839–943, for GCRS states and WGS84 conversions; **src/tatc/utils/geometry.py** for the WGS84 geodesic object; **src/tatc/schemas/surface/station.py** for the ground-station schema; **src/tatc/preprocess/terrain.py**, approximately lines 279–416, for terrain masking; and **src/tatc/utils/radar.py**, approximately lines 258–304, for Earth-radius-based curvature. The inspected terrain implementation permits a refraction factor of one but remains Earth-specific in other paths and treats unsampled azimuths permissively. **src/tatc/analysis/ground_track.py** and **sampling.py** show Earth-based solar calculations. **pyproject.toml** already lists SpiceyPy, and the resource directory includes DE421. No current lunar state API or CZML serializer was found in the inspected code paths and search. That bounded finding is not a claim that SPICE is wholly absent.

## D03

**NAIF SPICE concepts, frames, and lunar-kernel documentation.** [SPICE concepts](https://naif.jpl.nasa.gov/naif/spiceconcept.html), [reference-frame documentation](https://naif.jpl.nasa.gov/pub/naif/toolkit_docs/C/req/frames.html), [generic kernels](https://naif.jpl.nasa.gov/naif/data_generic.html), [lunar frame-kernel directory notes](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/aareadme.txt), and [DE440 lunar frame kernel](https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_de440_250416.tf).

These sources specify the implementation details behind the paper-backed SPICE approach. The lunar notes pair DE421 and DE440 frame kernels with their appropriate orientation kernels. The DE440 kernel explains the principal-axis and mean-Earth frames, generic aliases, and distinctions from IAU_MOON. Its close alignment with the DE421 mean-Earth realization is not identity. Kernel coverage, coordinate conventions, and the full selected kernel set still require run-specific validation.

## D04

**NASA PGDA lunar elevation and illumination products.** [South Pole LOLA DEM Mosaic](https://pgda.gsfc.nasa.gov/products/81), [high-resolution south-pole sites](https://pgda.gsfc.nasa.gov/products/78), and [Lunar Polar Illumination](https://pgda.gsfc.nasa.gov/products/69).

The mosaic page identifies five-meter-pixel GeoTIFFs, south-polar stereographic coordinates, and a DE421 mean-Earth frame. It also identifies interpolated elevation fill and associated count and slope products. The polar illumination page explains the reference radius and long-term nature of its averages. Crucially, it states that its Earth-visible definition is any unobscured part of Earth's disk, which can be optimistic for links to specific stations. These are dataset-specific facts, not universal performance guarantees.

## D05

**Cesium Moon official asset documentation.** [Cesium Moon](https://cesium.com/platform/cesium-ion/content/cesium-moon/).

The page supplies the current global 3D Tiles configuration, source-resolution descriptions, attributions, and example using Moon ellipsoid settings, a disabled Globe, and asset 2684829. It is software/data documentation, not research evidence for a communications algorithm. Its visual-source resolutions must not be confused with a validated numerical horizon model or a guarantee of current rendered detail.

## D06

**LunaNet Interoperability Specification, Version 5.** [NASA specification page](https://www.nasa.gov/directorates/somd/space-communications-navigation-program/lunanet-interoperability-specification), [Version 5 document](https://www.nasa.gov/wp-content/uploads/2025/02/lunanet-interoperability-specification-v5-baseline.pdf?emrc=606f95).

The inspected NASA page identifies Version 5 as current and states that it covers direct-with-Earth and lunar-relay communications and PNT. The specification is an interoperability framework, not a live public network inventory, service reservation, or evidence that SOMA is compliant. It complements the architecture research in P09.

## D07

**CCSDS 734.3-B-1, Schedule-Aware Bundle Routing, July 2019.** [Standard](https://ccsds.org/Pubs/734x3b1.pdf). Also [NASA's DTN explanation](https://www.nasa.gov/communicating-with-missions/delay-disruption-tolerant-networking/).

The inspected standard defines contacts, ranges, volumes, temporal routing, transmission and arrival timing, backlog, and route-volume limits. Sections 3.2.4 and 3.2.6 are particularly relevant. It is a standards reference, not a research-paper substitute, and SOMA's proposed centralized scheduler is not automatically a SABR implementation. The NASA explanation supports the practical meaning of store-and-forward; it does not guarantee that every relay preset has that capability.

## D08

**CCSDS Orbit Data Messages and Navigation Data Messages Overview.** [Orbit Data Messages, 502.0-B-3 with corrigendum](https://ccsds.org/Pubs/502x0b3e1.pdf), [Navigation Data Messages Overview](https://ccsds.org/Pubs/500x2g3.pdf).

These sources support using a documented Orbit Ephemeris Message as one possible trajectory interchange format. An implementation still needs to validate reference center, frame, time system, units, interpolation, and coverage. The format does not supply the spacecraft's trajectory or make an incomplete parser standards-compliant.

## D09

**NASA/JPL telecommunications-design references.** [DSN Telecommunications Link Design Handbook](https://deepspace.jpl.nasa.gov/dsndocs/810-005), [NASA Small Spacecraft Technology, Ground Data Systems and Mission Operations](https://www.nasa.gov/smallsat-institute/sst-soa/ground-data-systems-and-mission-operations/).

These engineering references support practical link-budget terms, receiver and ground-system considerations, frequency compatibility, service planning, and the need for margin. They complement the free-space research relation in P15 and the mission implementation in P07. Their examples and margins are not automatic requirements or verified hardware specifications for SOMA's fictional lander.

## D10

**NASA Deep Space Network locations.** [Where Is the DSN Located?](https://www.nasa.gov/directorates/somd/space-communications-navigation-program/dsn-complexes/).

This source identifies Goldstone, Madrid, and Canberra and explains their geographic distribution. It supports the ground-network architecture example. It does not supply permission, current antenna allocation, a complete terminal profile, or guaranteed access for a SOMA scenario.

## D11

**CesiumJS implementation references.** [Ellipsoid](https://cesium.com/learn/cesiumjs/ref-doc/Ellipsoid.html), [Scene](https://cesium.com/learn/cesiumjs/ref-doc/Scene.html), [SampledPositionProperty](https://cesium.com/learn/cesiumjs/ref-doc/SampledPositionProperty.html), [Transforms](https://cesium.com/learn/cesiumjs/ref-doc/Transforms.html), [CZML content](https://github.com/CesiumGS/cesium/wiki/CZML-Content), [experimental Cesium3DTilesTerrainProvider](https://cesium.com/learn/cesiumjs/ref-doc/Cesium3DTilesTerrainProvider.html), [Simon1994PlanetaryPositions](https://cesium.com/learn/cesiumjs/ref-doc/Simon1994PlanetaryPositions.html), and [SunLight](https://cesium.com/learn/cesiumjs/ref-doc/SunLight.html).

These current API references support the specific rendering and interaction recommendations: Moon ellipsoid configuration, depth-based picking, scene-level 3D Tiles height queries, fixed/inertial sampled positions, and the need to configure central-body transformations deliberately. They do not validate lunar RF, illumination, or power calculations. Pin the actual CesiumJS version during implementation and recheck any experimental or evolving API before coding against it.

## D12

**Cesium ion access and service terms.** [Access-token documentation](https://cesium.com/learn/ion/cesium-ion-access-tokens), [pricing and account plans](https://cesium.com/platform/cesium-ion/pricing/), and the [Moon product page](https://cesium.com/platform/cesium-ion/content/cesium-moon/).

These sources support requiring appropriate ion access, a properly scoped application token, and attribution. The plan does not promise unlimited free service or unrestricted redistribution. Confirm the intended usage, account limits, and current terms when the application is deployed.

## What remains a SOMA proposal

The overall product, the companion-package boundary, Cesium selection, public Python interface, HTTP job protocol, cache strategy, restricted route families, scheduling policy order, time discretization, specific hardware presets, default margins, and demonstration scenarios are proposed engineering choices. Their components have research or standards foundations, but no cited source proves this exact combined implementation. The most important future evidence is therefore a reproducible set of numerical tests, independent schedule replay, comparisons with appropriate reference cases, and transparent sensitivity analysis. This distinction is intentional: a properly researched plan should make its remaining work clearer, not disguise proposed work as an established result.
