# SupportOps AI — Internal IT Self-Service RAG Assistant

## 1. Project Overview

**SupportOps AI** is an internal AI-powered technical support assistant designed to help company employees solve common IT, Helpdesk, DevOps, cloud, networking, and application issues by themselves before contacting the IT team.

The project uses a **RAG architecture** — Retrieval-Augmented Generation — which means the assistant does not answer freely from general AI knowledge. Instead, it searches approved internal support documents and generates an answer based on the relevant company knowledge base content.

The main goal of the project is to reduce unnecessary calls, messages, and support tickets to the IT team by allowing employees to perform safe self-service troubleshooting first.

The system helps employees understand:

- What the problem probably is.
- What they are allowed to check by themselves.
- What they should not do.
- When the issue must be escalated to IT or DevOps.
- What information they should send to IT if escalation is required.

This project is not meant to fully replace IT employees.  
It is designed to act as a **first support layer** that reduces repetitive work and helps the IT team focus on more complex, urgent, and high-risk issues.

---

## 2. Business Problem

In many companies, employees contact IT for the same repeated problems:

- Password reset or locked account.
- MFA not working.
- VPN connection problems.
- Slow computer.
- Outlook or Teams issues.
- Network problems.
- Printer problems.
- Git or CI/CD errors.
- Docker or cloud service issues.
- Application errors such as 500, 502, SSL, or database connection failures.

Many of these issues can be partially solved by employees if they receive clear and safe instructions.

However, employees usually do not know:

- Which checks are safe.
- Which actions are dangerous.
- When they must stop and contact IT.
- What information IT needs in order to handle the issue quickly.

This creates unnecessary workload for IT and slows down business activity.

---

## 3. Project Goal

The goal of this project is to build an AI assistant that helps employees solve common issues independently while keeping company systems safe.

The assistant reduces IT workload by:

1. Answering common support questions automatically.
2. Giving safe self-service troubleshooting steps.
3. Preventing users from performing dangerous actions.
4. Explaining clearly when IT must be contacted.
5. Preparing structured issue details for IT escalation.
6. Using company-approved documents as the source of truth.
7. Saving chat history so the assistant can understand follow-up questions.
8. Supporting future integration with Tools and MCP for automatic actions.

Example future automation:

```text
Employee asks a question
        |
Assistant finds the relevant document
        |
Assistant detects that IT is required
        |
System triggers an automatic action
        |
Email or ticket is sent to IT
```

---

## 4. Main Project Topic

The topic of the project is:

> **AI-based internal IT self-service assistant for reducing IT workload and improving employee support efficiency.**

The assistant is focused on helping employees with common technical problems while escalating unsafe or critical cases to IT.

The project demonstrates how a company can use AI, AWS Bedrock, S3, and a structured knowledge base to create a practical internal support system.

---

## 5. How the Application Works

The application works as a web-based RAG chatbot.

### General Flow

```text
Employee
   |
   v
Web Chat UI
   |
   v
Flask Backend
   |
   v
AWS Bedrock Knowledge Base
   |
   v
Relevant support document chunks
   |
   v
AI-generated answer based only on retrieved documents
   |
   v
Response returned to employee
```

### Detailed Flow

1. The user opens the web application in the browser.
2. The user asks a technical support question.
3. The frontend sends the question to the Flask backend endpoint:

```text
POST /api/chat
```

4. The backend loads recent chat history from SQLite.
5. The current question and relevant history are passed to the RAG service.
6. The RAG service sends the question to AWS Bedrock Knowledge Base.
7. Bedrock retrieves the most relevant chunks from the uploaded documents.
8. The Bedrock model generates an answer using only the retrieved results.
9. The backend saves the user question and assistant answer in SQLite.
10. The answer is returned to the frontend and displayed to the employee.

---

## 6. RAG Architecture

RAG stands for:

```text
Retrieval-Augmented Generation
```

In this project, RAG is used to make the assistant answer from internal company support documents instead of relying on general model knowledge.

### Why RAG is useful here

RAG is useful because the assistant must follow the company’s approved troubleshooting rules.

For example:

- If employees are allowed to restart Outlook, the assistant can suggest it.
- If employees must not change DNS settings, the assistant should warn them.
- If database or production issues must go to DevOps, the assistant should not provide dangerous commands.
- If the document says IT must be contacted, the assistant should clearly escalate.

