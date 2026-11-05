# CourtBook: What You Need To Do

**You don't need to create an Azure account or install anything.** CourtBook is already live on Azure under Chinmay's account. All you need is a phone or laptop with a browser.

**Live site:** <https://courtbook-brooxxhh-g2hug8hkhnaze3gq.indiasouthcentral-01.azurewebsites.net>

CourtBook is a campus court booking app. Students book 30-minute slots on 4 courts, everyone sees the same live grid, and two people can't get the same slot.

## Your to-do list

### 1. Try the site (5 minutes)

1. Open the link on your phone.
2. On **Book**, tap a green slot and enter your name and registration number.
3. Open **My Bookings**, enter the same registration number, and cancel the booking.
4. Open **Admin**, **SLA** and **About** to see what each page shows.

### 2. Read the demo notes (20 minutes)

Open [CourtBook_Demo_and_Viva.pdf](CourtBook_Demo_and_Viva.pdf). It has the 5-minute talk and the viva questions with answers. On GitHub, click the file to read it, or use the download button.

Be ready for the viva even if you aren't presenting, because ma'am can ask either of you. Focus on these first:

- Why this project is PaaS
- How double booking is prevented
- Admission control
- Map, Shuffle and Reduce
- SLA, SLO and p95

### 3. Agree your part with Chinmay

Decide who speaks and who handles the phones. The easiest split is that Chinmay presents and you do the two live tests below.

### 4. Do the live tests on demo day

You need your phone, with the site open and tested. Use your own name and registration number.

**Double booking test**

1. Pick the same free slot as Chinmay, on the same court, time and day.
2. Both of you fill in the form.
3. Tap **Book slot** at the same moment.
4. One of you gets the booking. The other sees "Slot just taken by someone else – please pick another".

**Daily limit test**

Book 3 slots on the same day with one registration number. The third shows "Daily limit reached – admission denied".

If you run this test and already hold bookings, use another day's tab or a different test registration number.

## Please don't

- **Run load tests** or refresh the site automatically. The Free plan has a daily CPU limit, and the site stops if it runs out.
- **Book slots for fun just before the demo.** Each student is limited to 2 per day, and the live data shows up on the Admin page.
- **Share the link widely.** There is no login, so anyone who has it can book.

## If something goes wrong

| What you see | What to do |
|---|---|
| Site is slow to open | Wait up to a minute. The Free plan sleeps when nobody is using it |
| "503 Service Unavailable" page | Wait a few minutes and reload, because Azure is starting the app. If it stays, tell Chinmay |
| "This web app is stopped" | The daily CPU limit ran out. Tell Chinmay and use the screenshots |
| "Server busy – try again" | Try again after a moment. This is the app's own overload protection working |

## Only if you want to see the code

This part is optional. The code is at <https://github.com/Chinmay0801/Cloud_Project>, and `app.py` holds all of the server code.

To run your own copy, you need Python 3.11 or newer:

```
git clone https://github.com/Chinmay0801/Cloud_Project.git
cd Cloud_Project
pip install -r requirements.txt
python app.py
```

Then open <http://localhost:5000>. This copy uses a separate database on your laptop, so it won't affect the live site.

Only Chinmay can update the live site. If you change the code, send the change to Chinmay to deploy.

For deployment details and full troubleshooting, see [PROJECT_GUIDE.md](PROJECT_GUIDE.md).
