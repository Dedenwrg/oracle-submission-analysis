# Oracle Submission Analysis

This repository contains a collection of Quarto notebooks analyzing oracle submissions.

## Structure

- `/notebooks`: Contains 10 Quarto notebooks (`.qmd` files) with various analyses
- `_quarto.yml`: Configuration file for the Quarto website
- `index.qmd`: Home page
- `summary_2024_12.qmd`: Summary report of December 2024
- `summary_2025_01.qmd`: Summary report of January 2025
- `summary_2025_02.qmd`: Summary report of February 2025
- `styles.css`: Custom styling for the website

## Getting Started

### Prerequisites

- [Quarto](https://quarto.org/docs/get-started/) must be installed on your system

### Building the Website

To render all the notebooks, run:

```bash
quarto render .
```

To build the website for testing, run:

```bash
quarto preview
```

This will create the website in the `_site` directory.

### "Dummay" `*.csv` data

Due to the very large size of Oracle Submission data, only 1 day of Oracle Submission data (`Oracle_Submission_2025-01-01.csv`) and its corresponding Yahoo Finance datasets are stored in this repo for testing.