This makes the assistant safer and more aligned with company procedures.

---

## 7. High-Level Architecture

```text
+-------------------+
|   Employee User   |
+---------+---------+
          |
          v
+-------------------+
|   Web Interface   |
| HTML / CSS / JS   |
+---------+---------+
          |
          v
+-------------------+
|   Flask Backend   |
| Python / Gunicorn |
+---------+---------+
          |
          +-----------------------------+
          |                             |
          v                             v
+-------------------+         +----------------------+
|   SQLite DB       |         | AWS Bedrock Runtime  |
| Chat History      |         | RAG Question Answer  |
+-------------------+         +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Bedrock Knowledge    |
                              | Base                 |
                              +----------+-----------+
                                         |
                                         v
                              +----------------------+
                              | Amazon S3 Documents |
                              +----------------------+
```

---

## 8. Main AWS Architecture

```text
Local / EC2 Docker Container
        |
        v
Flask Application
        |
        |-- Upload document
        |       |
        |       v
        |   Amazon S3 Bucket
        |       |
        |       v
        |   Bedrock Knowledge Base Sync
        |
        |-- Ask question
                |
                v
            Bedrock Knowledge Base
                |
                v
            Bedrock Model
                |
                v
            Answer returned to Flask
```

---

## 9. Main Technologies Used

### Backend

- Python 3.11
- Flask
- Gunicorn
- boto3
- python-dotenv

### AI / RAG

- Amazon Bedrock
- Amazon Bedrock Knowledge Base
- Bedrock Agent Runtime
- Bedrock ingestion jobs

### Storage

- Amazon S3 for uploaded support documents.
- SQLite for local chat history.

### Deployment

- Docker
- Docker Compose
- AWS EC2 for hosting during development/demo.

### Frontend

- HTML
- CSS
- JavaScript
- Flask templates.

---

## 10. Main Application Files

### `app.py`

The main Flask application.

Responsible for:

- Starting the Flask web server.
- Serving the frontend page.
- Receiving user chat messages.
- Sending questions to the RAG service.
- Saving chat history.
- Handling new chat sessions.
- Uploading documents.
- Triggering Bedrock Knowledge Base sync.
- Providing a debug retrieval endpoint.

Important routes:

```text
GET  /
POST /api/chat
GET  /api/history
POST /api/new_session
POST /api/upload
POST /api/debug/retrieve
```

---

### `rag_service.py`

Responsible for communication with AWS Bedrock Knowledge Base.

Main responsibilities:

- Building a retrieval query.
- Sending user questions to Bedrock.
- Retrieving relevant document chunks.
- Generating answers based only on uploaded documents.
- Supporting follow-up questions using recent conversation history.
- Providing a debug function for retrieval testing.

The assistant is instructed to avoid guessing and to answer only from the uploaded documents.

---

### `s3_service.py`

Responsible for uploading files to Amazon S3.

When the user uploads a document, the file is uploaded into the configured S3 bucket.

The application uploads documents under:

```text
data/<filename>
```

Example:

```text
s3://your-bucket-name/data/01_it_helpdesk_endpoints.txt
```

---

### `bedrock_sync.py`

Responsible for triggering a Bedrock Knowledge Base ingestion job.

After a document is uploaded to S3, this file starts a sync operation so Bedrock can index the new content.

---

### `database.py`

Responsible for SQLite database operations.

Stores:

- Chat sessions.
- User messages.
- Assistant messages.
- Timestamps.

Database file location:

```text
database/chat_history.db
```

---

### `config.py`

Responsible for loading environment variables from `.env`.

Important configuration values:

- `SECRET_KEY`
- `AWS_REGION`
- `S3_BUCKET_NAME`
- `BEDROCK_KNOWLEDGE_BASE_ID`
- `BEDROCK_DATA_SOURCE_ID`
- `BEDROCK_MODEL_ARN`

---

### `docker-compose.yml`

Used to run the application as a Docker service.

Current service name:

```text
rag-app
```

Current container name:

```text
rag_app
```

Application port:

```text
5000:5000
```

The compose file also mounts local folders:

```text
./uploads:/app/uploads
./database:/app/database
```

This allows uploaded files and SQLite data to persist outside the container.

---

### `Dockerfile`

Builds the Python Flask application image.

