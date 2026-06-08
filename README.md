# SupportOps AI — RAG-Based IT Self-Service Assistant

SupportOps AI is a web-based IT support assistant that helps employees solve common IT, DevOps, cloud, web/API, authentication, and workplace technology issues using Retrieval-Augmented Generation (RAG) with AWS Bedrock Agent and a company Knowledge Base.

The system also includes an analytics dashboard that measures how many employee support requests were handled, how many were solved without IT, how many were escalated, estimated IT time saved, recurring categories, and Knowledge Base gaps.

---

## 1. Project Goal

Many organizations receive repeated IT support requests for issues such as:

- Account lockouts
- MFA problems
- VPN/network problems
- Microsoft 365 issues
- Docker/DevOps errors
- API errors
- Database and cloud infrastructure issues
- Security warnings
- CI/CD and Git problems

The goal of this project is to reduce unnecessary IT workload by allowing employees to safely resolve common issues using verified internal documentation.

When the issue is too sensitive or critical for self-service, the system automatically escalates the issue to IT using an AWS Bedrock Agent Tool connected to AWS Lambda and Resend email.

---

## 2. Main Features

### Employee Chat Assistant

Employees can ask questions such as:

```txt
My API is returning 401. What should I check?
```

The assistant searches the Knowledge Base and returns safe self-service steps.

### Automatic IT Escalation

For critical issues such as:

```txt
My account is locked and MFA does not work newEmploy@proton.me
```

The Agent calls the `contactIT` tool, which triggers an AWS Lambda function that sends an email to IT through Resend.

### Support Analytics

The system tracks:

- Total support requests
- Requests solved without IT
- Requests escalated to IT
- Diagnostics-required cases
- Estimated IT time saved
- Top recurring categories
- Knowledge Base gaps

Dashboard URL:

```txt
http://<EC2_PUBLIC_IP>:5000/analytics
```

### Knowledge Gap Detection

When the uploaded documents do not contain enough information, the Agent calls a Knowledge Gap tool. This creates a record that helps identify missing documentation and future improvements for the Knowledge Base.

---

## 3. System Architecture

```txt
User
 ↓
Flask Web App /api/chat
 ↓
agent_service.py
 ↓
AWS Bedrock Agent
 ↓
AWS Bedrock Knowledge Base
 ↓
Agent decides response / tool usage
 ↓
Action Group Function
 ↓
AWS Lambda
 ↓
Flask Internal API
 ↓
SQLite database
 ↓
Analytics Dashboard
```

### Important Design Rule

All tool actions are executed through:

```txt
Bedrock Agent → Action Group Function → AWS Lambda
```

Flask does not execute tools directly.

Flask is responsible for:

- Serving the web UI
- Calling the Bedrock Agent
- Providing secured internal APIs for Lambda callbacks
- Displaying the analytics dashboard
- Storing chat history and analytics in SQLite

---

## 4. Technologies Used

| Technology | Usage |
|---|---|
| Python | Backend application and Lambda functions |
| Flask | Web server, chat API, upload API, internal API, and analytics dashboard |
| AWS Bedrock Agent | Main AI agent and tool orchestration |
| AWS Bedrock Knowledge Base | RAG retrieval from uploaded support documents |
| AWS Lambda | Tool execution for email escalation and analytics actions |
| Resend API | Sending IT escalation emails |
| SQLite | Local application database for chat history and analytics |
| Docker | Containerizing the Flask application |
| Docker Compose | Running the application with volumes and environment variables |
| AWS EC2 | Hosting the Dockerized Flask application |
| AWS S3 | Document storage for Knowledge Base ingestion |
| Chart.js | Dashboard charts |
| Git / GitHub | Version control |

---

## 5. Project Structure

Example structure:

```txt
aws-rag-app/
├── app.py
├── agent_service.py
├── analytics_dashboard_service.py
├── bedrock_sync.py
├── config.py
├── database.py
├── rag_service.py
├── s3_service.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── docker-compose.prod.yml
├── templates/
│   ├── index.html
│   └── analytics.html
├── uploads/
├── database/
│   └── chat_history.db
└── data/
    └── analytics_policy.txt
```

---

## 6. Main Components

### app.py

Contains Flask routes such as:

```txt
/
 /api/chat
 /api/upload
 /api/debug/retrieve
 /analytics
 /api/analytics/summary
 /api/analytics/categories
 /api/analytics/interactions
 /api/analytics/knowledge-gaps
 /api/internal/tools/log-support-interaction
 /api/internal/tools/detect-knowledge-gap
 /api/internal/tools/generate-support-analytics
```

### agent_service.py

Responsible for invoking AWS Bedrock Agent.

It sends the user question, session ID, and recent chat history to the Agent.

The Agent decides whether to:

- Search the Knowledge Base
- Return self-service steps
- Call `contactIT`
- Call `logSupportInteraction`
- Call `generateSupportAnalytics`
- Call `detectKnowledgeGap`

### database.py

Manages SQLite tables:

```txt
sessions
messages
escalation_events
support_interactions
knowledge_gaps
```

### analytics_dashboard_service.py

Reads analytics data from SQLite and prepares JSON for the dashboard.

### templates/analytics.html

Displays:

- Total Requests
- Solved Without IT
- Escalated To IT
- Diagnostics Required
- Self-Service Rate
- IT Hours Saved
- Resolution chart
- Category chart
- Latest interactions
- Knowledge gaps

---

## 7. AWS Bedrock Agent Tools

The system uses separate Action Groups and separate Lambda functions.

### Existing Tool: contactIT

```txt
Action Group: ITSupportActions
Function: contactIT
Lambda: existing email escalation Lambda
```

Purpose:

- Sends an automatic email to IT through Resend.
- Used only for issues that require human IT intervention.

Example trigger:

```txt
My account is locked and MFA does not work newEmploy@proton.me
```

### Tool 1: logSupportInteraction

```txt
Action Group: SupportLoggingActions
Function: logSupportInteraction
Lambda: SupportLoggingActions-jud8f
```

Purpose:

- Logs every real support interaction.
- Saves category, resolution type, escalation status, tool used, and estimated minutes saved.

Important parameter:

```txt
interactionData
```

The `interactionData` parameter is a JSON string containing:

```json
{
  "sessionId": "current session id",
  "userQuestion": "current user question",
  "assistantAnswer": "short summary",
  "category": "support category",
  "resolutionType": "SELF_SERVICE",
  "escalatedToIT": "false",
  "toolUsed": "none",
  "estimatedMinutesSaved": "10",
  "employeeEmail": "unknown"
}
```

### Tool 2: generateSupportAnalytics

```txt
Action Group: SupportAnalyticsActions
Function: generateSupportAnalytics
Lambda: SupportAnalyticsActions-v4knu
```

Purpose:

- Generates analytics from the existing SQLite database through the secured Flask internal API.

Parameter:

```txt
days
```

Example user question:

```txt
Show me support analytics for the last 7 days
```

### Tool 3: detectKnowledgeGap

```txt
Action Group: SupportKnowledgeGapActions
Function: detectKnowledgeGap
Lambda: SupportKnowledgeGapActions-r3v1v
```

Purpose:

- Records missing or weak Knowledge Base coverage.
- Helps improve future documentation.

Parameters:

```txt
question
category
reason
suggestedArticleTitle
```

---

## 8. Lambda Callback Flow

The analytics Lambdas call Flask secured internal endpoints.

Example:

```txt
Lambda
 ↓
POST http://<EC2_PUBLIC_IP>:5000/api/internal/tools/log-support-interaction
 ↓
Header: X-Internal-Tool-Key
 ↓
Flask validates the key
 ↓
SQLite record is saved
```

This allows the project to keep using the existing SQLite database while still ensuring all tools are executed through AWS Bedrock Agent Action Groups and Lambda.

---

## 9. Environment Variables

### Flask / Docker `.env`

Create a `.env` file on the server:

```env
APP_VERSION=1.0.5

SECRET_KEY=change-me

AWS_REGION=us-east-2

S3_BUCKET_NAME=your-s3-bucket
BEDROCK_KNOWLEDGE_BASE_ID=your-knowledge-base-id
BEDROCK_DATA_SOURCE_ID=your-data-source-id

BEDROCK_AGENT_ID=your-agent-id
BEDROCK_AGENT_ALIAS_ID=your-agent-alias-id

INTERNAL_TOOL_API_KEY=your-long-secret-key
```

### Lambda Environment Variables

For analytics Lambdas:

```env
APP_BASE_URL=http://<EC2_PUBLIC_IP>:5000
INTERNAL_TOOL_API_KEY=your-long-secret-key
```

For contactIT Lambda:

```env
RESEND_API_KEY=re_xxxxxxxxx
RESEND_FROM_EMAIL=SupportOps AI <onboarding@resend.dev>
IT_SUPPORT_EMAIL=your-it-email@example.com
```

---

## 10. Docker Compose Production File

`docker-compose.prod.yml`:

```yaml
services:
  rag-app:
    image: yovelz/aws_webapp-rag-app:${APP_VERSION}
    container_name: rag_app
    ports:
      - "5000:5000"
    env_file:
      - .env
    volumes:
      - ./uploads:/app/uploads
      - ./database:/app/database
    command: gunicorn -b 0.0.0.0:5000 --worker-class gthread --workers 2 --threads 4 --timeout 180 app:app
    restart: unless-stopped
```

### Why gthread workers are required

The application calls Bedrock Agent from `/api/chat`.

The Agent may trigger a Lambda.

The Lambda calls back into Flask internal APIs.

If Gunicorn has only one synchronous worker, the internal callback can get blocked while `/api/chat` is waiting for Bedrock.

Using threaded Gunicorn workers prevents this deadlock.

---

## 11. Local Development

### Build and run locally

