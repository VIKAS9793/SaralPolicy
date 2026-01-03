# System & Data Architecture - SaralPolicy

**Product:** SaralPolicy  
**Version:** 1.0  
**Author:** Vikas Sahani (Product Manager)  
**Engineering Team:** Kiro (AI Co-Engineering Assistant), Antigravity (AI Co-Assistant)  
**Date:** January 2026  

---

## Architecture Overview

SaralPolicy implements a modern, scalable architecture that combines AI-powered analysis with human expertise through a Human-in-the-Loop (HITL) system, Retrieval-Augmented Generation (RAG), and comprehensive guardrails for safety and compliance.

---

## System Architecture Layers

### Layer 1: Frontend Layer
**Technology Stack:** React/Flutter, Material UI, Progressive Web App (PWA)

**Components:**
- **Web Application:** React-based responsive web interface
- **Mobile Applications:** Native iOS and Android apps
- **Progressive Web App:** Offline-capable web application
- **Admin Dashboard:** Expert review and management interface

**Responsibilities:**
- User interface and experience
- Document upload and management
- Results visualization and interaction
- Mobile-optimized experience
- Offline functionality

### Layer 2: API Gateway Layer
**Technology Stack:** FastAPI, NGINX, Load Balancer

**Components:**
- **API Gateway:** Request routing and load balancing
- **Authentication Service:** JWT-based authentication
- **Rate Limiting:** Request throttling and protection
- **API Versioning:** Backward compatibility management

**Responsibilities:**
- Request routing and load balancing
- Authentication and authorization
- Rate limiting and protection
- API versioning and compatibility

### Layer 3: Backend Services Layer
**Technology Stack:** FastAPI, Python 3.11, Microservices Architecture

**Core Services:**
- **Document Processing Service:** PDF/DOCX parsing and OCR
- **AI Analysis Service:** Policy summarization and analysis
- **RAG Service:** Document retrieval and question answering
- **HITL Service:** Human expert review and validation
- **Guardrails Service:** Safety checks and compliance
- **Evaluation Service:** Quality metrics and assessment

**Responsibilities:**
- Business logic implementation
- Service orchestration
- Data processing and transformation
- Integration with external services

### Layer 4: AI/ML Layer
**Technology Stack:** Local Llama-2-7b-chat, Transformers, LangChain, FAISS

**Components:**
- **Local LLM Service:** Llama-2 model for policy analysis
- **RAG Pipeline:** FAISS vector store with LangChain
- **Embedding Service:** Document and query embeddings
- **Model Management:** Model versioning and deployment
- **Fine-tuning Pipeline:** Continuous model improvement

**Responsibilities:**
- AI-powered policy analysis
- Document retrieval and search
- Natural language processing
- Model training and improvement

### Layer 5: Data Layer
**Technology Stack:** PostgreSQL, Redis, FAISS, S3-compatible Storage

**Components:**
- **Primary Database:** PostgreSQL for metadata and user data
- **Vector Database:** FAISS for document embeddings
- **Cache Layer:** Redis for session and temporary data
- **Object Storage:** S3-compatible storage for documents
- **Audit Database:** Separate database for compliance logs

**Responsibilities:**
- Data persistence and retrieval
- Vector similarity search
- Caching and performance optimization
- Audit trail maintenance

### Layer 6: Infrastructure Layer
**Technology Stack:** Docker, Kubernetes, Cloud Infrastructure

**Components:**
- **Container Orchestration:** Kubernetes for service management
- **Service Mesh:** Istio for service communication
- **Monitoring:** Prometheus, Grafana for system monitoring
- **Logging:** ELK Stack for log aggregation
- **Security:** Vault for secrets management

**Responsibilities:**
- Service deployment and management
- Monitoring and observability
- Security and compliance
- Infrastructure automation

---

## Data Architecture

### Data Flow Pipeline

#### 1. Document Ingestion
```
User Upload → File Validation → OCR Processing → Text Extraction → Metadata Extraction
```

**Components:**
- **File Upload Service:** Handles document upload and validation
- **OCR Service:** Processes scanned documents and images
- **Text Extraction Service:** Extracts text from various formats
- **Metadata Service:** Extracts document metadata and properties

#### 2. Document Processing
```
Text Extraction → Preprocessing → Embedding Generation → Vector Storage → Indexing
```

**Components:**
- **Text Preprocessing:** Cleaning and normalization
- **Embedding Generation:** Creating document embeddings
- **Vector Storage:** Storing embeddings in FAISS
- **Indexing Service:** Creating searchable indexes

#### 3. AI Analysis
```
Document Text → AI Model → Policy Analysis → Confidence Scoring → HITL Triggering
```

**Components:**
- **AI Model Service:** Local Llama-2 model for analysis
- **Analysis Engine:** Policy summarization and extraction
- **Confidence Scoring:** Quality assessment and validation
- **HITL Triggering:** Expert review for low confidence

#### 4. RAG Processing
```
User Query → Query Processing → Vector Search → Context Retrieval → Answer Generation
```

**Components:**
- **Query Processing:** Natural language understanding
- **Vector Search:** FAISS-based similarity search
- **Context Retrieval:** Relevant document retrieval
- **Answer Generation:** Context-aware answer creation

#### 5. HITL Validation
```
Low Confidence Analysis → Expert Assignment → Expert Review → Feedback Integration → Model Update
```

**Components:**
- **Expert Assignment:** Matching experts to review tasks
- **Review Interface:** Expert review and validation tools
- **Feedback Integration:** Incorporating expert feedback
- **Model Update:** Continuous model improvement

---

## Database Schema

### Core Tables

