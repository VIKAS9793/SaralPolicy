# Metrics & KPI Framework - SaralPolicy

**Product:** SaralPolicy  
**Version:** 1.0  
**Author:** Vikas Sahani (Product Manager)  
**Engineering Team:** Kiro (AI Co-Engineering Assistant), Antigravity (AI Co-Assistant)  
**Date:** January 2026  

---

## Metrics Framework Overview

SaralPolicy implements a comprehensive metrics and KPI framework that tracks product performance, business growth, technical excellence, and user satisfaction across multiple dimensions to ensure sustainable success and continuous improvement.

---

## North Star Metrics

### Primary North Star: Reduction in Claim Misunderstandings
**Definition:** Percentage reduction in insurance claim disputes and misunderstandings as measured by IRDAI-aligned complaint data.

**Target:** 30% reduction in claim disputes within 12 months

**Measurement:**
- **Baseline:** IRDAI complaint data (1.42M complaints in FY2025)
- **Current:** User-reported claim disputes
- **Target:** 30% reduction from baseline
- **Frequency:** Monthly measurement
- **Owner:** Product Team + Legal Team

**Calculation:**
```
Claim Dispute Reduction = (Baseline Complaints - Current Complaints) / Baseline Complaints × 100
```

### Secondary North Star: User Policy Understanding Score
**Definition:** Percentage of users who demonstrate improved understanding of their insurance policies after using SaralPolicy.

**Target:** 90%+ policy understanding score

**Measurement:**
- **Pre-usage Test:** Policy knowledge assessment before using SaralPolicy
- **Post-usage Test:** Policy knowledge assessment after using SaralPolicy
- **Understanding Score:** (Post-score - Pre-score) / Pre-score × 100
- **Frequency:** Per user session
- **Owner:** Product Team + UX Team

---

## Product Metrics

### 1. User Acquisition Metrics

#### Monthly Active Users (MAU)
**Definition:** Number of unique users who actively use SaralPolicy in a month

**Target:** 100,000 MAU by Month 6

**Measurement:**
- **Current:** 1,000 MAU (Month 1)
- **Target:** 100,000 MAU (Month 6)
- **Growth Rate:** 20% month-over-month
- **Frequency:** Daily measurement
- **Owner:** Marketing Team + Product Team

#### User Growth Rate
**Definition:** Month-over-month percentage growth in active users

**Target:** 20%+ month-over-month growth

**Calculation:**
```
User Growth Rate = (Current Month MAU - Previous Month MAU) / Previous Month MAU × 100
```

#### Customer Acquisition Cost (CAC)
**Definition:** Average cost to acquire a new customer

**Target:** ₹500 or less per customer

**Calculation:**
```
CAC = Total Marketing Spend / Number of New Customers
```

**Components:**
- **Digital Marketing:** 40% of CAC
- **Partnership Marketing:** 30% of CAC
- **Content Marketing:** 20% of CAC
- **Other Channels:** 10% of CAC

### 2. User Engagement Metrics

#### Daily Active Users (DAU)
**Definition:** Number of unique users who actively use SaralPolicy in a day

**Target:** 40% of MAU (40,000 DAU by Month 6)

**Measurement:**
- **Current:** 400 DAU (Month 1)
- **Target:** 40,000 DAU (Month 6)
- **DAU/MAU Ratio:** 40%
- **Frequency:** Daily measurement
- **Owner:** Product Team

#### Session Duration
**Definition:** Average time users spend in a single session

**Target:** 5+ minutes per session

**Measurement:**
- **Current:** 3 minutes per session
- **Target:** 5+ minutes per session
- **Frequency:** Per session
- **Owner:** Product Team + UX Team

#### Feature Adoption Rate
**Definition:** Percentage of users who use specific features

**Target:** 60%+ feature adoption rate

**Key Features:**
- **Policy Analysis:** 80%+ adoption
- **Q&A System:** 60%+ adoption
- **Policy Comparison:** 40%+ adoption
- **Export Reports:** 30%+ adoption

### 3. User Retention Metrics

#### User Retention Rate
**Definition:** Percentage of users who return to use SaralPolicy

**Target:** 70%+ retention rate (3 months)

**Measurement:**
- **Day 1 Retention:** 80%+
- **Week 1 Retention:** 70%+
- **Month 1 Retention:** 60%+
- **Month 3 Retention:** 50%+
- **Month 6 Retention:** 40%+

#### Churn Rate
**Definition:** Percentage of users who stop using SaralPolicy

**Target:** <10% monthly churn rate

