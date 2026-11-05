# CourtBook

Live sports court slot booking for a college campus. Flask + SQLite, built for Azure App Service (Linux, Python 3.15, Free F1).

**Live site:** <https://courtbook-brooxxhh-g2hug8hkhnaze3gq.indiasouthcentral-01.azurewebsites.net>

- [FRIEND_GUIDE.md](FRIEND_GUIDE.md): what a teammate needs to do
- [CourtBook_Demo_and_Viva.pdf](CourtBook_Demo_and_Viva.pdf): the 5-minute talk and viva questions
- [PROJECT_GUIDE.md](PROJECT_GUIDE.md): full setup, deployment and troubleshooting

## Run locally

```
pip install -r requirements.txt
python app.py
```

Open http://localhost:5000. The database is created at `./courtbook.db`. Gunicorn does not run on Windows, so local runs use Flask's own server.

## Deploy from VS Code

1. Install the **Azure App Service** extension and open this folder in VS Code.
2. Open the Azure side bar and sign in.
3. Under App Service, right-click your subscription and choose **Create New Web App**.
4. Enter a unique name, then choose **Python 3.15** (3.11 also works) and the **Free (F1)** tier.
5. In the Azure Portal, open the app, go to **Configuration → General settings**, set **Startup Command** to the line below, and save:

   ```
   gunicorn --bind=0.0.0.0 --timeout 600 --workers 1 --threads 8 app:app
   ```

   The same command is in `startup.txt`.
6. In **Settings → Environment variables**, check that `SCM_DO_BUILD_DURING_DEPLOYMENT` is `true`, and add it if it is missing. Without it, Azure does not install `requirements.txt`.
7. In VS Code, right-click the web app and choose **Deploy to Web App**, then select this folder.
8. Open the **Default domain** address from the portal's Overview page.

On Azure the database is at `/home/data/courtbook.db`, so bookings survive restarts and redeploys. The app detects Azure through the `WEBSITE_SITE_NAME` variable that App Service sets.

### Optional app settings

| Setting | Default | Purpose |
|---|---|---|
| `MAX_CONCURRENT` | `20` | Concurrent requests allowed before HTTP 503 |
| `UTC_OFFSET_MINUTES` | `330` (IST) | Campus time zone. Azure runs in UTC, and this decides which slots are past |

## Before the demo

- **Showing the 503:** with `--threads 8`, gunicorn runs at most 8 requests at once and queues the rest outside the app, so the in-app counter can never pass 20. In testing, 1,500 requests from 200 parallel clients produced no 503s, and `--threads 32` produced none either because requests finish too quickly. To show the rejection, set `MAX_CONCURRENT=6`, which gave 267 rejections out of 1,500 under the same load. The new value also applies to `/health`, so a heavy load test can lower availability on `/sla`.
- **Wake the app first:** Free F1 has no Always On, so the app sleeps after about 20 idle minutes and the next visit is slow. Open it a few minutes before the demo.
- **`/sla` numbers are in memory:** they reset whenever the app restarts or sleeps. Bookings do not.
- **F1 quota:** the plan allows 60 CPU minutes per day. Hidden browser tabs stop polling to save it.

## Which Module 4 concept each feature demonstrates

| Feature | Concept |
|---|---|
| Azure App Service deployment | Platform as a Service |
| SQLite on `/home` | Persistent storage on a stateless platform |
| `UNIQUE(court_id, date, slot_time)` and `BEGIN IMMEDIATE` | Concurrency control and atomic transactions |
| Daily limit, past-slot check, 503 when overloaded | Admission control |
| 3-second grid refresh | Shared state and consistency across clients |
| `map_phase`, `shuffle_phase`, `reduce_phase` on `/admin` | MapReduce programming model |
| Utilisation % on `/admin` | Resource utilisation |
| Response-time middleware, p95, 500 ms SLO on `/sla` | Service level objectives and QoS |
| `/health` pings and availability % | Cloud monitoring |
| 99.9% allowed downtime, SLA met or violated badge | Service level agreements |
| About page | Comparing AWS, Azure and GCP services |
