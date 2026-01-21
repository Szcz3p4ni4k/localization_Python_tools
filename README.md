# Localization Automation Tools

A collection of Python utilities designed to streamline localization engineering workflows, automate MemoQ server maintenance, and process translation assets (TMX, XLIFF, MQRES).

This repository demonstrates practical applications of Python in the translation industry, focusing on XML parsing optimization, API integration, and regular expressions.

## Project Index

| Project Name | Description | Key Technologies |
| :--- | :--- | :--- |
| **[MemoQ Server TM Cleaner](./rapi_memoq_server_tm_cleaner)** | A hybrid automation tool that audits and removes specific user entries from live Translation Memories on MemoQ Server via HTTP API. | `REST API`, `Iterative XML Parsing`, `Requests` |
| **[TMX Translator Analysis](./translator_id_tmx_analysis)** | High-performance analyzer for TMX files. Calculates detailed productivity statistics (segment/character counts) per user ID using memory-efficient streaming. | `XML Streaming (iterparse)`, `Data Mining`, `CSV Reporting` |
| **[XLIFF Source Copier](./xliff_copy_src_to_trg)** | Pre-processing tool for XML/XLIFF files. Automatically populates missing target elements with source content while preserving internal tags and namespaces. | `XML DOM`, `Namespace Handling`, `Deep Copy` |
| **[MQRES Name Extractor](./extract_tm_name_mqres)** | Bulk auditing tool for MemoQ resource backups. Extracts internal resource names from `.mqres` files using optimized Regex patterns. | `Regex`, `Batch Processing`, `Error Handling` |


## Technical Highlights

* **Memory Efficiency:** Heavy XML files (TMX backups) are processed using `xml.etree.ElementTree.iterparse` to minimize RAM usage during execution.
* **API Integration:** Scripts interact directly with localization platforms (MemoQ Server) to perform tasks not available in the standard GUI.
* **Data Integrity:** All tools implement safe write operations and encoding handling (UTF-8) to prevent data corruption in multilingual files.

## Requirements

* Python 3.6+
* No proprietary dependencies required for local file processing tools.
* Network access and valid credentials required for API-based tools.
