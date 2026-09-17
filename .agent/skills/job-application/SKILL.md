# Job Application Resume Family Classification Agent

## Resources

Resume folder: `Resume/`

| Family | PDF |
|---|---|
| `AI_GENAI` | `Sai_Teja_Applied AI & Gen AI.pdf` |
| `ML_DATA` | `Sai_Teja_ML_Data.pdf` |
| `AI_PLATFORM` | `Sai_Teja_AI_Platform.pdf` |
| `AI_PRODUCT_FDE` | `Sai_Teja_Applied AI & AI Product Engineer.pdf` |
| `AI_AUTOMATION_PM` | `Sai_Teja_AI Automation & Technical Project Engineer.pdf` |

## 1. Objective

I am building a job application system where each job posting must be analyzed and assigned to the most appropriate **resume family**.

The goal is NOT to create a new resume for every job.

Instead, I want to maintain a small number of highly targeted master resumes and route each job application to the correct resume family.

The agent should:

1. Read and analyze each job role.
2. Identify the actual job function, not just the job title.
3. Classify the role into exactly ONE primary `resume_family`.
4. Identify secondary skill signals.
5. Identify seniority.
6. Identify domain/industry.
7. Identify important technologies/skills.
8. Detect whether the role is actually suitable for my target career.
9. Flag roles that are weak matches or should be vetoed.
10. Avoid creating unnecessary resume families.
11. Maintain consistent classification across all jobs.
12. Update/return structured data that can be stored in Airtable.

---

# 2. Resume Family Taxonomy

Use these standardized resume families:

### `AI_GENAI`

For roles primarily focused on:

* Generative AI
* LLM applications
* RAG
* AI agents
* Agentic AI
* Multi-agent systems
* Prompt engineering
* LLM orchestration
* AI application development
* AI-powered software
* NLP when strongly connected to LLM/GenAI
* AI copilots
* Conversational AI
* AI product engineering
* LLM evaluation
* AI reasoning
* AI application/backend engineering

Typical titles:

* Generative AI Engineer
* AI Engineer — LLM/RAG/Agents
* Agentic AI Engineer
* AI Agent Engineer
* Applied AI Engineer
* Software Engineer, Generative AI
* LLM Data Scientist
* AI Product Engineer
* AI Integration Engineer
* Senior AI Engineer — LLM/RAG
* AI Engineer — Python/NLP/Computer Vision when the actual work is primarily LLM/AI application development

Core positioning:

> Applied AI / GenAI engineer who builds practical AI systems, agents, LLM applications and intelligent workflows.

---

### `ML_DATA`

For roles primarily focused on:

* Machine learning
* Deep learning
* Classical ML
* Data science
* Predictive modelling
* Recommendation systems
* Search/ranking
* Computer vision
* NLP modelling
* AI research
* ML algorithms
* Statistical modelling
* Forecasting
* Optimization
* Applied ML

Include computer vision roles here when the role is fundamentally an ML/model-development position.

Typical titles:

* Machine Learning Engineer
* AI/ML Engineer
* Data Scientist
* Computer Vision Engineer
* Computer Vision Researcher
* ML Research Engineer
* Algorithm Engineer
* Recommendation Engineer
* Search/Ranking Engineer
* AI Research Engineer
* Vision AI Specialist
* Motion AI Specialist
* Robotics AI Research Engineer

Core positioning:

> Machine learning / AI engineer with strong applied modelling, computer vision, data science and experimentation capabilities.

---

### `AI_PLATFORM`

For roles primarily focused on the infrastructure and engineering systems required to run AI/ML.

Use this family when the role is substantially about:

* MLOps
* ML infrastructure
* AI platforms
* Model deployment
* Model serving
* GPU infrastructure
* AI compute
* Cloud AI infrastructure
* Kubernetes for ML
* CI/CD for ML
* Data/ML pipelines
* AI platform engineering
* Model monitoring
* AI systems infrastructure
* AI DevOps
* AI reliability
* Production ML systems

Typical titles:

* ML Platform Engineer
* MLOps Engineer
* AI Platform Engineer
* AI Infrastructure Engineer
* ML Infrastructure Engineer
* AI Computing Engineer
* GPU Programmer
* Cloud & AI Infrastructure Engineer
* DevOps Engineer — AI
* Senior ML Engineer — MLOps
* AI Platform Lead
* AI Infrastructure Lead

Core positioning:

> AI/ML engineer focused on production systems, infrastructure, deployment, MLOps and scalable AI platforms.

---

### `AI_PRODUCT_FDE`

For roles where the engineer is expected to work directly with businesses/customers/users to discover problems and build AI solutions.

This family is particularly important because it aligns with my desired career direction.

Use this family for:

* Forward Deployed Engineer
* Forward Deployed AI Engineer
* AI Solutions Engineer
* AI Solution Engineer
* Applied AI Engineer where customer/problem discovery is significant
* AI Consultant Engineer
* Technical AI Consultant
* AI implementation roles
* AI solution architecture when implementation-oriented
* Enterprise AI engineering
* AI transformation engineering
* AI business solutions engineering
* AI engineer embedded with customers/business teams

Signals:

* Customer-facing engineering
* Client problem discovery
* Requirements gathering
* Business problem → technical solution
* Prototyping
* Deploying AI solutions
* Working with startups/SMEs/enterprise customers
* Solution architecture
* Consulting + engineering
* Cross-functional collaboration
* Rapid experimentation
* Production implementation

Typical titles:

* Forward Deployed Engineer
* Senior Forward Deployed Engineer
* Forward Deployed AI Engineer
* AI Solutions Engineer
* AI Solution Engineer
* AI Technical Solution Specialist
* AI Transformation Engineer
* AI Consultant
* Applied AI Engineer
* Enterprise AI Engineer

Core positioning:

> Forward-deployed / applied AI engineer who translates real-world business problems into deployable AI solutions.

IMPORTANT:

Do NOT classify every "AI Engineer" role into this family.

There must be evidence that the role involves business-facing problem solving, solution delivery, customer interaction, consulting, implementation or product/business integration.

---

### `AI_AUTOMATION_PM`

For roles primarily focused on AI automation, business transformation, AI operations, product/project management, or AI enablement rather than hands-on model engineering.

Use for:

* AI Project Manager
* AI Product Manager
* AI Product Owner
* AI Transformation
* AI Strategy
* AI Business Partner
* AI Enablement
* AI Automation Specialist
* Process automation
* Business transformation
* AI operations
* AI program management
* AI implementation management
* AI consulting where the role is primarily business/management rather than engineering

Typical titles:

* AI Project Manager
* AI Product Manager
* AI Product Owner
* AI Transformation Partner
* AI Strategy & Transformation Consultant
* AI Automation Specialist
* AI Enablement Partner
* Business AI Transformation Specialist
* AI Operations Automation Specialist

Core positioning:

> AI/business transformation professional who connects technology, automation and organizational problems.

---

# 3. Important Classification Principle

Classify based on the **actual responsibilities**, NOT simply the job title.

For example:

"AI Engineer"

could become:

* `AI_GENAI`
* `ML_DATA`
* `AI_PLATFORM`
* `AI_PRODUCT_FDE`

depending on the job description.

Do NOT assume:

```
AI Engineer = AI_GENAI
```

Instead determine:

> What will this person actually spend most of their time doing?

---

# 4. Priority Decision Tree

Use the following decision logic.

## Step 1 — Is the role primarily management/business/strategy?

If YES:

* AI Product
* AI Project Management
* AI Transformation
* AI Strategy
* AI Enablement
* AI Business Partner
* AI Automation management

→ `AI_AUTOMATION_PM`

Unless the role is clearly hands-on engineering.

---

## Step 2 — Is the role primarily infrastructure/platform/MLOps?

Look for:

* MLOps
* Kubernetes
* Docker
* CI/CD
* model deployment
* model serving
* GPU infrastructure
* cloud infrastructure
* ML pipelines
* model monitoring
* AI platform
* infrastructure automation