```bash
docker compose down --remove-orphans
docker compose build --no-cache
docker compose up -d --force-recreate
docker logs -f rag_app
```

Open:

```txt
http://localhost:5000
```

Dashboard:

```txt
http://localhost:5000/analytics
```

---

## 12. EC2 Deployment

### On local machine

Build and push image:

```bash
docker build -t yovelz/aws_webapp-rag-app:1.0.5 .
docker push yovelz/aws_webapp-rag-app:1.0.5
```

### On EC2

Create project folder:

```bash
mkdir -p ~/aws-rag-app
cd ~/aws-rag-app
```

Create `.env` and `docker-compose.prod.yml`.

Pull and run:

```bash
docker compose -f docker-compose.prod.yml pull
docker compose -f docker-compose.prod.yml up -d --force-recreate
docker logs -f rag_app
```

Open:

```txt
http://<EC2_PUBLIC_IP>:5000
http://<EC2_PUBLIC_IP>:5000/analytics
```

---

## 13. AWS Security Group

For demo use, EC2 must allow inbound traffic:

```txt
Port: 5000
Source: your IP or 0.0.0.0/0 for demo only
```

For production, use HTTPS, a domain, and a restricted network/security configuration.

---

## 14. Internal API Tests

### Test support interaction logging

```bash
curl -X POST "http://localhost:5000/api/internal/tools/log-support-interaction" \
  -H "Content-Type: application/json" \
  -H "X-Internal-Tool-Key: your-long-secret-key" \
  -d '{
    "sessionId": "test-session",
    "userQuestion": "My computer is slow",
    "assistantAnswer": "Restart the computer and close unused apps.",
    "category": "IT Helpdesk / Endpoint Support",
    "resolutionType": "SELF_SERVICE",
    "escalatedToIT": "false",
    "toolUsed": "none",
    "estimatedMinutesSaved": "10",
    "employeeEmail": "unknown"
  }'
```

### Test analytics API

```bash
curl "http://localhost:5000/api/analytics/summary?days=7"
curl "http://localhost:5000/api/analytics/interactions?limit=20"
curl "http://localhost:5000/api/analytics/knowledge-gaps?limit=20"
```

---

## 15. End-to-End Demo Questions

### Self-service

```txt
My API is returning 401. What should I check?
```

Expected:

- Agent searches Knowledge Base.
- Agent returns safe self-service steps.
- Agent calls `logSupportInteraction`.
- Dashboard updates.

### Analytics

```txt
Show me support analytics for the last 7 days
```

Expected:

- Agent calls `generateSupportAnalytics`.
- Agent returns analytics report.

### Knowledge Gap

```txt
How do I fix the office coffee machine using Kubernetes?
```

Expected:

- Agent calls `detectKnowledgeGap`.
- Agent calls `logSupportInteraction`.
- Dashboard shows a Knowledge Gap.

### Escalation

```txt
My account is locked and MFA does not work newEmploy@proton.me
```

Expected:

- Agent calls `contactIT`.
- Email is sent to IT.
- Agent calls `logSupportInteraction`.
- Dashboard shows an escalated request.

---

## 16. Troubleshooting

### Agent does not use tools

Check:

```txt
Bedrock Agent → Action Groups
Save
Prepare Agent
Alias points to latest version
BEDROCK_AGENT_ALIAS_ID in container is correct
```

### Lambda works manually but not from app

Check:

```txt
Agent Alias
Action Group function names
CloudWatch logs
```

### Lambda callback times out

Check:

```txt
EC2 Security Group port 5000
APP_BASE_URL
INTERNAL_TOOL_API_KEY
Gunicorn gthread workers
Lambda timeout 30 seconds
```

### Dashboard does not update

Check:

```txt
/api/analytics/interactions?limit=20
CloudWatch logs for SupportLoggingActions Lambda
SQLite database volume
```

### Reset analytics data before demo

```bash
docker exec -i rag_app python - <<'PY'
import sqlite3

conn = sqlite3.connect("/app/database/chat_history.db")
cur = conn.cursor()

cur.execute("DELETE FROM support_interactions")
cur.execute("DELETE FROM knowledge_gaps")

conn.commit()
conn.close()

print("Analytics data reset successfully.")
PY
```

---

## 17. Current Status

Working features:

- Flask chat application
- AWS Bedrock Agent integration
- AWS Knowledge Base RAG retrieval
- File upload and Knowledge Base sync
- Lambda-based IT escalation email
- Lambda-based support interaction logging
- Lambda-based analytics generation
- Lambda-based Knowledge Gap detection
- SQLite-backed dashboard
- Dockerized deployment on EC2

---

## 18. Suggested Improvements

Future improvements:

- Use HTTPS and a domain instead of raw EC2 IP
- Move analytics storage from SQLite to DynamoDB or PostgreSQL
- Add user authentication for the dashboard
- Add CSV export for analytics
- Add better category normalization
- Add admin panel to review Knowledge Gaps
- Add ticketing integration such as Jira, ServiceNow, or Slack