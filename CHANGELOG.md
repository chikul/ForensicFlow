# Changelog

All notable changes to this project will be documented in this file.
This project adheres to [Semantic Versioning](http://semver.org/).

## [1.2.0] - 2026.09.23

### Added

* Extended Alexa extractor with a service name.
* SHA-256 hashes alongside MD5.
* iSmartAlarm profileid to profileName mapping.
* Returned CubeOne and Unknown device to iSA event export.
* Hardware ID export for devices.
* Device IP extraction for iSA.

### Fixed

* Hashes were stored incorrectly.

## Refactored

* Extractors moved to `src` dir, `data` moved to the root. `dfrws2018` dir removed along with the old DCSDM2 application code.
* Legacy ForensicFlow code removed.
* Cleaned up extractors from the legacy `to_rdf()` methods.
* Devices are now assigned a more specific class - `SmartDevice`.

## Updated

* `README.md` is now up to date.

## [1.1.0] - 2026.09.21

### Added

* CSV Export.
* Application accounts.
* Account to email relationship.
* Entity merging.
* Owner relationship with confidence facet.
* Postprocessing layer with string similarity module.

## [1.0.0] - 2026.09.21

### Added

* Proper UCO/CASE extraction.
* Related papers.

### Updated

* UCO/CASE major version bump to 1.5.0.

## [0.11.0] - 2022.10.24

### Added

* Extraction for applications and events (with facets), origin reltaionships.

## [0.10.0] - 2022.10.16

### Added

* Definition for relationship.

## [0.9.0] - 2022.10.09

### Added

* Starting migration to UCO/CASE ontology standard (UCO 0.9.1/CASE 0.7.1).
* Definitions for device, person, event, application, file, and digital and email addresses.

## [0.8.0] - 2022.06.09

### Added

* Forensic artifact handling on both ontology and code levels.
* Time frame filter is now an option of `EventBase` class.
* Individuals merging on the example of artifacts.
* Bidirectional linking of all base classes.
* Evidence source and its hash are written to all extracted entities.
* Event correlation scores calculation. Initial approach.

### Removed

* All legacy elements from ontology.

## [0.7.0] - 2022.04.22

### Added

* Introduced bidirectional object properties to the ontology.
* Designed sample complex SPARQL queries to fetch semantic data.
* Added example of extended base class (`AmazonUser`).

## [0.6.0] - 2022.04.21

### Added

* New ontology to support distributed environment on the example of DFRWS 2018 IoT challenge data.
* Implemented a convenient Python framework to represent ontology classes in code.
* Any number of evidence source exporters can be easily added.
* Base classes could be easily extended to support additional fields and connections.
* Extracted events, users, and devices individuals are written directly to ontology.

### Updated

* Greately rearranged the ontology for work with distributed environments.

## [0.5.0] - 2021.02.12

### Added

* Firefox History events support.

### Updated

* Autopsy extractor up to date.

### Fixed

* Timestamp format was incorrect breaking ontology consistency.

## [0.4.0] - 2021.02.05

### Added

* Log2Timeline extractor.

### Updated

* Completely reworked ontology structure.
* Updated Volatilty extractor.

### Fixed

* Volatility module incorrectly handling entries with no PEB.
* Volatility module populates incorrect process list.
* TinyLeech irreversibly damages encrypted files.

## [0.3.0] - 2021.01.04

### Added

* Ransomware test project.

## [0.2.0] - 2020.12.29

### Fixed

* Volatility's `task.ImageFileName` chopped image file names longer than 14 characters.
* Autopsy XML-output was not thread safe which caused some entries to be lost randomly.

## [0.1.0] - 2020.12.22

### Added

* Ontology skeleton for Protege.
* Volatility plug-in for RDF-triplets extraction.
* Autopsy plug-in for RDF-triplets extraction (doesn't write to file still).
