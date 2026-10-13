# Showing what the Enki app sends

Sometimes a device works in the Enki app and not in Home Assistant. When that happens the
integration is almost certainly calling the wrong address, with the wrong payload, or on the wrong
service — and the only way to know which is to look at what the app itself sends.

This page is for that. You do not need to be a developer to follow it, and nothing here touches
your Home Assistant.

## First, check whether you need it

Most reports are answered without any of this. Try these in order and stop as soon as one gives an
answer:

1. **Diagnostics.** Settings → Devices & services → Enki → your device → the three dots →
   *Download diagnostics*. Attach the file to the issue. It is anonymized: no password, no token,
   no home id. It shows every capability your device declares and what the last poll read.
2. **Debug logs.** Add `enki: debug` to your logger configuration, reproduce the problem, attach
   the log.
3. **A one-line experiment**, when asked: toggle one entity at a time and say which, if any, moves
   the physical device.

Only when those leave the question open does a capture help — and then it answers it completely.

## The ground rules

Three of them, and they are not negotiable:

- **Your account, your devices.** Capture your own traffic, from your own phone, signed in to your
  own Enki account. Never someone else's.
- **Nothing is bypassed.** If the app refuses to work while the proxy is on, that is the app
  checking its own certificate, and that is where we stop. Do not install a patched Enki app and do
  not root your phone for this. Report that it happened — it is an answer in itself.
- **Your secrets stay yours.** Never capture or post your password or an access token, and remove
  the identifiers listed further down before posting. What we need is the address and the payload,
  nothing that identifies you.

