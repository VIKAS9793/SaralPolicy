# Explainability & Evals Framework - SaralPolicy

**Product:** SaralPolicy  
**Version:** 1.0  
**Author:** Vikas Sahani (Product Manager)  
**Engineering Team:** Kiro (AI Co-Engineering Assistant), Antigravity (AI Co-Assistant)  
**Date:** January 2026  

---

## Framework Overview

SaralPolicy implements a comprehensive evaluation and explainability framework that ensures AI transparency, accuracy, and trustworthiness through multiple evaluation frameworks, human-in-the-loop validation, and continuous monitoring.

---

## Evaluation Frameworks Integration

### 1. TruLens (2025) - LLM Evaluations

#### Purpose
Comprehensive evaluation of LLM outputs for factuality, relevance, and safety.

#### Implementation
```python
from trulens import TruLlama
from trulens.llm import LLM

# Initialize TruLens evaluator
tru_llama = TruLlama(
    model=llm_service,
    app_id="saralpolicy_analysis",
    feedback_functions=[
        "factuality",
        "relevance", 
        "safety",
        "grounding"
    ]
)

# Evaluate policy analysis
evaluation_result = tru_llama.evaluate(
    input_text=policy_text,
    output_text=analysis_summary,
    context=source_documents
)
```

#### Metrics Tracked
- **Factuality Score:** Accuracy of factual claims (Target: ≥98%)
- **Relevance Score:** Relevance to user query (Target: ≥95%)
- **Safety Score:** Absence of harmful content (Target: 100%)
- **Grounding Score:** Source document alignment (Target: ≥95%)

#### Quality Gates
- **Auto-approval:** All scores ≥95%
- **HITL Trigger:** Any score <95%
- **Rejection:** Safety score <90%

### 2. Giskard v3 - Hallucination & Bias Detection

#### Purpose
Detect AI hallucinations, bias, and fairness issues in policy analysis.

#### Implementation
```python
import giskard
from giskard import Model, Dataset, scan

# Initialize Giskard model
model = Model(
    model=llm_service,
    model_type="text_generation",
    name="saralpolicy_llm"
)

# Create test dataset
dataset = Dataset(
    df=test_policies,
    target="analysis_quality",
    name="policy_test_set"
)

# Run comprehensive scan
scan_results = scan(
    model=model,
    dataset=dataset,
    tests=[
        "hallucination_detection",
        "bias_detection", 
        "fairness_assessment",
        "robustness_testing"
    ]
)
```

#### Metrics Tracked
- **Hallucination Rate:** False information generation (Target: <2%)
- **Bias Score:** Demographic bias detection (Target: <5%)
- **Fairness Score:** Equal treatment across groups (Target: ≥95%)
- **Robustness Score:** Performance under adversarial inputs (Target: ≥90%)

#### Quality Gates
- **Green Zone:** All scores within targets
- **Yellow Zone:** Minor issues, monitor closely
- **Red Zone:** Major issues, immediate HITL review

### 3. DeepEval - RAG Integrity

#### Purpose
Evaluate retrieval-augmented generation system integrity and performance.

#### Implementation
```python
from deepeval import evaluate
from deepeval.metrics import HallucinationMetric, AnswerRelevancyMetric

# Define evaluation metrics
hallucination_metric = HallucinationMetric(threshold=0.5)
relevancy_metric = AnswerRelevancyMetric(threshold=0.7)

# Evaluate RAG system
evaluation_results = evaluate(
    model=rag_system,
    test_cases=test_qa_pairs,
    metrics=[hallucination_metric, relevancy_metric]
)
```

#### Metrics Tracked
- **Retrieval Accuracy:** Relevant document retrieval (Target: ≥95%)
- **Answer Relevancy:** Answer relevance to question (Target: ≥90%)
- **Source Attribution:** Correct source citation (Target: ≥95%)
- **Context Utilization:** Effective use of retrieved context (Target: ≥85%)

#### Quality Gates
- **High Quality:** All metrics ≥95%
- **Medium Quality:** Metrics 85-95%
- **Low Quality:** Metrics <85%, HITL required

### 4. HumanEval+ - HITL Validation

#### Purpose
Track and evaluate human-in-the-loop validation effectiveness.

