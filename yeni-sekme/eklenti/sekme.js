// Bandanix new tab: clock, date, search box and the 8 most visited sites.
"use strict";

const AYAR = Object.assign({ accent: "#C8102E", font: "", arkaPlan: "" }, window.BANDANIX || {});
const ADET = 8;
const hasChrome = typeof chrome !== "undefined";

// ---- theme --------------------------------------------------------------------------------
const root = document.documentElement.style;
if (/^#[0-9a-fA-F]{6}$/.test(AYAR.accent)) root.setProperty("--accent", AYAR.accent);
if (AYAR.font) root.setProperty("--font", `"${AYAR.font}", "Ubuntu", "Inter", system-ui, sans-serif`);
if (AYAR.arkaPlan) document.getElementById("arka").style.backgroundImage = `url("${AYAR.arkaPlan}")`;

// ---- clock --------------------------------------------------------------------------------
const saat = document.getElementById("saat");
const tarih = document.getElementById("tarih");
const gunBicim = new Intl.DateTimeFormat("tr-TR", { weekday: "long" });
const ayBicim = new Intl.DateTimeFormat("tr-TR", { day: "numeric", month: "long" });

function saatiYaz() {
  const now = new Date();
  saat.textContent = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`;
  tarih.textContent = `${gunBicim.format(now)}, ${ayBicim.format(now)}`;   // "Salı, 10 Kasım"
  setTimeout(saatiYaz, 60000 - (now.getSeconds() * 1000 + now.getMilliseconds()) + 50);
}
saatiYaz();

// ---- search -------------------------------------------------------------------------------
const ADRES = /^(https?:\/\/)?[^\s/]+\.[a-z]{2,}(:\d+)?(\/\S*)?$/i;

document.getElementById("arama").addEventListener("submit", (event) => {
  event.preventDefault();
  const text = document.getElementById("kutu").value.trim();
  if (!text) return;
  if (ADRES.test(text)) {
    location.href = /^https?:\/\//i.test(text) ? text : `https://${text}`;
  } else if (hasChrome && chrome.search && chrome.search.query) {
    chrome.search.query({ text, disposition: "CURRENT_TAB" });   // Brave's chosen search engine
  } else {
    location.href = `https://search.brave.com/search?q=${encodeURIComponent(text)}`;
  }
});

// ---- most visited -------------------------------------------------------------------------
// how a site is named under its icon: the subdomain when it says more than the domain
// (gemini.google.com → Gemini, uzem.gop.edu.tr → Uzem), proper spelling for well-known sites
const BILINEN = {
  "mail.google.com": "Gmail", "outlook.live.com": "Outlook", "outlook.office.com": "Outlook",
  "drive.google.com": "Drive", "docs.google.com": "Docs", "web.whatsapp.com": "WhatsApp",
  github: "GitHub", youtube: "YouTube", linkedin: "LinkedIn", whatsapp: "WhatsApp",
  chatgpt: "ChatGPT", openai: "OpenAI", stackoverflow: "Stack Overflow", tiktok: "TikTok",
  udemy: "Udemy", claude: "Claude",
};
const ATLA = new Set(["www", "www2", "m", "web", "app", "open", "accounts", "login", "my", "en", "tr"]);

function kisaAd(url) {
  let host;
  try {
    host = new URL(url).hostname.toLowerCase();
  } catch (e) {
    return url;
  }
  if (BILINEN[host]) return BILINEN[host];
  const parts = host.split(".");
  // registrable part: "gop.edu.tr" and "bbc.co.uk" keep three labels, "google.com" two
  const keep = parts.length > 2 && parts[parts.length - 1].length === 2 && parts[parts.length - 2].length <= 3 ? 3 : 2;
  const domain = parts[parts.length - keep] || host;
  const subs = parts.slice(0, Math.max(0, parts.length - keep)).filter((p) => !ATLA.has(p));
  const name = subs.length ? subs[0] : domain;
  if (BILINEN[name]) return BILINEN[name];
  return name.charAt(0).toLocaleUpperCase("tr-TR") + name.slice(1);
}

function ikonAdresi(url) {
  if (!hasChrome || !chrome.runtime || !chrome.runtime.getURL) return "";
  const u = new URL(chrome.runtime.getURL("/_favicon/"));
  u.searchParams.set("pageUrl", url);
  u.searchParams.set("size", "64");
  return u.toString();
}

function kisayol(site, gizle) {
  const a = document.createElement("a");
  a.className = "kisayol";
  a.href = site.url;
  a.title = site.title || site.url;

  const ikon = document.createElement("span");
  ikon.className = "ikon";
  const harf = kisaAd(site.url).charAt(0);
  const src = ikonAdresi(site.url);
  if (src) {
    const img = document.createElement("img");
    img.alt = "";
    img.src = src;
    img.onerror = () => { ikon.textContent = harf; };
    ikon.append(img);
  } else {
    ikon.textContent = harf;
  }

  const ad = document.createElement("span");
  ad.className = "ad";
  ad.textContent = kisaAd(site.url);

  const x = document.createElement("button");
  x.className = "gizle";
  x.type = "button";
  x.title = "Bu siteyi gösterme";
  x.textContent = "×";
  x.addEventListener("click", (event) => {
    event.preventDefault();
    event.stopPropagation();
    gizle(site.url);
  });

  a.append(ikon, ad, x);
  return a;
}

function depoOku(cb) {
  if (hasChrome && chrome.storage && chrome.storage.local) chrome.storage.local.get({ gizli: [] }, (v) => cb(v.gizli || []));
  else cb([]);
}

function depoYaz(gizli) {
  if (hasChrome && chrome.storage && chrome.storage.local) chrome.storage.local.set({ gizli });
}

function siteleriGoster() {
  if (!hasChrome || !chrome.topSites) {
    document.getElementById("bos").hidden = false;
    return;
  }
  chrome.topSites.get((sites) => {
    depoOku((gizli) => {
      const liste = document.getElementById("kisayollar");
      const secilen = (sites || []).filter((s) => !gizli.includes(s.url)).slice(0, ADET);
      liste.replaceChildren(...secilen.map((s) => kisayol(s, (url) => {
        depoYaz([...gizli, url]);
        siteleriGoster();
      })));
      document.getElementById("bos").hidden = secilen.length > 0;
    });
  });
}
siteleriGoster();
