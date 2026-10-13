# Quota guard operations

The quota guard can replace the Firebase Hosting site with a blank page and
restrict public access to the Cloud Run API when any configured quota reaches
`QUOTA_SHUTDOWN_PERCENT`. The deployment runbook is in
[`../DEPLOYMENT.md`](../DEPLOYMENT.md).

## Current deployment

The live guard is deployed to project `automate-511215` in `asia-south1` with
`QUOTA_SHUTDOWN_PERCENT=80`. Cloud Scheduler runs it every five minutes. The
80% triggers are 40,000 Firestore reads/day, 16,000 writes/day, 16,000
deletes/day, or 1,600,000 Cloud Run requests/month. At the latest check,
Firestore reads were 11,897 and Cloud Run requests were 285; writes and
deletes had no metric series.

The app had previously been shut down at 15%. It has now been restored for the
80% test: Hosting serves the app, Cloud Run ingress is public, and the enabled
scheduler returned HTTP 200. Reads are below 40,000, so the monitor can shut
the app down again when an available metric reaches its new threshold.

## Restore the app after automatic shutdown

Run these commands from the project root in PowerShell. Pause the monitor first
so it does not immediately shut the app down again:

```powershell
gcloud scheduler jobs pause quota-guard-every-five-minutes --location asia-south1 --project automate-511215
firebase deploy --only hosting --project automate-511215
gcloud run services update sustainbite-api --project automate-511215 --region asia-south1 --ingress all
```

Check why the threshold was reached. If usage is still above the configured
percentage, either wait for the monitored period to reset or deliberately
adjust the quota limit or threshold before resuming the monitor. Otherwise it
can shut the app down again on its next run.

```powershell
gcloud scheduler jobs resume quota-guard-every-five-minutes --location asia-south1 --project automate-511215
```

The Hosting deploy restores the current frontend bundle; the Cloud Run command
restores public ingress so Hosting's `/api/**` rewrite can reach the API. A
blank Hosting page and an ingress restriction do not remove existing browser
tabs, so users may need to refresh after restoration.

## Change the shutdown threshold

Set `QUOTA_SHUTDOWN_PERCENT` when deploying or updating the `quota-guard`
function. The threshold must be an integer from 1 through 100. For example,
set it to `80` to trigger at 80% of any configured quota. The values and metric
names being monitored are in [`limits.json`](./limits.json).

This is best-effort monitoring only. Usage metrics can arrive late, and
Firebase Hosting transfer/storage and Gemini API usage are not monitored.
Consult the limitations in [`../DEPLOYMENT.md`](../DEPLOYMENT.md) before
relying on it to prevent costs.
