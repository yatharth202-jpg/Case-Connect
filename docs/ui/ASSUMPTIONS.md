# Case Connect AI — Phase 2 UI Design & Workflow Assumptions

These assumptions establish concrete defaults for the Phase 2 implementation, aligning the Stitch screens (`docs/ui/pack/stitch_screens/`) with backend functionality and the Production Forensic Hygiene Protocol.

---

### 1. Authentication & Session Persistence
* **Token Storage**: JWT tokens (`access_token`) are stored in `sessionStorage` alongside active user role (`admin`, `investigator`, `viewer`).
* **Session Expiry**: Standard 8-hour token duration. 401 Unauthorized API responses automatically clear `sessionStorage` and redirect to `/login`.
* **Tactical Styling**: The login view adopts the Stitch `login_screen` split layout (tactical dark `#030712`, navy borders `#1e293b`, rectangular buttons, 0 purple gradients).

### 2. Role-Based Navigation & Access
* **Viewer**: Read-only access across assigned cases; upload and mutation buttons are hidden or disabled.
* **Investigator**: Full case management (create case, upload evidence, verify hashes, add notes). Cannot access `/audit` or user administration.
* **Admin**: Unrestricted access across all cases, evidence, audit verification (`/audit`), and user management.

### 3. Case Membership Enforcement
* Admins see all cases in the database.
* Non-admin users only see and access cases where their `user_id` exists in `case_members`.
* Direct navigation to an unassigned case returns a `403 Forbidden` error state with a clean return button.

### 4. Evidence Upload & Integrity
* Supported extensions: `.csv`, `.xlsx`, `.json`, `.jsonl`, `.txt`, `.pdf`, `.docx`.
* Max file size: 200 MB for tabular/JSON; 20 MB for document/text files.
* Files are saved to `data/uploads/<case_id>/<uuid>_<filename>` in read-only mode with stream-calculated SHA-256.
* An inline "Verify" button invokes `POST /evidence/{id}/verify` to guarantee bit-for-bit file integrity on disk.

### 5. Multi-Tab Case Workspace
* The Evidence tab is fully functional in Phase 2.
* Analysis tabs (Graph, Money Trail, Profiles, Leads, Reports) render structured empty states: *"Evidence files ingested. Analytics unlock upon evidence confirmation in Phase 3"* with zero fake demo metrics or placeholder cards.

### 6. Cryptographic Audit Log
* Every state-changing action writes an immutable row into `audit_log` with SHA-256 hash chaining back to `GENESIS`.
* The admin `/audit` screen includes a real-time "Verify Hash Chain" button checking for any direct database tampering.