Main behavior:

- Uses `python:3.11-slim`.
- Sets `/app` as the working directory.
- Installs Python dependencies from `requirements.txt`.
- Copies project files into the image.
- Creates `/app/uploads` and `/app/database`.
- Exposes port `5000`.
- Starts the application using Gunicorn.

---

## 11. Knowledge Base Documents Used

The project uses multiple structured text documents as the company support knowledge base.

These files are uploaded to S3 and synced into AWS Bedrock Knowledge Base.

---

### 11.1 IT Helpdesk and Endpoint Support

File:

```text
01_it_helpdesk_endpoints.txt
```

Purpose:

General employee IT helpdesk and endpoint support.

Includes issues such as:

- Password reset.
- Locked account.
- Windows computer running slowly.
- Windows update failure.
- Endpoint support problems.
- Basic safe checks employees can perform.
- Cases where IT must unlock, reset, or investigate the account/device.

---

### 11.2 Networking, VPN, DNS, Shared Folders, and Printers

File:

```text
02_networking_vpn_dns_printers.txt
```

Purpose:

Support knowledge for network-related employee issues.

Includes issues such as:

- No internet connection.
- VPN connection failed.
- DNS resolution failure.
- Shared folder access.
- Printer issues.
- Wi-Fi and Ethernet checks.
- Cases where employees must not change DNS, firewall, router, or VPN settings.

---

### 11.3 Microsoft 365, Identity, Collaboration, and Productivity

File:

```text
03_microsoft365_identity_collaboration.txt
```

Purpose:

Support knowledge for Microsoft 365 and identity-related issues.

Includes issues such as:

- MFA not working.
- Authenticator app problems.
- Outlook not syncing.
- Teams audio or microphone problems.
- OneDrive sync stuck.
- SharePoint and collaboration issues.
- Cases where account security or MFA reset requires IT.

---

### 11.4 Linux Operations

File:

```text
04_linux_operations.txt
```

Purpose:

Support knowledge for Linux server and infrastructure issues.

Includes issues such as:

- Linux server disk full.
- High CPU usage.
- High memory usage.
- Server crashes.
- Application infrastructure problems.
- Production server warnings.
- Situations where employees should only collect information and notify IT/DevOps.

---

### 11.5 Docker and Container Operations

File:

```text
05_docker_containers.txt
```

Purpose:

Support knowledge for Docker and container-related issues.

Includes issues such as:

- Docker container exits immediately.
- Docker Compose service cannot connect to database.
- Docker image build failure.
- Container logs.
- Docker networking.
- Dependency and environment variable issues.
- Cases where DevOps must handle the issue.

---

### 11.6 Kubernetes Operations

File:

```text
06_kubernetes_operations.txt
```

Purpose:

Support knowledge for Kubernetes infrastructure issues.

Includes issues such as:

- Pod CrashLoopBackOff.
- ImagePullBackOff.
- Kubernetes service not reachable.
- Ingress 502 or 404.
- Deployment failures.
- Cluster-related problems.
- Issues that must be escalated to DevOps.

---

### 11.7 CI/CD, Git, and Developer Support

File:

```text
07_cicd_git_developer_support.txt
```

Purpose:

Support knowledge for developers and CI/CD workflows.

Includes issues such as:

- CI pipeline failure.
- Git merge conflicts.
- “Not a git repository” error.
- npm install failure.
- Python dependency issues.
- Build/test/deploy errors.
- When developers can solve the issue themselves.
- When DevOps or a team lead should be contacted.

---

### 11.8 Databases, Redis, and Background Jobs

File:

```text
08_databases_redis_celery.txt
```

Purpose:

Support knowledge for database, Redis, and background job issues.

Includes issues such as:

- Database connection timeout.
- Slow database queries.
- PostgreSQL too many connections.
- Redis connection refused.
- Celery worker issues.
- Background job failures.
- Cases where employees must not run database commands or restart services.

---

### 11.9 Web, API, Nginx, SSL, Authentication, Authorization, CORS, and Security

File:

```text
09_web_api_security.txt
```

Purpose:

Support knowledge for web application, API, and security issues.

Includes issues such as:

- SSL/TLS certificate expired or invalid.
- Nginx 502 Bad Gateway.
- Nginx 404 Not Found.
- API 500 Internal Server Error.
- Authentication errors.
- Authorization errors.
- CORS problems.
- Security warnings.
- Cases where users must not bypass security warnings.

