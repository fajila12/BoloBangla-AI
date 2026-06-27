<div align="center">

# 🎙️ BoloBangla AI (বলো বাংলা এআই)

### Windows-এর জন্য বাংলা ও ইংরেজি ভয়েস টাইপিং সফটওয়্যার

কথা বলে যেকোনো অ্যাপে বাংলা লিখুন — Word, Facebook, WhatsApp, Gmail সব জায়গায়

![Version](https://img.shields.io/badge/version-1.2.0-blue)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![License](https://img.shields.io/badge/license-MIT-green)
![Made in Bangladesh](https://img.shields.io/badge/Made%20in-Bangladesh-red)

</div>

---

## ✨ ফিচারসমূহ

- 🎙️ **ভয়েস টাইপিং** — কথা বলে বাংলা ও ইংরেজি টাইপ করুন (key ছাড়াই চলে)
- ✨ **AI Polish** — এলোমেলো লেখা সুন্দর শুদ্ধ বাংলায় সাজায়
- 🖼️ **Image to Text** — ছবি থেকে লেখা বের করে (বাংলা ও ইংরেজি)
- 🔤 **Banglish → বাংলা** — "ami valo achi" → "আমি ভালো আছি"
- 📜 **বিজয় → Unicode** — পুরনো বিজয় ফন্টের লেখা আধুনিক Unicode-এ রূপান্তর
- 🔄 **অনুবাদ** — বাংলা ও ইংরেজি পারস্পরিক অনুবাদ
- ⌨️ **ভার্চুয়াল কিবোর্ড** — রঙিন, ৩ ট্যাব (মূল বর্ণ / যুক্তাক্ষর / কার-চিহ্ন)
- 📋 **সিস্টেম-ওয়াইড** — যেকোনো অ্যাপে কাজ করে
- 🔊 **System Tray** — background-এ চলে, Windows startup-এ auto-start

---

## 🚀 ইনস্টল করার নিয়ম

### প্রয়োজন
- Windows 10 বা 11
- Python 3.10+ ([python.org](https://www.python.org/downloads/) থেকে download করুন)

### ধাপসমূহ

```bash
# 1. Repository clone করুন
git clone https://github.com/USERNAME/BoloBangla-AI.git
cd BoloBangla-AI

# 2. প্রয়োজনীয় library ইনস্টল করুন
pip install -r requirements.txt

# 3. চালু করুন
python bolobangla.py
```

---

## 🔑 AI ফিচার চালু করা (FREE)

ভয়েস টাইপিং key ছাড়াই চলে। AI ফিচারের জন্য একটি **বিনামূল্যের** Groq API key লাগবে:

1. সফটওয়্যারে টুলবারের 🔑 বোতামে ক্লিক করুন
2. [console.groq.com](https://console.groq.com/keys) এ free অ্যাকাউন্ট খুলুন
3. "Create API Key" চেপে key তৈরি করুন
4. key কপি করে সফটওয়্যারে paste করুন → Save

বিস্তারিত নির্দেশনা PDF ম্যানুয়ালে (`BoloBangla_AI_Manual.pdf`) আছে।

---

## ⌨️ শর্টকাট কী

| শর্টকাট | কাজ |
|---------|-----|
| `Ctrl + Shift + B` | বাংলা রেকর্ডিং শুরু/বন্ধ |
| `Ctrl + Shift + E` | ইংরেজি রেকর্ডিং শুরু/বন্ধ |
| `Ctrl + V` | রেকর্ড করা লেখা পেস্ট |

---

## 🛠️ প্রযুক্তি

Python • tkinter • Google Speech Recognition • Groq AI (llama-3.3-70b)

---

## 📄 লাইসেন্স

[MIT License](LICENSE) — অবাধে ব্যবহার, পরিবর্তন ও বিতরণ করুন।

---

<div align="center">

বাংলা ভাষার মানুষের জন্য ❤️ দিয়ে তৈরি

</div>