#### Implementation
```python
class HumanEvalTracker:
    def __init__(self):
        self.expert_feedback = {}
        self.validation_metrics = {}
    
    def track_expert_review(self, review_id, expert_id, feedback):
        self.expert_feedback[review_id] = {
            "expert_id": expert_id,
            "feedback": feedback,
            "timestamp": datetime.now(),
            "validation_result": self.assess_feedback(feedback)
        }
    
    def calculate_hitl_metrics(self):
        return {
            "expert_agreement_rate": self.calculate_agreement(),
            "feedback_quality_score": self.assess_feedback_quality(),
            "validation_accuracy": self.calculate_validation_accuracy()
        }
```

#### Metrics Tracked
- **Expert Agreement Rate:** Consensus among experts (Target: ≥90%)
- **Feedback Quality Score:** Quality of expert feedback (Target: ≥85%)
- **Validation Accuracy:** Correctness of expert validation (Target: ≥95%)
- **Response Time:** Average expert response time (Target: <24 hours)

#### Quality Gates
- **Excellent:** All metrics ≥95%
- **Good:** Metrics 85-95%
- **Needs Improvement:** Metrics <85%

### 5. Guardrails.ai - Context Compliance

#### Purpose
Ensure AI responses comply with context and safety requirements.

#### Implementation
```python
from guardrails import Guard
from guardrails.hub import ProfanityFree, ToxicLanguage

# Define guardrails
guard = Guard().use(
    ProfanityFree(),
    ToxicLanguage(),
    ContextCompliance(),
    PIIProtection()
)

# Apply guardrails to AI responses
protected_response = guard.validate(
    user_input=user_question,
    ai_response=ai_answer,
    context=policy_document
)
```

#### Metrics Tracked
- **Context Compliance:** Adherence to source context (Target: ≥95%)
- **Safety Compliance:** Absence of harmful content (Target: 100%)
- **PII Protection:** Personal information redaction (Target: 100%)
- **Regulatory Compliance:** IRDAI guideline adherence (Target: 100%)

#### Quality Gates
- **Compliant:** All metrics meet targets
- **Non-compliant:** Any metric below target, immediate review

---

## Explainability Framework

### 1. SHAP (SHapley Additive exPlanations)

#### Purpose
Provide local explanations for individual AI decisions and predictions.

#### Implementation
```python
import shap
from shap import Explainer

# Initialize SHAP explainer
explainer = Explainer(
    model=llm_service,
    masker=policy_text,
    algorithm="auto"
)

# Generate explanations
shap_values = explainer(policy_text)
explanation = shap_values[0]

# Visualize explanations
shap.plots.text(explanation)
```

#### Use Cases
- **Clause Attribution:** Which clauses influenced the analysis
- **Term Importance:** Most important terms in policy interpretation
- **Decision Rationale:** Why specific conclusions were reached
- **Confidence Factors:** Factors affecting confidence scores

### 2. LIME (Local Interpretable Model-agnostic Explanations)

#### Purpose
Provide interpretable explanations for complex AI models.

#### Implementation
```python
from lime import LimeTextExplainer

# Initialize LIME explainer
explainer = LimeTextExplainer(class_names=['covered', 'excluded'])

# Generate explanations
explanation = explainer.explain_instance(
    text_instance=policy_text,
    classifier_fn=llm_service.predict,
    num_features=10
)

# Display explanation
explanation.show_in_notebook()
```

#### Use Cases
- **Feature Importance:** Most influential text features
- **Decision Boundaries:** Clear decision explanations
- **Model Behavior:** Understanding model reasoning
- **Error Analysis:** Identifying model limitations

### 3. Attention Visualization

#### Purpose
Visualize model attention patterns for transparency.

#### Implementation
```python
import torch
import matplotlib.pyplot as plt

# Extract attention weights
attention_weights = model.get_attention_weights(input_text)

# Visualize attention
plt.figure(figsize=(12, 8))
plt.imshow(attention_weights, cmap='Blues')
plt.title('Model Attention Visualization')
plt.xlabel('Input Tokens')
plt.ylabel('Attention Layers')
plt.show()
```

#### Use Cases
- **Attention Patterns:** What the model focuses on
- **Token Importance:** Most attended tokens
- **Layer Analysis:** Different attention layers
- **Comparative Analysis:** Attention across different inputs

---

## Continuous Evaluation Pipeline

### 1. Real-time Monitoring