---

### 11.10 Cloud Operations

File:

```text
10_cloud_operations.txt
```

Purpose:

Support knowledge for cloud infrastructure operations.

Includes issues such as:

- Cloud virtual machine unreachable.
- Cloud access denied.
- IAM permission problems.
- Security group or firewall blocking access.
- Cloud service issues.
- AWS/Azure/GCP troubleshooting concepts.
- Cases where cloud administrators or DevOps must be contacted.

---

## 12. Escalation Logic

Some knowledge base documents include escalation instructions.

Example escalation trigger:

```text
ACTION_REQUIRED: CONTACT_IT
```

This trigger means that the issue is not safe for employee self-service and should be handled by IT, DevOps, or the relevant support team.

Examples of issues that usually require escalation:

- Locked account.
- MFA reset.
- Suspicious login activity.
- DNS problems in internal systems.
- Production application errors.
- Database failures.
- Kubernetes production issues.
- SSL certificate warnings.
- Cloud access and IAM problems.
- Multiple users affected by the same issue.
- Business-critical work blocked.

In the current project stage, the assistant can return this trigger as part of the answer.

In the next stage, this trigger can be connected to Tools or MCP so the system can automatically send an email or create a ticket for IT.

---

## 13. Public IP Address

The application was deployed on an AWS EC2 instance for testing/demo purposes.

Public IP used for the project:

```text
PUBLIC_IP_HERE
```

Application URL:

```text
http://PUBLIC_IP_HERE:5000
```

Replace `PUBLIC_IP_HERE` manually with the real EC2 public IP address.

Example:

```text
http://1.2.3.4:5000
```

If the project is later connected to a domain, the URL can be changed to:

```text
http://your-domain.com
```

or with HTTPS:

```text
https://your-domain.com
```

---

## 14. Environment Variables

The application requires a `.env` file.

Example:

```env
SECRET_KEY=your_secret_key

AWS_REGION=us-east-2

S3_BUCKET_NAME=your_s3_bucket_name

BEDROCK_KNOWLEDGE_BASE_ID=your_bedrock_knowledge_base_id
BEDROCK_DATA_SOURCE_ID=your_bedrock_data_source_id
BEDROCK_MODEL_ARN=your_bedrock_model_arn

APP_VERSION=latest
```

Important:

- Do not commit `.env` to GitHub.
- Do not share AWS credentials.
- Do not upload secrets into the knowledge base.
- Use IAM roles or limited IAM users when possible.
- Keep production secrets separate from development secrets.

---

## 15. Running the Project with Docker

Build and run the project:

```bash
docker-compose up --build
```

Run in detached mode:

```bash
docker-compose up -d --build
```

View logs:

```bash
docker logs -f rag_app
```

Stop the project:

```bash
docker-compose down
```

Rebuild after changes:

```bash
docker-compose up --build
```

Open locally:

```text
http://localhost:5000
```

Open on EC2:

```text
http://PUBLIC_IP_HERE:5000
```

---

## 16. Uploading Documents

The application supports uploading support documents through the API.

Endpoint:

```text
POST /api/upload
```

Upload process:

1. User uploads a document.
2. Flask saves the file temporarily in the `uploads` folder.
3. The file is uploaded to S3 under the `data/` prefix.
4. The application triggers a Bedrock Knowledge Base ingestion job.
5. After the sync finishes, Bedrock can retrieve content from the new document.

S3 example:

```text
s3://your-bucket-name/data/01_it_helpdesk_endpoints.txt
```

---

## 17. Asking Questions

Chat endpoint:

```text
POST /api/chat
```

Example request:

```bash
curl -X POST http://localhost:5000/api/chat \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"My VPN is not working\"}"
```

Example response:

```json
{
  "answer": "Suggested troubleshooting answer from the knowledge base...",
  "session_id": "generated-session-id"
}
```

---

## 18. Chat History

The application saves chat history in SQLite.

This allows follow-up questions to work better.

Example:

User:

```text
My VPN is not working.
```

Assistant:

```text
Check your internet connection, restart the VPN client, restart the computer, and try another network.
```

User:

```text
What should I check next?
```

The system can understand that the follow-up question is still about the VPN problem because it loads recent chat history.

