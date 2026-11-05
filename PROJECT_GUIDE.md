# CourtBook Project Guide

Everything you need to run CourtBook, deploy it to Azure, and show it in the project demo.

**Live site:** <https://courtbook-brooxxhh-g2hug8hkhnaze3gq.indiasouthcentral-01.azurewebsites.net>

**Repository:** <https://github.com/Chinmay0801/Cloud_Project>

Helping with the demo? Start with [FRIEND_GUIDE.md](FRIEND_GUIDE.md). For the 5-minute talk and viva questions, see [CourtBook_Demo_and_Viva.pdf](CourtBook_Demo_and_Viva.pdf).

**In this guide**

1. [What this project is](#1-what-this-project-is)
2. [Run it on your laptop](#2-run-it-on-your-laptop)
3. [Deploy it to Azure](#3-deploy-it-to-azure)
4. [Prove it is running on Azure](#4-prove-it-is-running-on-azure)
5. [Demo script](#5-demo-script)
6. [How each feature works](#6-how-each-feature-works)
7. [Questions you may be asked](#7-questions-you-may-be-asked)
8. [Fixing common problems](#8-fixing-common-problems)
9. [Sharing the code with GitHub](#9-sharing-the-code-with-github)

---

## 1. What this project is

CourtBook lets students book 30-minute slots on campus sports courts from their phones. Everyone sees the same live grid, and two people can never get the same slot.

The cloud part is the main point of the project:

| What | How it is done |
|---|---|
| Hosting | **Azure App Service**, Linux, Python 3.15, Free F1 plan |
| Cloud model | **PaaS**: we upload code and Azure runs the servers, operating system and Python |
| Storage | SQLite file on Azure's persistent `/home` storage |
| Monitoring | **Azure Monitor** metrics, plus our own `/sla` page |
| Web server | Gunicorn, started by Azure with our startup command |

**Files**

| File | Purpose |
|---|---|
| `app.py` | All the server code |
| `templates/` | The web pages: `index` (Book), `my`, `admin`, `sla`, `about`, plus the shared `base` layout |
| `requirements.txt` | Python packages Azure installs |
| `startup.txt` | A copy of the startup command |
| `README.md` | Short project summary |

---

## 2. Run it on your laptop

You need Python 3.11 or newer (3.13 and 3.15 are tested). Open a terminal in the project folder and run:

```
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:5000**.

To open it on your phone, connect the phone to the same Wi-Fi and go to `http://<your-laptop-ip>:5000`. Run `ipconfig` to find the IPv4 address. Windows Firewall may ask for permission the first time.

Bookings are saved in `courtbook.db` in the project folder. Delete that file to start fresh. It is not uploaded to GitHub.

---

## 3. Deploy it to Azure

**What you need**

- An Azure account. Students can use **Azure for Students** at <https://azure.microsoft.com/free/students>, which normally needs only a college email and no credit card.
- VS Code with the **Azure App Service** extension.

**Steps**

1. Open the project folder in VS Code.
2. Click the Azure icon in the left side bar and sign in.
3. Under **App Service**, right-click your subscription and choose **Create New Web App**.
4. Enter a unique name, such as `courtbook-yourname`.
5. Choose **Python 3.15** (3.11 also works) and the **Free (F1)** tier.
6. Open <https://portal.azure.com>, find your app, and set the startup command in **Settings → Configuration → General settings**:

   ```
   gunicorn --bind=0.0.0.0 --timeout 600 --workers 1 --threads 8 app:app
   ```

   Click **Save**.
7. In **Settings → Environment variables**, add these two settings if they are missing, then click **Apply**:

   | Name | Value | Why |
   |---|---|---|
   | `SCM_DO_BUILD_DURING_DEPLOYMENT` | `true` | Makes Azure install `requirements.txt` |
   | `MAX_CONCURRENT` | `6` | Makes the "Server busy" rejection possible to show ([why](#why-max_concurrent-is-6)) |

8. Back in VS Code, right-click your web app, choose **Deploy to Web App**, and select the project folder.
9. Wait for the "Deployment successful" message, then open your address. Azure adds a random suffix to new app names, so copy the address from **Default domain** on the portal's Overview page. The first load can take a minute, and a "503 Service Unavailable" page straight after deploying usually clears within a few minutes.

Azure occasionally renames portal menus. If you can't find one, use the search box at the top of the app's menu.

**If you are outside India:** add `UTC_OFFSET_MINUTES` to the environment variables with your offset from UTC in minutes. The default is `330` (IST), and it decides which slots count as past.

---

## 4. Prove it is running on Azure

Do these in order. They go from easiest to most convincing. Take screenshots beforehand as a backup in case campus Wi-Fi fails.

### The address
Open <https://courtbook-brooxxhh-g2hug8hkhnaze3gq.indiasouthcentral-01.azurewebsites.net> on a phone using mobile data. It works with your laptop closed, so it clearly isn't running on your computer.

### The app's About page
Open **About** on the live site. The **Live deployment** card shows the app name, region, plan and Python version. The running app reads these from Azure. On a laptop, the same card says "Running locally".

### The Azure Portal
Open your app at <https://portal.azure.com> and show:

| Where | What to point out |
|---|---|
| **Overview** | Status Running, Linux, Free F1 plan, resource group, region |
| **Configuration → General settings** | The gunicorn startup command |
| **Environment variables** | `MAX_CONCURRENT` |
| **Deployment Center** or its logs | Your deployment history |

### Live logs
Open **Monitoring → Log stream** in the portal, keep it on screen, and book a slot on your phone. The request appears in the Azure logs.

If nothing appears, turn on **Monitoring → App Service logs → Application logging (File System)** first, wait a minute and try again.

### Azure Monitor charts
Open **Monitoring → Metrics** and add the **Requests** and **Response Time** metrics. The chart climbs while classmates are using the app. This is Azure's own measurement, and you can compare it with your `/sla` page. Metrics can take a few minutes to appear, so generate some traffic before class.

### Persistent storage
This is the best proof, because it shows a real cloud concept:

1. Book a slot, and note the **Total requests** number on `/sla`.
2. Click **Restart** on the portal's Overview page and wait about a minute.
3. Open the site again. **The booking is still there**, because it is saved on Azure's persistent `/home` storage.
4. Open `/sla`. **The counters have reset**, because they were only in memory.

You can also show the database file itself. In the portal, open **Development Tools → Advanced Tools → Go**, or go to <https://courtbook-brooxxhh-g2hug8hkhnaze3gq.scm.indiasouthcentral-01.azurewebsites.net>. Open the SSH or Bash console and run:

```
ls -la /home/data
```

---

## 5. Demo script

This takes about 8 minutes. Before class:

- [ ] Open the site 5 minutes early, because Free F1 sleeps after about 20 idle minutes
- [ ] Log in to the Azure Portal in another tab
- [ ] Make a QR code of your address for classmates to scan
- [ ] Make sure `MAX_CONCURRENT` is set to `6`
- [ ] Keep your screenshots ready

**Steps**

1. **Introduce it (30 seconds).** "CourtBook is a slot booking system hosted on Azure App Service using the PaaS model."
2. **Show Azure.** Show the portal Overview, then the About page's Live deployment card.
3. **Live users.** Classmates scan the QR code and book slots. Everyone's grid updates within 3 seconds.
4. **Double booking.** Two people open the same free slot and tap **Book slot** together. One succeeds, and the other sees "Slot just taken by someone else – please pick another".
5. **Daily limit.** Book a third slot on one day with the same registration number. It shows "Daily limit reached – admission denied".
6. **MapReduce.** Open **Admin**. Walk through Map, Shuffle and Reduce, then show the peak hour and most popular court.
7. **Overload.** Run the [load test](#load-test), then open **SLA** and show the Server busy count rising.
8. **SLA.** Explain response times, availability, the 43.2 minutes of allowed downtime per month, and the SLA badge.
9. **Persistence.** Restart the app from the portal and show the booking survived.

The load test can lower availability on `/sla`, because health checks can get rejected too. That is real behaviour and you can say so. Run it last if you want the badge to stay green during the SLA step.

### Load test

Save this as `load_test.py` outside the project folder:

```python
import urllib.request, urllib.error
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

URL = "https://courtbook-brooxxhh-g2hug8hkhnaze3gq.indiasouthcentral-01.azurewebsites.net/admin"

def hit(_):
    try:
        return urllib.request.urlopen(URL, timeout=30).status
    except urllib.error.HTTPError as error:
        return error.code
    except Exception:
        return "failed"

print(Counter(ThreadPoolExecutor(200).map(hit, range(1500))))
```

Run it with `python load_test.py`. The output counts each result, such as `{200: 1400, 503: 100}`. The numbers change on every run, and any `503` entries are the rejected requests.

---

## 6. How each feature works

| Feature | How it works | Where in `app.py` | Concept |
|---|---|---|---|
| Live grid | The browser fetches `/api/slots` every 3 seconds | `api_slots` | Shared state across clients |
| No double booking | The database allows one row per court, date and slot, so a second insert fails | `UNIQUE` in `init_db`, `api_book` | Atomic transactions and concurrency control |
| Daily limit | Counts the student's bookings inside the same transaction as the insert | `api_book` | Admission control |
| Past slot check | Compares the slot with campus time | `is_past` | Admission control |
| Server busy | A counter tracks requests in progress, and extras get HTTP 503 | `admit_request` | Admission control, overload protection |
| Peak hours report | Three separate steps turn bookings into totals | `map_phase`, `shuffle_phase`, `reduce_phase` | MapReduce |
| Response times | Timed before and after every request | `admit_request`, `record_response_time` | SLO and QoS |
| Availability | A background thread calls `/health` every 30 seconds | `health_monitor` | Cloud monitoring |
| SLA badge | Green if availability is at least 99.9% and p95 is under 500 ms | `sla` | SLA |

**Key terms**

- **SLA** is the promise, such as 99.9% availability.
- **SLO** is a measurable target behind it, here responses under 500 ms.
- **p95** means 95% of requests were faster than this time. It shows the slow cases that an average hides.
- **99.9% allowed downtime** is 0.1% of a 30-day month: 30 × 24 × 60 × 0.001 = **43.2 minutes**.
- **MapReduce** here works like this:
  - **Map:** each booking emits `(Court: Gym, 1)` and `(Hour: 6 PM, 1)`.
  - **Shuffle:** matching keys are grouped, giving `Court: Gym → [1, 1, 1]`.
  - **Reduce:** each group is summed, giving `Court: Gym → 3`.

### Why MAX_CONCURRENT is 6

The project specification says to reject requests above 20 at once, and that is the default in the code. But the startup command gives Gunicorn only 8 threads, so at most 8 requests are inside the app at a time, and the others wait in a queue outside it. The counter can therefore never pass 20.

We tested this with 1,500 requests from 200 parallel clients and got no rejections. Setting `MAX_CONCURRENT=6` puts the limit below the thread count, so the rejection can actually happen.

---

## 7. Questions you may be asked

**Which cloud service model is this?**
PaaS. Azure manages the servers, OS and runtime. We only provide the code and settings. On IaaS, such as a virtual machine, we would manage the OS ourselves.

**Why Azure App Service instead of a virtual machine?**
There are no servers to maintain, deployment is simple, and monitoring is built in. The Free tier also suits a student project.

**Why is the database in `/home/data`?**
On App Service, files elsewhere can be lost when the app restarts or redeploys. `/home` is persistent storage that stays.

**What is the AWS or GCP equivalent?**
App Service matches Elastic Beanstalk and App Engine. SQLite on persistent storage is in the place of RDS and Cloud SQL. Azure Monitor matches CloudWatch and Cloud Monitoring.

**How do you stop two people booking the same slot?**
The database has a `UNIQUE(court_id, date, slot_time)` rule, so the check and the insert happen as one atomic step. Checking first in Python would leave a gap where both users pass.

**Why one worker and 8 threads?**
The request counters and SLA numbers are stored in memory. Each worker is a separate process with its own memory, so several workers would each show different numbers. Threads share memory.

**How would you scale this for a whole university?**
- Move to a paid plan, because Free F1 can't scale out.
- Replace SQLite with a managed database such as Azure Database for PostgreSQL or Azure SQL.
- Move counters to a shared store such as Azure Cache for Redis.
- Then add more instances behind App Service's load balancer.

**What are the limits of this project?**
- Free F1 sleeps when idle and allows 60 CPU minutes per day.
- `/sla` numbers reset on restart.
- `/admin` has no login.
- Anyone who knows a registration number can see and cancel that student's bookings.
- Availability is measured from inside the app, so it can't detect a full outage. A real system would add an outside monitor such as Azure Application Insights availability tests.

**What is the difference between `/sla` and Azure Monitor?**
`/sla` is measured inside our app. Azure Monitor is measured by the platform. Showing both lets you compare them.

---

## 8. Fixing common problems

| Problem | Likely cause | Fix |
|---|---|---|
| `not registered to use namespace 'Microsoft.OperationalInsights'` when creating the app | New subscriptions don't have Azure's logging service switched on | In the portal, open **Subscriptions → your subscription → Settings → Resource providers**, then register `Microsoft.OperationalInsights` and `Microsoft.Insights`. When both show **Registered**, create the app again |
| "Application Error" page | App failed to start | Open **Log stream** and read the error |
| `No module named flask` in the logs | Requirements weren't installed | Set `SCM_DO_BUILD_DURING_DEPLOYMENT=true` and deploy again |
| Default Azure welcome page | Startup command missing, or code not deployed | Check step 6 of the deployment, then deploy again |
| Your Python version or F1 isn't offered | Region limits | Create the app in another region |
| "This web app is stopped" (403) | Free CPU quota used up | Wait for the daily reset, or deploy under another account |
| First load is very slow | App was asleep | Normal on F1. Open it before the demo |
| Current slots show as past or future | Wrong time zone | Set `UTC_OFFSET_MINUTES` |
| `/sla` shows no availability | App just started | The first check runs after about 5 seconds, so refresh |
| No 503s in the load test | `MAX_CONCURRENT` is still 20 | Set it to `6`. Azure restarts the app automatically |
| `pip` isn't recognised | Python isn't on PATH | Use `python -m pip install -r requirements.txt` |

---

## 9. Sharing the code with GitHub

The code is at <https://github.com/Chinmay0801/Cloud_Project>. Your friend doesn't need an Azure account, because the live site runs on one account and everyone uses the same link. See [FRIEND_GUIDE.md](FRIEND_GUIDE.md).

**To run the code on another laptop**

```
git clone https://github.com/Chinmay0801/Cloud_Project.git
cd Cloud_Project
pip install -r requirements.txt
python app.py
```

**After changing the code**

```
git add .
git commit -m "Describe your change"
git push
```

Pushing to GitHub doesn't update Azure. Deploy again from VS Code to update the live site.
