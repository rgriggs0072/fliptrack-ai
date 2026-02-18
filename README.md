# 🏠 FlipTrack AI

AI-first property investment tracking for house flippers and rental rehab companies.

## 🚀 Features

- 🎤 **Voice Entry** - Speak your expenses, AI categorizes automatically
- 📸 **Receipt OCR** - Snap a photo, AI extracts all data
- 📥 **Smart Import** - Upload Excel, AI maps and categorizes everything
- 📊 **Real-time Dashboard** - Track CI/M split, budget vs actual, ROI
- 🤖 **AI Categorization** - Never manually categorize again
- ☁️ **Cloud Database** - Snowflake backend, multi-tenant, scalable

## 📦 Installation

```bash
# Clone or create project
cd fliptrack-ai

# Install dependencies
pip install -r requirements.txt

# Setup secrets
cp .streamlit/secrets.toml.template .streamlit/secrets.toml
# Edit .streamlit/secrets.toml with your credentials

# Run the app
streamlit run Home.py
```

## 🔐 Setup

1. **Snowflake** - Already configured (KITUWAH_DB, FLIPTRACK_TENANTS, etc.)
2. **RSA Keys** - Already generated (`fliptrack_private_key.p8`)
3. **Anthropic API** - Get key from https://console.anthropic.com
4. **Secrets** - Copy template and fill in values

## 📁 Project Structure

```
fliptrack-ai/
├─ Home.py                      # Main entry
├─ pages/
│  ├─ 1_📊_Dashboard.py
│  ├─ 2_➕_Add_Expense.py
│  ├─ 3_📥_Import_Data.py      # Excel upload with AI
│  └─ 4_📈_Analytics.py
├─ agents/
│  ├─ excel_import_agent.py    # AI import engine
│  ├─ voice_agent.py
│  └─ receipt_agent.py
└─ utils/
   ├─ snowflake_connection.py
   └─ auth.py
```

## 🎯 Quick Start

1. Run `streamlit run Home.py`
2. Login (will need to create test user first)
3. Go to Import Data
4. Upload `5122_Bonnell_Ave.xlsx`
5. Watch AI categorize everything! 🎉

## 🤖 AI Features

- **Excel Analysis** - AI detects columns automatically
- **Smart Categorization** - 26 categories, AI chooses best fit
- **Vendor Extraction** - Pulls vendor names from descriptions
- **CI/M Classification** - Detects cash vs financed
- **Confidence Scoring** - Shows how sure AI is

## 📝 Next Steps

- [ ] Create first user account
- [ ] Import 5122 Bonnell Ave data
- [ ] Build voice entry agent
- [ ] Build receipt OCR agent
- [ ] Add budget tracking
- [ ] Build analytics dashboard

## 🔧 Tech Stack

- **Frontend**: Streamlit
- **Database**: Snowflake
- **AI**: Anthropic Claude Sonnet 4
- **Auth**: RSA Key Pair
- **Python**: 3.11+

## 📞 Support

Built for Kituwah Properties by the FlipTrack AI team.

---

**FlipTrack AI** - Making property investment tracking effortless with AI 🚀
