# Oracle Submission Analysis

This repository contains a collection of Quarto notebooks analyzing Oracle submissions between December 2024 and March 2025.

## Overview of the Oracle Submission Analysis

This analysis investigates Oracle submissions gathered between December 2024 and March 2025. Using Polars-based pipelines for data ingestion and transformation, Autonity evaluated over 10 million data submissions to detect anomalies in ten key issue areas, including:

i. missing or null submissions;  
ii. suspicious price outliers; and  
iii. stale data and validator synchronization gaps.

The analysis measured the validity of price relationships by checking their consistency against:

i. benchmark FX feeds; and  
ii. currency cross-rates. 

Additionally, time stamps were used to conduct:

i. time synchronization analysis to flag disparities among validators;  
ii. correlation statistics-based analysis to identify coordinated behaviors; and  
iii. confidence-value distribution checks for anomaly detection. 

Finally, Autonity analyzed vendor downtime events, weekend coverage metrics and implemented statistical thresholds, including deviation bands and submission frequency benchmarks, to categorize validators as healthy, irregular or potentially unhealthy.

First-half results indicate a broad decline in validator participation over the four-month period, with submission dropouts and stale data episodes becoming more frequent. Furthermore, Autonity identified a handful of validator groups exhibiting synchronized or nearly identical price patterns, raising questions about shared infrastructure or collusive strategies. A comprehensive analysis including detailed code and monthly metrics can be found in this repository.

## Recommendations for Improving Oracle Submission Quality

When Autonity conducted the Oracle submission analysis, it was found that some validators consistently used the same confidence value when submitting data. Having a constant confidence value regardless of conditions detracts from its intended purpose. Instead, the confidence value should vary over time. It should contribute information on the submitter's level of certitude, taking into account the number of sources, source quality and update frequency of the data. Submissions that draw upon a single, irregular source may not reflect broader market conditions and hence are assigned a lower confidence value, while those aggregated across multiple feeds can justifiably be given a higher score.

Validators are encouraged to improve the quality and diversity of their data sources rather than relying solely on the default plugin setup. While the Oracle client currently uses a global strategy to compute confidence scores—based on the number of valid data sources—future iterations may allow for more dynamic, symbol-specific, or plugin-weighted strategies.

In the meantime, validators can influence confidence and reporting accuracy by:

•	Dynamically enabling or disabling plugins based on data freshness and reliability
•	Developing new plugins that aggregate from more trusted or higher-frequency sources
•	Monitoring update intervals and market variance to ensure the submitted data reflects the most recent market state

Engineering teams are encouraged to explore more flexible confidence scoring mechanisms that account for factors like variance, volume, latency, and data source trust levels.


---

## Getting Started

### Structure of this Repo

- `/notebooks`: Contains 10 Quarto notebooks (`.qmd` files) analyzing 10 potential issues
- `_quarto.yml`: Configuration file for the Quarto website
- `index.qmd`: Home page
- `summary_2024_12.qmd`: Summary report of December 2024
- `summary_2025_01.qmd`: Summary report of January 2025
- `summary_2025_02.qmd`: Summary report of February 2025
- `summary_2025_03.qmd`: Summary report of March 2025
- `summary_first_half.qmd`: Aggregated summary report from December 2024 to March 2025
- `styles.css`: Custom styling for the website

### Prerequisites

You need these installed on your system:

- [nix installer](https://zero-to-nix.com/concepts/nix-installer)
- [devenv](https://devenv.sh/getting-started/)

### To build the website

To render all the notebooks, run:

```bash
quarto render .
```

To build the website for testing, run:

```bash
quarto preview
```

This will create the website in the `_site` directory.

### To download the Oracle submission data

Due to the very large size of Oracle submission data, only 1 day of the Oracle submission data (`Oracle_Submission_2025-01-01.csv`) is stored in this repository for building and testing purposes. The full Oracle submission data can be downloaded from [Google Drive](https://drive.google.com/drive/folders/1LIrAskzusoipLoftltbSoaLEM8E9-wK9).
