with open("tam-portfolio/index.html", "w") as f:
    f.write("""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Tam — Personal AI Life OS by Tanmay Agarwal</title>
<meta name="description" content="Voice-first personal AI built on Claude API. Persistent memory, real tool use, proactive behavior. Built from scratch in 4 weeks by Tanmay Agarwal, MS CS Columbia.">
<meta property="og:title" content="Tam — Personal AI Life OS">
<meta property="og:description" content="Not a chatbot. An operating system for your life.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600&family=JetBrains+Mono:wght@400;700&family=Syne:wght@600;700;800&display=swap" rel="stylesheet">
<style>
:root {
  --navy: #0a0f1e; --navy2: #060b18; --indigo: #6366f1;
  --indigo-dim: rgba(99,102,241,0.12); --indigo-border: rgba(99,102,241,0.22);
  --emerald: #10b981; --amber: #f59e0b; --white: rgba(255,255,255,0.87);
  --muted: rgba(255,255,255,0.4);
}
* { box-sizing: border-box; margin: 0; padding: 0; cursor: none !important; }
body {
  background-color: var(--navy); color: var(--white); font-family: 'DM Sans', sans-serif;
  overflow-x: hidden;
}
h1, h2, h3, h4, .syne { font-family: 'Syne', sans-serif; }
.mono { font-family: 'JetBrains Mono', monospace; }
a { color: inherit; text-decoration: none; }
#scroll-progress { position: fixed; top: 0; left: 0; height: 2px; background: var(--indigo); width: 0%; z-index: 9999; }
#cursor { position: fixed; width: 8px; height: 8px; background: var(--indigo); border-radius: 50%; pointer-events: none; z-index: 10000; transform: translate(-50%, -50%); }
#cursor-ring { position: fixed; width: 28px; height: 28px; border: 1px solid var(--indigo); border-radius: 50%; pointer-events: none; z-index: 9999; transform: translate(-50%, -50%); transition: width 0.12s ease, height 0.12s ease; }
#particle-canvas { position: fixed; top: 0; left: 0; width: 100%; height: 100%; pointer-events: none; z-index: 0; }
section { position: relative; z-index: 1; max-width: 1200px; margin: 0 auto; padding: 100px 20px; }
.section-label { display: block; font-family: 'JetBrains Mono', monospace; font-size: 11px; color: var(--muted); margin-bottom: 20px; letter-spacing: 2px; text-transform: uppercase; }
.section-title { font-size: 42px; color: var(--white); margin-bottom: 16px; }
.section-sub { font-size: 18px; color: var(--muted); max-width: 600px; line-height: 1.6; margin-bottom: 60px; }
.card { background: var(--navy2); border: 1px solid var(--indigo-border); border-radius: 10px; padding: 30px; }
.fade-up { opacity: 0; transform: translateY(22px); transition: opacity 0.55s ease, transform 0.55s ease; }
.fade-up.visible { opacity: 1; transform: translateY(0); }
</style></head><body>
""")