---

## 19. Debug Retrieval Endpoint

The project includes a debug endpoint to check which documents are retrieved from the Knowledge Base.

Endpoint:

```text
POST /api/debug/retrieve
```

Example:

```bash
curl -X POST http://localhost:5000/api/debug/retrieve \
  -H "Content-Type: application/json" \
  -d "{\"message\":\"VPN is not working\"}"
```

This endpoint is useful for verifying:

- Whether the right document was indexed.
- Whether Bedrock retrieves the expected content.
- Whether the question is matching the correct knowledge base topic.
- Why the assistant may be giving an incomplete answer.

---

## 20. AWS Resources Used in This Project

This project may use several AWS resources.

The main resources are:

1. EC2
2. EBS
3. Elastic IP
4. S3
5. Bedrock Knowledge Base
6. Bedrock Data Source
7. Bedrock model access
8. OpenSearch Serverless or another vector store
9. IAM roles and policies
10. CloudWatch logs
11. Security groups
12. EC2 key pair

Not every AWS account will show all of these resources, but they should be checked after finishing the project/demo.

---

## 21. AWS Cleanup After Use

Deleting the EC2 instance is important, but it may not be enough.

Some AWS resources can remain active and continue to create costs even after EC2 is deleted.

The following resources should be checked and deleted if they were created only for this project.

---

### 21.1 EC2 Instance

Purpose:

- Hosts the Dockerized Flask application.
- Provides the public IP during the demo.
- Runs the backend and frontend.

You already deleted the EC2 instance.

Why delete it?

EC2 instances create compute charges while running.

After deleting EC2, also check related resources such as EBS volumes and Elastic IP.

---

### 21.2 EBS Volume

Purpose:

- Stores the EC2 operating system.
- May store application files if the project was deployed directly on the instance.

Why check it?

Sometimes, when an EC2 instance is deleted, the attached EBS volume is not deleted automatically.

If an EBS volume remains, it may continue to generate storage costs.

Where to check:

```text
AWS Console -> EC2 -> Volumes
```

Delete volumes that:

- Are not attached to any instance.
- Were created only for this project.
- Do not contain needed data.

---

### 21.3 Elastic IP

Purpose:

- Provides a static public IP address for the EC2 instance.

Why check it?

An Elastic IP can generate charges if it is allocated but not attached to a running instance.

Where to check:

```text
AWS Console -> EC2 -> Elastic IPs
```

Delete/release the Elastic IP if it was created only for this project and is no longer used.

---

### 21.4 S3 Bucket

Purpose:

- Stores uploaded knowledge base documents.
- Acts as the source for Bedrock Knowledge Base.

Why delete it?

S3 storage is usually cheap, but files can still generate costs over time.

Where to check:

```text
AWS Console -> S3 -> Buckets
```

Before deleting the bucket:

1. Empty the bucket.
2. Delete all objects.
3. If versioning is enabled, delete all object versions.
4. Delete delete markers if they exist.
5. Delete the bucket.

---

### 21.5 Bedrock Knowledge Base

Purpose:

- Indexes the documents from S3.
- Retrieves relevant document chunks for user questions.
- Connects the RAG application to the Bedrock model and vector store.

Why delete it?

The Knowledge Base may keep related resources active, such as a vector store or IAM role.

Where to check:

```text
AWS Console -> Amazon Bedrock -> Knowledge Bases
```

Delete the Knowledge Base if the project is no longer needed.

---

### 21.6 Bedrock Data Source

Purpose:

- Defines the S3 location used by the Knowledge Base.
- Allows Bedrock to sync documents from S3.

Why delete it?

If the data source remains connected to a Knowledge Base, it may keep the project configuration active.

Where to check:

```text
AWS Console -> Amazon Bedrock -> Knowledge Bases -> Data Sources
```

Delete project-specific data sources if they are no longer needed.

---

### 21.7 Bedrock Ingestion Jobs

Purpose:

- Sync files from S3 into the Knowledge Base.
- Split and index the document content.

Why check it?

Completed jobs usually do not need manual cleanup, but they help identify what was synced and when.

Where to check:

```text
AWS Console -> Amazon Bedrock -> Knowledge Bases -> Ingestion history
```

Usually, you do not delete individual completed ingestion jobs manually.  
Instead, delete the Knowledge Base and related resources if the project is finished.

