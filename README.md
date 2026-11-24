# Drug Approval Tracker (EMA · TLV · NT-rådet)

Tracks newly approved drugs and new indications for already-approved drugs across:
- **EMA** (European Medicines Agency)
- **TLV** (Tandvårds- och läkemedelsförmånsverket)
- **NT-rådet** (Rådet för nya terapier via *samverkanlakemedel.se*)

## Structure
- `scraper/` — Python pipeline that fetches EMA, TLV, and NT-rådet, classifies `new_drug` vs `new_indication`, links records by active substance / drug name / ATC code, and writes `docs/data/drugs.json`.
- `android/` — Native Kotlin + Jetpack Compose Android app with search, Source/Update-Type/ATC filters, bookmarks, unified `EMA → TLV → NT-rådet` timelines, and `WorkManager` background notifications.
- `.github/workflows/` — Automated twice-daily data refresh (`update-data.yml`) and cloud APK builds (`build-apk.yml`).

## Quick Start (No Local Android Studio Required)
1. Create a new GitHub repository and push the contents of `drug-approval-tracker/`.
2. In GitHub → **Actions**:
   - Run **Update EMA / TLV / NT-rådet Feed** to populate `docs/data/drugs.json` with live data.
   - Run **Build Android APK** (or let it run on push) and download `DrugApprovalTracker-debug-apk` from the workflow run artifacts.
3. Transfer `app-debug.apk` to your Android phone and install it (allow installs from your browser/files app if prompted).
4. Open the app → tap the **Settings** gear icon → set **Feed JSON URL** to:
   `https://raw.githubusercontent.com/<YOUR_GITHUB_USERNAME>/<YOUR_REPO>/main/docs/data/drugs.json`