#### Users Table
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    phone VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    is_active BOOLEAN DEFAULT TRUE,
    subscription_tier VARCHAR(50) DEFAULT 'free'
);
```

#### Documents Table
```sql
CREATE TABLE documents (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50) NOT NULL,
    file_size BIGINT NOT NULL,
    upload_status VARCHAR(50) DEFAULT 'pending',
    processing_status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metadata JSONB,
    storage_path VARCHAR(500)
);
```

#### Policy Analysis Table
```sql
CREATE TABLE policy_analyses (
    id UUID PRIMARY KEY,
    document_id UUID REFERENCES documents(id),
    user_id UUID REFERENCES users(id),
    summary TEXT,
    key_terms JSONB,
    exclusions JSONB,
    coverage_details JSONB,
    confidence_score DECIMAL(3,2),
    hitl_triggered BOOLEAN DEFAULT FALSE,
    hitl_review_id UUID,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### HITL Reviews Table
```sql
CREATE TABLE hitl_reviews (
    id UUID PRIMARY KEY,
    analysis_id UUID REFERENCES policy_analyses(id),
    expert_id UUID,
    review_status VARCHAR(50) DEFAULT 'pending',
    expert_feedback TEXT,
    validation_result VARCHAR(50),
    confidence_score DECIMAL(3,2),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);
```

#### Q&A Sessions Table
```sql
CREATE TABLE qa_sessions (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    document_id UUID REFERENCES documents(id),
    question TEXT NOT NULL,
    answer TEXT,
    confidence_score DECIMAL(3,2),
    source_citations JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Vector Database Schema

#### Document Embeddings
```python
# FAISS Index Structure
{
    "document_id": "uuid",
    "embedding": "vector[768]",  # 768-dimensional embedding
    "metadata": {
        "document_type": "policy",
        "section": "coverage",
        "page_number": 1,
        "confidence": 0.95
    }
}
```

#### Query Embeddings
```python
# Query Vector Structure
{
    "query_id": "uuid",
    "embedding": "vector[768]",
    "metadata": {
        "query_type": "coverage",
        "user_id": "uuid",
        "timestamp": "2025-10-01T00:00:00Z"
    }
}
```

---

## Security Architecture

### Data Protection
- **Encryption at Rest:** AES-256 encryption for all stored data
- **Encryption in Transit:** TLS 1.3 for all communications
- **PII Redaction:** Automatic removal of sensitive information
- **Data Anonymization:** User data anonymization for analytics

### Access Control
- **Authentication:** JWT-based authentication with refresh tokens
- **Authorization:** Role-based access control (RBAC)
- **API Security:** Rate limiting and request validation
- **Session Management:** Secure session handling and timeout

### Compliance
- **IRDAI Compliance:** Regulatory compliance for insurance sector
- **DPDP 2023:** Data privacy and protection compliance
- **Audit Logging:** Comprehensive audit trail for all operations
- **Data Retention:** Automated data retention and deletion

---

## Scalability Architecture

### Horizontal Scaling
- **Microservices:** Independent service scaling
- **Load Balancing:** Distributed request handling
- **Auto-scaling:** Automatic resource scaling based on demand
- **Database Sharding:** Horizontal database partitioning

### Performance Optimization
- **Caching Strategy:** Multi-level caching (Redis, CDN)
- **Database Optimization:** Query optimization and indexing
- **CDN Integration:** Global content delivery network
- **Async Processing:** Background task processing

### Monitoring and Observability
- **Application Metrics:** Performance and usage metrics
- **Infrastructure Metrics:** System resource monitoring
- **Log Aggregation:** Centralized logging with ELK stack
- **Alerting:** Proactive issue detection and notification

---

## Integration Architecture

### External Integrations
- **Insurer APIs:** Real-time policy verification
- **Payment Gateways:** Subscription and payment processing
- **Notification Services:** Email and SMS notifications
- **Analytics Services:** User behavior and performance analytics

### Internal Integrations
- **AI/ML Services:** Model training and inference
- **Document Processing:** OCR and text extraction
- **Vector Search:** FAISS-based similarity search
- **Expert Network:** Human-in-the-loop validation

---

## Deployment Architecture

### Development Environment
- **Local Development:** Docker Compose for local development
- **Testing Environment:** Automated testing and validation
- **Staging Environment:** Production-like testing environment
- **CI/CD Pipeline:** Automated deployment and testing

### Production Environment
- **Cloud Infrastructure:** Scalable cloud deployment
- **Container Orchestration:** Kubernetes for service management
- **Service Mesh:** Istio for service communication
- **Monitoring:** Comprehensive monitoring and alerting

### Disaster Recovery
- **Backup Strategy:** Automated backup and recovery
- **Failover Procedures:** Automatic failover mechanisms
- **Data Replication:** Multi-region data replication
- **Recovery Testing:** Regular disaster recovery testing

---

## Technology Stack Summary

### Frontend
- **Web:** React, Material UI, Progressive Web App
- **Mobile:** React Native, Native iOS/Android
- **State Management:** Redux, Context API
- **Styling:** Material UI, CSS-in-JS

### Backend
- **Framework:** FastAPI, Python 3.11
- **Database:** PostgreSQL, Redis, FAISS
- **AI/ML:** Transformers, LangChain, Local Llama
- **Storage:** S3-compatible object storage

### Infrastructure
- **Containerization:** Docker, Kubernetes
- **Cloud:** AWS/Azure/GCP
- **Monitoring:** Prometheus, Grafana, ELK Stack
- **Security:** Vault, OAuth2, JWT

---

**Next Steps:** Begin implementation with core services, focusing on document processing, AI analysis, and HITL system development.
