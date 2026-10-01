# BankGuard AI Architecture

## Purpose

BankGuard AI is a banking fraud detection and
security monitoring platform built for educational
and portfolio demonstration purposes.

The system uses synthetic banking data.

## Architecture

```mermaid
flowchart LR
    USER[Bank Analyst]

    UI[Next.js Dashboard]

    API[FastAPI]

    AUTH[Authentication / RBAC]

    RULES[Fraud Rule Engine]

    ML[ML Fraud Model]

    RISK[Risk Scoring Engine]

    ALERTS[Alert & Case Management]

    DB[(PostgreSQL)]

    USER --> UI
    UI --> API

    API --> AUTH
    API --> RULES
    API --> ML

    RULES --> RISK
    ML --> RISK

    RISK --> ALERTS

    AUTH --> DB
    RULES --> DB
    ML --> DB
    ALERTS --> DB