---

### 21.8 Vector Store / OpenSearch Serverless Collection

Purpose:

- Stores embeddings created from the uploaded documents.
- Enables semantic search for the RAG system.

Why delete it?

This can be one of the most important cost-related resources to check.

If Bedrock created or used OpenSearch Serverless for the Knowledge Base, the collection may continue to exist even after the EC2 instance is deleted.

Where to check:

```text
AWS Console -> Amazon OpenSearch Service -> Serverless -> Collections
```

Look for project-related collections.

Delete the collection if:

- It was created only for this project.
- The Knowledge Base is no longer needed.
- No other application depends on it.

---

### 21.9 IAM Roles and Policies

Purpose:

IAM roles and policies may allow:

- EC2 to access AWS services.
- Bedrock to access S3.
- Bedrock to access the vector store.
- The application to use S3 and Bedrock APIs.

Why check them?

IAM roles usually do not cost money directly, but unused roles create security risk and account clutter.

Where to check:

```text
AWS Console -> IAM -> Roles
AWS Console -> IAM -> Policies
```

Delete only roles and policies that were created specifically for this project and are not used by anything else.

Do not delete shared roles.

---

### 21.10 CloudWatch Logs

Purpose:

CloudWatch may store logs for AWS services or application-related resources.

Why delete them?

CloudWatch logs can generate storage costs over time.

Where to check:

```text
AWS Console -> CloudWatch -> Log groups
```

Delete log groups that:

- Were created only for this project.
- Are no longer needed.
- Do not contain important audit/debug information.

---

### 21.11 Security Groups

Purpose:

Security groups control inbound and outbound network access for EC2.

For this project, a security group may allow:

```text
Port 22   - SSH
Port 5000 - Flask application
Port 80   - HTTP, if configured
Port 443  - HTTPS, if configured
```

Why check them?

Security groups usually do not cost money, but unused security groups create clutter and can cause security confusion.

Where to check:

```text
AWS Console -> EC2 -> Security Groups
```

Delete project-specific security groups after deleting the EC2 instance.

---

### 21.12 EC2 Key Pair

Purpose:

Used for SSH access to the EC2 instance.

Why check it?

The AWS key pair itself usually does not cost money, but keeping unused keys is not recommended.

Where to check:

```text
AWS Console -> EC2 -> Key Pairs
```

Delete the key pair if it was created only for this project.

Also delete the local `.pem` file from your computer if it is no longer needed.

Do not delete a key pair used by another active EC2 instance.

---

## 22. AWS Cleanup Checklist

Use this checklist after finishing the project/demo:

```text
[ ] EC2 instance deleted
[ ] EBS volume deleted if no longer needed
[ ] Elastic IP released if allocated
[ ] S3 bucket emptied and deleted if no longer needed
[ ] Bedrock Knowledge Base deleted
[ ] Bedrock Data Source deleted
[ ] OpenSearch Serverless / vector store deleted
[ ] Project-specific IAM roles deleted
[ ] Project-specific IAM policies deleted
[ ] CloudWatch log groups deleted if not needed
[ ] Project-specific Security Group deleted
[ ] Project-specific EC2 Key Pair deleted
```

---

## 23. Recommended AWS Deletion Order

Recommended cleanup order:

1. Stop and delete the EC2 instance.
2. Release the Elastic IP if one was allocated.
3. Check and delete unattached EBS volumes.
4. Delete the Bedrock Knowledge Base.
5. Delete the Bedrock Data Source if still visible.
6. Delete the vector store or OpenSearch Serverless collection.
7. Empty and delete the S3 bucket.
8. Delete project-specific CloudWatch log groups.
9. Delete project-specific IAM roles and policies.
10. Delete unused security groups.
11. Delete unused EC2 key pairs.

This order helps prevent resources from depending on each other during deletion.

---

## 24. Important Cost-Saving Notes

Deleting only the EC2 instance does not guarantee that all costs stop.

After deleting EC2, the most important resources to check are:

```text
EBS Volumes
Elastic IP
S3 Bucket
Bedrock Knowledge Base
OpenSearch Serverless Collection / Vector Store
CloudWatch Logs
```

The most likely resources to continue costing money after EC2 deletion are:

- Unattached EBS volumes.
- Allocated Elastic IPs.
- S3 stored files.
- OpenSearch Serverless collections.
- CloudWatch stored logs.
- Any active vector store connected to the Knowledge Base.

---

## 25. Security Notes

This project handles internal support information, so security is important.

Important rules:

- Do not upload secrets into the Knowledge Base.
- Do not upload passwords.
- Do not upload API keys.
- Do not upload private SSH keys.
- Do not commit `.env` to GitHub.
- Do not expose port `5000` publicly in production without authentication.
- Do not allow employees to run dangerous server/database/cloud commands.
- Do not allow the assistant to bypass security procedures.
- Use least-privilege IAM permissions.
- Use HTTPS in production.
- Add authentication before using the system with real company employees.

---

## 26. Limitations

Current limitations:

- No user authentication yet.
- No role-based access control.
- No automatic IT email/ticket creation in the current base version.
- No admin dashboard for managing uploaded documents.
- No direct document deletion flow from the UI.
- Bedrock sync may take time after uploading files.
- The assistant depends on the quality of uploaded documents.
- If the Knowledge Base does not retrieve the right content, the answer may be incomplete.
- Public EC2 deployment should not be considered production-ready without HTTPS and authentication.

---

## 27. Future Improvements

Recommended future improvements:

1. Add employee login.
2. Add admin login.
3. Add document management dashboard.
4. Add Knowledge Base sync status page.
5. Add automatic email to IT when escalation is required.
6. Add MCP tools.
7. Add helpdesk ticket creation.
8. Add Teams or Slack notifications.
9. Add role-based permissions.
10. Add HTTPS with Nginx and SSL certificate.
11. Add CloudWatch monitoring.
12. Add production deployment with domain name.
13. Add audit logs for all escalations.
14. Add feedback buttons for answer quality.
15. Add analytics dashboard for most common employee issues.

---

## 28. Future Tools and MCP Integration

In the next project phase, the system can be extended with Tools and MCP.

The idea:

```text
User asks question
       |
RAG assistant answers from uploaded support documents
       |
Answer includes ACTION_REQUIRED: CONTACT_IT
       |
Tool Dispatcher detects the trigger
       |
MCP Tool sends email / creates ticket / logs incident
       |
User receives confirmation
```

Possible tools:

- Send email to IT.
- Create helpdesk ticket.
- Send Teams notification.
- Save escalation event to database.
- Upload screenshots or logs to S3.
- Check Knowledge Base sync status.
- Check system health endpoints.
- Notify manager for access approval.

This would turn the project from a chatbot into an action-based internal support assistant.

---

## 29. Example Use Cases

### Example 1: VPN Issue

User:

```text
My VPN is not working.
```

Assistant:

- Checks the VPN support document.
- Suggests safe checks such as restarting VPN, checking internet, trying another network.
- Tells the user when IT must be contacted.

---

### Example 2: MFA Issue

User:

```text
I changed my phone and now MFA does not work.
```

Assistant:

- Finds the MFA document.
- Explains basic checks.
- Identifies that IT must reset or re-register MFA.
- Escalates the issue according to the document.

---

### Example 3: Docker Issue

User:

```text
My Docker container exits immediately.
```

Assistant:

- Finds the Docker troubleshooting document.
- Explains what logs and symptoms to collect.
- Warns regular employees not to change production containers.
- Escalates to DevOps if production or shared systems are affected.

---

### Example 4: Cloud Access Denied

User:

```text
I get AccessDenied in AWS.
```

Assistant:

- Finds the cloud IAM document.
- Explains what details to collect.
- Warns not to use another employee’s account.
- Recommends manager/resource owner approval and IT/cloud admin support.

---

## 30. Summary

SupportOps AI is a practical internal IT self-service assistant.

It helps employees solve common problems faster and reduces unnecessary IT workload.

The project combines:

- Flask backend.
- Web chat interface.
- AWS Bedrock Knowledge Base.
- Amazon S3 document storage.
- SQLite chat history.
- Docker deployment.
- Structured company IT support documents.

The assistant is designed to:

- Answer only from uploaded internal documents.
- Give safe troubleshooting steps.
- Prevent dangerous user actions.
- Escalate issues that require IT or DevOps.
- Prepare the project for future Tools and MCP automation.

Overall, the system demonstrates how AI can be used responsibly inside a company to improve support efficiency while keeping technical control and safety.