The point of all this is interoperability: making your devices work with Home Assistant. See the
[disclaimer](DISCLAIMER.md#legal-basis) for the footing this project stands on.

## What a capture is

A small program on your computer sits between your phone and the internet and writes down the
requests your phone makes. You press a button in the Enki app, and you can read the exact request
it sent. That program is [mitmproxy](https://mitmproxy.org/), it is free, and you remove it when
you are done.

You will need:

- a computer and a phone **on the same Wi-Fi**;
- about twenty minutes the first time;
- an **iPhone or iPad**, realistically. See the Android section for why.

## Set up the computer

Install mitmproxy:

- **macOS**: `brew install mitmproxy`
- **Windows**: the installer from [mitmproxy.org](https://mitmproxy.org/)
- **Linux**: your package manager, or `pipx install mitmproxy`

Start it:

```bash
mitmweb
```

That opens a page in your browser. Leave it open — that is where the requests will appear.

Now find your computer's address on the Wi-Fi:

- **macOS**: `ipconfig getifaddr en0`
- **Windows**: `ipconfig`, then the *IPv4 Address* of your Wi-Fi adapter
- **Linux**: `hostname -I`

It looks like `192.168.1.24`. Write it down.

## Set up an iPhone or iPad

**1. Send the phone's traffic through the computer.**

Settings → Wi-Fi → the small **ⓘ** next to your network → *Configure Proxy* → **Manual**.
Server: your computer's address. Port: `8080`. Save.

**2. Install mitmproxy's certificate.**

Open Safari and go to **http://mitm.it**. If the page does not load, the proxy is not set
correctly — go back to step 1. Tap the Apple icon to download the profile, then
Settings → **VPN & Device Management** → the downloaded profile → *Install*.

**3. Trust it. People miss this step, and nothing works without it.**

Settings → General → **About** → **Certificate Trust Settings** → turn **mitmproxy** on.

Now go to the mitmweb page on your computer and open any website on the phone. If lines appear,
you are set.

## Android

On Android 7 and later, apps ignore certificates you install yourself unless the app explicitly
opts in, and the Enki app does not. So the setup above will show you the phone's browser traffic
and **not** the Enki app's. Getting around it means a rooted phone or a repackaged app, which is
not worth asking anyone to do.

If Android is all you have, say so on the issue. Diagnostics and debug logs answer more than you
would think, and someone with an iPhone and the same device may be able to run the capture
instead.

## Capture the thing we asked about

1. Clear the mitmweb list so it is easier to read (the broom icon).
2. In the mitmweb filter box, type **`adeo`**. Every Enki request goes to one address, and that
   keeps everything else out.
3. On the phone, **do the one action** that was asked — turn the light off, open the live view,
   whatever it was. Do it once.
4. New lines appear. Click the one whose address matches what was asked about, and look at the
   **Request** tab.

## What to paste in the issue

For each request that matters, four things:

- the **method** and the **address**: `POST /api-enki-power-prod/v1/power/<node>/switch-electrical-power?endpoints=1`
- the **body** of the request, if it has one: `{"value":"OFF"}`
- the **status** the server answered: `202`
- the **body** of the answer, when there is one

**Replace these before posting.** They identify you or give access to your account:

| Remove | Looks like | Replace with |
|--------|-----------|--------------|
| `Authorization` header | `Bearer eyJ…` | drop the line entirely |
| your home id | a long id in the address or an `homeId` header | `<home>` |
| your device id | a long id in the address | `<node>` |
| your email, your password | — | never capture them at all |

You can drop every other header too. `X-Gateway-APIKey` is an app key rather than a personal
secret, and the integration already ships them all, so it is of no use here.

When you are done: Settings → Wi-Fi → ⓘ → *Configure Proxy* → **Off**, and delete the mitmproxy
profile in VPN & Device Management.

## When it does not work

- **http://mitm.it does not load.** The proxy is not reaching the computer. Same Wi-Fi? Right
  address? Is `mitmweb` still running? A firewall on the computer may be blocking port 8080.
- **Websites work but the Enki app shows nothing.** On Android, that is the expected outcome above.
  On iOS, check the *Certificate Trust Settings* step.
- **The app shows an error or refuses to connect while the proxy is on.** The app may be checking
  the certificate itself, which a proxy cannot fake. Say so on the issue, and we find another way.

Neither of the last two is a failure on your part. Report what you saw and we work from there.

## Getting an AI assistant to walk you through it

If you would rather be guided step by step, paste the prompt below into ChatGPT, Claude or
whichever assistant you use. Paste it as it is — it starts by asking you about your phone, your
computer and what you are trying to capture, and it adapts from your answers.

<details>
<summary>Prompt to copy</summary>

```text
You are helping me capture one HTTP request from a phone app, for a bug report
on an open-source project. Read all of these instructions before replying.

## Context

The project is a Home Assistant integration for Enki, Leroy Merlin's smart home
system. It talks to Enki's cloud, and sometimes a device works in the official
Enki phone app but not in Home Assistant. That means the integration is calling
the wrong address or sending the wrong payload, and the way to find out is to
read what the app itself sends.

A maintainer asked me to capture that request with mitmproxy and post it on a
GitHub issue. I am not a developer. I have a computer and a phone.

Useful facts about this particular app:
- Every Enki request goes to the host enki.api.devportal.adeo.cloud, so
  filtering captured traffic on "adeo" isolates it from everything else.
- Each request carries an Authorization header with a bearer token, an
  X-Gateway-APIKey header, and often a homeId header. The address usually
  contains the micro-service name, for example api-enki-power-prod, and the
  identifier of one device.
- The maintainer needs the method, the address, the request body, the status
  that came back and the response body. Nothing else.

## Before you give me any instruction

Interview me first. Ask these questions, **one message at a time**, and wait for
my answer before the next one. Do not number them all out at once, and do not
start explaining mitmproxy until you have the answers.

1. What phone do I have, and which operating system version? (If I do not know
   where to find it, tell me where to look.)
2. What computer do I have, Windows, macOS or Linux, and which version?
3. Can I install software on that computer, or is it managed by an employer?
4. Is the phone managed by an employer or a school? (Managed phones often block
   installing certificate profiles, which would stop us.)
5. Are the phone and the computer on the same Wi-Fi network?
6. What exactly did the maintainer ask me to capture? Ask me to paste their
   request in their words.
7. Can I reproduce the problem whenever I want, or does it only happen
   sometimes? (We need to perform the action while the capture is running.)
8. Have I ever used a terminal or command prompt? Answering no is fine, it only
   changes how you phrase things.

## What to do with my answers

- **Android 7 or later.** Stop and tell me plainly, before any setup, that apps
  on modern Android ignore certificates I install myself, so the Enki app's
  traffic will almost certainly not appear. Explain that the alternatives need a
  rooted phone or a repackaged app and are not worth it. Then help me write a
  short note for the issue saying I only have Android, and offer to help me
  produce the Home Assistant diagnostics file instead. Do not walk me through
  mitmproxy anyway "just in case" unless I ask for it.
- **iPhone or iPad.** This is the path that works. Continue.
- **Managed phone or computer.** Warn me that a step may be blocked, tell me
  which one, and agree with me to stop there rather than fighting it.
- **The problem is intermittent.** Plan for it: have me start the capture and
  leave it running, rather than trying to time the action.

## Then walk me through it

One step per message. After each step, ask me what I see and wait. Tell me what
the screen should look like when a step worked, so I can tell you if it does
not. Name menus and buttons exactly rather than describing them. No jargon
without a one-line explanation the first time.

The steps, in this order:

1. Install mitmproxy on my computer, and start it with mitmweb. Tell me what the
   page that opens looks like.
2. Find my computer's address on the Wi-Fi, and have me read it back to you so
   you can sanity-check it. It normally starts with 192.168 or 10.
3. Point the phone's Wi-Fi through it: a manual proxy, my computer's address,
   port 8080.
4. Install mitmproxy's certificate from http://mitm.it on the phone. If that
   page does not load, go back to step 3 with me, do not continue.
5. On iOS, trust the certificate. This is a separate step in a different place
   and it is the one people miss: Settings, then General, then About, then
   Certificate Trust Settings. Confirm with me that the switch is on.
6. Check that interception works at all: have me open any website on the phone
   and tell you whether lines appear in mitmweb.
7. Have me clear the captured list, then filter it on "adeo".
8. Have me perform the one action the maintainer asked about, once.
9. Help me find the right line among the new ones, and read the Request and
   Response tabs out of the mitmweb interface.

## Troubleshooting, when I report a problem

- mitm.it does not load: the proxy is not reaching the computer. Check with me,
  in this order, that both are on the same Wi-Fi, that the address is right,
  that mitmweb is still running, and that the computer's firewall is not
  blocking port 8080.
- Websites appear in mitmweb but nothing from the Enki app: on iOS, the
  certificate trust step. On Android, it is the expected dead end above.
- The Enki app shows a connection error while the proxy is on: the app is
  probably checking the certificate itself, which a proxy cannot fake. Tell me
  that this is a real possibility, not my mistake, and help me report it.

## At the end

Help me write the comment to post, in this shape:

    POST /api-enki-power-prod/v1/power/<node>/switch-electrical-power?endpoints=1
    body: {"value":"OFF"}
    -> 202, no body

Then take me through the redaction, item by item, and ask me to confirm each one
before I post:
- the Authorization header is removed entirely;
- my home id is replaced by <home>, wherever it appears;
- my device id is replaced by <node>, wherever it appears;
- no email address and no password anywhere.

Finally, remind me to undo the setup: turn the proxy off in the phone's Wi-Fi
settings, and delete the mitmproxy profile from the phone.

If we gave up at some point, help me write what we did and where it stopped
instead. That is still useful to the maintainer and I should post it.

## Rules

- Never ask me for my Enki password, my email address or any access token, and
  tell me not to paste them to you. If I paste one by accident, tell me to treat
  it as compromised and to sign out of the Enki app on all devices.
- This is my own phone and my own Enki account. Do not help me capture anyone
  else's traffic.
- If the app will not work while the proxy is on, it is checking its own
  certificate. That is where we stop. Do not suggest a patched version of the
  app, rooting or jailbreaking my phone, or any other way around it, even if I
  ask. Help me report that instead.
- One step at a time. Do not dump the whole procedure in one message, even if I
  seem comfortable.
- If a menu you describe does not exist on my version, ask me what I see instead
  and adapt. Do not insist that it must be there.
- If I say I want to stop, stop, and tell me what is still worth reporting.
```

</details>

The menus in iOS and Android move between versions, so if the assistant describes something you
cannot find, tell it what is on your screen instead of hunting for the name it used. If its steps
and this page disagree, say so on the issue — it means this page needs updating.

## Capturing a gateway key

Same setup, different goal, and it is a maintainer's errand rather than a reporter's:
see [DEVELOPMENT.md](DEVELOPMENT.md#capturing-a-gateway-key-with-mitmproxy-fallback).
