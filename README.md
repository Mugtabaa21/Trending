# Daily Trends Bot — Setup (mobile only, no PC needed)

## Step 1 — Create the repo
1. Open github.com in your phone browser (or the GitHub app)
2. Tap **+** → **New repository**
3. Name it `trends-bot`, set to **Private**, tap **Create repository**

## Step 2 — Add the files
GitHub's mobile web editor lets you create files by typing a full path —
it auto-creates the folders for you. Do this 3 times:

1. Tap **Add file → Create new file**
2. In the filename box type: `trend_scanner.py`
3. Paste in the contents of `trend_scanner.py` (below)
4. Scroll down, tap **Commit changes**

Repeat for:
- `requirements.txt`
- `.github/workflows/daily-scan.yml` (yes, type the slashes — GitHub creates the folders automatically)

## Step 3 — Add your secrets (so the token isn't public)
1. In the repo, tap **Settings**
2. Tap **Secrets and variables → Actions**
3. Tap **New repository secret**
4. Add:
   - Name: `TELEGRAM_TOKEN` → Value: your bot token
   - Name: `TELEGRAM_CHAT_ID` → Value: `643262525`

## Step 4 — Test it manually
1. Tap the **Actions** tab
2. Tap **Daily Trends Scan** on the left
3. Tap **Run workflow** → **Run workflow** (green button)
4. Wait ~1-2 minutes, then check Telegram — you should get your first digest

## Step 5 — Done
It'll now run automatically every day at 6:00 AM Baghdad time and message you
on Telegram. Reply here in our chat with the number you like, and I'll start
building that idea into a SaaS.

## Notes
- This uses free GitHub Actions minutes (well within the free tier for 1 run/day)
- Sources scanned: Google Trends (Iraq trending searches + growth on business
  terms), Reddit (r/Iraq, r/smallbusiness, r/Entrepreneur, r/SaaS)
- Iraq-specific data is thinner than global data — treat low-signal days as
  normal, not broken
- History of past digests is saved in the `history/` folder in the repo so we
  can look back over time