**Calculation:**
```
Churn Rate = (Users at Start of Month - Users at End of Month) / Users at Start of Month × 100
```

#### Customer Lifetime Value (LTV)
**Definition:** Total revenue generated from a customer over their lifetime

**Target:** ₹2,500+ LTV

**Calculation:**
```
LTV = Average Revenue Per User (ARPU) × Customer Lifetime (Months)
```

---

## Business Metrics

### 1. Revenue Metrics

#### Monthly Recurring Revenue (MRR)
**Definition:** Monthly recurring revenue from subscriptions

**Target:** ₹10,00,000 MRR by Month 6

**Measurement:**
- **Current:** ₹10,000 MRR (Month 1)
- **Target:** ₹10,00,000 MRR (Month 6)
- **Growth Rate:** 30% month-over-month
- **Frequency:** Monthly measurement
- **Owner:** Finance Team + Product Team

#### Annual Recurring Revenue (ARR)
**Definition:** Annual recurring revenue from subscriptions

**Target:** ₹1,20,00,000 ARR by Year 1

**Calculation:**
```
ARR = MRR × 12
```

#### Revenue Growth Rate
**Definition:** Month-over-month percentage growth in revenue

**Target:** 30%+ month-over-month growth

**Calculation:**
```
Revenue Growth Rate = (Current Month Revenue - Previous Month Revenue) / Previous Month Revenue × 100
```

### 2. Customer Metrics

#### Average Revenue Per User (ARPU)
**Definition:** Average revenue generated per user per month

**Target:** ₹200+ ARPU

**Calculation:**
```
ARPU = Total Monthly Revenue / Number of Paying Users
```

#### Customer Acquisition Cost (CAC)
**Definition:** Average cost to acquire a new customer

**Target:** ₹500 or less per customer

#### Customer Lifetime Value (LTV)
**Definition:** Total revenue generated from a customer over their lifetime

**Target:** ₹2,500+ LTV

#### LTV/CAC Ratio
**Definition:** Ratio of customer lifetime value to customer acquisition cost

**Target:** 5:1 or higher

**Calculation:**
```
LTV/CAC Ratio = LTV / CAC
```

### 3. Market Metrics

#### Market Share
**Definition:** Percentage of total addressable market captured

**Target:** 5%+ market share by Year 1

**Calculation:**
```
Market Share = SaralPolicy Users / Total Addressable Market × 100
```

#### Brand Awareness
**Definition:** Percentage of target audience aware of SaralPolicy

**Target:** 80%+ brand awareness

**Measurement:**
- **Unaided Awareness:** 40%+
- **Aided Awareness:** 80%+
- **Brand Recognition:** 90%+

#### Net Promoter Score (NPS)
**Definition:** Measure of customer satisfaction and loyalty

**Target:** 70+ NPS

**Calculation:**
```
NPS = % Promoters - % Detractors
```

---

## Technical Metrics

### 1. AI Performance Metrics

#### Model Accuracy
**Definition:** Accuracy of AI model predictions

**Target:** 95%+ accuracy

**Measurement:**
- **Factuality Score:** 98%+
- **Grounding Ratio:** 95%+
- **Relevance Score:** 90%+
- **Completeness Score:** 85%+

#### AI Response Time
**Definition:** Time taken for AI to generate responses

**Target:** <5 seconds per response

**Measurement:**
- **Policy Analysis:** <30 seconds
- **Q&A Response:** <5 seconds
- **Key Terms Extraction:** <10 seconds
- **Exclusion Identification:** <15 seconds

#### HITL Trigger Rate
**Definition:** Percentage of analyses requiring human expert review

**Target:** <10% HITL trigger rate

**Measurement:**
- **Current:** 15% HITL trigger rate
- **Target:** <10% HITL trigger rate
- **Frequency:** Per analysis
- **Owner:** AI Team + HITL Team

### 2. System Performance Metrics

#### API Response Time
**Definition:** Time taken for API endpoints to respond

**Target:** <2 seconds per API call

**Measurement:**
- **Document Upload:** <5 seconds
- **Policy Analysis:** <30 seconds
- **Q&A Response:** <5 seconds
- **User Authentication:** <1 second

#### System Uptime
**Definition:** Percentage of time system is operational

**Target:** 99.9% uptime

**Measurement:**
- **Current:** 99.5% uptime
- **Target:** 99.9% uptime
- **Frequency:** Continuous monitoring
- **Owner:** Engineering Team

#### Error Rate
**Definition:** Percentage of requests that result in errors

**Target:** <1% error rate