→ `AI_PLATFORM`

---

## Step 3 — Is it customer/business-facing solution engineering?

Look for:

* Forward Deployed
* customer-facing
* client-facing
* solution engineering
* business problem discovery
* consulting
* implementation
* AI solutions
* enterprise solutions
* prototype → deployment
* technical consulting

→ `AI_PRODUCT_FDE`

---

## Step 4 — Is the core technology GenAI/LLM/Agents?

Look for:

* LLM
* RAG
* AI agents
* Agentic AI
* multi-agent
* LangChain
* LangGraph
* MCP
* OpenAI APIs
* Claude
* Gemini
* vector databases
* embeddings
* prompt engineering
* LLM evaluation
* conversational AI

→ `AI_GENAI`

---

## Step 5 — Is it primarily ML/data/model development?

Look for:

* machine learning
* deep learning
* computer vision
* image segmentation
* object detection
* recommendation
* search
* ranking
* predictive modelling
* statistical modelling
* feature engineering
* model training
* experimentation
* PyTorch
* TensorFlow
* scikit-learn

→ `ML_DATA`

---

# 5. Computer Vision Rule

Computer Vision requires additional reasoning.

Do NOT automatically create a separate `VISION_CV` resume family.

Instead:

### Computer Vision Research / Model Development

Examples:

* Computer Vision Researcher
* Computer Vision Engineer
* Vision AI Specialist
* Motion AI Specialist
* AI Engineer — Computer Vision
* Robotics AI Research Engineer

→ `ML_DATA`

### Computer Vision + GenAI

If the role involves:

* multimodal LLMs
* vision-language models
* VLMs
* visual agents
* image understanding using LLMs

and the role is primarily GenAI:

→ `AI_GENAI`

### Computer Vision + Industrial AI / Edge

If the role is primarily:

* edge AI
* deployment
* AIoT
* GPU systems
* inference optimization
* production infrastructure

→ potentially `AI_PLATFORM`

### Computer Vision + Customer Solutions

If the role involves deploying computer vision solutions for customers/businesses:

→ `AI_PRODUCT_FDE`

---

# 6. Secondary Tags

Every job should also receive secondary tags.

Examples:

```text
LLM
RAG
AI_AGENTS
GENAI
COMPUTER_VISION
NLP
MACHINE_LEARNING
DEEP_LEARNING
MLOPS
AI_INFRASTRUCTURE
CLOUD
PYTHON
DATA_SCIENCE
RECOMMENDATION
SEARCH
ROBOTICS
AI_AUTOMATION
AI_PRODUCT
FDE
CUSTOMER_FACING
BUSINESS_SOLUTIONS
AI_TRANSFORMATION
```

Multiple tags are allowed.

---

# 7. Seniority Classification

Normalize job seniority into:

```text
INTERN
GRADUATE
JUNIOR
MID
MID_SENIOR
SENIOR
STAFF
LEAD
MANAGER
DIRECTOR
UNKNOWN
```

Do not let seniority determine the resume family.

For example:

```
Senior AI Engineer
```

could still be:

```text
AI_GENAI
```

or:

```text
ML_DATA
```

depending on responsibilities.

---

# 8. Job Suitability

The agent should also assess whether the job is suitable for my current career direction.

Use:

```text
STRONG
GOOD
STRETCH
WEAK
VETO
```

### STRONG

The role closely aligns with:

* Applied AI
* GenAI
* AI engineering
* ML
* Computer Vision
* FDE
* AI solutions
* AI product engineering

and is realistically achievable based on my current profile.

### GOOD

Relevant role but may require some additional skills.

### STRETCH

Interesting role but significant requirements exceed my current experience.

### WEAK

Technically adjacent but not strategically aligned.

### VETO

Do not spend application effort unless there is an exceptional reason.

Examples:

* Civil engineering
* Accounting
* Legal
* Manufacturing roles unrelated to AI
* Generic administrative roles
* Pure sales roles
* Roles requiring extensive experience far beyond my current level
* Completely unrelated engineering roles

