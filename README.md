# CollabDocs API

Django REST Framework backend for the CollabDocs assignment.

## Requirements
- Python 3.11+
- PostgreSQL 14+
- Postman

## 1. Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
```

Create a PostgreSQL database named `collabdocs`, then update `.env` with your local PostgreSQL credentials. Never commit `.env`.

## 2. Migrations

```powershell
python manage.py migrate
python manage.py showmigrations
```

The repository contains the initial migration and it can be applied from scratch.

## 3. Run

```powershell
python manage.py runserver
```

Base URL: `http://127.0.0.1:8000/api/`

## 4. Postman

Import `CollabDocs_Postman_Collection.json` from the repository root. The collection contains all 17 required endpoints and sample POST/PUT bodies, organized into Users, Workspaces, Documents, Comments, Tags and Audit Logs.

Run the requests in this order for the easiest demo:
1. Create User 1
2. Create User 2
3. Create Workspace
4. Get Workspace
5. Add Member
6. List Members
7. Workspace Summary
8. Create Document
9. Update Document
10. List Documents
11. Document Versions
12. Document Stats
13. Add Tags
14. Create Comment
15. List Comments
16. Create Tag
17. Audit Logs

Postman variables are preconfigured with `base_url` and IDs are captured automatically by test scripts.

## 5. Assignment requirement demonstrations

### Atomic rollback
The workspace POST supports a demo-only `simulate_failure: true` flag. The endpoint creates the workspace and owner member inside one `transaction.atomic()` block, then intentionally attempts to add the same owner twice. The second insert raises `IntegrityError`, the response is HTTP 409, and the transaction rolls back the workspace and first member as well.

Use this body for the demo:

```json
{
  "name": "Rollback Demo",
  "owner": "{{user_id}}",
  "is_active": true,
  "simulate_failure": true
}
```

Then GET the workspace by the ID you would have received: there is no ID because the entire transaction rolled back. The server console will show the 409 request.

### Document transaction + versioning
Document create/update wraps the document save and `DocumentVersion` creation in `transaction.atomic()`. Each save creates the next per-document version using `document.versions.count() + 1`.

### Middleware
Every request prints:

`[REQUEST] METHOD /path/ -> status (N.NN ms)`

### Signal audit logging
`post_save` on `Document` creates an `AuditLog` with actor, action, model name and object ID. Updating a document therefore creates an `updated` audit entry visible from the Audit Logs endpoint.