**Measurement:**
- **API Errors:** <1%
- **Processing Errors:** <2%
- **User Errors:** <5%
- **System Errors:** <0.1%

### 3. Scalability Metrics

#### Concurrent Users
**Definition:** Maximum number of users using system simultaneously

**Target:** 10,000+ concurrent users

**Measurement:**
- **Current:** 100 concurrent users
- **Target:** 10,000+ concurrent users
- **Peak Usage:** 15,000+ concurrent users
- **Frequency:** Real-time monitoring

#### Throughput
**Definition:** Number of requests processed per second

**Target:** 1,000+ requests per second

**Measurement:**
- **API Requests:** 1,000+ per second
- **Document Processing:** 100+ per minute
- **Q&A Requests:** 1,000+ per minute
- **User Authentication:** 500+ per second

---

## Quality Metrics

### 1. AI Quality Metrics

#### Factuality Score
**Definition:** Accuracy of factual claims in AI responses

**Target:** 98%+ factuality score

**Measurement:**
- **Human Evaluation:** Expert assessment
- **Automated Evaluation:** TruLens evaluation
- **User Feedback:** User satisfaction scores
- **HITL Validation:** Expert review scores

#### Grounding Ratio
**Definition:** Percentage of AI responses grounded in source documents

**Target:** 95%+ grounding ratio

**Measurement:**
- **Source Citation:** 95%+ responses cite sources
- **Document Alignment:** 90%+ alignment with source documents
- **Context Relevance:** 85%+ context relevance
- **Accuracy Verification:** 95%+ accuracy verification

#### Bias Score
**Definition:** Measure of bias in AI responses

**Target:** <5% bias score

**Measurement:**
- **Demographic Bias:** <5%
- **Geographic Bias:** <5%
- **Socioeconomic Bias:** <5%
- **Overall Bias:** <5%

### 2. User Experience Metrics

#### User Satisfaction Score
**Definition:** Overall user satisfaction with SaralPolicy

**Target:** 90%+ satisfaction score

**Measurement:**
- **User Surveys:** Monthly satisfaction surveys
- **App Store Ratings:** 4.5+ stars
- **User Feedback:** Positive feedback percentage
- **Support Tickets:** Low support ticket volume

#### Task Completion Rate
**Definition:** Percentage of users who successfully complete tasks

**Target:** 80%+ task completion rate

**Key Tasks:**
- **Document Upload:** 90%+ completion
- **Policy Analysis:** 85%+ completion
- **Q&A Usage:** 70%+ completion
- **Report Export:** 60%+ completion

#### User Onboarding Success Rate
**Definition:** Percentage of users who successfully complete onboarding

**Target:** 80%+ onboarding success rate

**Measurement:**
- **Account Creation:** 90%+ success
- **First Analysis:** 80%+ success
- **Feature Discovery:** 70%+ success
- **Retention:** 60%+ success

### 3. Compliance Metrics

#### IRDAI Compliance Score
**Definition:** Compliance with IRDAI regulations

**Target:** 100% compliance

**Measurement:**
- **Regulatory Compliance:** 100%
- **Audit Readiness:** 100%
- **Documentation:** 100%
- **Reporting:** 100%

#### DPDP Compliance Score
**Definition:** Compliance with DPDP 2023 regulations

**Target:** 100% compliance

**Measurement:**
- **Privacy Compliance:** 100%
- **Data Protection:** 100%
- **User Rights:** 100%
- **Consent Management:** 100%

---

## Operational Metrics

### 1. Team Performance Metrics

#### Development Velocity
**Definition:** Speed of feature development and delivery

**Target:** 2+ features per sprint

**Measurement:**
- **Story Points:** 20+ story points per sprint
- **Feature Delivery:** 2+ features per sprint
- **Bug Fixes:** 5+ bug fixes per sprint
- **Code Quality:** 90%+ code coverage

#### Team Productivity
**Definition:** Overall team productivity and efficiency

**Target:** 90%+ productivity score

**Measurement:**
- **Task Completion:** 90%+ task completion
- **Sprint Success:** 80%+ sprint success
- **Code Quality:** 90%+ code quality
- **Team Satisfaction:** 80%+ team satisfaction

### 2. Customer Support Metrics

#### Support Ticket Volume
**Definition:** Number of customer support tickets

**Target:** <5% of users per month

**Measurement:**
- **Current:** 10% of users
- **Target:** <5% of users
- **Frequency:** Monthly measurement
- **Owner:** Support Team

#### Support Response Time
**Definition:** Time taken to respond to support tickets

**Target:** <2 hours for critical issues