#### Metrics Dashboard
```python
class EvaluationDashboard:
    def __init__(self):
        self.metrics = {
            "factuality_score": 0.0,
            "relevance_score": 0.0,
            "safety_score": 0.0,
            "grounding_score": 0.0,
            "hallucination_rate": 0.0,
            "bias_score": 0.0,
            "expert_agreement_rate": 0.0
        }
    
    def update_metrics(self, evaluation_results):
        for metric, value in evaluation_results.items():
            self.metrics[metric] = value
    
    def check_quality_gates(self):
        alerts = []
        if self.metrics["factuality_score"] < 0.95:
            alerts.append("Factuality score below threshold")
        if self.metrics["hallucination_rate"] > 0.02:
            alerts.append("Hallucination rate above threshold")
        return alerts
```

### 2. Automated Quality Gates

#### Quality Gate Implementation
```python
class QualityGate:
    def __init__(self):
        self.thresholds = {
            "factuality_score": 0.95,
            "relevance_score": 0.95,
            "safety_score": 0.90,
            "grounding_score": 0.95,
            "hallucination_rate": 0.02,
            "bias_score": 0.05
        }
    
    def evaluate_quality(self, metrics):
        quality_score = 0
        total_metrics = len(metrics)
        
        for metric, value in metrics.items():
            if value >= self.thresholds.get(metric, 0):
                quality_score += 1
        
        return quality_score / total_metrics
    
    def determine_action(self, quality_score):
        if quality_score >= 0.95:
            return "auto_approve"
        elif quality_score >= 0.85:
            return "monitor"
        else:
            return "hitl_review"
```

### 3. Feedback Loop Integration

#### Continuous Improvement
```python
class FeedbackLoop:
    def __init__(self):
        self.expert_feedback = []
        self.model_performance = {}
    
    def collect_feedback(self, review_id, expert_feedback):
        self.expert_feedback.append({
            "review_id": review_id,
            "feedback": expert_feedback,
            "timestamp": datetime.now()
        })
    
    def update_model(self):
        # Analyze feedback patterns
        feedback_analysis = self.analyze_feedback()
        
        # Update model parameters
        model_updates = self.generate_model_updates(feedback_analysis)
        
        # Deploy updated model
        self.deploy_model_updates(model_updates)
```

---

## Evaluation Metrics Summary

### Core Quality Metrics
| Metric | Target | Measurement Method | Action Threshold |
|--------|--------|-------------------|------------------|
| Factuality Score | ≥98% | TruLens evaluation | <95% → HITL |
| Grounding Ratio | ≥95% | Source alignment | <95% → HITL |
| Hallucination Rate | <2% | Giskard detection | >2% → HITL |
| Bias Score | <5% | Giskard assessment | >5% → Review |
| Expert Agreement | ≥90% | HITL validation | <90% → Retrain |

### Performance Metrics
| Metric | Target | Measurement Method | Action Threshold |
|--------|--------|-------------------|------------------|
| Response Time | <5s | System monitoring | >10s → Optimize |
| Throughput | 1000/min | Load testing | <500/min → Scale |
| Uptime | 99.9% | Infrastructure monitoring | <99% → Alert |
| Error Rate | <1% | Error tracking | >5% → Investigate |

### Compliance Metrics
| Metric | Target | Measurement Method | Action Threshold |
|--------|--------|-------------------|------------------|
| IRDAI Compliance | 100% | Regulatory audit | <100% → Fix |
| DPDP Compliance | 100% | Privacy audit | <100% → Fix |
| PII Protection | 100% | Data scanning | <100% → Fix |
| Audit Trail | 100% | Log verification | <100% → Fix |

---

## Implementation Roadmap

### Phase 1: Foundation (Months 1-2)
- [ ] TruLens integration and basic evaluation
- [ ] Giskard setup for hallucination detection
- [ ] Basic quality gates implementation
- [ ] Real-time monitoring dashboard

### Phase 2: Advanced Evaluation (Months 3-4)
- [ ] DeepEval RAG integrity assessment
- [ ] HumanEval+ HITL tracking
- [ ] Guardrails.ai context compliance
- [ ] SHAP/LIME explainability integration

### Phase 3: Continuous Improvement (Months 5-6)
- [ ] Automated feedback loop
- [ ] Model retraining pipeline
- [ ] Advanced quality gates
- [ ] Comprehensive reporting

---

**Next Steps:** Begin with TruLens and Giskard integration, establish basic quality gates, and implement real-time monitoring dashboard.