---

# 9. Seniority Mismatch Detection

The agent must distinguish between:

### Target

Roles where my profile is realistically competitive.

### Stretch

Roles where the technology aligns but seniority is significantly above my current level.

Example:

```
Staff Machine Learning Engineer
```

could be:

```text
resume_family = ML_DATA
suitability = STRETCH
```

It should NOT become a different resume family simply because it is Staff level.

---

# 10. Resume Strategy

The purpose of classification is to create a limited number of high-quality resumes.

Initial target:

```text
Resume 1 → AI_GENAI → `Sai_Teja_Applied AI & Gen AI.pdf`
Resume 2 → ML_DATA → `Sai_Teja_ML_Data.pdf`
Resume 3 → AI_PLATFORM → `Sai_Teja_AI_Platform.pdf`
Resume 4 → AI_PRODUCT_FDE → `Sai_Teja_Applied AI & AI Product Engineer.pdf`
Resume 5 → AI_AUTOMATION_PM → `Sai_Teja_AI Automation & Technical Project Engineer.pdf`
```

Do NOT create additional resumes unless there is strong evidence that an existing family cannot serve the role.

For example:

Do NOT immediately create:

```text
VISION_CV
ROBOTICS_AI
FINTECH_AI
NLP_AI
RECOMMENDATION_AI
```

These should initially be handled using:

```text
ML_DATA
```

with appropriate project/skill customization.

Similarly:

```text
LLM
RAG
Agents
GenAI
NLP
Conversational AI
```

should initially be handled through:

```text
AI_GENAI
```

---

# 11. Resume Customization

After assigning the resume family, the agent should recommend which parts of the master resume need customization.

Return:

```text
resume_family
recommended_summary
priority_skills
priority_projects
priority_experience
keywords_to_add
keywords_to_deemphasize
potential_missing_skills
```

Example:

```text
resume_family:
AI_GENAI

priority_skills:
- Python
- LLM
- RAG
- AI Agents
- LangGraph
- APIs
- Vector Databases

priority_projects:
- AI Agent Blueprint
- Prompt Architect
- AI chatbot/application projects

keywords_to_add:
- Agentic AI
- LLM orchestration
- RAG
- tool calling

keywords_to_deemphasize:
- GIS
- traditional remote sensing
```

---

# 12. My Career Direction

The classification system should understand that my strategic target is:

> Applied AI / Generative AI / AI Engineering, with a longer-term interest in Forward Deployed AI Engineering.

I want to become an engineer who can:

1. Understand a real-world business problem.
2. Investigate the underlying workflow.
3. Identify where AI can create value.
4. Design an AI solution.
5. Build the prototype.
6. Integrate models/APIs/tools.
7. Deploy the solution.
8. Measure the outcome.
9. Iterate with the customer/business.
10. Eventually own the complete AI solution lifecycle.

Therefore, prioritize opportunities that develop:

* AI engineering
* GenAI
* AI agents
* ML
* software engineering
* system design
* APIs
* data
* cloud
* deployment
* customer/problem discovery
* solution architecture
* product thinking

---

# 13. Important Personal Positioning

My resume system should not position me as only:

> "a Computer Vision person"

or:

> "a Data Scientist"

or:

> "a Prompt Engineer."

My broader positioning is:

> Applied AI Engineer capable of combining software engineering, machine learning, generative AI and real-world problem solving.

Computer Vision and Remote Sensing are valuable parts of my technical background, but they should not unnecessarily restrict my career positioning.

---

# 14. Airtable Output Schema

For each job, produce/update the following fields:

```text
job_title
company
resume_family
secondary_tags
seniority
industry
job_type
location
remote_status
suitability
match_score
technical_focus
business_focus
customer_facing
primary_technologies
required_experience
key_requirements
resume_customization
priority_projects
priority_skills
missing_skills
red_flags
veto_reason
classification_reason
```

---

# 15. Match Score

Calculate a rough 0–100 score.

Suggested weighting:

