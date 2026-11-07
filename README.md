# Translation Keyboard

A keyboard-style web app. Pick a target language or dialect, type in your own
language, and a translation streams in about 400 ms after you stop typing. It
aims to write what a native speaker would actually send, with local greetings,
politeness rules and idioms, not a word-for-word rendering.

> **Want it online?** Follow [Put it online](#put-it-online-github-pages--render-no-command-line).
>
> **Status: MVP, not yet reviewed by native speakers.** Every language profile
> is marked `needs_native_review`. Don't launch publicly until the checks in
> [Native review before launch](#native-review-before-launch) are done.

## Languages

| Region | Languages | Scripts |
|---|---|---|
| West Africa | Hausa, Yoruba, Igbo, Nigerian Pidgin | Latin |
| North Africa | Moroccan Darija, Egyptian Arabic | Arabic or Latin letters |
| Gulf | Saudi Arabic (urban Najdi, some Hijazi) | Arabic or Latin letters |
| Levant | Levantine Arabic (shared urban forms) | Arabic or Latin letters |
| East Africa | Swahili | Latin |
| Europe | French (Metropolitan) | Latin |

Users can type in any language. "Check and explain" answers in the language
they typed in.

## How it works

```
browser (web/)  ──POST /api/translate──▶  FastAPI (app/main.py)
   400 ms debounce                         ├─ access code, rate limits, daily caps (app/security.py)
   streams NDJSON  ◀── chunk, chunk… ───── └─ engine (app/engine.py) ──▶ Claude API
                                                 uses profiles in app/languages.py
```

**Quality approach (app/engine.py)**

1. **Intent first.** The model writes short private notes inside `<intent>`
   covering what the writer wants, the emotion and the likely relationship.
   Only then does it write the message inside `<message>`. The server streams
   only the `<message>` part, so the browser never sees the notes.
2. **Native voice.** The prompt includes the dialect profile (voice,
   greetings, politeness, idioms, things to avoid, 3 examples). It also sets
   the chosen tone, the script, and who you're writing to (a man, a woman or a
   group), because Arabic, Hausa and French change forms by gender and number.
3. **Second pass ("Check and explain").** A reviewer prompt explains the
   message back in the writer's language, adds cultural notes, flags anything
   that sounds unnatural (calques, Modern Standard Arabic creeping in, the
   wrong formality) and gives a low/medium/high confidence.
4. **Text is data.** User text goes inside `<source>` tags and is never treated
   as instructions to the model.

## Quick start (VS Code, Windows / Mac / Linux)

You need **Python 3.10 or newer** ([python.org](https://www.python.org/downloads/); on Windows tick
"Add python.exe to PATH") and VS Code with the **Python** and **Live Server** extensions
(VS Code suggests them when you open the folder).

### Option 1: just see the page (no Python)

1. Open the `translation-keyboard` folder in VS Code.
2. Click **Go Live** in the bottom-right corner (Live Server).
   `.vscode/settings.json` already points Live Server at the `web/` folder.
3. The page opens at `http://127.0.0.1:5500` in **Preview mode**: everything works,
   but translations are placeholders because no server is running.

### Option 2: real app (Python server + Live Server or the server's own page)

In the VS Code terminal (**Terminal > New Terminal**):

```bash
# 1. create a virtual environment (once)
python -m venv .venv
#    Windows:      .venv\Scripts\activate
#    Mac / Linux:  source .venv/bin/activate

# 2. install (once)
python -m pip install -r requirements-dev.txt

# 3. settings (once): copy the example file
#    Windows:      copy .env.example .env
#    Mac / Linux:  cp .env.example .env
#    then open .env and fill in ANTHROPIC_API_KEY and ACCESS_CODES
#    (leave the key empty to try the free mock engine first)

# 4. start the server
python -m uvicorn app.main:app --reload --port 8000
```

Then either open **http://localhost:8000** (the server serves the page itself) or
click **Go Live**: the Live Server page finds the server on port 8000 by itself.
You can also press **F5** (launch config "Run Translation Keyboard server") or use
**Terminal > Run Task > Start server**.

Run the tests with `python -m pytest` (or **Terminal > Run Task > Run tests**).

> Opening `web/index.html` by double-clicking it (a `file://` address) won't work:
> browsers block what the page needs. Use Live Server or the Python server.

## Put it online: GitHub Pages + Render (no command line)

GitHub Pages shows the page. A free **Render** server holds your Claude API key
and does the translating, because GitHub Pages can't run Python or keep a key
secret. Total time is about 20 minutes.

### A. Upload to GitHub (5 min)

1. On github.com click **+ > New repository**. Name it `translation-keyboard`
   and choose **Public**: free GitHub Pages needs a public repo. The code holds
   no secrets, because your key goes only on Render. Don't add a README, then
   click **Create repository**.
2. On the new, empty repo page click **uploading an existing file**.
3. Unzip `translation-keyboard.zip` on your computer and open the
   `translation-keyboard` folder. Select **everything inside it** (Ctrl+A, or
   Cmd+A on Mac) and drag it into the browser.
   - Make sure `.github`, `.gitignore` and `.nojekyll` are included.
   - On a Mac, press Cmd+Shift+. in Finder to show files that start with a dot.
4. Click **Commit changes**.
5. Go to **Settings > Pages**. Under "Build and deployment" choose **Deploy
   from a branch**, Branch **main**, folder **/ (root)**, then click **Save**.
6. After 1–2 minutes your page is at
   `https://YOUR-NAME.github.io/translation-keyboard/`. It will say **"Almost
   there"**, which is expected until part C.

### B. Start the server on Render (10 min)

1. Get a Claude API key at **console.anthropic.com > API Keys**. The account
   needs billing credit.
2. Sign up at **render.com** with your GitHub account.
3. Click **New > Web Service**, pick your `translation-keyboard` repo, and
   grant Render access if asked.
4. Fill in the form:
   - **Language:** Docker. It's detected from the `Dockerfile`.
   - **Region:** the one nearest your users (Frankfurt is closest to West
     Africa).
   - **Instance type:** Free.
5. Under **Environment Variables**, add:

   | Name | Value |
   |---|---|
   | `ANTHROPIC_API_KEY` | your key (starts with `sk-ant-`) |
   | `ACCESS_CODES` | one or more long made-up codes separated by commas, e.g. `amina-7Qp2xL9v,team-K3m8Rw1z` |
   | `ALLOWED_ORIGINS` | `https://YOUR-NAME.github.io` (your Pages address, **without** `/translation-keyboard`) |

6. Under **Advanced**, set **Health Check Path** to `/api/health`. Click
   **Deploy Web Service**.
7. Wait until it says **Live** (3–5 minutes). Copy its address, e.g.
   `https://translation-keyboard-abcd.onrender.com`.
8. Check it: open that address with `/api/health` on the end. You should see
   `"status":"ok"` and `"engine":"claude"`.

### C. Connect the page to the server (2 min)

1. In your GitHub repo open `web/config.js` and click the **pencil (Edit)**.
2. Change `apiBase: "",` to your Render address, e.g.
   `apiBase: "https://translation-keyboard-abcd.onrender.com",`. Don't add a
   slash at the end.
3. Click **Commit changes**. Wait 1–2 minutes for Pages to update.
4. Open your Pages address, enter one of your access codes, and type.

Share the Pages link plus an access code with each person you want to let in.
The Render address works on its own as well: it serves the same page, so you
can use that and keep the GitHub repo private.

### If something doesn't work

| What you see | Fix |
|---|---|
| "Almost there" banner | `apiBase` in `web/config.js` is empty; do part C. |
| "Connecting… can take up to a minute" | Normal on the free plan after about 15 minutes idle. Wait. |
| "Can't reach the server" | Check that the Render service is Live. Check that `ALLOWED_ORIGINS` exactly matches the address in the message (https, no trailing slash, no path). Save, and Render redeploys by itself. |
| "Demo mode" banner | `ANTHROPIC_API_KEY` isn't set on Render. Add it under Environment. |
| "This server has no access codes set" | Add `ACCESS_CODES` on Render. |
| "That code didn't work" | The code must match one in `ACCESS_CODES` exactly. After 10 wrong tries, wait 10 minutes. |
| "The translation service is unavailable" | Key wrong or out of credit. Check console.anthropic.com. |
| Pages shows a 404 | Wait 2 minutes. Check that Settings > Pages uses branch `main`, folder `/ (root)`, and that `index.html` sits at the top of the repo. |
| Red ✗ next to a commit on GitHub | The automatic tests failed. Open the **Actions** tab, copy the error, and ask for help. The site may still work. |

### With git instead of uploading (optional)

```bash
git init && git add . && git commit -m "Translation Keyboard"
git branch -M main
git remote add origin https://github.com/YOUR-NAME/translation-keyboard.git
git push -u origin main
```

## Tests

```bash
python -m pytest
```

If you edit `app/languages.py`, run `python -m app.export_languages` to refresh
`web/languages.json` (used by Preview mode). A test reminds you if you forget.

The tests never call the real API. They cover the profiles, the prompts, the
stream filter that hides the intent notes, the explain parser, rate limits,
daily caps, lockout after wrong codes, input checks, the HTTP API (streaming,
validation, security headers), a check that message text never reaches the
logs, and the eval CSV.

## Security and privacy

- **API key:** read from an environment variable on the server only. It is
  never sent to the browser and never in the repo. CI fails if a key-like
  string is committed.
- **Access codes:** checked in constant time. After 10 wrong codes in 10
  minutes an IP is locked out, and after 200 wrong codes in 10 minutes across
  all IPs every IP is locked out. The browser keeps the code in memory only.
- **Rate limits:** 40 requests per minute per IP and 60 per minute per code.
  The daily cap is 1,000 per code and 10,000 overall, resetting at midnight
  UTC. All are configurable.
- **Abuse checks:** request bodies are limited to 16 KB, messages to 1,000
  characters, control characters are stripped, and obviously repetitive or
  automated input is rejected.
- **No message logging:** the app logs only method, path, status and timing.
  Validation errors don't echo input. Engine errors log the exception type
  only. Uvicorn's access log is off.
- **No storage:** nothing is written to disk or a database. "Recent" lives in
  the tab's memory and disappears when the tab closes.
- **CORS:** only the addresses in `ALLOWED_ORIGINS` (default: Live Server on port 5500)
  can call the API from another site.
- **Browser hardening:** strict Content-Security-Policy (no inline scripts, no
  third-party resources), `X-Frame-Options: DENY`, `no-referrer`, HSTS, and
  `no-store` on API responses.
- **Third party:** messages are sent to Anthropic to be translated. Their data
  retention terms apply; check them and mention this in your privacy notice.

## Evaluation for native reviewers

`eval/sentences.json` holds 30 test sentences: greetings, condolences,
business requests, negotiation, jokes and teasing, an English idiom, apologies,
thanks, congratulations, a request to an elder, an invitation, a boundary, and
one with an emoji and a link.

```bash
python -m eval.run_eval --languages ha,ary,arz,ar-SA,apc --scripts both --out eval/review.csv
python -m eval.run_eval --languages all --mock     # check the layout for free
```

The CSV opens in Excel or Google Sheets (UTF-8 with BOM, so Arabic displays
correctly). It has 1–5 score columns for **meaning, tone, naturalness and
originality**, plus "better version", notes, initials and the reviewer's
region. Ask at least two reviewers per language, from the right country or
region. Generated CSVs are git-ignored.

## Native review before launch

For each language, native speakers (ideally two, from the target
region) should check:

1. **Greetings.** Are the greetings in the profile the ones people really use
   today, and in the right situations (morning vs. any time, elders vs.
   friends)?
2. **Respect words.** Are the titles and polite forms right, and is anything
   old-fashioned or too stiff? Examples: Malam/Hajiya in Hausa, ẹ vs o in
   Yoruba, 7adretak in Egyptian, Tal 3umrak in Saudi, tu vs vous in French.
3. **Idioms.** Is each idiom real and current, does it mean what we say, and
   is it safe to use in the situation we list? A wrong proverb is worse than
   none.
4. **The 3 examples per language.** Would you actually send each one? Fix
   any that sound translated.
5. **Spelling.**
   - Hausa: hooked letters ɓ ɗ ƙ ƴ
   - Yoruba: every tone mark and under-dot
   - Igbo: ị ọ ụ ṅ
   - Arabic dialects: dialect spelling, not Modern Standard Arabic
6. **Latin-letter Arabic.** Are the number-letters (3, 7, 9, 2) the ones
   people in that country use when texting?
7. **Condolences and religion.** Are condolence and blessing formulas correct,
   respectful and suitable for people of other faiths where relevant?
8. **Gender and plural.** Do "To: a man / a woman / a group" produce correct
   forms? Is the "anyone" default acceptable?
9. **Dialect drift.** Do Egyptian or MSA words leak into Darija, Saudi or
   Levantine output (and the other way round)? Is "Levantine" acceptable to
   Lebanese, Syrian, Jordanian and Palestinian readers, or do we need separate
   options?
10. **Humour (playful tone).** Is it actually funny and never insulting?
11. **The "Check and explain" notes.** Are the cultural notes true? Do the
    confidence labels match your own judgement?
12. **Score the eval CSV.** A sensible launch bar is an average of 4 or more
    for meaning and naturalness, with no 1s on condolence rows.

When a profile passes, set `needs_native_review=False` and fill `reviewed_by`
with initials and the date in `app/languages.py`.

## Known weak spots (honest list)

- **Not verified.** The profiles were drafted without native review. Some
  greetings, idioms or spellings may be wrong or dated.
- **Lower-resource languages.** Hausa, Yoruba, Igbo, Nigerian Pidgin and
  Moroccan Darija have much less good text online. Expect more unnatural
  phrasing, missing tone marks or diacritics, and wrong gender agreement. The
  app shows "Less data" next to these.
- **Dialects are simplified.** One variety each: no Sa'idi Egyptian, no
  regional Darija, no separate Lebanese/Syrian/Jordanian/Palestinian, Najdi as
  the default for Saudi, standard-ish Igbo, Metropolitan French.
- **Latin-letter Arabic varies** from person to person; no spelling is
  "correct".
- **The AI checker isn't a native speaker.** It can miss problems or flag fine
  text, and a "high" confidence is the model's opinion only.
- **Gender** is unknown unless the user sets "To:", so some output may assume
  the wrong form.
- **Limits are in memory.** They reset on every deploy or restart and don't
  work across several instances. Use Redis if you scale out.
- **IP-based limits can be fooled** by someone forging `X-Forwarded-For`. The
  per-code limits, daily caps and global lockout still apply. Use long random
  codes.
- **Cost.** Each pause while typing is one API call. The debounce, the
  "skip if unchanged" check and the caps keep this down, but watch your bill.
- **Speed.** The intent-first step adds a little delay before the first words
  appear. A smaller model (`ANTHROPIC_MODEL`) is faster but likely weaker on
  lower-resource languages.

## Project layout

```
app/main.py        FastAPI app, routes, headers, logging without message text
app/engine.py      prompts, intent-first stream filter, Claude + mock engines, explain pass
app/languages.py   per-dialect profiles (needs native review)
app/security.py    access codes, rate limits, daily caps, input checks
web/index.html     page + styles (no build step)
web/app.js         picker, tones, script toggle, streaming, explain, recent (memory only)
web/config.js      optional server address (for GitHub Pages)
web/languages.json language list for Preview mode (generated)
.vscode/           Live Server root, F5 launch, tasks, recommended extensions
eval/              30 test sentences + CSV generator for reviewers
tests/             pytest suite
Dockerfile, render.yaml, .github/workflows/ci.yml, .github/workflows/pages.yml
```
