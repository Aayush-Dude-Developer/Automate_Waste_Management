# GCP application shutdown

## What was done

On November 10, 2026, the deployed application in GCP project
`automate-511215` was shut down:

- Deleted the `sustainbite-api` Cloud Run service in `asia-south1`.
- Paused and deleted the `quota-guard-every-five-minutes` Cloud Scheduler job.
- Deleted the second-generation `quota-guard` Cloud Function and its backing
  Cloud Run service.
- Deleted the `GEMINI_API_KEY` Secret Manager secret.
- Replaced the Firebase Hosting site's published app with a blank HTML page.
  Firebase does not allow deleting this project's default Hosting site.
- Unlinked the project's Cloud Billing account. GCP reported
  `billingEnabled: false`.

The old API and quota-guard URLs returned HTTP 404 after shutdown, and the
Hosting URL returned the blank page. The default Firestore database was
intentionally preserved, along with the project and Firebase configuration.
Artifact Registry repositories, Cloud Storage buckets, service accounts, IAM
bindings, and enabled APIs were not explicitly deleted. With billing disabled,
GCP may restrict access to some services and resources.

This cannot remove charges already accrued, prevent a final invoice, or disable
separate Gemini AI Studio billing. A project owner could also relink billing
and redeploy the app later.

## Repeat the shutdown

From this directory, run the guarded PowerShell script:

```powershell
.\shutdown-gcp.ps1
```

The script is pinned to `automate-511215`, requires `gcloud` and `firebase`
authentication, refuses to proceed when project billing is already disabled,
and asks you to type `SHUTDOWN` before deleting resources. If you have
re-enabled billing and redeployed the application, run it again to repeat the
shutdown. It does not delete Firestore data, the Firebase project, or retained
storage and registry resources.

Disabling billing is not a permanent lock: someone with sufficient permissions
can relink the project or deploy resources elsewhere. To prevent future use by
project owners, delete the entire project instead, after backing up any data
you want to keep.