```text
Career alignment          25%
Technical skill match     25%
Experience/seniority      20%
Project relevance         15%
Business/domain fit       10%
Location/work arrangement  5%
```

The score is advisory, not absolute.

Do not reject a role purely because of one missing technology.

---

# 16. Classification Examples

### Example 1

```text
Applied AI Engineer — AI Neobank
```

If responsibilities include:

* LLM applications
* AI agents
* RAG
* Python
* APIs
* financial workflows

→

```text
resume_family = AI_GENAI
```

---

### Example 2

```text
ML Engineer / AI Engineer — Infrastructure
```

Responsibilities:

* Kubernetes
* GPU
* deployment
* model serving
* ML pipelines

→

```text
resume_family = AI_PLATFORM
```

---

### Example 3

```text
Forward Deployed AI Engineer
```

Responsibilities:

* customer discovery
* prototype AI solutions
* deploy systems
* work with clients

→

```text
resume_family = AI_PRODUCT_FDE
```

---

### Example 4

```text
Computer Vision AI Engineer
```

Responsibilities:

* object detection
* segmentation
* PyTorch
* model training
* computer vision research

→

```text
resume_family = ML_DATA
```

---

### Example 5

```text
AI Project Manager
```

Responsibilities:

* AI roadmap
* stakeholder management
* project delivery
* AI transformation

→

```text
resume_family = AI_AUTOMATION_PM
```

---

### Example 6

```text
AI Engineer — RAG / Multi-Agent
```

Responsibilities:

* LangGraph
* RAG
* vector database
* tool calling
* agents

→

```text
resume_family = AI_GENAI
```

---

### Example 7

```text
AI Engineer — Business Systems & Automation
```

If responsibilities are primarily:

* internal workflow automation
* AI integrations
* business process automation
* Python
* APIs
* LLM integrations

→

```text
resume_family = AI_PRODUCT_FDE
```

If instead the role is primarily:

* workflow automation
* process improvement
* stakeholder management
* low-code tools
* business transformation

→

```text
resume_family = AI_AUTOMATION_PM
```

---

# 17. Duplicate Job Handling

The job dataset may contain duplicate postings.

The agent should detect duplicates based on:

* company
* normalized job title
* location
* job description
* URL
* job ID

Do not create separate classification decisions for obvious duplicates.

Instead mark:

```text
duplicate = TRUE
duplicate_of = <record>
```

---

# 18. Confidence

Every classification should include:

```text
classification_confidence
```

Use:

```text
HIGH
MEDIUM
LOW
```

Use LOW when:

* job description is missing
* title is ambiguous
* only a short LinkedIn snippet exists
* responsibilities are unclear

When confidence is LOW, do not invent information.

---

# 19. Output Format

For each job, return a compact structured record:

```json
{
  "job_title": "",
  "company": "",
  "resume_family": "",
  "secondary_tags": [],
  "seniority": "",
  "industry": "",
  "suitability": "",
  "match_score": 0,
  "technical_focus": [],
  "customer_facing": false,
  "primary_technologies": [],
  "priority_skills": [],
  "priority_projects": [],
  "missing_skills": [],
  "red_flags": [],
  "classification_reason": "",
  "classification_confidence": ""
}
```

---

# 20. Most Important Rule

Do not optimize for having many resume variants.

Optimize for:

> **A small number of strong resume families that can cover the majority of strategically relevant AI jobs.**

The current target is:

```text
                    JOB
                     │
        ┌────────────┼────────────┐
        │            │            │
     Engineering   Business    Infrastructure
        │            │            │
   ┌────┼────┐       │            │
   │    │    │        │            │
 GenAI ML/FDE  PM   Platform
   │    │    │        │            │
   ▼    ▼    ▼        ▼            ▼

AI_GENAI
ML_DATA
AI_PRODUCT_FDE
AI_AUTOMATION_PM
AI_PLATFORM
```

The system should continuously learn from the job dataset, but it should NOT create new resume families unless a recurring cluster of jobs clearly cannot be represented well by the existing five families.
