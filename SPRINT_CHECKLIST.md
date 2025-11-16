# SPRINT CHECKLIST

## Team Assignments
- **Teammate 1:** Front-End 1
- **Teammate 2:** Front-End 2
- **Teammate 3:** Back-End 1
- **Teammate 4:** Back-End 2
- **Teammate 5:** Client

---

## Phase 1: Initial Setup (Do First, In Parallel)
- [ ] **All:** Agree on data models and API contracts (input/output formats)
- [ ] **Back-End 1 & 2:** Set up Flask app skeleton, MongoDB connection, and basic API endpoints (mock data ok)
- [ ] **Front-End 1 & 2:** Scaffold web UI, set up project structure, create placeholder pages for recording and viewing notes
- [ ] **Client:** Set up basic client structure and test connectivity to the back-end (mock endpoints ok)

---

## Phase 2: Core Features (Parallel)
- [ ] **Back-End 1:** Implement audio upload endpoint and storage in MongoDB
- [ ] **Front-End 1:** Implement audio recording and upload UI, connect to back-end upload endpoint
- [ ] **Client:** Implement audio capture and upload to back-end

---

## Phase 3: AI Integration (Back-End First, Then Front-End/Client)
- [ ] **Back-End 2:** Integrate AI transcription service and structured note generation (mock responses at first, then real AI)
- [ ] **Front-End 2:** Once back-end supports AI, update UI to display transcriptions and structured notes
- [ ] **Client:** Update to display AI results if needed

---

## Phase 4: Notes Management (Parallel)
- [ ] **Back-End 1 & 2:** Implement endpoints for retrieving, searching, and sorting notes
- [ ] **Front-End 1 & 2:** Build UI for listing, searching, sorting, and viewing notes
- [ ] **Client:** Add features for retrieving and displaying past notes if needed

---

## Phase 5: Polish & Testing (Do Last, In Parallel)
- [ ] **All:** End-to-end testing, error handling, UI/UX improvements, documentation, and deployment scripts

---

## Notes
- Initial setup and API/data model agreements must be completed before starting core features.
- Back-end endpoints should be ready before full front-end/client integration.
- AI integration on the back-end should be ready before front-end/client can display AI results.
- Notes management and polish can be done in parallel once core flows work.
