# LastMile+ Project Charter

**Project Name**: LastMile+ | AI-Powered Distribution Planning  
**Version**: 0.1 (Draft)  
**Date**: April 2026  
**Prepared for**: Ministries of Health, NGOs, and Implementing Partners  

## 1. Objective

LastMile+ is a practical decision-support application designed to strengthen **last-mile distribution planning** of health commodities (medicines, vaccines, diagnostics, and supplies).  

The system helps planners at national, regional, and district levels make better, data-driven decisions on **what quantities** to allocate to each facility in the upcoming distribution cycle, while reducing stockouts and minimizing overstock and wastage.

**Important**: This tool **supports planning only**. It does **not** execute procurement, automatically place orders, or manage physical deliveries.

## 2. Scope

### In Scope
- Facility-level **demand forecasting** (short-term and medium-term)
- **Stockout risk prediction** with early warning indicators and risk scores
- **Distribution quantity recommendations** based on forecasted demand, current stock, and available transport capacity
- **Scenario simulation** ("what-if" analysis) for delays, budget constraints, emergencies, or supply disruptions
- Explainable recommendations with clear reasoning for human review
- Integration with existing systems: DHIS2, eLMIS/LMIS, warehouse management data, and facility stock/consumption reports

### Out of Scope
- Autonomous decision-making or execution of distributions
- Procurement planning or supplier ordering
- Real-time tracking of vehicles or delivery execution
- Replacement of existing LMIS or warehouse systems
- Mobile execution apps for field staff

## 5. Design Principles

- **Human-centered**: Planners remain fully in control; AI provides suggestions only.
- **Transparent & Explainable**: Every recommendation shows supporting data and logic.
- **Reliable in low-resource settings**: Works with limited connectivity and modest hardware.
- **Conservative**: Uses proven, interpretable methods rather than complex black-box models.
- **Ethical & Compliant**: Strong focus on data privacy, security, and alignment with national health policies and donor guidelines.
- **Practical**: Designed around real public health logistics workflows.

## 8. Constraints & Non-Negotiables

- The system must **never** make autonomous procurement or delivery decisions.
- All outputs are **recommendations** requiring human approval.
- Full compliance with data protection policies.

## 9. Phased Development Plan

**Phase 0**: Foundations (Project Charter, data model, sample data) — Current  
**Phase 1**: Core forecasting and risk scoring modules + basic dashboard  
**Phase 2**: Distribution planning and scenario simulation  
**Phase 3**: Integration with DHIS2/eLMIS + offline support  
**Phase 4**: Pilot testing in selected districts

---

**Approval**

This charter provides the guiding framework for the development of LastMile+.
Add Project Charter document
