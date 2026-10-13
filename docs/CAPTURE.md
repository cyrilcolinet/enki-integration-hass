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
whichever assistant you use. Fill in the three lines at the top first.

<details>
<summary>Prompt to copy</summary>

```text
I am helping debug an open-source Home Assistant integration for the Enki app
(Leroy Merlin smart home). A maintainer asked me to capture the HTTP request the
Enki phone app sends when I perform one action, using mitmproxy, and to paste it
into a GitHub issue.

My setup:
- Phone: <iPhone or Android, and which OS version>
- Computer: <macOS, Windows or Linux, and which version>
- The action I was asked to capture: <for example "turn the main light of my ceiling fan off">

Please walk me through it one step at a time. Wait for me to tell you a step
worked before giving me the next one, and ask me what I see on screen rather
than assuming. I am not a developer, so name the menus and buttons rather than
describing them.

Cover, in this order: installing mitmproxy on my computer, finding my computer's
address on my Wi-Fi, pointing my phone's Wi-Fi through it, installing and
trusting mitmproxy's certificate on my phone, checking that interception works
at all, filtering the captured requests for the address "adeo", performing the
action once, and reading the request out of the mitmproxy interface.

Two things to know about my phone:
- On iOS, trusting the certificate takes a second step that is easy to miss,
  in Settings under General then About then Certificate Trust Settings.
- On Android 7 and later, apps ignore certificates I install myself, so the
  Enki app's traffic will probably not appear at all. If that is my situation,
  tell me early rather than after an hour, so I can report that instead.

Rules:
- Never ask me for my Enki password, my email, or any access token, and tell me
  not to paste them to you.
- At the end, help me write what to post on the issue: the method and address of
  the request, its body, the status that came back and its body, with my home id
  and device id replaced by <home> and <node> and the Authorization header
  removed. Nothing else is needed.
- If a menu you describe does not exist on my version, ask me what I see instead
  and adapt. Do not insist.
- When I am finished, remind me to turn the proxy off and delete the certificate.
```

</details>

The menus in iOS and Android move between versions, so if the assistant describes something you
cannot find, tell it what is on your screen instead of hunting for the name it used. If its steps
and this page disagree, say so on the issue — it means this page needs updating.

## Capturing a gateway key

Same setup, different goal, and it is a maintainer's errand rather than a reporter's:
see [DEVELOPMENT.md](DEVELOPMENT.md#capturing-a-gateway-key-with-mitmproxy-fallback).
