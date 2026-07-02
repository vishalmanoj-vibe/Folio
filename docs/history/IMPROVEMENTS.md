# Code Improvements Index

This document acts as the central index for all technical and architectural improvements implemented in the Folio dashboard.

## Overview of Changes

To maintain clean and readable files, the improvements journal has been split into three thematic child files:

1.  **[Core Infrastructure & Resilience (Items 1–11)](IMPROVEMENTS_CORE_INFRASTRUCTURE.md)**
    *   *Focus:* Input transaction validation pipeline, API retry logic, global environment configurations, logging setup, SQLite migration (WAL mode), testing framework initialization, and project-wide file layer cleanups.
2.  **[Feature Architecture & Orchestration (Items 12–20)](IMPROVEMENTS_FEATURE_ARCHITECTURES.md)**
    *   *Focus:* Risk metrics engine (Volatility/Sharpe/Drawdowns), Prophet projection engine, Deep Dive correlation heatmap, ex-dividend realised dividend engine, Plotly theme stability, CSS modularization, and Single Refresh Owner stores pattern.
3.  **[Technical Intelligence & UI Polish (Items 21–34)](IMPROVEMENTS_INTELLIGENCE_AND_POLISH.md)**
    *   *Focus:* Pure Pandas technical indicators (RSI/MACD/BB), positions candlestick charts, multi-page period sync, AI research chatbot context caching, UI grid isolation (AI card containers), custom Y-axis ranges, standard chart layout wrappers, and background worker task offloading.
