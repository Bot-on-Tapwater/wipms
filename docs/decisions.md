# Design decisions

Notes on what changed compared with the old backend, and why.

## Payment bugs fixed from the old backend

1. **Subcontractor amount.** The subcontractor is now paid the work's total
   minus all labour due minus retention. The old code did not subtract all
   of the labour due, so money could be paid twice.
2. **Failed payments.** Every payment attempt is stored as a payment record,
   whether it succeeded or failed. Failed payments can be retried
   (`POST /works/{id}/payments/retry`) and only the failed ones are sent
   again, so nobody is paid twice.
3. **Double payout.** The work row and its project wallet are locked while
   a payout or deposit runs, so two requests arriving at the same time
   cannot both pay out or overwrite each other's wallet balance.
4. **Wallets.** Each project has its own wallet. Deposits and payments are
   recorded as wallet transactions, so the balance can always be explained.
   Payments may only use `WALLET_USABLE_RATIO` of the balance (old rule: 99%).
5. **Retention cap.** When labourers are owed almost the whole labour
   estimate, the subcontractor's share is zero and the full retention on top
   would pay out more than the work costs. Retention is now limited to what
   is left of the work's cost.
6. **Stale approvals.** Changing a work's cost, its labourers, their days,
   its subcontractor, or a labourer's daily rate withdraws the payment
   request and payment approvals, so nobody approves amounts that have since
   changed. Once payouts have started (including a payout with failed
   payments waiting for a retry) the work can no longer be edited.

## Other changes

- Permissions are stored in the database and can be changed without a code
  change (CLI or API). See the root README.
- Subcontractors only see payment records and reports for their own works,
  including the "Total paid" figures in the projects report. They do not see
  wallet transactions (`projects.view_wallet`). Payment summaries need
  `payments.view`.
- Changing or resetting a password cancels every token issued before it
  (a `token_version` on the user is written into each token).
- Labourer search escapes `%` and `_`, so typed text is matched literally.
- The main contractor emails that were hard-coded are now the
  `MAIN_CONTRACTOR_EMAILS` setting.
- Reports are emailed only to the user who asks for them.
- The API refuses to start in production with a weak `SECRET_KEY`.
- `GET /works` and `GET /payments/records` work without a `project_id`:
  they return what the user can see across all their projects. The
  dashboard ("Waiting for you") and the Payments page use this, instead of
  calling the API once per project.

## Frontend

- **Next.js with every page rendered in the browser.** The pages need the
  logged in user's token, so there is nothing useful to render on the server.
  This keeps the code simple: one way of loading data (`useApi`).
- **Tokens in `localStorage`.** The API returns tokens in the response body,
  not cookies. When several requests find an expired token at the same time,
  only one refresh is sent (a refresh token works once).
- **Permissions come from the backend** (`GET /permissions/me`) and only hide
  things; the backend checks every action again.
- **`NEXT_PUBLIC_API_URL` is fixed at build time** (a Next.js rule), so the
  production Dockerfile takes it as a build argument.
- **Printing reports** uses the backend's printable HTML page in a hidden
  frame without scripts, so no pop-up window is needed and the report page
  cannot run code.
- **Repeated pieces are components**: the labourer autocomplete (used for the
  name and the ID field), the payment records table (work page and Payments
  page), `ActionButton` (confirm, call the API, toast) and the `ui/` blocks.

### Removed or merged from the old app

- The landing page (with the animated particles) is gone: `/` opens the
  dashboard, or the login page when logged out.
- "Add labourer details" and "Assign labourer" are one form: typing a name or
  ID suggests existing labourers, otherwise a new one is registered.
- The "Create subcontracted work" page is a pop-up form on the project page.
- The "Subcontractor Management" page is the Team section of each project,
  where supervisors and subcontractors are added and removed.
- Redux is replaced by two small hooks (`useAuth`, `useApi`).

### Added

- Dashboard "Waiting for you": works where the user has an approval or
  payment step to do.
- Labourer autocomplete by name and by ID number.
- Payments page with a filter for failed payments and a retry button on the
  work page.
- Reports page: view, print, download PDF or email any report.
- Profile page: change details and password.
- Toasts for every action, and a warning when some payments in a payout fail.

## Insights page (labourer stats)

A new "Insights" page shows labourers by trade, project, gender and age
group, with days worked, amount paid, numbers per month and the labourers
who came back most often. Clicking a bar, a month, a project or a trade
filters the whole page.

- **Who sees it.** Only the super admin (every project) and main
  contractors (only projects they created or are on the team of). Main
  contractors can see all projects elsewhere (`projects.view_all`), but not
  here. Two new permission codes: `stats.view` and `stats.view_all`. Run
  `python -m app.scripts.seed_permissions` after deploying.
- **Gender and age.** Both are new optional fields on a labourer. Age is
  typed in (18 to 80) and stored as a birth year, so it stays right as years
  pass. They are only shown as totals, never next to a name. The gender
  list comes from `/metadata/choices` (`genders`). Migration `0002` adds
  the two columns.
- **Trade.** A labourer's trade is their current title, so pay per trade
  uses the title they have today.
- **What is counted.**
  - Days worked include every work, whatever its payment status.
  - Amount paid counts only successful labourer payments.
  - "Registered" counts labourers whose record was created in the period.
    For a main contractor that means labourers who have worked on their
    projects, even if they signed up on another project first.
- **Dates.** The From and To filters use the date the work was created
  (days worked), the date of the payment (amount paid) and the date the
  labourer was registered (registered).

## Open questions

1. Which emails should be allowed to register as main contractor
   (`MAIN_CONTRACTOR_EMAILS`)?
2. Should data from the old system be migrated into the new database?
3. Should this live in a new repository or a branch of the existing one?
4. Which bank API will be used for real payments?
