#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Goal-setting restructure. (1) Onboarding goal weight optional (default "show me what's
  possible"); stretch = engine safe maximum, not entered goal. (2) Edit goal (weight/timeline/
  direction) anytime with confirmation + regeneration; keep goal history (archive, no overwrite).
  (3) Switch active target conservative/expected/stretch anytime without redoing onboarding.
  (4) "What's my best case?" optimum preview across 16/26/39 weeks (real renders, cached).
  (5) recomp engine fix so the 3 targets are visibly distinct (were near-identical at ~80kg).

backend:
  - task: "Versioned goals: PATCH /goal archives current goal+renders+plan (no overwrite), creates new active goal, resets targets/plan, starts regeneration job"
    implemented: true
    working: "NA"
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "New PATCH /goal + GET /goal. Migration _migrate_goal_versioning backfills id/active/started_at + goal_id on fss/plan/logs/photos. Verify old goal set active=false with ended_at and its fss/plan remain queryable; new goal active."
  - task: "Optional goal weight + optimum-vs-goal note on GET /targets"
    implemented: true
    working: "NA"
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "GET /targets returns goal{} + optimum_note when desired goal is more modest than stretch."
  - task: "Optimum preview: POST /optimum (cached by base_sha+weight+direction), GET /optimum/job/{id}, GET /optimum — renders stretch for 16/26/39 weeks"
    implemented: true
    working: "NA"
    file: "backend/server.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "3 real Gemini renders; second call should return cached done immediately."
  - task: "Target switching via POST /target/choose rebuilds plan for chosen label (now keyed by goal_id)"
    implemented: true
    working: "NA"
    file: "backend/server.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Plan upserted on {goal_id}. Verify switching updates user.chosen_target and /plan reflects it."
  - task: "TargetEngine recomp fix — distinct conservative/expected/stretch body-fat"
    implemented: true
    working: true
    file: "backend/target_engine.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        -working: true
        -agent: "main"
        -comment: "Verified: recomp now yields 23.0/22.0/19.7% BF from 27.1% (was 26.7/26.6/26.2). 11 engine unit tests pass. edizkanata@gmail.com renders regenerated."

frontend:
  - task: "Onboarding: optional goal weight with default 'Show me what's possible' vs 'I have a target'"
    implemented: true
    working: "NA"
    file: "frontend/app/onboarding.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Only sends desired_weight_kg when custom mode + value entered."
  - task: "Profile My Goal section: edit goal (confirm + regen) and switch active target"
    implemented: true
    working: "NA"
    file: "frontend/src/components/MyGoalSection.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Renders correctly (smoke screenshot). Edit -> confirm -> PATCH /goal -> /generating?job=. Target switch -> /target/choose."
  - task: "Optimum screen /optimum (What's my best case?) with 16/26/39wk renders"
    implemented: true
    working: "NA"
    file: "frontend/app/optimum.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "POST /optimum then poll or GET cached."
  - task: "Targets screen: goal marker + optimum note + best-case entry"
    implemented: true
    working: "NA"
    file: "frontend/app/targets.tsx"
    stuck_count: 0
    priority: "medium"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "Shows goal marker line and optimum_note card; button to /optimum."
  - task: "generating.tsx polls existing job via ?job= (goal regeneration)"
    implemented: true
    working: "NA"
    file: "frontend/app/generating.tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: true
    status_history:
        -working: "NA"
        -agent: "main"
        -comment: "When ?job= present, poll that job instead of starting a new /generate."

metadata:
  created_by: "main_agent"
  version: "1.2"
  test_sequence: 1

test_plan:
  current_focus:
    - "Versioned goals: PATCH /goal archives current goal+renders+plan (no overwrite), creates new active goal, resets targets/plan, starts regeneration job"
    - "Target switching via POST /target/choose rebuilds plan for chosen label (now keyed by goal_id)"
    - "Optional goal weight + optimum-vs-goal note on GET /targets"
    - "Optimum preview: POST /optimum (cached), GET /optimum/job/{id}, GET /optimum"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    -agent: "main"
    -message: |
      Implemented goal restructure. Please test BACKEND first with account calibration@trueform.app / Test1234!
      (onboarded, has base photo, has targets+plan). Focus:
      1) GET /goal returns active goal + chosen_target + archived_goals count.
      2) POST /target/choose with each label -> user.chosen_target updates, GET /plan reflects it.
      3) PATCH /goal {direction/timeline_weeks/clear_desired_weight/desired_weight_kg}: returns job_id;
         old goal becomes active=false with ended_at; its future_self_sets + plan (by goal_id) still exist
         (NOT overwritten); new active goal created; user has_targets/has_plan reset then a generate job runs.
         Poll GET /generate/{job_id} to done. NOTE: each PATCH triggers 3 Gemini image renders (cost) — run once.
      4) GET /targets returns goal{} and optimum_note (optimum_note only when a desired goal is more modest than stretch).
      5) POST /optimum -> job or cached; GET /optimum/job/{id} to done -> 3 items (16/26/39 wk); second POST returns cached=true. (3 renders cost — run once.)
      Then FRONTEND: onboarding optional goal-weight path, Profile My Goal (switch target + edit->confirm->regen), Optimum screen, Plan 'sliders' shortcut to Profile.
      Do NOT re-test the recomp engine math (already unit-verified).