**Measurement:**
- **Critical Issues:** <2 hours
- **High Priority:** <4 hours
- **Medium Priority:** <8 hours
- **Low Priority:** <24 hours

#### Support Resolution Rate
**Definition:** Percentage of support tickets resolved

**Target:** 95%+ resolution rate

**Measurement:**
- **First Contact Resolution:** 70%+
- **Overall Resolution:** 95%+
- **User Satisfaction:** 90%+
- **Escalation Rate:** <5%

---

## Metrics Dashboard

### 1. Executive Dashboard

#### Key Metrics
- **North Star:** Claim dispute reduction
- **Revenue:** MRR, ARR, growth rate
- **Users:** MAU, growth rate, retention
- **Quality:** AI accuracy, user satisfaction
- **Performance:** System uptime, response time

#### Frequency: Daily updates

### 2. Product Dashboard

#### Key Metrics
- **User Engagement:** DAU, session duration, feature adoption
- **User Experience:** Satisfaction, task completion, onboarding
- **Product Performance:** Feature usage, user feedback, improvements
- **Quality:** AI accuracy, bias scores, HITL rates

#### Frequency: Daily updates

### 3. Technical Dashboard

#### Key Metrics
- **System Performance:** Uptime, response time, error rate
- **AI Performance:** Accuracy, response time, HITL rates
- **Scalability:** Concurrent users, throughput, capacity
- **Security:** Security incidents, compliance scores

#### Frequency: Real-time updates

### 4. Business Dashboard

#### Key Metrics
- **Revenue:** MRR, ARR, growth rate, ARPU
- **Customer:** CAC, LTV, churn rate, retention
- **Market:** Market share, brand awareness, NPS
- **Operations:** Support tickets, resolution rate, team productivity

#### Frequency: Weekly updates

---

## Metrics Implementation

### 1. Data Collection

#### Automated Collection
- **System Metrics:** Automated system monitoring
- **User Behavior:** Analytics and tracking
- **Performance Metrics:** Real-time performance monitoring
- **Quality Metrics:** Automated quality assessment

#### Manual Collection
- **User Surveys:** Regular user satisfaction surveys
- **Expert Evaluation:** Human expert assessments
- **Market Research:** Market analysis and research
- **Competitive Analysis:** Competitive benchmarking

### 2. Data Analysis

#### Trend Analysis
- **Historical Trends:** Long-term trend analysis
- **Seasonal Patterns:** Seasonal variation analysis
- **Growth Patterns:** Growth trajectory analysis
- **Performance Patterns:** Performance trend analysis

#### Comparative Analysis
- **Benchmarking:** Industry benchmark comparison
- **Competitive Analysis:** Competitive performance comparison
- **Internal Comparison:** Internal performance comparison
- **Target Comparison:** Target vs. actual performance

### 3. Reporting and Communication

#### Reporting Frequency
- **Daily:** Real-time metrics dashboard
- **Weekly:** Weekly performance reports
- **Monthly:** Monthly business reviews
- **Quarterly:** Quarterly strategic reviews

#### Communication Channels
- **Dashboard:** Real-time metrics dashboard
- **Reports:** Automated performance reports
- **Meetings:** Regular performance review meetings
- **Alerts:** Automated alerts for critical metrics

---

## Success Criteria

### 1. Short-term Success (6 months)

#### User Metrics
- **MAU:** 100,000+ users
- **Retention:** 70%+ retention rate
- **Satisfaction:** 90%+ satisfaction score
- **Engagement:** 5+ minutes per session

#### Business Metrics
- **MRR:** ₹10,00,000+ MRR
- **Growth:** 30%+ month-over-month growth
- **CAC:** ₹500 or less per customer
- **LTV:** ₹2,500+ LTV

#### Technical Metrics
- **Accuracy:** 95%+ AI accuracy
- **Performance:** 99.9% uptime
- **Response Time:** <5 seconds per response
- **Scalability:** 10,000+ concurrent users

### 2. Long-term Success (12 months)

#### Market Metrics
- **Market Share:** 5%+ market share
- **Brand Awareness:** 80%+ awareness
- **NPS:** 70+ NPS
- **Revenue:** ₹1,20,00,000+ ARR

#### Quality Metrics
- **Claim Reduction:** 30%+ claim dispute reduction
- **User Understanding:** 90%+ policy understanding
- **Compliance:** 100% regulatory compliance
- **Trust:** 95%+ user trust score

---

**Next Steps:** Implement metrics collection system, establish reporting dashboards, and begin continuous monitoring of key performance indicators.
